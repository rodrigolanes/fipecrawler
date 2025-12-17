"""
Módulo de crawling da API FIPE
"""
from .fipe_crawler import (
    buscar_tabela_referencia,
    buscar_marcas_carros,
    buscar_modelos,
    buscar_anos_modelo,
    buscar_modelos_por_ano,
    buscar_valor_veiculo,
    obter_codigo_referencia_atual
)

__all__ = [
    'buscar_tabela_referencia',
    'buscar_marcas_carros',
    'buscar_modelos',
    'buscar_anos_modelo',
    'buscar_modelos_por_ano',
    'buscar_valor_veiculo',
    'obter_codigo_referencia_atual'
]
