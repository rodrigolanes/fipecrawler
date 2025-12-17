"""
Scripts de manutenção do FIPE Crawler

Este módulo configura o path para importar os módulos do src/
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
