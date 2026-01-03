# Instruções do Projeto - FIPE Crawler

## 🌍 Idioma do Projeto

**IMPORTANTE**: Este projeto é 100% em **Português Brasileiro (pt-BR)**.

- ✅ **Código**: Variáveis, funções, classes, comentários em PT-BR
- ✅ **Documentação**: README, docstrings, markdown em PT-BR
- ✅ **Commits**: Mensagens de commit em PT-BR
- ✅ **Conversas**: Todas as interações com GitHub Copilot devem ser em PT-BR
- ✅ **Logs**: Mensagens de output e debug em PT-BR

**Motivo**: Projeto brasileiro, API brasileira (FIPE), equipe brasileira.

## Visão Geral

Crawler Python para buscar dados de veículos da tabela FIPE (Fundação Instituto de Pesquisas Econômicas) com sistema de cache duplo (SQLite local + Supabase PostgreSQL) para máxima performance e evitar requisições duplicadas/bloqueio por rate limiting.

## Arquitetura

### Componentes Principais

1. **fipe_crawler.py**: Funções para interagir com a API FIPE (requisições HTTP)
2. **fipe_local_cache.py**: Classe `FipeLocalCache` para cache SQLite local (rápido, thread-safe)
3. **fipe_cache.py**: Classe `FipeCache` para gerenciar cache no Supabase (remoto, opcional)
4. **supabase_client.py**: Cliente singleton do Supabase com configuração SSL
5. **httpx_ssl_patch.py**: Patch para desabilitar verificação SSL em ambiente corporativo
6. **popular_banco_otimizado.py**: Script paralelo para popular banco SQLite (uso inicial, 10x mais rápido)
7. **atualizar_modelos.py**: Script para atualização incremental de modelos (busca Zero Km)
8. **atualizar_valores.py**: Script para atualização mensal de valores FIPE
9. **upload_para_supabase.py**: Script para sincronizar SQLite → Supabase em lote

### Fluxo de Dados (Arquitetura Otimizada)

```
API FIPE → fipe_crawler → fipe_local_cache (SQLite) → upload_para_supabase → Supabase PostgreSQL
                                ↓
                          fipe_local.db (persistente)
```

**Vantagens da arquitetura atual**:
- ⚡ Gravação 100x mais rápida (SQLite vs rede)
- 🔒 Thread-safe com locks para paralelização
- 💾 Funciona offline (não depende do Supabase)
- 🔄 Upload opcional em lote após coleta

## Tecnologias e Versões

### Python

- **Versão**: Python 3.13.2
- **Ambiente Virtual**: `.venv` (sempre ativar antes de executar scripts)

### Bibliotecas Principais

- `requests==2.31.0`: Requisições HTTP para API FIPE
- `supabase==2.3.4`: Cliente Python para Supabase
- `python-dotenv==1.0.0`: Gerenciamento de variáveis de ambiente
- `httpx`: Usado internamente pelo Supabase (requer patch)
- `urllib3`, `certifi`: Gerenciamento de SSL/TLS

### Banco de Dados

- **SQLite Local** (`fipe_local.db`): Cache principal, gravação rápida, thread-safe
- **Supabase PostgreSQL** (cloud): Backup remoto opcional, acesso via API
- **RLS**: Row Level Security habilitado com políticas para role `anon`

## Configuração de Ambiente

### Variáveis de Ambiente (.env)

```env
SUPABASE_URL=https://frnfahrjfmnggeaccyty.supabase.co
SUPABASE_KEY=<anon_key>
```

### Certificados SSL

- **Pasta**: `certs/`
- **Arquivos**: `petrobras_root_cadeia.pem`, `certadmin.pem`
- **Motivo**: Ambiente corporativo Petrobras requer certificados customizados
- **Importante**: SEMPRE importar `httpx_ssl_patch` ANTES de qualquer operação Supabase

### Ordem de Imports Crítica

```python
# SEMPRE nesta ordem:
import httpx_ssl_patch  # Deve vir PRIMEIRO
from supabase_client import get_supabase_client
from fipe_cache import FipeCache
```

## API FIPE

### Endpoint Base

```
https://veiculos.fipe.org.br/api/veiculos
```

### Endpoints Principais

1. **Tabelas de Referência**: `/ConsultarTabelaDeReferencia`
2. **Marcas**: `/ConsultarMarcas`
3. **Modelos**: `/ConsultarModelos`
4. **Anos**: `/ConsultarAnoModelo`
5. **Valor**: `/ConsultarValorComTodosParametros`
6. **Modelos por Ano**: `/ConsultarModelosAtravesDoAno` (para descobrir novos modelos Zero Km)

### Headers Padrão

```python
headers = {
    "Content-Type": "application/json",
    "Referer": "https://veiculos.fipe.org.br"
}
```

### Payload Padrão

```python
{
    "codigoTabelaReferencia": "328",  # Código dinâmico (dezembro/2025)
    "codigoTipoVeiculo": 1  # 1=Carros, 2=Motos, 3=Caminhões
}
```

### SSL na API FIPE

- **Verificação**: `verify=False` (ambiente corporativo)
- **Warnings**: Suprimir com `urllib3.disable_warnings()`

## Estrutura do Banco de Dados

### Tabelas

#### 1. tabelas_referencia

```sql
- codigo (PK): integer
- mes: varchar(50)
- created_at, updated_at: timestamp
```

#### 2. marcas

```sql
- codigo (PK): varchar(10)
- nome: varchar(100)
- created_at, updated_at: timestamp
```

#### 3. modelos

```sql
- codigo (PK): integer
- codigo_marca (FK): varchar(10) → marcas
- nome: varchar(200)
- created_at, updated_at: timestamp
```

#### 4. anos_combustivel

```sql
- codigo (PK): varchar(20)
- nome: varchar(50)
- created_at, updated_at: timestamp
```

**Importante**: Código "32000" representa "Zero Km" (veículos novos)

#### 5. modelos_anos (N:N)

```sql
- modelo_codigo (FK): integer → modelos
- ano_codigo (FK): varchar(20) → anos_combustivel
- created_at: timestamp
- PK: (modelo_codigo, ano_codigo)
```

#### 6. valores_fipe

```sql
- codigo_marca (FK): varchar(10) → marcas
- codigo_modelo (FK): integer → modelos
- codigo_ano (FK): varchar(20) → anos_combustivel
- mes_referencia: varchar(50)
- tipo_veiculo: integer
- marca: varchar(100)
- modelo: varchar(200)
- ano_modelo: integer
- combustivel: varchar(50)
- codigo_fipe: varchar(20)
- valor_texto: varchar(50)
- valor_numerico: numeric(10, 2)
- created_at, updated_at: timestamp
- PK: (codigo_marca, codigo_modelo, codigo_ano)
```

### Índices

- `idx_modelos_marca`: modelos(codigo_marca)
- `idx_valores_marca`: valores_fipe(codigo_marca)
- `idx_valores_modelo`: valores_fipe(codigo_modelo)
- `idx_valores_ano`: valores_fipe(codigo_ano)

### Triggers

- `update_updated_at_column()`: Atualiza `updated_at` automaticamente em todas as tabelas

## Regras de Código

### 1. Cache First

SEMPRE verificar cache antes de fazer requisição à API:

```python
# ✅ CORRETO
marcas = cache.get_marcas()
if not marcas:
    marcas = buscar_marcas_carros()
    cache.save_marcas(marcas)

# ❌ ERRADO
marcas = buscar_marcas_carros()  # Ignora cache
```

### 2. Tratamento de Ano "Zero Km"

Ano com código "32000" deve ser tratado como "Zero Km":

```python
if ano["Value"] == "32000":
    anos_salvos = cache.save_anos_modelo(codigo_marca, codigo_modelo, [{
        "Value": "32000",
        "Label": "Zero Km"
    }])
```

### 3. Parsing de Valores Monetários

Valores da FIPE vêm no formato "R$ 69.252,00":

```python
def _parse_valor(self, valor_texto: str) -> float:
    """Converte 'R$ 69.252,00' para 69252.00"""
    valor_limpo = valor_texto.replace("R$", "").replace(".", "").replace(",", ".").strip()
    return float(valor_limpo)
```

### 4. Delays Entre Requisições

**IMPORTANTE**: Delays estão centralizados em `src/config.py` e implementados no módulo base `fipe_crawler.py`.

**Configuração atual** (testada e validada):
```python
from src.config import get_delay_padrao, DELAY_RATE_LIMIT_429

# Delay padrão entre requisições (0.8-1.2s randomizado)
time.sleep(get_delay_padrao())

# Delay após erro 429 (rate limit)
time.sleep(DELAY_RATE_LIMIT_429)  # 30s
```

**Regras**:
- ✅ Delays JÁ implementados em todas as funções de `fipe_crawler.py`
- ❌ NÃO adicione `time.sleep()` nos scripts que chamam essas funções (duplicação!)
- ✅ Use apenas para delays de retry em caso de erro 429
- ✅ Para ajustar delays globalmente, edite `src/config.py`

**Exemplo CORRETO**:
```python
from src.crawler.fipe_crawler import buscar_marcas_carros

# Delay já implementado internamente, não adicione aqui
marcas = buscar_marcas_carros()
```

**Exemplo ERRADO**:
```python
marcas = buscar_marcas_carros()
time.sleep(1.0)  # ❌ DUPLICAÇÃO! Delay já existe internamente
```

### 5. Tratamento de Erros

Sempre capturar exceções de rede e banco:

```python
try:
    response = requests.post(url, json=payload, headers=headers, verify=False)
    response.raise_for_status()
except requests.RequestException as e:
    print(f"❌ Erro na requisição: {e}")
    return None
```

### 6. Logs Informativos

Usar emojis para melhor visualização:

```python
print("✅ Sucesso")
print("❌ Erro")
print("📦 Cache")
print("🌐 API")
print("⚠️ Aviso")
print("📊 Estatísticas")
```

## Padrões de Nomenclatura

### Variáveis

- Snake_case: `codigo_marca`, `codigo_modelo`, `ano_combustivel`
- Português: Manter nomenclatura em PT-BR (FIPE é brasileiro)

### Funções

- Verbos no infinitivo: `buscar_marcas`, `salvar_modelos`, `obter_codigo`
- Snake_case: `buscar_anos_modelo()`, `save_valor_fipe()`

### Constantes

- UPPER_CASE: `TIPO_VEICULO_CARRO = 1`

## Ordem de Execução

### 1. Configuração Inicial

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Banco

```sql
-- Executar no Supabase SQL Editor
-- 1. database_schema.sql
-- 2. fix_rls_policies.sql
```

### 3. Popular Banco (Primeira Vez)

```bash
python popular_banco_otimizado.py
```

**Importante**: Execute apenas na primeira vez ou para repopular do zero. Pode levar 2-4 horas com 5 workers.
**Características**:
- Processamento paralelo (5 marcas simultâneas por padrão)
- Gravação em SQLite local (100x mais rápido que Supabase)
- Estratégia inteligente: escolhe buscar por modelo ou por ano conforme mais eficiente
- Thread-safe com locks
- Progresso persistente (pode ser interrompido e retomado)

### 3.1. Upload para Supabase (Opcional)

```bash
python upload_para_supabase.py
```

**Quando usar**: Após popular/atualizar o banco local
**Características**:
- Upload em lotes de 1000 registros
- Idempotente (pode ser executado múltiplas vezes)
- Mostra estatísticas comparativas SQLite vs Supabase

### 4. Atualização Mensal de Modelos

```bash
python atualizar_modelos.py
```

**Objetivo**: Buscar novos modelos Zero Km de todas as marcas. Execute mensalmente para descobrir lançamentos.
**Tempo**: ~10-15 minutos.

### 5. Atualização Mensal de Valores

```bash
python atualizar_valores.py
```

**Objetivo**: Atualizar valores FIPE de todos os veículos cadastrados. Execute quando a tabela FIPE é atualizada.
**Tempo**: Várias horas (depende da quantidade de veículos).

### 6. Usar Crawler

```python
# Exemplo 1: Usando cache local (SQLite)
from fipe_crawler import buscar_marcas_carros, buscar_modelos
from fipe_local_cache import FipeLocalCache

cache = FipeLocalCache()
marcas = cache.get_all_marcas()  # Busca do SQLite local

# Exemplo 2: Usando cache remoto (Supabase)
import httpx_ssl_patch  # SEMPRE primeiro
from fipe_cache import FipeCache

cache = FipeCache()
marcas = cache.get_marcas()  # Busca do Supabase
```

## Estratégia de Atualização

### Atualização Incremental de Modelos

- **Quando**: Mensalmente (início do mês quando FIPE atualiza)
- **Script**: `atualizar_modelos.py`
- **Como funciona**: Busca modelos Zero Km de todas as marcas usando endpoint `/ConsultarModelosAtravesDoAno`
- **Vantagem**: Descobre lançamentos sem reprocessar tudo (~10 min vs várias horas)

### Atualização Completa de Valores

- **Quando**: Mensalmente após atualizar modelos
- **Script**: `atualizar_valores.py`
- **Como funciona**: Busca valores de todos os veículos cadastrados (marca+modelo+ano)
- **Necessidade**: Valores FIPE mudam mensalmente, precisam ser atualizados completamente

### População Inicial

- **Quando**: Apenas uma vez (ou para repopular do zero)
- **Script**: `popular_banco_otimizado.py`
- **Como funciona**: Busca TODAS as marcas, modelos e anos disponíveis
- **Tempo**: 2-4 horas com 5 workers paralelos
- **Vantagens**: Gravação local (SQLite), paralelização, estratégia inteligente

## Troubleshooting

### Erro SSL/Certificate

- **Verificar**: Certificados em `certs/`
- **Verificar**: Import de `httpx_ssl_patch` no início do arquivo
- **Solução**: `verify=False` em todas as requisições

### Erro RLS Policy (42501)

- **Causa**: Role `anon` sem permissão INSERT/UPDATE
- **Solução**: Executar `fix_rls_policies.sql`

### Erro Foreign Key Constraint

- **Causa**: Tentando salvar modelos/anos antes das marcas
- **Solução**: Respeitar ordem: tabelas_referencia → marcas → modelos → anos → valores

### Timeout/Rate Limiting

- **Causa**: Muitas requisições seguidas ou delays insuficientes
- **Identificação**: Erro 429 (Too Many Requests) nos logs
- **Solução Imediata**: Scripts já implementam retry automático com delay de 30s
- **Solução Permanente**: Ajustar delays em `src/config.py` se necessário:
  ```python
  def get_delay_padrao():
      return random.uniform(1.0, 1.5)  # Aumentar de 0.8-1.2s para 1.0-1.5s
  ```
- **Monitoramento**: Taxa de erros 429 deve ser < 5% das requisições

## Gestão de Schema de Banco de Dados

**IMPORTANTE**: Sempre que houver qualquer alteração no schema do banco de dados (tabelas, colunas, índices, triggers, constraints, etc.), você DEVE atualizar ambos os arquivos:

1. **scripts_banco/database_schema.sql**: Script SQL completo com a estrutura atualizada do banco
2. **docs/database_schema.md**: Documentação em Markdown refletindo as mudanças

### Processo de Alteração de Banco

1. Fazer a alteração no script SQL principal (`database_schema.sql`)
2. Criar script de migração em `scripts_banco/migrations/` (se aplicável)
3. Atualizar documentação Markdown (`docs/database_schema.md`)
4. Testar alterações no Supabase antes de commitar
5. Documentar razão da alteração nos comentários do commit

### Sincronização SQL ↔ MD

- **database_schema.sql**: Fonte de verdade técnica (executável)
- **database_schema.md**: Documentação legível para desenvolvedores
- Ambos devem estar sempre sincronizados
- Qualquer divergência entre eles é considerada um bug

## Boas Práticas

1. **Sempre ativar ambiente virtual** antes de executar scripts
2. **Não commitar** arquivos `.env` ou `certs/`
3. **Usar cache** para evitar requisições desnecessárias
4. **Respeitar rate limits** da API FIPE
5. **Validar dados** antes de salvar no banco
6. **Logar operações** para debugging
7. **Tratar exceções** adequadamente
8. **Documentar funções** com docstrings
9. **Testar em pequena escala** antes de popular banco completo
10. **Fazer backup** do banco antes de operações destrutivas
11. **Atualizar SQL e MD** sempre que houver alteração de schema no banco

## Referências

- **API FIPE**: https://veiculos.fipe.org.br
- **Supabase Docs**: https://supabase.com/docs/reference/python/introduction
- **Requests Docs**: https://docs.python-requests.org/
