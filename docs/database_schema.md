# Esquema do Banco de Dados - FIPE Crawler (Supabase PostgreSQL)

## Visão Geral

Banco de dados PostgreSQL hospedado no Supabase para armazenar dados da tabela FIPE (Fundação Instituto de Pesquisas Econômicas).

**URL**: `https://frnfahrjfmnggeaccyty.supabase.co`

## Índice

- [Diagrama de Relacionamentos](#diagrama-de-relacionamentos)
- [Tabelas](#tabelas)
  - [marcas](#1-marcas)
  - [modelos](#2-modelos)
  - [anos_combustivel](#3-anos_combustivel)
  - [modelos_anos](#4-modelos_anos-relacionamento-nn)
  - [valores_fipe](#5-valores_fipe)
  - [tabelas_referencia](#6-tabelas_referencia)
- [Códigos de Referência](#códigos-de-referência)
- [Índices](#índices)
- [Triggers](#triggers)
- [Row Level Security (RLS)](#row-level-security-rls)

---

## Diagrama de Relacionamentos

```
tabelas_referencia
       ↓
marcas (1) ←───── (N) modelos (N) ───→ modelos_anos (N) ───→ anos_combustivel
   ↓                    ↓
valores_fipe         valores_fipe
```

**Relacionamentos**:

- `marcas` → `modelos`: 1:N (uma marca tem vários modelos)
- `modelos` → `modelos_anos`: N:N (um modelo pode ter vários anos/combustíveis)
- `anos_combustivel` → `modelos_anos`: 1:N (um ano/combustível pode estar em vários modelos)
- `modelos` → `valores_fipe`: 1:N (um modelo pode ter vários valores históricos)

---

## Tabelas

### 1. `marcas`

Armazena todas as marcas de veículos disponíveis na tabela FIPE.

| Coluna         | Tipo                     | Tamanho | Constraints      | Descrição                              |
| -------------- | ------------------------ | ------- | ---------------- | -------------------------------------- |
| `id`           | BIGSERIAL                | -       | PRIMARY KEY      | Identificador interno sequencial       |
| `codigo`       | INTEGER                  | 4 bytes | NOT NULL, UNIQUE | Código da marca na FIPE (ex: 6 = Audi) |
| `nome`         | VARCHAR                  | 255     | NOT NULL         | Nome da marca (ex: "Audi", "Fiat")     |
| `tipo_veiculo` | INTEGER                  | 4 bytes | NOT NULL         | 1=carro, 2=moto, 3=caminhão            |
| `created_at`   | TIMESTAMP WITH TIME ZONE | 8 bytes | DEFAULT NOW()    | Data de criação do registro            |
| `updated_at`   | TIMESTAMP WITH TIME ZONE | 8 bytes | DEFAULT NOW()    | Data da última atualização             |

**Índices**:

- `idx_marcas_codigo` em `codigo`
- `idx_marcas_tipo_veiculo` em `tipo_veiculo`

**Exemplo de registro**:

```json
{
  "codigo": 6,
  "nome": "Audi",
  "tipo_veiculo": 1
}
```

---

### 2. `modelos`

Armazena todos os modelos de veículos por marca.

| Coluna         | Tipo                     | Tamanho  | Constraints   | Descrição                           |
| -------------- | ------------------------ | -------- | ------------- | ----------------------------------- |
| `id`           | BIGSERIAL                | -        | PRIMARY KEY   | Identificador interno sequencial    |
| `codigo`       | INTEGER                  | 4 bytes  | NOT NULL      | Código do modelo na FIPE (ex: 5496) |
| `nome`         | TEXT                     | variável | NOT NULL      | Nome completo do modelo             |
| `codigo_marca` | INTEGER                  | 4 bytes  | NOT NULL, FK  | Referência à marca                  |
| `created_at`   | TIMESTAMP WITH TIME ZONE | 8 bytes  | DEFAULT NOW() | Data de criação do registro         |
| `updated_at`   | TIMESTAMP WITH TIME ZONE | 8 bytes  | DEFAULT NOW() | Data da última atualização          |

**Constraints**:

- `UNIQUE(codigo, codigo_marca)` - combinação única
- `FOREIGN KEY (codigo_marca) REFERENCES marcas(codigo) ON DELETE CASCADE`

**Índices**:

- `idx_modelos_codigo` em `codigo`
- `idx_modelos_codigo_marca` em `codigo_marca`

**Exemplo de registro**:

```json
{
  "codigo": 5496,
  "nome": "A1 Sportback 1.4 TFSI S tronic",
  "codigo_marca": 6
}
```

---

### 3. `anos_combustivel`

Armazena combinações únicas de ano e tipo de combustível disponíveis.

| Coluna               | Tipo                     | Tamanho | Constraints      | Descrição                                                    |
| -------------------- | ------------------------ | ------- | ---------------- | ------------------------------------------------------------ |
| `id`                 | BIGSERIAL                | -       | PRIMARY KEY      | Identificador interno sequencial                             |
| `codigo`             | VARCHAR                  | 50      | NOT NULL, UNIQUE | Código combinado "ano-combustível" (ex: "2014-1", "32000-6") |
| `nome`               | VARCHAR                  | 100     | NOT NULL         | Nome legível (ex: "2014 Gasolina", "Zero Km")                |
| `ano`                | VARCHAR                  | 10      | -                | Ano extraído (ex: "2014" ou "32000" para Zero Km)            |
| `codigo_combustivel` | INTEGER                  | 4 bytes | -                | Código do combustível (1-7)                                  |
| `combustivel`        | VARCHAR                  | 50      | -                | Nome do combustível extraído                                 |
| `created_at`         | TIMESTAMP WITH TIME ZONE | 8 bytes | DEFAULT NOW()    | Data de criação do registro                                  |

**Índices**:

- `idx_anos_combustivel_codigo` em `codigo`
- `idx_anos_combustivel_ano` em `ano`
- `idx_anos_combustivel_combustivel` em `codigo_combustivel`

**Códigos de Combustível**:
| Código | Nome |
|--------|------|
| 1 | Gasolina |
| 2 | Álcool/Etanol |
| 3 | Diesel |
| 4 | Elétrico |
| 5 | Flex |
| 6 | Híbrido |
| 7 | Gás Natural |

**Exemplos de registros**:

```json
[
  {
    "codigo": "2014-1",
    "nome": "2014 Gasolina",
    "ano": "2014",
    "codigo_combustivel": 1,
    "combustivel": "Gasolina"
  },
  {
    "codigo": "32000-6",
    "nome": "Zero Km",
    "ano": "32000",
    "codigo_combustivel": 6,
    "combustivel": "Híbrido"
  }
]
```

---

### 4. `modelos_anos` (Relacionamento N:N)

Define quais combinações de ano/combustível estão disponíveis para cada modelo.

| Coluna                   | Tipo                     | Tamanho | Constraints   | Descrição                                |
| ------------------------ | ------------------------ | ------- | ------------- | ---------------------------------------- |
| `id`                     | BIGSERIAL                | -       | PRIMARY KEY   | Identificador interno sequencial         |
| `codigo_marca`           | INTEGER                  | 4 bytes | NOT NULL      | Código da marca                          |
| `codigo_modelo`          | INTEGER                  | 4 bytes | NOT NULL      | Código do modelo                         |
| `codigo_ano_combustivel` | VARCHAR                  | 50      | NOT NULL, FK  | Código do ano/combustível (ex: "2014-1") |
| `created_at`             | TIMESTAMP WITH TIME ZONE | 8 bytes | DEFAULT NOW() | Data de criação do registro              |

**Constraints**:

- `UNIQUE(codigo_marca, codigo_modelo, codigo_ano_combustivel)` - combinação única
- `FOREIGN KEY (codigo_modelo, codigo_marca) REFERENCES modelos(codigo, codigo_marca) ON DELETE CASCADE`
- `FOREIGN KEY (codigo_ano_combustivel) REFERENCES anos_combustivel(codigo) ON DELETE CASCADE`

**Índices**:

- `idx_modelos_anos_modelo` em `(codigo_marca, codigo_modelo)`
- `idx_modelos_anos_ano_combustivel` em `codigo_ano_combustivel`

**Exemplo de registro**:

```json
{
  "codigo_marca": 6,
  "codigo_modelo": 5496,
  "codigo_ano_combustivel": "2014-1"
}
```

**Interpretação**: O modelo Audi A1 (código 5496) está disponível no ano 2014 com motor Gasolina.

---

### 5. `valores_fipe`

Armazena o histórico de valores consultados na tabela FIPE para cada veículo.

| Coluna                   | Tipo                     | Tamanho  | Constraints   | Descrição                                               |
| ------------------------ | ------------------------ | -------- | ------------- | ------------------------------------------------------- |
| `id`                     | BIGSERIAL                | -        | PRIMARY KEY   | Identificador interno sequencial                        |
| `codigo_marca`           | INTEGER                  | 4 bytes  | NOT NULL      | Código da marca                                         |
| `codigo_modelo`          | INTEGER                  | 4 bytes  | NOT NULL      | Código do modelo                                        |
| `ano_modelo`             | INTEGER                  | 4 bytes  | NOT NULL      | Ano do veículo (ex: 2014 ou 32000 para Zero Km)         |
| `codigo_combustivel`     | INTEGER                  | 4 bytes  | NOT NULL      | Código do tipo de combustível (1-7)                     |
| `codigo_ano_combustivel` | VARCHAR                  | 20       | -             | Código combinado para JOIN direto (ex: "2014-1")        |
| `valor`                  | VARCHAR                  | 50       | NOT NULL      | Valor formatado (ex: "R$ 69.252,00")                    |
| `valor_numerico`         | DECIMAL                  | 12, 2    | -             | Valor numérico para cálculos (ex: 69252.00)             |
| `codigo_fipe`            | VARCHAR                  | 20       | -             | Código FIPE do veículo (ex: "008153-1")                 |
| `mes_referencia`         | VARCHAR                  | 50       | -             | Mês de referência (ex: "dezembro de 2025")              |
| `codigo_referencia`      | INTEGER                  | 4 bytes  | -             | Código da tabela de referência (ex: 328)                |
| `data_consulta`          | TIMESTAMP WITH TIME ZONE | 8 bytes  | NOT NULL      | Data/hora da consulta à API                             |
| `marca`                  | VARCHAR                  | 100      | -             | Nome da marca (desnormalizado para facilitar consultas) |
| `modelo`                 | TEXT                     | variável | -             | Nome do modelo (desnormalizado)                         |
| `combustivel`            | VARCHAR                  | 100      | -             | Nome do combustível (desnormalizado)                    |
| `created_at`             | TIMESTAMP WITH TIME ZONE | 8 bytes  | DEFAULT NOW() | Data de criação do registro                             |

**Constraints**:

- `FOREIGN KEY (codigo_modelo, codigo_marca) REFERENCES modelos(codigo, codigo_marca) ON DELETE CASCADE`

**Constraints**:

- `UNIQUE (codigo_marca, codigo_modelo, ano_modelo, codigo_combustivel, mes_referencia)` - previne valores duplicados do mesmo veículo no mesmo mês
- `FOREIGN KEY (codigo_modelo, codigo_marca) REFERENCES modelos(codigo, codigo_marca) ON DELETE CASCADE`

**Índices**:

- `idx_valores_fipe_veiculo` em `(codigo_marca, codigo_modelo, ano_modelo, codigo_combustivel)` - busca por veículo
- `idx_valores_fipe_codigo_fipe` em `codigo_fipe` - busca por código FIPE
- `idx_valores_fipe_data_consulta` em `data_consulta DESC` - busca por data (mais recentes primeiro)
- `idx_valores_fipe_mes_referencia` em `mes_referencia` - busca por mês de referência
- `idx_valores_fipe_codigo_ano_combustivel` em `codigo_ano_combustivel` - performance JOIN

**Exemplo de registro**:

```json
{
  "codigo_marca": 6,
  "codigo_modelo": 5496,
  "ano_modelo": 2014,
  "codigo_combustivel": 1,
  "codigo_ano_combustivel": "2014-1",
  "valor": "R$ 69.252,00",
  "valor_numerico": 69252.0,
  "codigo_fipe": "008153-1",
  "mes_referencia": "dezembro de 2025",
  "codigo_referencia": 328,
  "data_consulta": "2025-12-15T14:23:10Z",
  "marca": "Audi",
  "modelo": "A1 Sportback 1.4 TFSI S tronic",
  "combustivel": "Gasolina"
}
```

---

### 6. `tabelas_referencia`

Armazena o histórico de tabelas de referência (mês/ano) disponibilizadas pela FIPE.

| Coluna       | Tipo                     | Tamanho | Constraints      | Descrição                                |
| ------------ | ------------------------ | ------- | ---------------- | ---------------------------------------- |
| `id`         | BIGSERIAL                | -       | PRIMARY KEY      | Identificador interno sequencial         |
| `codigo`     | INTEGER                  | 4 bytes | NOT NULL, UNIQUE | Código da tabela de referência (ex: 328) |
| `mes`        | VARCHAR                  | 50      | NOT NULL         | Mês de referência (ex: "dezembro/2025")  |
| `created_at` | TIMESTAMP WITH TIME ZONE | 8 bytes | DEFAULT NOW()    | Data de criação do registro              |

**Índices**:

- `idx_tabelas_referencia_codigo` em `codigo`

**Exemplo de registro**:

```json
{
  "codigo": 328,
  "mes": "dezembro/2025"
}
```

**Nota**: A tabela de referência mais recente (maior código) corresponde ao mês atual.

---

## Códigos de Referência

### Tipo de Veículo

- **1**: Carro
- **2**: Moto
- **3**: Caminhão

### Combustível

| Código | Nome          | Descrição                                |
| ------ | ------------- | ---------------------------------------- |
| 1      | Gasolina      | Motor a gasolina                         |
| 2      | Álcool/Etanol | Motor a álcool ou etanol                 |
| 3      | Diesel        | Motor diesel                             |
| 4      | Elétrico      | Motor 100% elétrico                      |
| 5      | Flex          | Bicombustível (gasolina/etanol)          |
| 6      | Híbrido       | Combinação de motor elétrico e combustão |
| 7      | Gás Natural   | Motor a GNV (Gás Natural Veicular)       |

### Ano Especial

- **32000**: Representa veículos "Zero Km" (novos, sem uso)

---

## Índices

### Performance de Busca

Todos os índices são criados automaticamente pelo schema:

**marcas**:

- `idx_marcas_codigo`: Busca rápida por código de marca
- `idx_marcas_tipo_veiculo`: Filtragem por tipo (carros/motos/caminhões)

**modelos**:

- `idx_modelos_codigo`: Busca por código de modelo
- `idx_modelos_codigo_marca`: Busca todos os modelos de uma marca

**anos_combustivel**:

- `idx_anos_combustivel_codigo`: Busca por código combinado
- `idx_anos_combustivel_ano`: Filtragem por ano
- `idx_anos_combustivel_combustivel`: Filtragem por tipo de combustível

**modelos_anos**:

- `idx_modelos_anos_modelo`: Busca todas as variantes de um modelo
- `idx_modelos_anos_ano_combustivel`: Busca todos os modelos disponíveis para um ano/combustível

**valores_fipe**:

- `idx_valores_fipe_veiculo`: Busca valores de um veículo específico
- `idx_valores_fipe_codigo_fipe`: Busca por código FIPE
- `idx_valores_fipe_data_consulta`: Histórico de valores (mais recentes primeiro)
- `idx_valores_fipe_mes_referencia`: Valores de um mês específico
- `idx_valores_fipe_codigo_ano_combustivel`: Performance JOIN com modelos_anos

**tabelas_referencia**:

- `idx_tabelas_referencia_codigo`: Busca por código de referência

---

## Triggers

### `update_updated_at_column()`

Função PL/pgSQL que atualiza automaticamente o campo `updated_at` sempre que um registro é modificado.

**Ativa em**:

- `marcas`
- `modelos`

**Comportamento**: Antes de cada UPDATE, define `updated_at = NOW()`

---

## Row Level Security (RLS)

### Configuração Geral

Todas as tabelas têm RLS habilitado para controle granular de acesso.

### Políticas de Segurança

#### 1. Leitura Pública (SELECT)

```sql
CREATE POLICY "Permitir leitura pública" ON [tabela]
    FOR SELECT USING (true);
```

**Aplicado em**: Todas as tabelas  
**Permite**: Qualquer usuário pode ler dados

#### 2. Inserção com Autenticação (INSERT)

```sql
CREATE POLICY "Permitir inserção com API key" ON [tabela]
    FOR INSERT
    TO authenticated, anon
    WITH CHECK (true);
```

**Aplicado em**: Todas as tabelas  
**Permite**: Usuários autenticados (via API key) podem inserir dados

#### 3. Atualização com Autenticação (UPDATE)

```sql
CREATE POLICY "Permitir atualização com API key" ON [tabela]
    FOR UPDATE
    TO authenticated, anon
    USING (true)
    WITH CHECK (true);
```

**Aplicado em**: Todas as tabelas  
**Permite**: Necessário para operações UPSERT

### Roles Suportadas

- **authenticated**: Usuários com JWT válido
- **anon**: Usuários com apenas anon key (usada pelos scripts Python)

---

## Consultas Úteis

### Buscar todos os modelos de uma marca

```sql
SELECT m.codigo, m.nome, ma.nome AS marca
FROM modelos m
JOIN marcas ma ON m.codigo_marca = ma.codigo
WHERE ma.codigo = 6  -- Audi
ORDER BY m.nome;
```

### Buscar valores FIPE mais recentes de um veículo

```sql
SELECT v.*, m.nome AS modelo_nome, ma.nome AS marca_nome
FROM valores_fipe v
JOIN modelos m ON v.codigo_modelo = m.codigo AND v.codigo_marca = m.codigo_marca
JOIN marcas ma ON m.codigo_marca = ma.codigo
WHERE v.codigo_marca = 6
  AND v.codigo_modelo = 5496
  AND v.ano_modelo = 2014
ORDER BY v.data_consulta DESC
LIMIT 1;
```

### Contar veículos por marca

```sql
SELECT ma.nome, COUNT(DISTINCT m.codigo) as total_modelos
FROM marcas ma
LEFT JOIN modelos m ON ma.codigo = m.codigo_marca
GROUP BY ma.nome
ORDER BY total_modelos DESC;
```

### Buscar modelos Zero Km disponíveis

```sql
SELECT DISTINCT m.nome, ma.nome AS marca
FROM modelos m
JOIN marcas ma ON m.codigo_marca = ma.codigo
JOIN modelos_anos man ON m.codigo = man.codigo_modelo
  AND m.codigo_marca = man.codigo_marca
JOIN anos_combustivel ac ON man.codigo_ano_combustivel = ac.codigo
WHERE ac.ano = '32000'  -- Zero Km
ORDER BY ma.nome, m.nome;
```

---

## Tamanho Estimado do Banco

### Registros Típicos

- **Marcas**: ~100 registros
- **Modelos**: ~30.000 registros
- **Anos/Combustível**: ~500 registros
- **Modelos/Anos**: ~250.000 relacionamentos
- **Valores FIPE**: ~250.000+ registros (cresce mensalmente)
- **Tabelas Referência**: ~100 registros (histórico mensal)

### Estimativa de Espaço

- **Tabelas + Índices**: ~500 MB (inicial)
- **Crescimento mensal**: ~100 MB (novos valores FIPE)
- **Após 1 ano**: ~1.7 GB

---

## Backup e Manutenção

### Backup Recomendado

- **Frequência**: Diário (automático no Supabase)
- **Retenção**: 30 dias (Supabase Pro)

### Manutenção

```sql
-- Vacuum para recuperar espaço
VACUUM ANALYZE valores_fipe;

-- Reindex para otimizar índices
REINDEX TABLE valores_fipe;
```

---

## Versionamento

- **Versão do Schema**: 2.0
- **Data**: 2025-12-16
- **Última atualização**: Adição da coluna `codigo_ano_combustivel` em `valores_fipe`

---

## Contato e Suporte

Para questões relacionadas ao schema:

- **Projeto**: FIPE Crawler
- **Database**: Supabase PostgreSQL
- **Ambiente**: Produção
