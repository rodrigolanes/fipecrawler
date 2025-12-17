# Reorganização de Estrutura - FIPE Crawler

## 📁 Nova Estrutura

```
fipecrawler/
├── src/                              # Código-fonte principal
│   ├── crawler/
│   │   ├── __init__.py
│   │   ├── fipe_crawler.py           # Funções de requisição à API FIPE
│   │   └── ssl_config.py             # Configurações SSL (se houver)
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── fipe_local_cache.py       # Cache SQLite local
│   │   └── fipe_cache.py             # Cache Supabase remoto
│   └── database/
│       ├── __init__.py
│       ├── supabase_client.py        # Cliente Supabase
│       └── httpx_ssl_patch.py        # Patch SSL para httpx
├── scripts/                          # Scripts de manutenção
│   ├── atualizar_modelos.py          # Atualização incremental de modelos
│   ├── atualizar_valores.py          # Atualização mensal de valores
│   ├── popular_banco_otimizado.py    # População inicial do banco
│   ├── repopular_motos_caminhoes.py  # Correção de tipos de veículo
│   ├── upload_para_supabase.py       # Upload em lote para Supabase
│   ├── sincronizar_relacionamentos.py # Sincronização SQLite ↔ Supabase
│   ├── migrar_sqlite.py              # Migrações SQLite
│   └── migrar_sqlite_tipo_veiculo.py # Migração específica tipo_veiculo
├── scripts_banco/                    # Scripts SQL
│   ├── database_schema.sql
│   ├── drop_database.sql
│   └── migrations/
│       ├── adicionar_codigo_ano_combustivel.sql
│       └── adicionar_constraint_unique_valores_fipe.sql
├── tests/                            # Scripts de teste (NÃO versionado)
│   ├── __init__.py
│   ├── debug_api_fipe.py
│   ├── testar_retry_429.py
│   ├── testar_todas_funcoes.py
│   ├── testar_volvo_2016.py
│   ├── testar_volvo_completo.py
│   ├── validar_configuracoes.py
│   ├── verificar_completude.py
│   ├── verificar_relacionamentos_incompletos.py
│   ├── verificar_tipos_veiculo.py
│   └── verificar_volvo.py
├── docs/                             # Documentação
│   ├── database_schema.md
│   ├── correcao_brotli.md
│   └── correcao_bug_tipo_veiculo.md
├── .env                              # Variáveis de ambiente (não versionado)
├── .env.example                      # Exemplo de .env
├── .gitignore
├── requirements.txt
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── MIGRACAO.md
└── LICENSE
```

## 🔄 Comandos para Migração

Execute os comandos abaixo no PowerShell para mover os arquivos:

```powershell
# Mover módulos para src/
mv fipe_crawler.py src/crawler/
mv fipe_local_cache.py src/cache/
mv fipe_cache.py src/cache/
mv supabase_client.py src/database/

# Verificar se existe ssl_config.py e httpx_ssl_patch.py
if (Test-Path ssl_config.py) { mv ssl_config.py src/crawler/ }
if (Test-Path httpx_ssl_patch.py) { mv httpx_ssl_patch.py src/database/ }

# Mover scripts de manutenção
mv atualizar_modelos.py scripts/
mv atualizar_valores.py scripts/
mv popular_banco_otimizado.py scripts/
mv repopular_motos_caminhoes.py scripts/
mv upload_para_supabase.py scripts/
mv sincronizar_relacionamentos.py scripts/
mv migrar_sqlite.py scripts/
mv migrar_sqlite_tipo_veiculo.py scripts/

# Mover scripts de teste para tests/
mv debug_api_fipe.py tests/
mv testar_*.py tests/
mv validar_configuracoes.py tests/
mv verificar_*.py tests/

# Adicionar documentação faltante
if (Test-Path scripts_banco/database_schema.sql) {
    # Já existe
}
```

## 📝 Atualizações Necessárias

### 1. Atualizar imports nos scripts

Os scripts em `scripts/` precisarão de imports atualizados:

```python
# ANTES
from fipe_crawler import buscar_marcas_carros
from fipe_local_cache import FipeLocalCache
from supabase_client import get_supabase_client

# DEPOIS
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawler.fipe_crawler import buscar_marcas_carros
from src.cache.fipe_local_cache import FipeLocalCache
from src.database.supabase_client import get_supabase_client
```

Ou usar imports relativos se preferir manter o `src/` no PYTHONPATH.

### 2. Atualizar .gitignore

Adicionar a pasta `tests/` ao .gitignore:

```gitignore
# Scripts de teste temporários
tests/
!tests/__init__.py
```

### 3. Atualizar README.md

Atualizar paths nos exemplos de uso e documentação.

## ✅ Benefícios da Nova Estrutura

1. **Organização Clara**: Separação entre código-fonte, scripts e testes
2. **Modularidade**: Cada módulo tem responsabilidade bem definida
3. **Testes Isolados**: Scripts temporários não poluem o repositório
4. **Fácil Navegação**: Estrutura padronizada facilita encontrar arquivos
5. **Imports Limpos**: Uso de `__init__.py` para expor APIs públicas

## ⚠️ Importante

Após mover os arquivos, teste os scripts principais:
- `python scripts/popular_banco_otimizado.py`
- `python scripts/atualizar_modelos.py`
- `python scripts/repopular_motos_caminhoes.py`
