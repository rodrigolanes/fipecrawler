"""
Script otimizado para popular o banco de dados com paralelização e cache SQLite local.
Até 10x mais rápido que popular_banco.py tradicional.

Tipos de Veículo FIPE:
- 1 = Carros
- 2 = Motos
- 3 = Caminhões

Códigos de Combustível FIPE:
- 1 = Gasolina
- 2 = Álcool/Etanol
- 3 = Diesel
- 4 = Elétrico
- 5 = Flex
- 6 = Híbrido
- 7 = Gás Natural (GNV)
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Lock, current_thread
from src.config import RETRY_BASE_WAIT, MAX_RETRIES
from src.crawler.fipe_crawler import buscar_marcas_carros, buscar_modelos, buscar_anos_modelo, buscar_tabela_referencia, buscar_modelos_por_ano
from src.cache.fipe_local_cache import FipeLocalCache


class PopularBancoOtimizado:
    """
    Classe para popular o banco de forma otimizada:
    1. Gravação local em SQLite (rápido)
    2. Processamento paralelo (5 marcas simultâneas)
    3. Suporte a carros, motos e caminhões
    """
    
    # Mapeamento de tipos de veículos
    TIPOS_VEICULO = {
        1: {'nome': 'Carros', 'emoji': '🚗'},
        2: {'nome': 'Motos', 'emoji': '🏍️'},
        3: {'nome': 'Caminhões', 'emoji': '🚚'}
    }
    
    def __init__(self, max_workers=5, tipos_veiculo=None):
        self.max_workers = max_workers
        self.semaphore = Semaphore(max_workers)  # Controla concorrência
        self.lock = Lock()  # Thread-safe para stats
                # Tipos de veículo a processar (padrão: todos)
        self.tipos_veiculo = tipos_veiculo if tipos_veiculo else [1, 2, 3]
        # Cache local
        self.cache_local = FipeLocalCache()
        
        # Estatísticas
        self.stats = {
            'tabelas_referencia': 0,
            'marcas': 0,
            'modelos': 0,
            'anos': 0,
            'erros': 0,
            'tempo_api': 0.0,
            'tempo_db_local': 0.0,
            'tempo_delays': 0.0
        }
    
    def processar_marca(self, marca, i, total, tipo_veiculo):
        """
        Processa uma marca em paralelo usando estratégia híbrida inteligente.
        - Se poucos modelos (<50): busca anos por modelo (menos requisições)
        - Se muitos modelos (>=50): busca modelos por ano (evita centenas de requisições)
        
        Args:
            marca: Dicionário com dados da marca
            i: Índice atual
            total: Total de marcas
            tipo_veiculo: Tipo de veículo (1=Carros, 2=Motos, 3=Caminhões)
        """
        with self.semaphore:  # Limita concorrência a max_workers
            codigo_marca = marca['Value']
            nome_marca = marca['Label']
            tipo_info = self.TIPOS_VEICULO.get(tipo_veiculo, {'nome': 'Desconhecido', 'emoji': '❓'})
            
            # Identifica worker (thread)
            worker_id = current_thread().name.replace('ThreadPoolExecutor-', 'W')
            
            print(f"[{worker_id}] [{i}/{total}] {tipo_info['emoji']} Processando: {nome_marca} ({codigo_marca}) - {tipo_info['nome']}")
            
            try:
                # 1. Busca modelos da marca (para decidir estratégia)
                inicio_api = time.time()
                resultado = self._buscar_modelos_com_retry(codigo_marca, nome_marca, worker_id, tipo_veiculo)
                tempo_api = time.time() - inicio_api
                
                with self.lock:
                    self.stats['tempo_api'] += tempo_api
                
                # Delay já implementado em buscar_modelos() no fipe_crawler.py
                
                if not resultado or 'Modelos' not in resultado:
                    print(f"[{worker_id}]     ⚠️ Nenhum modelo encontrado para {nome_marca} ({codigo_marca})")
                    return
                
                modelos_api = resultado['Modelos']
                anos_api = resultado.get('Anos', [])  # Anos disponíveis da marca
                total_modelos = len(modelos_api)
                
                # DEBUG: Mostra informação sobre o retorno da API
                print(f"[{worker_id}]     🔍 API retornou: {total_modelos} modelos, {len(anos_api)} anos")
                
                # 2. Verifica se há modelos sem anos (marca incompleta)
                modelos_cache = self.cache_local.get_modelos_marca_dict(codigo_marca)
                modelos_sem_anos = self.cache_local.get_modelos_sem_anos_marca(codigo_marca)
                
                if modelos_sem_anos:
                    print(f"[{worker_id}]     ⚠️  {len(modelos_sem_anos)} modelos sem anos - REPROCESSANDO")
                    reprocessar = True
                elif modelos_cache and len(modelos_cache) >= total_modelos:
                    print(f"[{worker_id}]     ✅ Marca completa ({total_modelos} modelos) - pulando")
                    return
                else:
                    print(f"[{worker_id}]     🆕 Marca nova/incompleta - processando")
                    reprocessar = False
                
                # 3. DECISÃO INTELIGENTE: qual estratégia usar?
                # Compara diretamente: modelos vs combinações de anos da API
                # Escolhe o que tiver MENOS requisições
                
                total_combinacoes_anos = len(anos_api)
                
                if total_modelos <= total_combinacoes_anos:
                    # Menos modelos que combinações de anos: busca POR MODELO
                    print(f"[{worker_id}]     📊 {total_modelos} modelos vs {total_combinacoes_anos} combinações → Estratégia: ANOS POR MODELO")
                    self._processar_por_modelo(codigo_marca, nome_marca, modelos_api, modelos_cache, modelos_sem_anos, worker_id, tipo_veiculo)
                else:
                    # Menos combinações de anos que modelos: busca POR ANO
                    print(f"[{worker_id}]     📊 {total_modelos} modelos vs {total_combinacoes_anos} combinações → Estratégia: MODELOS POR ANO")
                    self._processar_por_ano(codigo_marca, nome_marca, anos_api, worker_id, tipo_veiculo)
                
                # Delay entre marcas (2.0s fixo)
                inicio_delay = time.time()
                time.sleep(2.0)
                tempo_delay = time.time() - inicio_delay
                
                with self.lock:
                    self.stats['tempo_delays'] += tempo_delay
            
            except Exception as e:
                print(f"[{worker_id}]     ❌ Erro ao processar {nome_marca} ({codigo_marca}): {e}")
                with self.lock:
                    self.stats['erros'] += 1
                print()
    
    def _processar_por_modelo(self, codigo_marca, nome_marca, modelos_api, modelos_cache, modelos_sem_anos, worker_id, tipo_veiculo):
        """
        Estratégia 1: Busca anos para cada modelo.
        Mais eficiente quando há poucos modelos (<50).
        """
        # Identifica modelos novos ou que precisam reprocessar
        codigos_cache = set(modelos_cache.keys())
        codigos_sem_anos = set(str(cod) for cod in modelos_sem_anos)  # Modelos que precisam reprocessar
        
        # Prioriza modelos sem anos, depois novos modelos
        modelos_processar = [m for m in modelos_api if str(m['Value']) not in codigos_cache or str(m['Value']) in codigos_sem_anos]
        
        if not modelos_processar:
            modelos_processar = modelos_api  # Reprocessa todos se houver problemas
        
        # Salva modelos
        inicio_db = time.time()
        self.cache_local.save_modelos(modelos_processar, codigo_marca, tipo_veiculo)
        tempo_db = time.time() - inicio_db
        
        with self.lock:
            self.stats['modelos'] += len(modelos_processar)
            self.stats['tempo_db_local'] += tempo_db
        
        if modelos_sem_anos:
            print(f"[{worker_id}]     🔄 {len(modelos_processar)} modelos reprocessados (estavam sem anos)")
        else:
            print(f"[{worker_id}]     💾 {len(modelos_processar)} modelos salvos")
        print(f"[{worker_id}]     📅 Buscando anos de cada modelo...")
        
        anos_total = 0
        
        for j, modelo in enumerate(modelos_processar, 1):
            codigo_modelo = modelo['Value']
            nome_modelo = modelo['Label']
            
            # Progresso a cada 20 modelos
            if j % 20 == 0:
                print(f"[{worker_id}]         Progresso: {j}/{len(modelos_processar)} modelos...")
            
            try:
                # Busca anos da API com retry
                inicio_anos = time.time()
                anos = self._buscar_anos_com_retry(codigo_marca, codigo_modelo, worker_id, nome_modelo, tipo_veiculo)
                tempo_anos = time.time() - inicio_anos
                
                with self.lock:
                    self.stats['tempo_api'] += tempo_anos
                
                if anos:
                    # Salva localmente
                    inicio_db = time.time()
                    self.cache_local.save_anos_modelo(anos, codigo_marca, codigo_modelo, tipo_veiculo)
                    tempo_db = time.time() - inicio_db
                    
                    with self.lock:
                        self.stats['anos'] += len(anos)
                        self.stats['tempo_db_local'] += tempo_db
                    
                    anos_total += len(anos)
                
                # Delay já implementado em buscar_anos_modelo() no fipe_crawler.py
            
            except Exception as e:
                print(f"[{worker_id}]         ⚠️ Erro: {nome_modelo} ({codigo_modelo}) - {e}")
                with self.lock:
                    self.stats['erros'] += 1
                continue
        
        print(f"[{worker_id}]     ✅ {len(modelos_processar)} modelos, {anos_total} anos salvos")
        print()
    
    def _processar_por_ano(self, codigo_marca, nome_marca, anos_api, worker_id, tipo_veiculo):
        """
        Estratégia 2: Busca modelos para cada ano/combustível.
        Mais eficiente quando há muitos modelos (>=50).
        """
        from src.crawler.fipe_crawler import buscar_modelos_por_ano
        
        print(f"[{worker_id}]     📅 Buscando modelos por ano/combustível...")
        
        # OTIMIZAÇÃO: Usa as combinações ano+combustível EXATAS da API
        # Cada item em anos_api já é uma combinação válida que existe
        if anos_api and len(anos_api) > 0:
            # API retorna combinações prontas: [{'Value': '2024-1', 'Label': '2024 Gasolina'}]
            combinacoes_validas = anos_api
            print(f"[{worker_id}]     ✅ {len(combinacoes_validas)} combinações ano+combustível da API")
        else:
            # Fallback: se API não retornar anos, gera combinações padrão
            print(f"[{worker_id}]     ⚠️  API não retornou anos, gerando combinações padrão")
            anos_padrao = ["32000"]  # Zero Km
            ano_atual = 2025
            for ano in range(ano_atual, ano_atual - 30, -1):
                anos_padrao.append(str(ano))
            
            combustiveis_padrao = {
                1: "Gasolina",
                2: "Álcool/Etanol", 
                3: "Diesel",
                4: "Elétrico",
                5: "Flex",
                6: "Híbrido",
                7: "Gás Natural"
            }
            
            # Gera produto cartesiano apenas no fallback
            combinacoes_validas = []
            for ano in anos_padrao:
                for cod_comb, nome_comb in combustiveis_padrao.items():
                    ano_label = "Zero Km" if ano == "32000" else ano
                    combinacoes_validas.append({
                        'Value': f"{ano}-{cod_comb}",
                        'Label': f"{ano_label} {nome_comb}"
                    })
            
            print(f"[{worker_id}]     📅 {len(combinacoes_validas)} combinações padrão geradas")
        
        modelos_encontrados = {}  # {codigo: {'Value': X, 'Label': Y}}
        relacionamentos = []  # [(codigo_modelo, codigo_ano_combustivel)]
        total_requisicoes = 0
        
        for combinacao in combinacoes_validas:
            try:
                # Extrai ano e combustível da combinação (Value: "2024-1")
                codigo_ano_completo = combinacao['Value']
                label_completo = combinacao['Label']
                
                try:
                    ano_modelo, codigo_combustivel = codigo_ano_completo.split('-')
                    codigo_combustivel = int(codigo_combustivel)
                except (ValueError, AttributeError):
                    print(f"[{worker_id}]         ⚠️ Formato inválido: {codigo_ano_completo}")
                    continue
                
                # Busca modelos desta combinação específica
                inicio_api = time.time()
                modelos = self._buscar_modelos_por_ano_com_retry(
                    codigo_marca=codigo_marca,
                    ano_modelo=ano_modelo,
                    codigo_combustivel=codigo_combustivel,
                    nome_marca=nome_marca,
                    tipo_veiculo=tipo_veiculo,
                    label_completo=label_completo,
                    worker_id=worker_id
                )
                tempo_api = time.time() - inicio_api
                total_requisicoes += 1
                    
                with self.lock:
                    self.stats['tempo_api'] += tempo_api
                
                if modelos:
                    # Valida estrutura dos dados
                    if isinstance(modelos, str):
                        print(f"[{worker_id}]         ⚠️ API retornou string em {label_completo}")
                        continue
                    
                    for modelo in modelos:
                        # Valida que modelo é dict
                        if not isinstance(modelo, dict):
                            continue
                        
                        if 'Value' not in modelo or 'Label' not in modelo:
                            continue
                        
                        codigo_modelo = str(modelo['Value'])
                        
                        # Adiciona modelo (se ainda não existe)
                        if codigo_modelo not in modelos_encontrados:
                            modelos_encontrados[codigo_modelo] = modelo
                        
                        # Adiciona relacionamento usando o código ano+combustível completo
                        relacionamentos.append((codigo_modelo, codigo_ano_completo, label_completo))
                
                # Delay já implementado em buscar_modelos_por_ano() no fipe_crawler.py
            
            except Exception as e:
                # Erros não-429 (já que retry interno trata 429)
                print(f"[{worker_id}]         ⚠️ Erro inesperado em {nome_marca} ({codigo_marca}) {label_completo}: {e}")
                with self.lock:
                    self.stats['erros'] += 1
        
        # Salva modelos no cache
        if modelos_encontrados:
            print(f"[{worker_id}]     💾 Salvando {len(modelos_encontrados)} modelos...")
            inicio_db = time.time()
            
            modelos_lista = list(modelos_encontrados.values())
            self.cache_local.save_modelos(modelos_lista, codigo_marca, tipo_veiculo)
            
            tempo_db = time.time() - inicio_db
            
            with self.lock:
                self.stats['modelos'] += len(modelos_lista)
                self.stats['tempo_db_local'] += tempo_db
        
        # Salva relacionamentos anos/combustível
        if relacionamentos:
            print(f"[{worker_id}]     💾 Salvando {len(relacionamentos)} relacionamentos...")
            inicio_db = time.time()
            
            # Prepara dados para save_anos_modelo
            for codigo_modelo, codigo_ano_completo, label_completo in relacionamentos:
                anos_data = [{
                    'Value': codigo_ano_completo,
                    'Label': label_completo
                }]
                self.cache_local.save_anos_modelo(anos_data, codigo_marca, int(codigo_modelo), tipo_veiculo)
            
            tempo_db = time.time() - inicio_db
            
            with self.lock:
                self.stats['anos'] += len(relacionamentos)
                self.stats['tempo_db_local'] += tempo_db
        
        # Calcula economia de requisições
        requisicoes_por_modelo = len(modelos_encontrados)  # Se fosse buscar anos de cada modelo
        economia = requisicoes_por_modelo - total_requisicoes
        economia_perc = (economia / requisicoes_por_modelo * 100) if requisicoes_por_modelo > 0 else 0
        
        print(f"[{worker_id}]     ✅ {len(modelos_encontrados)} modelos, {len(relacionamentos)} relacionamentos")
        print(f"[{worker_id}]     📊 {total_requisicoes} requisições (economizou {economia} req, {economia_perc:.1f}%)")
        print()
    
    def _buscar_modelos_com_retry(self, codigo_marca, nome_marca, worker_id, tipo_veiculo=1, max_retries=MAX_RETRIES):
        """Busca modelos com retry em caso de rate limiting"""
        for retry in range(max_retries):
            try:
                return buscar_modelos(codigo_marca, tipo_veiculo, nome_marca)
            except Exception as e:
                if "429" in str(e) or "too many" in str(e).lower():
                    if retry < max_retries - 1:
                        wait_time = RETRY_BASE_WAIT * (2 ** retry)
                        print(f"[{worker_id}]     ⚠️  Rate limit ao buscar modelos de {nome_marca} ({codigo_marca}). Aguardando {wait_time}s... (tentativa {retry+1}/{max_retries})")
                        time.sleep(wait_time)
                        with self.lock:
                            self.stats['tempo_delays'] += wait_time
                    else:
                        # Após tentativas, desiste e retorna None
                        print(f"[{worker_id}]     ❌ Rate limit persistente em {nome_marca} ({codigo_marca}) após {max_retries} tentativas")
                        return None
                else:
                    raise
        return None
    
    def _buscar_modelos_por_ano_com_retry(self, codigo_marca, ano_modelo, codigo_combustivel, nome_marca, tipo_veiculo, label_completo, worker_id, max_retries=MAX_RETRIES):
        """Busca modelos por ano com retry em caso de rate limiting"""
        for retry in range(max_retries):
            try:
                return buscar_modelos_por_ano(
                    codigo_marca=codigo_marca,
                    ano_modelo=ano_modelo,
                    codigo_combustivel=codigo_combustivel,
                    nome_marca=nome_marca,
                    tipo_veiculo=tipo_veiculo
                )
            except Exception as e:
                if "429" in str(e) or "too many" in str(e).lower():
                    if retry < max_retries - 1:
                        wait_time = RETRY_BASE_WAIT * (2 ** retry)
                        print(f"[{worker_id}]         ⚠️  Rate limit em {nome_marca} ({codigo_marca}) {label_completo}. Aguardando {wait_time}s... (tentativa {retry+1}/{max_retries})")
                        time.sleep(wait_time)
                        with self.lock:
                            self.stats['tempo_delays'] += wait_time
                    else:
                        # Após tentativas, desiste e retorna lista vazia
                        print(f"[{worker_id}]         ❌ Rate limit persistente em {nome_marca} ({codigo_marca}) {label_completo} após {max_retries} tentativas")
                        return []
                else:
                    raise
        return []
    
    def _buscar_anos_com_retry(self, codigo_marca, codigo_modelo, worker_id, nome_modelo="", tipo_veiculo=1, max_retries=MAX_RETRIES):
        """Busca anos com retry em caso de rate limiting"""
        for retry in range(max_retries):
            try:
                return buscar_anos_modelo(codigo_marca, codigo_modelo, tipo_veiculo, nome_modelo)
            except Exception as e:
                if "429" in str(e) or "too many" in str(e).lower():
                    if retry < max_retries - 1:
                        wait_time = RETRY_BASE_WAIT * (2 ** retry)
                        modelo_info = f"{nome_modelo} ({codigo_modelo})" if nome_modelo else codigo_modelo
                        print(f"[{worker_id}]         ⚠️ Rate limit em {modelo_info}. Aguardando {wait_time}s... (tentativa {retry+1}/{max_retries})")
                        time.sleep(wait_time)
                        with self.lock:
                            self.stats['tempo_delays'] += wait_time
                    else:
                        # Após tentativas, desiste e propaga exceção
                        print(f"[{worker_id}]         ❌ Rate limit persistente em {modelo_info} após {max_retries} tentativas")
                        raise
                else:
                    raise
        return None
    
    def popular(self):
        """Execução principal do processo otimizado"""
        print("=" * 70)
        print("FIPE CRAWLER - População Otimizada (SQLite + Paralelo)")
        print("=" * 70)
        print()
        print(f"⚙️  Configuração: {self.max_workers} workers paralelos")
        print(f"💾 Cache persistente: fipe_local.db")
        print()
        
        try:
            # Estatísticas do cache local
            stats_local = self.cache_local.get_estatisticas()
            print("♻️  CACHE LOCAL")
            print("-" * 70)
            print(f"📊 Dados em cache:")
            print(f"   • Marcas: {stats_local['marcas']}")
            print(f"   • Modelos: {stats_local['modelos']}")
            print(f"   • Anos/Combustível: {stats_local['anos_combustivel']}")
            print(f"   • Relacionamentos: {stats_local['modelos_anos']}")
            print()
            
            # 1. Buscar e salvar tabelas de referência (sempre atualizar)
            print("📊 ETAPA 1/3: Atualizando tabelas de referência...")
            print("-" * 70)
            tabelas = buscar_tabela_referencia()
            
            if tabelas:
                for tabela in tabelas:
                    self.cache_local.save_tabela_referencia(tabela['Codigo'], tabela['Mes'])
                    self.stats['tabelas_referencia'] += 1
                
                print(f"✅ {self.stats['tabelas_referencia']} tabelas carregadas")
                print(f"   Mais recente: {tabelas[0]['Mes']} (código {tabelas[0]['Codigo']})\n")
            
            # 2. Processar cada tipo de veículo
            for tipo_veiculo in self.tipos_veiculo:
                tipo_info = self.TIPOS_VEICULO[tipo_veiculo]
                
                print(f"\n{tipo_info['emoji']} ETAPA 2/{len(self.tipos_veiculo)+1}: Processando {tipo_info['nome'].upper()}")
                print("=" * 70)
                
                # 2.1. Buscar marcas da API
                print(f"📊 Buscando marcas de {tipo_info['nome'].lower()}...")
                print("-" * 70)
                inicio_api = time.time()
                marcas_api = buscar_marcas_carros(tipo_veiculo)
                self.stats['tempo_api'] += time.time() - inicio_api
                
                if not marcas_api:
                    print(f"⚠️  Nenhuma marca de {tipo_info['nome'].lower()} encontrada\n")
                    continue
                
                # Salva novas marcas no cache local
                inicio_db = time.time()
                self.cache_local.save_marcas(marcas_api, tipo_veiculo)
                self.stats['tempo_db_local'] += time.time() - inicio_db
                
                self.stats['marcas'] += len(marcas_api)
                print(f"✅ {len(marcas_api)} marcas de {tipo_info['nome'].lower()} encontradas")
                print(f"ℹ️  Todas as marcas serão verificadas para completude\n")
                
                # 2.2. Processar TODAS as marcas deste tipo
                print(f"📊 Verificando e atualizando modelos de {tipo_info['nome'].upper()} (PARALELO)...")
                print("-" * 70)
                print(f"🚀 Processando {min(self.max_workers, len(marcas_api))} marcas simultaneamente...")
                print(f"📦 Total a verificar: {len(marcas_api)} marcas")
                print(f"ℹ️  Processará apenas modelos novos de cada marca\n")
                
                inicio_paralelo = time.time()
                
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = [
                        executor.submit(self.processar_marca, marca, i, len(marcas_api), tipo_veiculo)
                        for i, marca in enumerate(marcas_api, 1)
                    ]
                    
                    # Aguarda todas as threads terminarem
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            print(f"❌ Erro em thread: {e}")
                            self.stats['erros'] += 1
                
                tempo_paralelo = time.time() - inicio_paralelo
                print(f"\n✅ {tipo_info['nome']} concluído em {tempo_paralelo/60:.1f} minutos")
                print()
            
            # Resumo final
            self._imprimir_resumo()
        
        except KeyboardInterrupt:
            print("\n\n⚠️ Processo interrompido pelo usuário")
            self._imprimir_estatisticas_parciais()
        
        except Exception as e:
            print(f"\n\n❌ Erro fatal: {e}")
            import traceback
            traceback.print_exc()
            self._imprimir_estatisticas_parciais()
        
        finally:
            # NÃO fecha conexão - mantém SQLite persistente
            pass
    
    def _imprimir_resumo(self):
        """Imprime resumo final com análise de performance"""
        print("=" * 70)
        print("✅ POPULAÇÃO DO BANCO CONCLUÍDA!")
        print("=" * 70)
        print()
        print(f"📊 ESTATÍSTICAS FINAIS:")
        print(f"   • Tabelas de referência: {self.stats['tabelas_referencia']}")
        print(f"   • Marcas: {self.stats['marcas']}")
        print(f"   • Modelos: {self.stats['modelos']}")
        print(f"   • Anos/Combustível: {self.stats['anos']}")
        print(f"   • Erros: {self.stats['erros']}")
        print()
        
        # Tempos
        tempo_total = (self.stats['tempo_api'] + self.stats['tempo_db_local'] + 
                      self.stats['tempo_delays'])
        
        print(f"⏱️  TEMPO:")
        print(f"   • API FIPE: {self.stats['tempo_api']:.1f}s ({self.stats['tempo_api']/60:.1f} min)")
        print(f"   • SQLite local: {self.stats['tempo_db_local']:.1f}s ({self.stats['tempo_db_local']/60:.1f} min)")
        print(f"   • Delays (rate limiting): {self.stats['tempo_delays']:.1f}s ({self.stats['tempo_delays']/60:.1f} min)")
        print(f"   • Total: {tempo_total:.1f}s ({tempo_total/60:.1f} min)")
        print()
        
        # Análise
        if tempo_total > 0:
            perc_api = (self.stats['tempo_api'] / tempo_total) * 100
            perc_db = (self.stats['tempo_db_local'] / tempo_total) * 100
            perc_delays = (self.stats['tempo_delays'] / tempo_total) * 100
            
            print(f"📈 ANÁLISE DE PERFORMANCE:")
            print(f"   • API FIPE: {perc_api:.1f}%")
            print(f"   • SQLite local: {perc_db:.1f}%")
            print(f"   • Delays: {perc_delays:.1f}%")
            print()
            
            print(f"🚀 GANHO DE PERFORMANCE:")
            print(f"   • SQLite local {self.stats['modelos'] + self.stats['anos']} gravações instantâneas")
            print(f"   • Paralelização: {self.max_workers}x mais rápido")
        
        
        print()
        print("💾 Todos os dados foram salvos no SQLite (fipe_local.db)!")
        print()
    
    def _imprimir_estatisticas_parciais(self):
        """Imprime estatísticas parciais em caso de interrupção"""
        print(f"\n📊 Dados parciais salvos no SQLite:")
        stats_local = self.cache_local.get_estatisticas()
        print(f"   • Tabelas referência: {stats_local['tabelas_referencia']}")
        print(f"   • Marcas: {stats_local['marcas']}")
        print(f"   • Modelos: {stats_local['modelos']}")
        print(f"   • Anos/Combustível: {stats_local['anos_combustivel']}")
        print(f"   • Relacionamentos: {stats_local['modelos_anos']}")
        print()
        print("💡 Execute novamente para continuar ou consulte fipe_local.db")
        print()


def main():
    print()
    print("⚠️  PROCESSO OTIMIZADO: SQLite Local + Paralelização")
    print("⚠️  Até 10x mais rápido que o modo tradicional!")
    print("⚠️  Tempo estimado: 15-30 minutos por tipo de veículo")
    print("⚠️  Resultado: Banco SQLite (fipe_local.db)")
    print()
    
    resposta = input("Deseja continuar? (s/n): ")
    
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        print()
        
        # Escolha de tipos de veículo
        print("📋 Tipos de veículo disponíveis:")
        print("   1. 🚗 Carros")
        print("   2. 🏍️  Motos")
        print("   3. 🚚 Caminhões")
        print()
        print("Escolha os tipos a processar:")
        tipos_input = input("Digite os números separados por vírgula (ex: 1,2,3) ou Enter para todos: ")
        
        if tipos_input.strip():
            try:
                tipos_veiculo = [int(t.strip()) for t in tipos_input.split(',') if t.strip() in ['1', '2', '3']]
                if not tipos_veiculo:
                    print("⚠️  Nenhum tipo válido selecionado. Usando todos.")
                    tipos_veiculo = [1, 2, 3]
            except:
                print("⚠️  Entrada inválida. Usando todos os tipos.")
                tipos_veiculo = [1, 2, 3]
        else:
            tipos_veiculo = [1, 2, 3]
        
        # Mostra seleção
        tipos_nomes = {1: "Carros", 2: "Motos", 3: "Caminhões"}
        tipos_selecionados = [tipos_nomes[t] for t in tipos_veiculo]
        print(f"\n✅ Tipos selecionados: {', '.join(tipos_selecionados)}")
        print()
        
        # Configuração de workers (padrão: 5)
        workers_input = input("Número de workers paralelos (padrão 5, máximo 10): ")
        try:
            workers = int(workers_input) if workers_input else 5
            workers = min(max(workers, 1), 10)  # Entre 1 e 10
        except:
            workers = 5
        
        print()
        populator = PopularBancoOtimizado(max_workers=workers, tipos_veiculo=tipos_veiculo)
        populator.popular()
    else:
        print("\n❌ Operação cancelada pelo usuário.")


if __name__ == "__main__":
    main()
