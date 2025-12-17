# 📂 Estrutura de Scripts - FIPE Crawler

## 🎯 Organização por Fluxo de Dados

```
scripts/
├── 1_carga_inicial/          [API → SQLite] Execução única ou eventual
├── 2_atualizacao_mensal/     [API → SQLite] Execução mensal obrigatória
└── 3_sincronizacao/          [SQLite → Supabase] Após carga/atualização
```

---

## 📦 1. Carga Inicial (Execução Única)

### `popular_completo.py`
**Quando executar:** Apenas UMA VEZ na configuração inicial do projeto, ou para repopular do zero.

**O que faz:**
- Busca TODAS as marcas de carros, motos e caminhões da API FIPE
- Busca TODOS os modelos de cada marca
- Busca TODOS os anos e combustíveis de cada modelo
- Salva tudo no SQLite local (fipe_local.db)

**Características:**
- ⚡ Processamento paralelo (5 marcas simultâneas)
- 🧠 Estratégia inteligente (escolhe buscar por modelo ou por ano conforme mais eficiente)
- 💾 Gravação local (100x mais rápido que Supabase)
- 🔒 Thread-safe com locks

**Tempo estimado:** 2-4 horas com 5 workers

**Comando:**
```bash
python scripts/1_carga_inicial/popular_completo.py
```

---

### `corrigir_relacionamentos.py`
**Quando executar:** Quando necessário corrigir relacionamentos faltantes ou órfãos.

**O que faz:**
- Repopula relacionamentos marca→modelo→ano/combustível
- Útil após correção de bugs ou para preencher dados faltantes
- Permite escolher tipo de veículo (carros, motos, caminhões ou todos)

**Características:**
- 🔄 Retry automático em caso de rate limiting
- 📊 Estratégia inteligente (por modelo vs por ano)
- 🎯 Processa apenas relacionamentos faltantes

**Tempo estimado:** Varia conforme quantidade de dados faltantes

**Comando:**
```bash
python scripts/1_carga_inicial/corrigir_relacionamentos.py
```

---

## 🗓️ 2. Atualização Mensal (Obrigatória)

> **Execute no início de cada mês quando a tabela FIPE é atualizada (geralmente primeira semana do mês)**

### `executar_mes.py` ⭐ **RECOMENDADO**
**Script principal que executa toda a rotina mensal em sequência.**

**O que faz:**
1. Executa `1_atualizar_modelos.py` (novos modelos)
2. Executa `2_atualizar_valores.py` (valores do mês)
3. Mostra relatório completo ao final

**Comando:**
```bash
python scripts/2_atualizacao_mensal/executar_mes.py
```

**Tempo estimado:** ~10-15 min (modelos) + várias horas (valores)

---

### `1_atualizar_modelos.py`
**Quando executar:** Início do mês (antes de atualizar valores)

**O que faz:**
- Busca novos modelos Zero Km de TODAS as marcas
- Descobre lançamentos sem reprocessar tudo
- Endpoint especial: `/ConsultarModelosAtravesDoAno`

**Por que executar:**
- Novos modelos lançados no mês
- Necessário cadastrar antes de buscar valores

**Tempo estimado:** ~10-15 minutos

**Comando:**
```bash
python scripts/2_atualizacao_mensal/1_atualizar_modelos.py
```

---

### `2_atualizar_valores.py`
**Quando executar:** Após atualizar modelos, início do mês

**O que faz:**
- Busca valores FIPE atualizados de TODOS os veículos cadastrados
- Atualiza preços do mês de referência atual
- Salva no SQLite local

**Por que executar:**
- Valores FIPE mudam mensalmente
- Necessário para ter preços atualizados

**Tempo estimado:** Várias horas (depende da quantidade de veículos)

**Características:**
- 📊 Busca apenas veículos sem valor do mês atual
- 💾 Commit a cada 10 registros (não perde progresso)
- 🔄 Pode ser interrompido (Ctrl+C) e retomado

**Comando:**
```bash
python scripts/2_atualizacao_mensal/2_atualizar_valores.py
```

---

## 🔄 3. Sincronização (Após Carga/Atualização)

### `sincronizar_supabase.py`
**Quando executar:** Após popular/atualizar dados locais

**O que faz:**
- Envia dados do SQLite local para Supabase PostgreSQL
- Upload em lotes de 1000 registros
- Mostra estatísticas comparativas ao final

**Características:**
- 📦 Upload em lotes (performance)
- 🔁 Idempotente (pode executar múltiplas vezes)
- ✅ Upsert (atualiza se existir, insere se não existir)
- 📊 Relatório comparativo SQLite vs Supabase

**Tempo estimado:** 10-30 minutos (depende da quantidade de dados)

**Comando:**
```bash
python scripts/3_sincronizacao/sincronizar_supabase.py
```

---

## 🔄 Fluxo Completo Mensal

```
┌─────────────────────────────────────────────────────┐
│  INÍCIO DO MÊS (quando FIPE atualiza)               │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  1️⃣  ATUALIZAR MODELOS                              │
│  python 2_atualizacao_mensal/1_atualizar_modelos.py │
│  (~10-15 minutos)                                   │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  2️⃣  ATUALIZAR VALORES                              │
│  python 2_atualizacao_mensal/2_atualizar_valores.py │
│  (várias horas)                                     │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  3️⃣  SINCRONIZAR COM SUPABASE                       │
│  python 3_sincronizacao/sincronizar_supabase.py     │
│  (~10-30 minutos)                                   │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
                   ✅ PRONTO!
```

**OU use o script automatizado:**

```bash
# Executa etapas 1 e 2 automaticamente
python scripts/2_atualizacao_mensal/executar_mes.py

# Depois sincronize
python scripts/3_sincronizacao/sincronizar_supabase.py
```

---

## 📊 Resumo Rápido

| Script | Quando | Tempo | Fluxo |
|--------|--------|-------|-------|
| `popular_completo.py` | 1x (inicial) | 2-4h | API → SQLite |
| `corrigir_relacionamentos.py` | Eventual | Varia | API → SQLite |
| `1_atualizar_modelos.py` | Mensal | 10-15min | API → SQLite |
| `2_atualizar_valores.py` | Mensal | Horas | API → SQLite |
| `executar_mes.py` ⭐ | Mensal | = 1+2 | API → SQLite |
| `sincronizar_supabase.py` | Após carga | 10-30min | SQLite → Supabase |

---

## ⚡ Comandos Rápidos

**Configuração Inicial (primeira vez):**
```bash
python scripts/1_carga_inicial/popular_completo.py
python scripts/3_sincronizacao/sincronizar_supabase.py
```

**Atualização Mensal (todo mês):**
```bash
# Opção 1: Script automatizado (recomendado)
python scripts/2_atualizacao_mensal/executar_mes.py
python scripts/3_sincronizacao/sincronizar_supabase.py

# Opção 2: Passo a passo
python scripts/2_atualizacao_mensal/1_atualizar_modelos.py
python scripts/2_atualizacao_mensal/2_atualizar_valores.py
python scripts/3_sincronizacao/sincronizar_supabase.py
```

**Correção Eventual:**
```bash
python scripts/1_carga_inicial/corrigir_relacionamentos.py
python scripts/3_sincronizacao/sincronizar_supabase.py
```

---

## 💡 Dicas

- ✅ Sempre ative o ambiente virtual antes: `.venv\Scripts\activate` (Windows)
- ✅ Verifique conexão com internet antes de executar scripts de API
- ✅ Scripts de atualização podem ser interrompidos (Ctrl+C) e retomados
- ✅ Dados são salvos no SQLite local primeiro (mais rápido)
- ✅ Sincronize com Supabase quando tiver certeza que dados estão corretos
- ⚠️  Atualização de valores pode levar várias horas, execute em horário apropriado
