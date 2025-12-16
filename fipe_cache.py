from datetime import datetime
from typing import List, Dict, Optional
import ssl
import urllib3
import os

# Aplica patch no httpx ANTES de importar supabase
import httpx_ssl_patch

# Desabilita avisos SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from supabase_client import get_supabase_client


class FipeCache:
    """
    Classe para gerenciar cache de dados da FIPE no Supabase.
    Evita requisições duplicadas à API da FIPE.
    """
    
    def __init__(self):
        # Configuração SSL para ambientes corporativos
        import warnings
        
        # Cria contexto SSL não verificado
        ssl._create_default_https_context = ssl._create_unverified_context
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        
        # Configura também para httpx (usado pelo Supabase)
        os.environ['HTTPX_VERIFY_SSL'] = 'false'
        
        self.client = get_supabase_client()
    
    # ============================================
    # MARCAS
    # ============================================
    
    def get_marcas(self, tipo_veiculo: int = 1) -> List[Dict]:
        """
        Busca marcas do cache. Se não existir, retorna lista vazia.
        
        Args:
            tipo_veiculo: 1=carro, 2=moto, 3=caminhão
            
        Returns:
            Lista de marcas do banco
        """
        try:
            response = self.client.table('marcas')\
                .select('*')\
                .eq('tipo_veiculo', tipo_veiculo)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao buscar marcas do cache: {e}")
            return []
    
    def save_marcas(self, marcas: List[Dict], tipo_veiculo: int = 1) -> bool:
        """
        Salva marcas no cache.
        
        Args:
            marcas: Lista de marcas da API FIPE
            tipo_veiculo: 1=carro, 2=moto, 3=caminhão
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            data = [
                {
                    'codigo': marca['Value'],
                    'nome': marca['Label'],
                    'tipo_veiculo': tipo_veiculo
                }
                for marca in marcas
            ]
            
            # Upsert: insere ou atualiza se já existir
            self.client.table('marcas').upsert(data, on_conflict='codigo').execute()
            print(f"✅ {len(data)} marcas salvas no cache")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar marcas no cache: {e}")
            return False
    
    # ============================================
    # MODELOS
    # ============================================
    
    def get_modelos(self, codigo_marca: int) -> List[Dict]:
        """
        Busca modelos de uma marca do cache.
        
        Args:
            codigo_marca: Código da marca
            
        Returns:
            Lista de modelos do banco
        """
        try:
            response = self.client.table('modelos')\
                .select('*')\
                .eq('codigo_marca', codigo_marca)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao buscar modelos do cache: {e}")
            return []
    
    def save_modelos(self, modelos: List[Dict], codigo_marca: int) -> bool:
        """
        Salva modelos no cache.
        
        Args:
            modelos: Lista de modelos da API FIPE
            codigo_marca: Código da marca
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            data = [
                {
                    'codigo': modelo['Value'],
                    'nome': modelo['Label'],
                    'codigo_marca': codigo_marca
                }
                for modelo in modelos
            ]
            
            self.client.table('modelos').upsert(data, on_conflict='codigo,codigo_marca').execute()
            print(f"✅ {len(data)} modelos salvos no cache")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar modelos no cache: {e}")
            return False
    
    # ============================================
    # ANOS E COMBUSTÍVEL
    # ============================================
    
    def get_anos_modelo(self, codigo_marca: int, codigo_modelo: int) -> List[Dict]:
        """
        Busca anos/combustível de um modelo do cache.
        
        Args:
            codigo_marca: Código da marca
            codigo_modelo: Código do modelo
            
        Returns:
            Lista de anos/combustível do banco
        """
        try:
            response = self.client.table('modelos_anos')\
                .select('*, anos_combustivel(*)')\
                .eq('codigo_marca', codigo_marca)\
                .eq('codigo_modelo', codigo_modelo)\
                .execute()
            
            return response.data if response.data else []
        except Exception as e:
            print(f"Erro ao buscar anos do cache: {e}")
            return []
    
    def save_anos_modelo(self, anos: List[Dict], codigo_marca: int, codigo_modelo: int) -> bool:
        """
        Salva anos/combustível de um modelo no cache.
        
        Args:
            anos: Lista de anos da API FIPE
            codigo_marca: Código da marca
            codigo_modelo: Código do modelo
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            # Primeiro, salva os anos/combustível únicos
            anos_combustivel = []
            for ano in anos:
                codigo = ano['Value']  # ex: "2014-1" ou "32000-1"
                label = ano['Label']   # ex: "2014 Gasolina" ou "32000 Gasolina"
                
                # Extrai ano e combustível do código
                partes = codigo.split('-')
                ano_num = int(partes[0]) if len(partes) > 0 else 0
                
                # Trata Zero Km (ano 32000)
                if ano_num == 32000:
                    # Para Zero Km, usa o label original
                    combustivel = label.replace('32000', '').strip()
                else:
                    # Extrai combustível do label
                    combustivel = label.split(' ', 1)[-1] if ' ' in label else 'Desconhecido'
                
                anos_combustivel.append({
                    'codigo': codigo,
                    'ano': ano_num,
                    'combustivel': combustivel,
                    'sigla_combustivel': None  # Será preenchido ao buscar valor FIPE
                })
            
            # Upsert anos_combustivel
            if anos_combustivel:
                self.client.table('anos_combustivel').upsert(anos_combustivel, on_conflict='codigo').execute()
            
            # Depois, cria relacionamento N:N
            modelos_anos = [
                {
                    'codigo_marca': codigo_marca,
                    'codigo_modelo': codigo_modelo,
                    'codigo_ano_combustivel': ano['Value']
                }
                for ano in anos
            ]
            
            self.client.table('modelos_anos').upsert(
                modelos_anos, 
                on_conflict='codigo_marca,codigo_modelo,codigo_ano_combustivel'
            ).execute()
            
            print(f"✅ {len(anos)} anos/combustível salvos no cache")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar anos no cache: {e}")
            return False
    
    # ============================================
    # VALORES FIPE
    # ============================================
    
    def get_valor_fipe(self, codigo_marca: int, codigo_modelo: int, 
                       ano_modelo: int, codigo_combustivel: int) -> Optional[Dict]:
        """
        Busca valor FIPE do cache (consulta mais recente).
        
        Args:
            codigo_marca: Código da marca
            codigo_modelo: Código do modelo
            ano_modelo: Ano do modelo
            codigo_combustivel: Código do combustível
            
        Returns:
            Dados do valor FIPE ou None
        """
        try:
            response = self.client.table('valores_fipe')\
                .select('*')\
                .eq('codigo_marca', codigo_marca)\
                .eq('codigo_modelo', codigo_modelo)\
                .eq('ano_modelo', ano_modelo)\
                .eq('codigo_combustivel', codigo_combustivel)\
                .order('data_consulta', desc=True)\
                .limit(1)\
                .execute()
            
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Erro ao buscar valor FIPE do cache: {e}")
            return None
    
    def save_valor_fipe(self, dados_fipe: Dict, codigo_marca: int, 
                        codigo_modelo: int, ano_modelo: int, 
                        codigo_combustivel: int, codigo_referencia: int) -> bool:
        """
        Salva valor FIPE consultado no cache.
        
        Args:
            dados_fipe: Resposta completa da API FIPE
            codigo_marca: Código da marca
            codigo_modelo: Código do modelo
            ano_modelo: Ano do modelo
            codigo_combustivel: Código do combustível
            codigo_referencia: Código da tabela de referência
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            # Extrai valor numérico (remove "R$" e converte)
            valor_str = dados_fipe.get('Valor', 'R$ 0,00')
            valor_numerico = self._parse_valor(valor_str)
            
            data = {
                'codigo_marca': codigo_marca,
                'codigo_modelo': codigo_modelo,
                'ano_modelo': ano_modelo,
                'codigo_combustivel': codigo_combustivel,
                'valor': valor_str,
                'valor_numerico': valor_numerico,
                'codigo_fipe': dados_fipe.get('CodigoFipe'),
                'mes_referencia': dados_fipe.get('MesReferencia'),
                'codigo_referencia': codigo_referencia,
                'data_consulta': datetime.now().isoformat(),
                'marca': dados_fipe.get('Marca'),
                'modelo': dados_fipe.get('Modelo'),
                'combustivel': dados_fipe.get('Combustivel')
            }
            
            self.client.table('valores_fipe').insert(data).execute()
            print(f"✅ Valor FIPE salvo no cache: {valor_str}")
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar valor FIPE no cache: {e}")
            return False
    
    # ============================================
    # TABELAS DE REFERÊNCIA
    # ============================================
    
    def save_tabela_referencia(self, codigo: int, mes: str) -> bool:
        """
        Salva tabela de referência no cache.
        
        Args:
            codigo: Código da tabela
            mes: Mês/ano da tabela
            
        Returns:
            True se sucesso, False se erro
        """
        try:
            data = {
                'codigo': codigo,
                'mes': mes
            }
            
            self.client.table('tabelas_referencia').upsert(data, on_conflict='codigo').execute()
            return True
        except Exception as e:
            print(f"❌ Erro ao salvar tabela de referência: {e}")
            return False
    
    # ============================================
    # UTILITÁRIOS
    # ============================================
    
    def _parse_valor(self, valor_str: str) -> float:
        """
        Converte string de valor para float.
        Ex: "R$ 69.252,00" -> 69252.00
        """
        try:
            # Remove "R$", espaços, e pontos de milhar
            valor = valor_str.replace('R$', '').replace(' ', '').replace('.', '')
            # Substitui vírgula por ponto decimal
            valor = valor.replace(',', '.')
            return float(valor)
        except:
            return 0.0
