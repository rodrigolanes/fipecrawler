import requests
import json
import urllib3
import time
import sys
from pathlib import Path

# Adiciona o diretório src ao path para importar config
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from config import get_delay_padrao

# Desabilita avisos de SSL (apenas para desenvolvimento)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Sessão global compartilhada para manter cookies
_session = None

def get_session():
    """Retorna sessão compartilhada com cookies e headers configurados"""
    global _session
    if _session is None:
        _session = requests.Session()
        
        # Headers padrão que imitam navegador real
        _session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate",  # Removido 'br' (Brotli) - requests não descomprime corretamente
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://veiculos.fipe.org.br/",
            "Origin": "https://veiculos.fipe.org.br",
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": '"Microsoft Edge";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        })
        
        # Cookies que imitam visita real ao site
        _session.cookies.set("_ga", "GA1.3.1274497137.1765802022", domain=".fipe.org.br")
        _session.cookies.set("_gid", "GA1.3.478016371.1765802022", domain=".fipe.org.br")
        _session.cookies.set("_gcl_au", "1.1.788238918.1765802022", domain=".fipe.org.br")
        _session.cookies.set("ROUTEID", ".5", domain="veiculos.fipe.org.br")
        
    return _session


def buscar_tabela_referencia():
    """
    Busca a tabela de referência com todos os meses/anos disponíveis.
    O primeiro item da lista é sempre o mais recente.
    
    Returns:
        list: Lista de tabelas de referência com Codigo e Mes
    """
    from config import MAX_RETRIES, RETRY_BASE_WAIT, DELAY_RATE_LIMIT_429
    
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarTabelaDeReferencia"
    session = get_session()
    
    for retry in range(MAX_RETRIES):
        try:
            response = session.post(url, data={}, verify=False)
            response.raise_for_status()
            
            tabelas = response.json()
            time.sleep(get_delay_padrao())  # Delay padrão entre requisições
            return tabelas
        
        except requests.exceptions.HTTPError as e:
            if '429' in str(e) or (hasattr(e.response, 'status_code') and e.response.status_code == 429):
                if retry < MAX_RETRIES - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)
                    print(f"⚠️  Rate limit na tabela de referência. Aguardando {wait_time}s... (tentativa {retry+1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Rate limit persistente na tabela de referência após {MAX_RETRIES} tentativas")
                    return []
            else:
                print(f"Erro ao fazer requisição: {e}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"Erro ao fazer requisição: {e}")
            return []
    
    return []


def obter_codigo_referencia_atual():
    """
    Obtém o código da tabela de referência mais recente.
    
    Returns:
        int: Código da tabela de referência atual
    """
    tabelas = buscar_tabela_referencia()
    if tabelas and len(tabelas) > 0:
        return tabelas[0]['Codigo']
    return 328  # Fallback para o valor atual se não conseguir buscar


def buscar_marcas_carros(tipo_veiculo=1):
    """
    Busca as marcas disponíveis na API da FIPE por tipo de veículo.
    
    Args:
        tipo_veiculo: Tipo de veículo (1=Carros, 2=Motos, 3=Caminhões). Padrão: 1
    
    Returns:
        list: Lista de marcas de veículos
    """
    from config import MAX_RETRIES, RETRY_BASE_WAIT, DELAY_RATE_LIMIT_429
    
    tipos_nome = {1: "carros", 2: "motos", 3: "caminhões"}
    print(f"🌐 Buscando marcas de {tipos_nome.get(tipo_veiculo, 'veículos')} da API da FIPE...")
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarMarcas"
    session = get_session()
    
    payload = {
        "codigoTabelaReferencia": obter_codigo_referencia_atual(),
        "codigoTipoVeiculo": tipo_veiculo
    }
    
    for retry in range(MAX_RETRIES):
        try:
            response = session.post(url, data=payload, verify=False)
            response.raise_for_status()  # Levanta exceção se houver erro HTTP
            
            # Retornando os dados em formato JSON
            marcas = response.json()
            time.sleep(get_delay_padrao())  # Delay padrão entre requisições
            return marcas
        
        except requests.exceptions.HTTPError as e:
            if '429' in str(e) or (hasattr(e.response, 'status_code') and e.response.status_code == 429):
                if retry < MAX_RETRIES - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)
                    print(f"⚠️  Rate limit ao buscar marcas. Aguardando {wait_time}s... (tentativa {retry+1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    print(f"❌ Rate limit persistente ao buscar marcas após {MAX_RETRIES} tentativas")
                    raise
            else:
                print(f"Erro ao fazer requisição: {e}")
                raise
        except requests.exceptions.RequestException as e:
            print(f"Erro ao fazer requisição: {e}")
            raise
    
    return []


def buscar_modelos(codigo_marca, tipo_veiculo=1, nome_marca=None):
    """
    Busca os modelos de uma marca específica.
    SEMPRE busca da API para garantir que retorna os anos disponíveis.
    
    Args:
        codigo_marca: Código da marca (ex: 6 para Audi)
        tipo_veiculo: Tipo de veículo (1=Carros, 2=Motos, 3=Caminhões). Padrão: 1
        nome_marca: Nome da marca (opcional, para logs mais claros)
    
    Returns:
        dict: Dicionário contendo 'Modelos' (lista de modelos) e 'Anos' (lista de anos)
    """
    # IMPORTANTE: Sempre busca da API para obter os Anos, mesmo que modelos estejam em cache
    # A API retorna tanto Modelos quanto Anos em uma única requisição
    from config import MAX_RETRIES, RETRY_BASE_WAIT, DELAY_RATE_LIMIT_429
    
    marca_info = f"{nome_marca} ({codigo_marca})" if nome_marca else codigo_marca
    print(f"🌐 Buscando modelos da marca {marca_info} da API da FIPE...")
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarModelos"
    session = get_session()
    
    payload = {
        "codigoTipoVeiculo": tipo_veiculo,
        "codigoTabelaReferencia": obter_codigo_referencia_atual(),
        "codigoMarca": codigo_marca
    }
    
    for retry in range(MAX_RETRIES):
        try:
            response = session.post(url, data=payload, verify=False)
            response.raise_for_status()
            
            dados = response.json()
            time.sleep(get_delay_padrao())  # Delay padrão entre requisições
            return dados
        
        except requests.exceptions.HTTPError as e:
            # Trata erro 429 com retry
            if '429' in str(e) or (hasattr(e.response, 'status_code') and e.response.status_code == 429):
                if retry < MAX_RETRIES - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)
                    print(f"   ⚠️  Rate limit em {marca_info}. Aguardando {wait_time}s... (tentativa {retry+1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ Rate limit persistente em {marca_info} após {MAX_RETRIES} tentativas")
                    return None
            else:
                print(f"   ❌ Erro HTTP: {e}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Erro ao fazer requisição: {e}")
            return None
    
    return None


def buscar_anos_modelo(codigo_marca, codigo_modelo, tipo_veiculo=1, nome_modelo=None):
    """
    Busca os anos disponíveis para um modelo específico.
    
    Args:
        codigo_marca: Código da marca (ex: 6 para Audi)
        codigo_modelo: Código do modelo (ex: 5496 para A1)
        tipo_veiculo: Tipo de veículo (1=Carros, 2=Motos, 3=Caminhões). Padrão: 1
        nome_modelo: Nome do modelo (opcional, para logs mais claros)
    
    Returns:
        list: Lista de anos disponíveis com Label e Value
    """
    from config import MAX_RETRIES, RETRY_BASE_WAIT, DELAY_RATE_LIMIT_429
    
    modelo_info = f"{nome_modelo} ({codigo_modelo})" if nome_modelo else codigo_modelo
    print(f"🌐 Buscando anos do modelo {modelo_info} da API da FIPE...")
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarAnoModelo"
    session = get_session()
    
    payload = {
        "codigoTipoVeiculo": tipo_veiculo,
        "codigoTabelaReferencia": obter_codigo_referencia_atual(),
        "codigoMarca": codigo_marca,
        "codigoModelo": codigo_modelo
    }
    
    for retry in range(MAX_RETRIES):
        try:
            response = session.post(url, data=payload, verify=False)
            response.raise_for_status()
            
            # Força encoding UTF-8
            response.encoding = 'utf-8-sig'  # utf-8-sig remove BOM automaticamente
            
            # Verifica se resposta está vazia
            if not response.text or response.text.strip() == '':
                print(f"   ℹ️  Resposta vazia (modelo sem anos cadastrados)")
                return []
            
            # Limpeza agressiva: encontra o primeiro caractere válido JSON
            texto_limpo = response.text.strip()
            
            # Remove tudo antes do primeiro [ ou {
            primeiro_bracket = texto_limpo.find('[')
            primeiro_brace = texto_limpo.find('{')
            
            if primeiro_bracket != -1 and (primeiro_brace == -1 or primeiro_bracket < primeiro_brace):
                texto_limpo = texto_limpo[primeiro_bracket:]
                # Remove tudo após o ] final
                ultimo_bracket = texto_limpo.rfind(']')
                if ultimo_bracket != -1:
                    texto_limpo = texto_limpo[:ultimo_bracket + 1]
            elif primeiro_brace != -1:
                texto_limpo = texto_limpo[primeiro_brace:]
                # Remove tudo após o } final
                ultimo_brace = texto_limpo.rfind('}')
                if ultimo_brace != -1:
                    texto_limpo = texto_limpo[:ultimo_brace + 1]
            
            anos = json.loads(texto_limpo)
            
            # Verifica se é erro conhecido
            if isinstance(anos, dict) and anos.get('erro'):
                print(f"   ℹ️  API retornou erro: {anos.get('erro')}")
                return []
            
            if isinstance(anos, list) and anos:
                print(f"✅ {len(anos)} anos encontrados")
            
            time.sleep(get_delay_padrao())  # Delay padrão entre requisições
            return anos if isinstance(anos, list) else []
        
        except json.JSONDecodeError as e:
            print(f"   ⚠️  JSON inválido após limpeza.")
            print(f"   📄 Texto: {texto_limpo[:200] if 'texto_limpo' in locals() else response.text[:200]}")
            print(f"   ❌ Erro: {e}")
            return []
        except requests.exceptions.HTTPError as e:
            # Trata erro 429 com retry
            if '429' in str(e) or (hasattr(e.response, 'status_code') and e.response.status_code == 429):
                if retry < MAX_RETRIES - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)
                    print(f"   ⚠️  Rate limit em {modelo_info}. Aguardando {wait_time}s... (tentativa {retry+1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ Rate limit persistente em {modelo_info} após {MAX_RETRIES} tentativas")
                    return []
            else:
                print(f"   ❌ Erro HTTP: {e}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Erro de rede: {e}")
            return []
    
    return []


def buscar_modelos_por_ano(codigo_marca, ano_modelo="32000", codigo_combustivel=1, nome_marca=None, tipo_veiculo=1):
    """
    Busca modelos disponíveis para uma marca através do ano/combustível.
    Útil para descobrir novos modelos (especialmente Zero Km).
    
    Args:
        codigo_marca: Código da marca (ex: 6 para Audi)
        ano_modelo: Ano do modelo (ex: "32000" para Zero Km, "2025" para ano específico)
        codigo_combustivel: Código do combustível:
            1 = Gasolina
            2 = Álcool
            3 = Diesel
            4 = Elétrico
            5 = Flex
            6 = Híbrido
        nome_marca: Nome da marca (opcional, para logs mais claros)
        tipo_veiculo: Tipo de veículo (1=Carros, 2=Motos, 3=Caminhões). Padrão: 1
    
    Returns:
        list: Lista de modelos encontrados
    """
    from config import MAX_RETRIES, RETRY_BASE_WAIT, DELAY_RATE_LIMIT_429
    
    combustivel_nome = {1: "Gasolina", 2: "Álcool", 3: "Diesel", 4: "Elétrico", 5: "Flex", 6: "Híbrido"}
    marca_info = f"{nome_marca} ({codigo_marca})" if nome_marca else codigo_marca
    print(f"🌐 Buscando modelos {ano_modelo} ({combustivel_nome.get(codigo_combustivel, 'Outro')}) de {marca_info}...")
    
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarModelosAtravesDoAno"
    session = get_session()
    
    # Constrói o código ano no formato correto: "32000-1", "32000-2", etc
    codigo_ano = f"{ano_modelo}-{codigo_combustivel}"
    
    # Payload como form-urlencoded (formato que o navegador usa)
    payload = {
        "codigoTipoVeiculo": tipo_veiculo,
        "codigoTabelaReferencia": obter_codigo_referencia_atual(),
        "codigoModelo": "",
        "codigoMarca": codigo_marca,
        "ano": codigo_ano,
        "codigoTipoCombustivel": codigo_combustivel,
        "anoModelo": ano_modelo,
        "modeloCodigoExterno": ""
    }
    
    for retry in range(MAX_RETRIES):
        try:
            response = session.post(url, data=payload, verify=False)
            response.raise_for_status()
            
            # Força encoding UTF-8
            response.encoding = 'utf-8-sig'  # utf-8-sig remove BOM automaticamente
            
            # Verifica se resposta está vazia
            if not response.text or response.text.strip() == '':
                print(f"   ℹ️  Resposta vazia (ano/combustível não disponível)")
                return []
            
            # Limpeza agressiva: encontra o primeiro caractere válido JSON
            texto_limpo = response.text.strip()
            
            # Remove tudo antes do primeiro [ ou {
            primeiro_bracket = texto_limpo.find('[')
            primeiro_brace = texto_limpo.find('{')
            
            if primeiro_bracket != -1 and (primeiro_brace == -1 or primeiro_bracket < primeiro_brace):
                texto_limpo = texto_limpo[primeiro_bracket:]
                # Remove tudo após o ] final
                ultimo_bracket = texto_limpo.rfind(']')
                if ultimo_bracket != -1:
                    texto_limpo = texto_limpo[:ultimo_bracket + 1]
            elif primeiro_brace != -1:
                texto_limpo = texto_limpo[primeiro_brace:]
                # Remove tudo após o } final
                ultimo_brace = texto_limpo.rfind('}')
                if ultimo_brace != -1:
                    texto_limpo = texto_limpo[:ultimo_brace + 1]
            
            modelos = json.loads(texto_limpo)
            
            # Verifica se API retornou erro "nadaencontrado"
            if isinstance(modelos, dict):
                if modelos.get('erro') == 'nadaencontrado':
                    print(f"   ℹ️  Nenhum modelo (API: nadaencontrado)")
                    return []
                else:
                    print(f"   ⚠️  API retornou dict inesperado: {modelos}")
                    return []
            
            # Log detalhado dos modelos encontrados
            if modelos and isinstance(modelos, list):
                print(f"✅ {len(modelos)} modelos encontrados")
                
                # Se poucos modelos, mostra os nomes para validação
                if len(modelos) <= 5:
                    for modelo in modelos:
                        if isinstance(modelo, dict) and 'Label' in modelo:
                            print(f"   • {modelo['Label']} ({modelo.get('Value', '?')})")
            elif not isinstance(modelos, list):
                print(f"   ⚠️  Resposta não é lista: {type(modelos)}")
                return []
            
            time.sleep(get_delay_padrao())  # Delay padrão entre requisições
            return modelos if isinstance(modelos, list) else []
        
        except json.JSONDecodeError as e:
            # Mostra o conteúdo que causou erro de parse
            print(f"   ⚠️  JSON inválido após limpeza: {texto_limpo[:100] if 'texto_limpo' in locals() else response.text[:100]}")
            return []
        except requests.exceptions.HTTPError as e:
            # Trata erro 429 com retry
            if '429' in str(e) or (hasattr(e.response, 'status_code') and e.response.status_code == 429):
                if retry < MAX_RETRIES - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)
                    print(f"   ⚠️  Rate limit em {marca_info}. Aguardando {wait_time}s... (tentativa {retry+1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ Rate limit persistente em {marca_info} após {MAX_RETRIES} tentativas")
                    return []
            else:
                print(f"   ❌ Erro HTTP: {e}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Erro de rede: {e}")
            return []
    
    return []


def buscar_valor_veiculo(codigo_marca, codigo_modelo, ano_modelo, codigo_combustivel, tipo_veiculo=1, codigo_ref=None):
    """
    Busca o valor FIPE e informações completas de um veículo específico.
    
    Args:
        codigo_marca: Código da marca (ex: 6 para Audi)
        codigo_modelo: Código do modelo (ex: 5496 para A1)
        ano_modelo: Ano do modelo (ex: 2014 ou 32000 para Zero Km)
        codigo_combustivel: Código do combustível (ex: 1 para Gasolina)
        tipo_veiculo: Tipo de veículo (1=Carros, 2=Motos, 3=Caminhões). Padrão: 1
        codigo_ref: Código da tabela de referência (opcional, se não informado busca o atual)
    
    Returns:
        dict: Dicionário com todas as informações do veículo incluindo valor FIPE
    """
    from config import MAX_RETRIES, RETRY_BASE_WAIT, DELAY_RATE_LIMIT_429
    
    print(f"🌐 Buscando valor do veículo da API da FIPE...")
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarValorComTodosParametros"
    session = get_session()
    
    # Usa codigo_ref fornecido ou busca o atual
    if codigo_ref is None:
        codigo_ref = obter_codigo_referencia_atual()
    
    # Mapeia tipo_veiculo para string
    tipo_veiculo_map = {1: "carro", 2: "moto", 3: "caminhao"}
    tipo_veiculo_str = tipo_veiculo_map.get(tipo_veiculo, "carro")
    
    payload = {
        "codigoTabelaReferencia": codigo_ref,
        "codigoMarca": codigo_marca,
        "codigoModelo": codigo_modelo,
        "codigoTipoVeiculo": tipo_veiculo,
        "anoModelo": ano_modelo,
        "codigoTipoCombustivel": codigo_combustivel,
        "tipoVeiculo": tipo_veiculo_str,
        "tipoConsulta": "tradicional"
    }
    
    for retry in range(MAX_RETRIES):
        try:
            response = session.post(url, data=payload, verify=False)
            response.raise_for_status()
            
            dados = response.json()
            time.sleep(get_delay_padrao())  # Delay padrão entre requisições
            return dados
        
        except requests.exceptions.HTTPError as e:
            # Trata erro 429 com retry
            if '429' in str(e) or (hasattr(e.response, 'status_code') and e.response.status_code == 429):
                if retry < MAX_RETRIES - 1:
                    wait_time = RETRY_BASE_WAIT * (2 ** retry)
                    print(f"   ⚠️  Rate limit ao buscar valor. Aguardando {wait_time}s... (tentativa {retry+1}/{MAX_RETRIES})")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ Rate limit persistente ao buscar valor após {MAX_RETRIES} tentativas")
                    return None
            else:
                print(f"Erro ao fazer requisição: {e}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Erro ao fazer requisição: {e}")
            return None
    
    return None


def atualizar_modelos_marca(codigo_marca, incluir_ano_atual=True):
    """
    Atualiza modelos de uma marca buscando por Zero Km e ano atual em todos os tipos de combustível.
    Descobre novos modelos que não estavam no cache.
    
    Args:
        codigo_marca: Código da marca
        incluir_ano_atual: Se True, busca também modelos do ano atual além de Zero Km
    
    Returns:
        list: Lista de novos modelos encontrados
    """
    print(f"\n🔄 Atualizando modelos da marca {codigo_marca}...")
    
    # Busca modelos em todos os tipos de combustível
    codigos_cache = set()
    novos_modelos = []
    combustiveis = {
        1: "Gasolina",
        2: "Álcool", 
        3: "Diesel",
        4: "Elétrico",
        5: "Flex",
        6: "Híbrido"
    }
    
    # Anos a buscar: sempre Zero Km, opcionalmente ano atual
    from datetime import datetime
    ano_atual = str(datetime.now().year)
    anos_buscar = ["32000"]
    if incluir_ano_atual:
        anos_buscar.append(ano_atual)
    
    for ano in anos_buscar:
        ano_label = "Zero Km" if ano == "32000" else ano
        print(f"    Buscando modelos {ano_label}...")
        
        for codigo_combustivel, nome_combustivel in combustiveis.items():
            modelos_api = buscar_modelos_por_ano(codigo_marca, ano, codigo_combustivel)
            
            if modelos_api:
                for modelo in modelos_api:
                    codigo_modelo = str(modelo.get('Value', ''))
                    if codigo_modelo and codigo_modelo not in codigos_cache:
                        novos_modelos.append(modelo)
                        codigos_cache.add(codigo_modelo)  # Evita duplicatas
    
    # Retorna novos modelos
    if novos_modelos:
        print(f"✅ {len(novos_modelos)} novos modelos encontrados!")
    else:
        print(f"ℹ️  Nenhum modelo novo encontrado")
    
    return novos_modelos


def main():
    print("=" * 60)
    print("CRAWLER FIPE - Teste com Código Dinâmico")
    print("=" * 60)
    print()
    
    # Obtendo código de referência atual
    codigo_ref = obter_codigo_referencia_atual()
    print(f"Usando código de referência: {codigo_ref}\n")
    
    # Consultando valor do Audi A1 2014
    print("Consultando: Audi A1 1.4 TFSI 2014 Gasolina")
    print("-" * 60)
    
    dados = buscar_valor_veiculo(6, 5496, 2014, 1)
    
    if dados:
        print(f"Marca: {dados.get('Marca')}")
        print(f"Modelo: {dados.get('Modelo')}")
        print(f"Ano: {dados.get('AnoModelo')}")
        print(f"Combustível: {dados.get('Combustivel')}")
        print(f"Código FIPE: {dados.get('CodigoFipe')}")
        print()
        print(f"💰 VALOR: {dados.get('Valor')}")
        print()
        print(f"Referência: {dados.get('MesReferencia')}")
    else:
        print("❌ Não foi possível consultar o valor.")


if __name__ == "__main__":
    main()
