"""
Configurações centralizadas do projeto FIPE Crawler.

Este módulo contém todas as constantes e configurações utilizadas em todo o projeto,
incluindo delays para requisições à API FIPE, configurações de retry, etc.
"""

import random


# =============================================================================
# DELAYS DA API FIPE
# =============================================================================

def get_delay_padrao():
    """
    Retorna um delay randomizado entre 0.8 e 1.2 segundos.
    
    Usado entre todas as requisições à API FIPE para evitar rate limiting.
    A randomização torna o comportamento mais natural e dificulta detecção de bot.
    
    Returns:
        float: Tempo de delay em segundos (entre 0.8 e 1.2)
    """
    #return random.uniform(1.5, 2.0)
    return 1.5


# Delay fixo após receber erro 429 (Too Many Requests)
DELAY_RATE_LIMIT_429 = 30  # segundos


# =============================================================================
# CONFIGURAÇÕES DE RETRY
# =============================================================================

# Número máximo de tentativas em caso de erro
MAX_RETRIES = 3

# Tempo base para retry exponencial (5s, 10s, 20s)
RETRY_BASE_WAIT = 5  # segundos


# =============================================================================
# CONFIGURAÇÕES DE PARALELIZAÇÃO
# =============================================================================

# Número de workers paralelos para popular banco
NUM_WORKERS = 5

# Tamanho dos lotes para upload ao Supabase
BATCH_SIZE = 1000


# =============================================================================
# CONFIGURAÇÕES DA API FIPE
# =============================================================================

# URL base da API FIPE
FIPE_API_BASE_URL = "https://veiculos.fipe.org.br/api/veiculos"

# Headers padrão para requisições
FIPE_API_HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://veiculos.fipe.org.br"
}

# Tipos de veículo
TIPO_VEICULO_CARROS = 1
TIPO_VEICULO_MOTOS = 2
TIPO_VEICULO_CAMINHOES = 3

# Código especial para veículos Zero Km
CODIGO_ZERO_KM = "32000"


# =============================================================================
# CONVERSÃO DE MÊS DE REFERÊNCIA
# =============================================================================

# Mapeamento de meses em português para números
MESES_PT = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

MESES_NUM = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}


def mes_pt_para_yyyymm(mes_referencia):
    """
    Converte mês de referência do formato português para YYYYMM.
    
    Formatos aceitos:
    - "janeiro/2026" (formato da API)
    - "janeiro de 2026" (formato antigo do banco)
    - "202601" (já convertido - retorna direto)
    
    Args:
        mes_referencia (str): Mês no formato português ou YYYYMM
    
    Returns:
        str: Mês no formato YYYYMM (ex: "202601")
    
    Examples:
        >>> mes_pt_para_yyyymm("janeiro/2026")
        "202601"
        >>> mes_pt_para_yyyymm("janeiro de 2026")
        "202601"
        >>> mes_pt_para_yyyymm("202601")
        "202601"
    """
    if not mes_referencia:
        return None
    
    # Se já está no formato YYYYMM, retorna direto
    if mes_referencia.isdigit() and len(mes_referencia) == 6:
        return mes_referencia
    
    try:
        # Remove espaços extras e converte para minúsculas
        mes_ref_limpo = mes_referencia.strip().lower()
        
        # Separa mês e ano (trata ambos formatos: "/" e " de ")
        if '/' in mes_ref_limpo:
            mes_nome, ano = mes_ref_limpo.split('/')
        elif ' de ' in mes_ref_limpo:
            mes_nome, ano = mes_ref_limpo.split(' de ')
        else:
            raise ValueError(f"Formato inválido: {mes_referencia}")
        
        mes_nome = mes_nome.strip()
        ano = ano.strip()
        
        # Busca número do mês
        if mes_nome not in MESES_PT:
            raise ValueError(f"Mês inválido: {mes_nome}")
        
        mes_num = MESES_PT[mes_nome]
        
        # Formata como YYYYMM
        return f"{ano}{mes_num:02d}"
    
    except Exception as e:
        print(f"⚠️ Erro ao converter mês '{mes_referencia}': {e}")
        return None


def yyyymm_para_mes_display(yyyymm):
    """
    Converte mês do formato YYYYMM para formato legível.
    
    Args:
        yyyymm (str): Mês no formato YYYYMM (ex: "202601")
    
    Returns:
        str: Mês no formato legível (ex: "Janeiro/2026")
    
    Examples:
        >>> yyyymm_para_mes_display("202601")
        "Janeiro/2026"
        >>> yyyymm_para_mes_display("202512")
        "Dezembro/2025"
    """
    if not yyyymm:
        return "Desconhecido"
    
    # Se não está no formato YYYYMM, retorna como está
    if not yyyymm.isdigit() or len(yyyymm) != 6:
        return yyyymm
    
    try:
        ano = yyyymm[:4]
        mes_num = int(yyyymm[4:6])
        
        if mes_num < 1 or mes_num > 12:
            return yyyymm
        
        mes_nome = MESES_NUM[mes_num]
        return f"{mes_nome}/{ano}"
    
    except Exception as e:
        print(f"⚠️ Erro ao formatar mês '{yyyymm}': {e}")
        return yyyymm
