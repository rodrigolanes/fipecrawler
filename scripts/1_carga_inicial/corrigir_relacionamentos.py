"""
Script para repopular relacionamentos de veículos (carros, motos e caminhões).
Útil após correções de bugs ou para preencher relacionamentos faltantes.
Tipos: 1 (Carros), 2 (Motos), 3 (Caminhões)
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para permitir imports
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

import time
from src.config import get_delay_padrao, DELAY_RATE_LIMIT_429, RETRY_BASE_WAIT, MAX_RETRIES
from src.crawler.fipe_crawler import buscar_marcas_carros, buscar_modelos, buscar_anos_modelo
from src.cache.fipe_local_cache import FipeLocalCache


def buscar_marcas_com_retry(tipo_veiculo, stats=None, max_retries=MAX_RETRIES):
    """Busca marcas com retry em caso de rate limiting"""
    for retry in range(max_retries):
        try:
            return buscar_marcas_carros(tipo_veiculo)
        except Exception as e:
            if "429" in str(e) or "too many" in str(e).lower():
                if stats:
                    stats['retries_429'] += 1
                if retry < max_retries - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)  # 5s, 10s, 20s (baseado em config)
                    print(f"⚠️  Rate limit ao buscar marcas. Aguardando {wait_time}s... (tentativa {retry+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Rate limit persistente ao buscar marcas após {max_retries} tentativas")
                    return None
            else:
                raise
    return None


def buscar_modelos_com_retry(codigo_marca, tipo_veiculo, nome_marca, stats=None, max_retries=MAX_RETRIES):
    """Busca modelos com retry em caso de rate limiting"""
    for retry in range(max_retries):
        try:
            return buscar_modelos(codigo_marca, tipo_veiculo, nome_marca)
        except Exception as e:
            if "429" in str(e) or "too many" in str(e).lower():
                if stats:
                    stats['retries_429'] += 1
                if retry < max_retries - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)
                    print(f"    ⚠️  Rate limit ao buscar modelos de {nome_marca} ({codigo_marca}). Aguardando {wait_time}s... (tentativa {retry+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"    ❌ Rate limit persistente em {nome_marca} ({codigo_marca}) após {max_retries} tentativas")
                    return None
            else:
                raise
    return None


def buscar_anos_com_retry(codigo_marca, codigo_modelo, tipo_veiculo, nome_modelo, stats=None, max_retries=MAX_RETRIES):
    """Busca anos com retry em caso de rate limiting"""
    for retry in range(max_retries):
        try:
            return buscar_anos_modelo(codigo_marca, codigo_modelo, tipo_veiculo, nome_modelo)
        except Exception as e:
            if "429" in str(e) or "too many" in str(e).lower():
                if stats:
                    stats['retries_429'] += 1
                if retry < max_retries - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)
                    modelo_info = f"{nome_modelo} ({codigo_modelo})" if nome_modelo else codigo_modelo
                    print(f"      ⚠️ Rate limit em {modelo_info}. Aguardando {wait_time}s... (tentativa {retry+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    modelo_info = f"{nome_modelo} ({codigo_modelo})" if nome_modelo else codigo_modelo
                    print(f"      ❌ Rate limit persistente em {modelo_info} após {max_retries} tentativas")
                    raise
            else:
                raise
    return None


def buscar_modelos_por_ano_com_retry(codigo_marca, ano_modelo, codigo_combustivel, nome_marca, tipo_veiculo, label_completo, stats=None, max_retries=MAX_RETRIES):
    """Busca modelos por ano com retry em caso de rate limiting"""
    from src.crawler.fipe_crawler import buscar_modelos_por_ano
    
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
                if stats:
                    stats['retries_429'] += 1
                if retry < max_retries - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)
                    print(f"      ⚠️ Rate limit em {nome_marca} ({codigo_marca}) {label_completo}. Aguardando {wait_time}s... (tentativa {retry+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    print(f"      ❌ Rate limit persistente em {nome_marca} ({codigo_marca}) {label_completo} após {max_retries} tentativas")
                    return []
            else:
                raise
    return []


def processar_por_modelo(cache, codigo_marca, nome_marca, modelos, stats, tipo_veiculo):
    """
    Estratégia 1: Busca anos para cada modelo.
    Mais eficiente quando há poucos modelos.
    """
    print(f"  📅 Buscando anos de cada modelo...")
    
    relacionamentos_marca = 0
    
    for j, modelo in enumerate(modelos, 1):
        try:
            codigo_modelo = int(modelo['Value'])
            nome_modelo = modelo['Label']
            
            # Busca anos do modelo
            anos = buscar_anos_com_retry(codigo_marca, codigo_modelo, tipo_veiculo, nome_modelo, stats)
            
            if anos:
                # Salva relacionamentos com tipo_veiculo
                cache.save_anos_modelo(anos, codigo_marca, codigo_modelo, tipo_veiculo)
                stats['relacionamentos_criados'] += len(anos)
                relacionamentos_marca += len(anos)
                
                if j % 10 == 0:
                    print(f"    Progresso: {j}/{len(modelos)} modelos ({stats['relacionamentos_criados']} relacionamentos)")
            
            # Delay já implementado em buscar_anos_modelo() no fipe_crawler.py
        
        except Exception as e:
            print(f"    ❌ Erro no modelo {j}: {e}")
            stats['erros'] += 1
            time.sleep(1.0)
    
    return relacionamentos_marca


def processar_por_ano(cache, codigo_marca, nome_marca, anos_api, stats, tipo_veiculo):
    """
    Estratégia 2: Busca modelos para cada ano/combustível.
    Mais eficiente quando há muitos modelos.
    """
    print(f"  📅 Buscando modelos por ano/combustível...")
    
    modelos_encontrados = {}  # {codigo: {'Value': X, 'Label': Y}}
    relacionamentos = []  # [(codigo_modelo, codigo_ano_combustivel, label)]
    
    for combinacao in anos_api:
        try:
            # Extrai ano e combustível da combinação (Value: "2024-1")
            codigo_ano_completo = combinacao['Value']
            label_completo = combinacao['Label']
            
            try:
                ano_modelo, codigo_combustivel = codigo_ano_completo.split('-')
                codigo_combustivel = int(codigo_combustivel)
            except (ValueError, AttributeError):
                print(f"    ⚠️ Formato inválido: {codigo_ano_completo}")
                continue
            
            # Busca modelos desta combinação específica
            modelos = buscar_modelos_por_ano_com_retry(
                codigo_marca=codigo_marca,
                ano_modelo=ano_modelo,
                codigo_combustivel=codigo_combustivel,
                nome_marca=nome_marca,
                tipo_veiculo=tipo_veiculo,
                label_completo=label_completo,
                stats=stats
            )
            
            if modelos:
                # Valida estrutura dos dados
                if isinstance(modelos, str):
                    print(f"    ⚠️ API retornou string em {label_completo}")
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
                    
                    # Adiciona relacionamento
                    relacionamentos.append((codigo_modelo, codigo_ano_completo, label_completo))
            
            # Delay entre requisições (2.0s fixo)
            time.sleep(2.0)
        
        except Exception as e:
            print(f"    ⚠️ Erro em {nome_marca} ({codigo_marca}) {label_completo}: {e}")
            stats['erros'] += 1
    
    # Salva modelos no cache
    if modelos_encontrados:
        print(f"  💾 Salvando {len(modelos_encontrados)} modelos...")
        modelos_lista = list(modelos_encontrados.values())
        cache.save_modelos(modelos_lista, codigo_marca, tipo_veiculo)
        stats['modelos_processados'] += len(modelos_lista)
    
    # Salva relacionamentos anos/combustível
    if relacionamentos:
        print(f"  💾 Salvando {len(relacionamentos)} relacionamentos...")
        for codigo_modelo, codigo_ano_completo, label_completo in relacionamentos:
            anos_data = [{
                'Value': codigo_ano_completo,
                'Label': label_completo
            }]
            cache.save_anos_modelo(anos_data, codigo_marca, int(codigo_modelo), tipo_veiculo)
        
        stats['relacionamentos_criados'] += len(relacionamentos)
    
    return len(relacionamentos)


def repopular_tipo(tipo_veiculo: int, nome_tipo: str, codigo_marca_inicio: str = None):
    """
    Repopula relacionamentos de um tipo específico de veículo.
    
    Args:
        tipo_veiculo: 1 para carros, 2 para motos, 3 para caminhões
        nome_tipo: Nome legível do tipo (ex: "Carros", "Motos", "Caminhões")
        codigo_marca_inicio: Código da marca para começar (pula marcas anteriores)
    """
    cache = FipeLocalCache()
    
    print("=" * 80)
    print(f"FIPE CRAWLER - Repopular Relacionamentos de {nome_tipo}")
    print("=" * 80)
    print()
    
    # Estatísticas
    stats = {
        'marcas_processadas': 0,
        'modelos_processados': 0,
        'relacionamentos_criados': 0,
        'erros': 0,
        'retries_429': 0,
        'tempo_total': 0
    }
    
    inicio_total = time.time()
    
    try:
        # 1. Busca marcas com retry
        print(f"📊 Buscando marcas de {nome_tipo}...")
        print("-" * 80)
        marcas = buscar_marcas_com_retry(tipo_veiculo, stats)
        
        if not marcas:
            print(f"❌ Nenhuma marca encontrada para {nome_tipo}")
            return
        
        # Delay após buscar marcas
        time.sleep(2.0)
        
        total_marcas = len(marcas)
        print(f"✅ {total_marcas} marcas encontradas\n")
        
        # 2. Processa cada marca
        print(f"🔄 Processando modelos e anos de {nome_tipo}...")
        print("-" * 80)
        
        for i, marca in enumerate(marcas, 1):
            codigo_marca = marca['Value']
            nome_marca = marca['Label']
            
            # Pula marcas até chegar no código de início (se especificado)
            if codigo_marca_inicio and codigo_marca != codigo_marca_inicio:
                if i == 1:  # Mostra mensagem apenas na primeira iteração
                    print(f"⏩ Pulando marcas até {codigo_marca_inicio}...")
                continue
            elif codigo_marca_inicio and codigo_marca == codigo_marca_inicio:
                print(f"✅ Iniciando da marca {nome_marca} ({codigo_marca})\n")
                codigo_marca_inicio = None  # Desativa o filtro após encontrar
            
            print(f"[{i}/{total_marcas}] {nome_marca} ({codigo_marca})")
            
            try:
                # 2.1 Busca modelos da marca
                resultado_modelos = buscar_modelos_com_retry(codigo_marca, tipo_veiculo, nome_marca, stats)
                
                if not resultado_modelos or 'Modelos' not in resultado_modelos:
                    print(f"  ⚠️ Nenhum modelo encontrado")
                    continue
                
                modelos = resultado_modelos['Modelos']
                anos_api = resultado_modelos.get('Anos', [])
                total_modelos = len(modelos)
                total_combinacoes = len(anos_api)
                
                print(f"  🔍 API retornou: {total_modelos} modelos, {total_combinacoes} combinações ano+combustível")
                
                # Delay após buscar modelos
                time.sleep(2.0)
                
                # 2.2 DECISÃO INTELIGENTE: qual estratégia usar?
                # Compara modelos vs combinações ano+combustível
                # Escolhe o que tiver MENOS requisições
                
                relacionamentos_marca = 0
                
                if total_modelos <= total_combinacoes:
                    # Menos modelos que combinações: busca POR MODELO
                    print(f"  📊 {total_modelos} modelos vs {total_combinacoes} combinações → Estratégia: ANOS POR MODELO")
                    relacionamentos_marca = processar_por_modelo(cache, codigo_marca, nome_marca, modelos, stats, tipo_veiculo)
                    stats['modelos_processados'] += total_modelos
                else:
                    # Menos combinações que modelos: busca POR ANO
                    print(f"  📊 {total_modelos} modelos vs {total_combinacoes} combinações → Estratégia: MODELOS POR ANO")
                    relacionamentos_marca = processar_por_ano(cache, codigo_marca, nome_marca, anos_api, stats, tipo_veiculo)
                
                stats['marcas_processadas'] += 1
                print(f"  ✅ Concluído: {relacionamentos_marca} relacionamentos salvos\n")
                
                # Delay entre marcas (2.0s fixo)
                time.sleep(2.0)
            
            except Exception as e:
                print(f"  ❌ Erro na marca {codigo_marca}: {e}\n")
                stats['erros'] += 1
                time.sleep(2.0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro geral: {e}")
    finally:
        stats['tempo_total'] = time.time() - inicio_total
        
        # Mostra estatísticas finais
        print("\n" + "=" * 80)
        print(f"📊 ESTATÍSTICAS FINAIS - {nome_tipo}")
        print("=" * 80)
        print(f"Marcas processadas: {stats['marcas_processadas']}")
        print(f"Modelos processados: {stats['modelos_processados']}")
        print(f"Relacionamentos criados: {stats['relacionamentos_criados']}")
        print(f"Erros: {stats['erros']}")
        print(f"Retries (429): {stats['retries_429']}")
        print(f"Tempo total: {stats['tempo_total']:.1f}s")
        print("=" * 80)


def verificar_antes_depois():
    """Mostra estatísticas antes e depois da repopulação."""
    cache = FipeLocalCache()
    
    print("\n📊 Estatísticas Antes da Repopulação")
    print("-" * 80)
    
    for tipo, nome in [(1, "Carros"), (2, "Motos"), (3, "Caminhões")]:
        count = cache.conn.execute(
            "SELECT COUNT(*) FROM modelos_anos WHERE tipo_veiculo = ?", 
            (tipo,)
        ).fetchone()[0]
        print(f"{nome}: {count:,} relacionamentos")


def main():
    """Função principal."""
    print()
    verificar_antes_depois()
    print()
    
    # Menu
    print("=" * 80)
    print("OPÇÕES:")
    print("=" * 80)
    print("1 - Repopular apenas CARROS")
    print("2 - Repopular apenas MOTOS")
    print("3 - Repopular apenas CAMINHÕES")
    print("4 - Repopular MOTOS e CAMINHÕES")
    print("5 - Repopular TODOS (Carros, Motos e Caminhões)")
    print("0 - Sair")
    print("=" * 80)
    
    opcao = input("\nEscolha uma opção: ").strip()
    print()
    
    if opcao == "1":
        repopular_tipo(1, "Carros")
    elif opcao == "2":
        repopular_tipo(2, "Motos")
    elif opcao == "3":
        repopular_tipo(3, "Caminhões")
    elif opcao == "4":
        repopular_tipo(2, "Motos")
        print("\n" + "=" * 80 + "\n")
        repopular_tipo(3, "Caminhões")
    elif opcao == "5":
        repopular_tipo(1, "Carros")
        print("\n" + "=" * 80 + "\n")
        repopular_tipo(2, "Motos")
        print("\n" + "=" * 80 + "\n")
        repopular_tipo(3, "Caminhões")
    elif opcao == "0":
        print("👋 Saindo...")
    else:
        print("❌ Opção inválida")
    
    print()
    verificar_antes_depois()
    print()


if __name__ == "__main__":
    main()
