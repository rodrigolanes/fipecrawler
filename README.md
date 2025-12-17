# 🚗 FIPE Crawler

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Crawler Python otimizado para coletar e armazenar dados de veículos da **Tabela FIPE** (Fundação Instituto de Pesquisas Econômicas), com sistema de cache duplo (SQLite local + Supabase PostgreSQL) para máxima performance e confiabilidade.

## 📋 Índice

- [Características](#-características)
- [Arquitetura](#-arquitetura)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Configuração](#️-configuração)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Scripts Disponíveis](#-scripts-disponíveis)
- [API FIPE](#-api-fipe)
- [Banco de Dados](#-banco-de-dados)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)

## ✨ Características

- 🚀 **Alta Performance**: Cache duplo (SQLite + Supabase) com processamento paralelo
- 🔄 **Atualização Incremental**: Busca apenas novos modelos e valores (não reprocessa tudo)
- 💾 **Persistência**: SQLite local para gravação rápida + Supabase cloud para acesso remoto
- 🔐 **SSL Corporativo**: Suporte a ambientes com proxy/certificados customizados
- 📊 **Estatísticas**: Logs detalhados de progresso e análise de performance
- 🛡️ **Rate Limiting**: Delays inteligentes para evitar bloqueio da API
- 🔁 **Retry Logic**: Tentativas automáticas em caso de falhas temporárias
- 🧵 **Thread-Safe**: Processamento paralelo seguro com locks

## 🏗 Arquitetura

```
┌─────────────┐
│  API FIPE   │ ← Requisições HTTP (com delays)
└──────┬──────┘
       │
       ▼
┌──────────────┐
│ fipe_crawler │ ← Funções de coleta
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ fipe_local_cache     │ ← SQLite (gravação rápida)
│ (fipe_local.db)      │
└──────┬───────────────┘
       │
       ▼ (upload em lote)
┌──────────────────────┐
│ Supabase PostgreSQL  │ ← Cloud (acesso remoto)
│ (fipe_cache)         │
└──────────────────────┘
```

### Fluxo de Dados

1. **Coleta**: Scripts buscam dados da API FIPE
2. **Cache Local**: Gravação rápida no SQLite (thread-safe)
3. **Upload**: Sincronização em lote para Supabase
4. **Consulta**: Aplicações podem usar SQLite (local) ou Supabase (remoto)

## 📦 Requisitos

### Software

- **Python**: 3.13.2 ou superior
- **SQLite**: 3.x (incluído no Python)
- **Supabase**: Conta gratuita ou Pro

### Dependências Python

```
requests==2.31.0
supabase==2.3.4
python-dotenv==1.0.0
```

## 🔧 Instalação

### 1. Clone o Repositório

```bash
git clone <url-do-repositorio>
cd fipecrawler
```

### 2. Crie o Ambiente Virtual

```bash
python -m venv .venv
```

### 3. Ative o Ambiente Virtual

**Windows (PowerShell)**:
```powershell
.venv\Scripts\activate
```

**Windows (CMD)**:
```cmd
.venv\Scripts\activate.bat
```

**Linux/Mac**:
```bash
source .venv/bin/activate
```

### 4. Instale as Dependências

```bash
pip install -r requirements.txt
```

## ⚙️ Configuração

### 1. Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Supabase (obrigatório para upload remoto)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua_anon_key_aqui
```

**Nota**: Se for usar apenas SQLite local, o `.env` é opcional.

### 2. Certificados SSL (Opcional)

Para ambientes corporativos com proxy:

```
certs/
├── petrobras_root_cadeia.pem
└── certadmin.pem
```

O arquivo `httpx_ssl_patch.py` configura automaticamente os certificados.

### 3. Configurar Banco Supabase (Primeira Vez)

Execute os scripts SQL no Supabase SQL Editor:

```bash
# Ordem de execução:
1. scripts_banco/database_schema.sql
2. scripts_banco/fix_rls_policies.sql (se houver erro de permissão)
```

## 🚀 Uso

### População Inicial (Primeira Vez)

Coleta **TODOS** os dados da FIPE (marcas, modelos, anos, valores):

```bash
python popular_banco_otimizado.py
```

**Características**:
- ⏱️ Tempo: 2-4 horas (depende da conexão)
- 💾 Resultado: ~250.000 registros no SQLite
- 🚀 Usa paralelização (5 workers padrão)
- 📊 Progresso detalhado em tempo real

**Opções**:
```bash
# Configurar número de workers paralelos
python popular_banco_otimizado.py
# Quando perguntado, escolha 1-10 workers (padrão: 5)
```

### Atualização Mensal de Modelos

Busca **apenas novos modelos** Zero Km (lançamentos):

```bash
python atualizar_modelos.py
```

**Características**:
- ⏱️ Tempo: 10-15 minutos
- 🔍 Busca só modelos Zero Km (novos)
- 📅 Executar: Início do mês (após FIPE atualizar)

### Atualização Mensal de Valores

Atualiza **valores FIPE** de todos os veículos cadastrados:

```bash
python atualizar_valores.py
```

**Características**:
- ⏱️ Tempo: 3-6 horas (depende da quantidade)
- 💰 Atualiza preços de todos os veículos
- 📅 Executar: Após FIPE publicar nova tabela
- ♻️ Pode ser interrompido (Ctrl+C) e retomado

### Upload para Supabase

Sincroniza dados do SQLite local para Supabase:

```bash
python upload_para_supabase.py
```

**Características**:
- ⏱️ Tempo: 5-15 minutos
- 📤 Upload em lotes de 1000 registros
- ✅ Verifica integridade após upload
- 🔄 Suporta re-execução (idempotente)

## 📂 Estrutura do Projeto

```
fipecrawler/
├── .env                          # Variáveis de ambiente (não commitado)
├── .env.example                  # Exemplo de configuração
├── requirements.txt              # Dependências Python
├── fipe_local.db                 # SQLite local (não commitado)
│
├── fipe_crawler.py               # 🌐 Funções de requisição à API FIPE
├── fipe_local_cache.py           # 💾 Cache SQLite (rápido)
├── fipe_cache.py                 # ☁️ Cache Supabase (remoto)
│
├── popular_banco_otimizado.py    # 🚀 População inicial paralela
├── atualizar_modelos.py          # 🔄 Atualização incremental de modelos
├── atualizar_valores.py          # 💰 Atualização mensal de valores
├── upload_para_supabase.py       # 📤 Sincronização SQLite → Supabase
│
├── supabase_client.py            # 🔌 Cliente Supabase singleton
├── httpx_ssl_patch.py            # 🔒 Patch SSL para ambientes corporativos
├── ssl_config.py                 # 🔐 Configuração de certificados
│
├── docs/
│   └── database_schema.md        # 📖 Documentação do schema
│
├── scripts_banco/
│   ├── database_schema.sql       # 🗄️ Schema completo do banco
│   ├── drop_database.sql         # ⚠️ Script para limpar banco
│   └── migrations/               # 🔄 Migrações de schema
│
├── .github/
│   └── copilot-instructions.md   # 🤖 Instruções para GitHub Copilot
│
└── README.md                     # 📚 Este arquivo
```

## 📜 Scripts Disponíveis

### 1. `popular_banco_otimizado.py`

**Quando usar**: Primeira vez ou para repopular do zero

**O que faz**:
- Busca todas as marcas de carros
- Para cada marca:
  - Busca modelos (estratégia inteligente: por modelo ou por ano)
  - Busca anos/combustível de cada modelo
- Grava tudo no SQLite local

**Estratégias de coleta**:
- **Poucos modelos** (<50): Busca anos de cada modelo
- **Muitos modelos** (≥50): Busca modelos de cada ano/combustível

**Configuração**:
```python
# Editar no código ou via prompt:
max_workers=5  # Número de marcas em paralelo (1-10)
```

### 2. `atualizar_modelos.py`

**Quando usar**: Mensalmente (início do mês)

**O que faz**:
- Para cada marca:
  - Busca modelos Zero Km em todos os combustíveis (1-7)
  - Adiciona apenas modelos novos
  - Busca anos disponíveis dos modelos novos

**Otimização**:
- Não reprocessa modelos já cadastrados
- ~90% mais rápido que população completa

### 3. `atualizar_valores.py`

**Quando usar**: Mensalmente (após nova tabela FIPE)

**O que faz**:
- Busca valores atualizados de TODOS os veículos cadastrados
- Apenas veículos sem valor no mês atual são processados
- Salva histórico completo (permite análise temporal)

**Interrupção segura**:
- Commit a cada 10 registros
- Ctrl+C salva progresso
- Pode retomar de onde parou

### 4. `upload_para_supabase.py`

**Quando usar**: Após popular/atualizar localmente

**O que faz**:
- Lê dados do SQLite local
- Envia para Supabase em lotes de 1000
- Usa UPSERT (não duplica dados)
- Mostra estatísticas comparativas

## 🌐 API FIPE

### Endpoint Base

```
https://veiculos.fipe.org.br/api/veiculos
```

### Principais Endpoints

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/ConsultarTabelaDeReferencia` | POST | Lista de meses/anos disponíveis |
| `/ConsultarMarcas` | POST | Marcas de veículos |
| `/ConsultarModelos` | POST | Modelos de uma marca |
| `/ConsultarAnoModelo` | POST | Anos/combustível de um modelo |
| `/ConsultarModelosAtravesDoAno` | POST | Modelos disponíveis em um ano |
| `/ConsultarValorComTodosParametros` | POST | Valor FIPE completo |

### Códigos de Referência

#### Tipo de Veículo
- `1`: Carros
- `2`: Motos
- `3`: Caminhões

#### Combustível
| Código | Nome |
|--------|------|
| 1 | Gasolina |
| 2 | Álcool/Etanol |
| 3 | Diesel |
| 4 | Elétrico |
| 5 | Flex |
| 6 | Híbrido |
| 7 | Gás Natural (GNV) |

#### Ano Especial
- `32000`: Representa veículos "Zero Km" (novos)

### Exemplo de Requisição

```python
import requests

url = "https://veiculos.fipe.org.br/api/veiculos/ConsultarMarcas"
headers = {
    "Content-Type": "application/json",
    "Referer": "https://veiculos.fipe.org.br"
}
payload = {
    "codigoTabelaReferencia": 328,  # Dezembro/2025
    "codigoTipoVeiculo": 1  # Carros
}

response = requests.post(url, json=payload, headers=headers, verify=False)
marcas = response.json()
```

## 🗄️ Banco de Dados

### SQLite Local

**Arquivo**: `fipe_local.db`

**Vantagens**:
- ⚡ Gravação extremamente rápida
- 💻 Funciona offline
- 🔒 Não requer credenciais
- 📊 Ideal para coleta e análise local

**Tabelas**: Espelho do Supabase (veja schema abaixo)

### Supabase PostgreSQL

**URL**: Configurado em `.env`

**Vantagens**:
- ☁️ Acesso remoto de qualquer lugar
- 🔐 Row Level Security (RLS)
- 📈 Escalável
- 🔄 Backup automático

### Schema do Banco

```sql
-- Principais tabelas (ordem de dependência):

1. tabelas_referencia (código + mês)
2. marcas (código + nome)
3. modelos (código + nome + FK marca)
4. anos_combustivel (código combinado: "2024-1")
5. modelos_anos (N:N entre modelos e anos)
6. valores_fipe (histórico de preços)
```

**Documentação completa**: [docs/database_schema.md](docs/database_schema.md)

### Relacionamentos

```
marcas (1) ──→ (N) modelos (N) ──→ (N:N) modelos_anos (N) ──→ (1) anos_combustivel
   ↓                    ↓
valores_fipe       valores_fipe
```

## 🔍 Troubleshooting

### Problema: Erro SSL/Certificate

**Sintoma**: `SSLError`, `CERTIFICATE_VERIFY_FAILED`

**Solução**:
```python
# Certifique-se de importar httpx_ssl_patch PRIMEIRO
import httpx_ssl_patch  # ← SEMPRE primeiro
from supabase_client import get_supabase_client
```

### Problema: Erro 42501 (RLS Policy)

**Sintoma**: `new row violates row-level security policy`

**Solução**:
```bash
# Execute no Supabase SQL Editor:
scripts_banco/fix_rls_policies.sql
```

### Problema: Rate Limiting (HTTP 429)

**Sintoma**: `Too Many Requests`, bloqueio temporário

**Solução**:
- Os scripts já têm delays automáticos
- Se persistir, aumente os delays em `fipe_crawler.py`:
  ```python
  time.sleep(random.uniform(2.0, 3.0))  # Aumentar valores
  ```

### Problema: Foreign Key Constraint

**Sintoma**: `FOREIGN KEY constraint failed`

**Solução**:
- Sempre respeite a ordem de execução:
  1. `popular_banco_otimizado.py` (cria estrutura)
  2. `atualizar_modelos.py` (adiciona modelos)
  3. `atualizar_valores.py` (adiciona valores)
  4. `upload_para_supabase.py` (sincroniza)

### Problema: Marca/Modelo Sem Anos

**Sintoma**: Modelos cadastrados mas sem relacionamentos `modelos_anos`

**Solução**:
```python
# O script otimizado detecta e reprocessa automaticamente
python popular_banco_otimizado.py
# Escolha mesma configuração de workers
```

### Problema: Processo Travado

**Sintoma**: Script parou de responder

**Solução**:
1. Verifique conexão com internet
2. Aguarde 2-3 minutos (pode ser delay de rate limiting)
3. Se persistir: Ctrl+C (progresso é salvo a cada 10 registros)
4. Execute novamente (retoma de onde parou)

## 🛣️ Roadmap

### Versão 1.1 (Atual)
- [x] Cache duplo (SQLite + Supabase)
- [x] Processamento paralelo
- [x] Atualização incremental
- [x] Retry logic
- [x] Documentação completa

### Versão 1.2 (Próxima)
- [ ] API REST com FastAPI
- [ ] Dashboard de estatísticas
- [ ] Suporte a motos e caminhões
- [ ] Exportação para CSV/Excel
- [ ] Testes automatizados

### Versão 2.0 (Futuro)
- [ ] Análise de tendências de preços
- [ ] Machine Learning para predição
- [ ] Sistema de alertas (novos modelos/mudanças)
- [ ] Interface web completa

## 🤝 Contribuindo

Contribuições são bem-vindas! Siga o processo:

1. **Fork** o repositório
2. **Clone** seu fork: `git clone <seu-fork>`
3. **Crie branch**: `git checkout -b feature/minha-feature`
4. **Commit**: `git commit -m "feat: adiciona nova feature"`
5. **Push**: `git push origin feature/minha-feature`
6. **Pull Request**: Abra PR para `main`

### Convenção de Commits

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Documentação
- `refactor:` Refatoração de código
- `test:` Adição de testes
- `chore:` Manutenção geral

### Diretrizes de Código

- **Idioma**: Português (BR) para código e documentação
- **Estilo**: PEP 8 (Python)
- **Docstrings**: Google Style
- **Type Hints**: Usar sempre que possível

## 📄 Licença

Este projeto está licenciado sob a **MIT License** - veja o arquivo [LICENSE](LICENSE) para detalhes.

---

## 📞 Contato

- **Projeto**: FIPE Crawler
- **Autor**: Rodrigo
- **Ambiente**: Petrobras (ambiente corporativo)

---

## 🙏 Agradecimentos

- **FIPE** - Por disponibilizar a API pública
- **Supabase** - Pela infraestrutura cloud PostgreSQL
- **Python Community** - Pelas excelentes bibliotecas

---

## 📊 Estatísticas do Projeto

| Métrica | Valor |
|---------|-------|
| Marcas cadastradas | ~100 |
| Modelos cadastrados | ~30.000 |
| Anos/Combustível | ~500 |
| Relacionamentos | ~250.000 |
| Valores FIPE | ~250.000+ |
| Performance | 10x mais rápido que v1.0 |

---

**Última atualização**: 16 de dezembro de 2025
