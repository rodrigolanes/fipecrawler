"""
Módulo de cache (SQLite local e Supabase remoto)
"""
from .fipe_local_cache import FipeLocalCache

# FipeCache comentado pois não está sendo usado ativamente
# from .fipe_cache import FipeCache

__all__ = ['FipeLocalCache']
