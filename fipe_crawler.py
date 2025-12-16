import requests
import json
import urllib3
import time

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
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
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarTabelaDeReferencia"
    session = get_session()
    
    try:
        response = session.post(url, json={}, verify=False)
        response.raise_for_status()
        
        tabelas = response.json()
        return tabelas
    
    except requests.exceptions.RequestException as e:
        print(f"Erro ao fazer requisição: {e}")
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


def buscar_marcas_carros():
    """
    Busca as marcas de carros disponíveis na API da FIPE.
    
    Returns:
        list: Lista de marcas de veículos
    """
    print("🌐 Buscando marcas da API da FIPE...")
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarMarcas"
    session = get_session()
    
    payload = {
        "codigoTabelaReferencia": obter_codigo_referencia_atual(),
        "codigoTipoVeiculo": 1
    }
    
    try:
        response = session.post(url, json=payload, verify=False)
        # verify=False desabilita verificação SSL (usar apenas em desenvolvimento)
        response = requests.post(url, json=payload, headers=headers, verify=False)
        response.raise_for_status()  # Levanta exceção se houver erro HTTP
        
        # Retornando os dados em formato JSON
        marcas = response.json()
        
        return marcas
    
    except requests.exceptions.RequestException as e:
        print(f"Erro ao fazer requisição: {e}")
        return []


def buscar_modelos(codigo_marca):
    """
    Busca os modelos disponíveis para uma marca específica.
    SEMPRE busca da API para garantir que retorna os anos disponíveis.
    
    Args:
        codigo_marca: Código da marca (ex: 6 para Audi)
    
    Returns:
        dict: Dicionário contendo 'Modelos' (lista de modelos) e 'Anos' (lista de anos)
    """
    # IMPORTANTE: Sempre busca da API para obter os Anos, mesmo que modelos estejam em cache
    # A API retorna tanto Modelos quanto Anos em uma única requisição
    print(f"🌐 Buscando modelos da marca {codigo_marca} da API da FIPE...")
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarModelos"
    session = get_session()
    
    payload = {
        "codigoTipoVeiculo": 1,
        "codigoTabelaReferencia": obter_codigo_referencia_atual(),
        "codigoMarca": codigo_marca
    }
    
    try:
        response = session.post(url, json=payload, verify=False)
        response.raise_for_status()
        
        dados = response.json()
        
        return dados
    
    except requests.exceptions.RequestException as e:
        print(f"Erro ao fazer requisição: {e}")
        return None


def buscar_anos_modelo(codigo_marca, codigo_modelo):
    """
    Busca os anos disponíveis para um modelo específico.
    
    Args:
        codigo_marca: Código da marca (ex: 6 para Audi)
        codigo_modelo: Código do modelo (ex: 5496 para A1)
    
    Returns:
        list: Lista de anos disponíveis com Label e Value
    """
    print(f"🌐 Buscando anos do modelo {codigo_modelo} da API da FIPE...")
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarAnoModelo"
    session = get_session()
    
    payload = {
        "codigoTipoVeiculo": 1,
        "codigoTabelaReferencia": obter_codigo_referencia_atual(),
        "codigoMarca": codigo_marca,
        "codigoModelo": codigo_modelo
    }
    
    try:
        response = session.post(url, json=payload, verify=False)
        response.raise_for_status()
        
        anos = response.json()
        
        return anos
    
    except requests.exceptions.RequestException as e:
        print(f"Erro ao fazer requisição: {e}")
        return []


def buscar_modelos_por_ano(codigo_marca, ano_modelo="32000", codigo_combustivel=1, nome_marca=None):
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
    
    Returns:
        list: Lista de modelos encontrados
    """
    combustivel_nome = {1: "Gasolina", 2: "Álcool", 3: "Diesel", 4: "Elétrico", 5: "Flex", 6: "Híbrido"}
    marca_info = f"{nome_marca} ({codigo_marca})" if nome_marca else codigo_marca
    print(f"🌐 Buscando modelos {ano_modelo} ({combustivel_nome.get(codigo_combustivel, 'Outro')}) de {marca_info}...")
    
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarModelosAtravesDoAno"
    session = get_session()
    
    # Constrói o código ano no formato correto: "32000-1", "32000-2", etc
    codigo_ano = f"{ano_modelo}-{codigo_combustivel}"
    
    # Payload no formato form-urlencoded
    payload = {
        "codigoTipoVeiculo": 1,
        "codigoTabelaReferencia": obter_codigo_referencia_atual(),
        "codigoModelo": "",
        "codigoMarca": codigo_marca,
        "ano": codigo_ano,
        "codigoTipoCombustivel": codigo_combustivel,
        "anoModelo": ano_modelo,
        "modeloCodigoExterno": ""
    }
    
    try:
        response = session.post(url, json=payload, verify=False)
        response.raise_for_status()
        
        modelos = response.json()
        
        # Verifica se API retornou erro "nadaencontrado"
        if isinstance(modelos, dict) and modelos.get('erro') == 'nadaencontrado':
            print("⚠️ Nenhum modelo encontrado (nadaencontrado)")
            return []
        
        # Log detalhado dos modelos encontrados
        if modelos and isinstance(modelos, list):
            print(f"✅ {len(modelos)} modelos encontrados")
            
            # Se poucos modelos, mostra os nomes para validação
            if len(modelos) <= 5:
                for modelo in modelos:
                    if isinstance(modelo, dict) and 'Label' in modelo:
                        print(f"   • {modelo['Label']} ({modelo.get('Value', '?')})")
                    else:
                        print(f"   ⚠️ Modelo em formato inesperado: {type(modelo)}")
        elif not isinstance(modelos, list):
            print(f"   ⚠️ Resposta não é lista: {type(modelos)} - {str(modelos)[:100]}")
            return []
        else:
            print("⚠️ Nenhum modelo encontrado")
        
        return modelos if isinstance(modelos, list) else []
    
    except requests.exceptions.RequestException as e:
        print(f"Erro ao fazer requisição: {e}")
        return []


def buscar_valor_veiculo(codigo_marca, codigo_modelo, ano_modelo, codigo_combustivel, codigo_ref=None):
    """
    Busca o valor FIPE e informações completas de um veículo específico.
    
    Args:
        codigo_marca: Código da marca (ex: 6 para Audi)
        codigo_modelo: Código do modelo (ex: 5496 para A1)
        ano_modelo: Ano do modelo (ex: 2014 ou 32000 para Zero Km)
        codigo_combustivel: Código do combustível (ex: 1 para Gasolina)
        codigo_ref: Código da tabela de referência (opcional, se não informado busca o atual)
    
    Returns:
        dict: Dicionário com todas as informações do veículo incluindo valor FIPE
    """
    print(f"🌐 Buscando valor do veículo da API da FIPE...")
    url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarValorComTodosParametros"
    session = get_session()
    
    # Usa codigo_ref fornecido ou busca o atual
    if codigo_ref is None:
        codigo_ref = obter_codigo_referencia_atual()
    
    payload = {
        "codigoTabelaReferencia": codigo_ref,
        "codigoMarca": codigo_marca,
        "codigoModelo": codigo_modelo,
        "codigoTipoVeiculo": 1,
        "anoModelo": ano_modelo,
        "codigoTipoCombustivel": codigo_combustivel,
        "tipoVeiculo": "carro",
        "tipoConsulta": "tradicional"
    }
    
    try:
        response = session.post(url, json=payload, verify=False)
        response.raise_for_status()
        
        dados = response.json()
        
        return dados
    
    except requests.exceptions.RequestException as e:
        print(f"Erro ao fazer requisição: {e}")
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
