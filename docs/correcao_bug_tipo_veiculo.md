# Correção do Bug: tipo_veiculo ausente em modelos_anos

## 📋 Resumo do Problema

### Bug Crítico Identificado
A função `save_anos_modelo()` em `fipe_local_cache.py` não estava inserindo a coluna `tipo_veiculo` na tabela `modelos_anos`, mesmo sendo parte da chave primária composta.

### Impacto
- ✅ **Carros (tipo 1)**: 48.986 relacionamentos salvos (funcionou porque tipo_veiculo tinha default=1)
- ❌ **Motos (tipo 2)**: 0 relacionamentos (perdidos)
- ❌ **Caminhões (tipo 3)**: 0 relacionamentos (perdidos)

### Causa Raiz
```sql
-- ANTES (INCORRETO)
INSERT INTO modelos_anos (codigo_marca, codigo_modelo, codigo_ano_combustivel)
VALUES (?, ?, ?)

-- DEPOIS (CORRETO)
INSERT INTO modelos_anos (codigo_marca, codigo_modelo, tipo_veiculo, codigo_ano_combustivel)
VALUES (?, ?, ?, ?)
```

## 🔧 Correções Aplicadas

### 1. fipe_local_cache.py
**Linha 170** - Assinatura da função:
```python
# ANTES
def save_anos_modelo(self, anos, codigo_marca, codigo_modelo):

# DEPOIS
def save_anos_modelo(self, anos, codigo_marca, codigo_modelo, tipo_veiculo=1):
```

**Linhas 212-216** - INSERT SQL:
```python
# ANTES
cursor.execute("""
    INSERT OR IGNORE INTO modelos_anos (codigo_marca, codigo_modelo, codigo_ano_combustivel)
    VALUES (?, ?, ?)
""", (codigo_marca, codigo_modelo, codigo_ano))

# DEPOIS
cursor.execute("""
    INSERT OR IGNORE INTO modelos_anos (codigo_marca, codigo_modelo, tipo_veiculo, codigo_ano_combustivel)
    VALUES (?, ?, ?, ?)
""", (codigo_marca, codigo_modelo, tipo_veiculo, codigo_ano))
```

### 2. popular_banco_otimizado.py
**Linha 207** - Estratégia por modelo:
```python
# ANTES
self.cache_local.save_anos_modelo(anos, codigo_marca, codigo_modelo)

# DEPOIS
self.cache_local.save_anos_modelo(anos, codigo_marca, codigo_modelo, tipo_veiculo)
```

**Linha 374** - Estratégia por ano:
```python
# ANTES
self.cache_local.save_anos_modelo(anos_data, codigo_marca, int(codigo_modelo))

# DEPOIS
self.cache_local.save_anos_modelo(anos_data, codigo_marca, int(codigo_modelo), tipo_veiculo)
```

### 3. verificar_relacionamentos_incompletos.py
**Linha 197**:
```python
# ANTES
self.cache.save_anos_modelo(anos_data, codigo_marca, int(cod_modelo))

# DEPOIS
self.cache.save_anos_modelo(anos_data, codigo_marca, int(cod_modelo), tipo_veiculo)
```

### 4. atualizar_modelos.py
**Linha 105**:
```python
# ANTES
cache.save_anos_modelo(anos, codigo_marca, codigo_modelo)

# DEPOIS
cache.save_anos_modelo(anos, codigo_marca, codigo_modelo, tipo_veiculo=1)
```

**Linha 107** - buscar_anos_modelo:
```python
# ANTES
anos = buscar_anos_modelo(codigo_marca, codigo_modelo)

# DEPOIS
anos = buscar_anos_modelo(codigo_marca, codigo_modelo, tipo_veiculo=1)
```

## ✅ Arquivos Corrigidos

| Arquivo | Linhas Alteradas | Status |
|---------|------------------|--------|
| fipe_local_cache.py | 170, 212-216 | ✅ Corrigido |
| popular_banco_otimizado.py | 207, 374 | ✅ Corrigido |
| verificar_relacionamentos_incompletos.py | 197 | ✅ Corrigido |
| atualizar_modelos.py | 105, 107 | ✅ Corrigido |

## 📊 Próximos Passos

### 1. Repopular Motos e Caminhões
Execute o script de repopulação:
```bash
python repopular_motos_caminhoes.py
```

Opções disponíveis:
- **Opção 1**: Repopular apenas motos (~98 marcas, 1.904 modelos)
- **Opção 2**: Repopular apenas caminhões (~29 marcas, 1.957 modelos)
- **Opção 3**: Repopular ambos

### 2. Verificar Resultados
Após repopular, verificar estatísticas:
```bash
python verificar_tipos_veiculo.py
```

Esperado:
- Carros: ~48.986 relacionamentos
- Motos: ~10.000-15.000 relacionamentos (estimativa)
- Caminhões: ~8.000-12.000 relacionamentos (estimativa)

### 3. Sincronizar com Supabase
Após repopular localmente, enviar para Supabase:
```bash
python upload_para_supabase.py
```

Ou usar sincronização completa:
```bash
python sincronizar_relacionamentos.py --corrigir
```

## 🔍 Validação

### Teste Manual
Para validar que a correção funciona:
```python
from fipe_local_cache import FipeLocalCache
from fipe_crawler import buscar_marcas, buscar_modelos, buscar_anos_modelo

cache = FipeLocalCache()

# Teste com motos (tipo 2)
marcas_motos = buscar_marcas(tipo_veiculo=2)
primeira_marca = marcas_motos[0]
codigo_marca = primeira_marca['Value']

modelos = buscar_modelos(codigo_marca, tipo_veiculo=2)
primeiro_modelo = modelos[0]
codigo_modelo = primeiro_modelo['Value']

anos = buscar_anos_modelo(codigo_marca, codigo_modelo, tipo_veiculo=2)
cache.save_anos_modelo(anos, codigo_marca, codigo_modelo, tipo_veiculo=2)

# Verificar se foi salvo
result = cache.conn.execute("""
    SELECT COUNT(*) FROM modelos_anos 
    WHERE codigo_marca = ? AND codigo_modelo = ? AND tipo_veiculo = 2
""", (codigo_marca, codigo_modelo)).fetchone()[0]

print(f"✅ Relacionamentos salvos: {result}")
```

## 📝 Lições Aprendidas

1. **Chave Primária Composta**: Sempre incluir TODAS as colunas da PK em INSERTs
2. **Default Values**: Não confiar em defaults para PK, sempre passar explicitamente
3. **Testes por Tipo**: Validar TODOS os tipos de veículos, não apenas um
4. **Estatísticas**: Monitorar quantidade de registros por tipo para detectar anomalias

## 🚨 Importante

**SEMPRE** passar `tipo_veiculo` ao chamar `save_anos_modelo()`:
```python
# ✅ CORRETO
cache.save_anos_modelo(anos, codigo_marca, codigo_modelo, tipo_veiculo)

# ❌ ERRADO (vai usar default=1, sempre carros)
cache.save_anos_modelo(anos, codigo_marca, codigo_modelo)
```
