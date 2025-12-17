# 📋 Guia de Migração - Suporte a Motos e Caminhões

Este guia explica como atualizar seus bancos de dados (SQLite local e Supabase) para suportar motos e caminhões.

## 🎯 Cenários

### Cenário 1: Você NÃO TEM banco de dados ainda

✅ **Ação**: Nada a fazer! Apenas execute `python popular_banco_otimizado.py`

O banco será criado automaticamente com o schema correto incluindo suporte a motos e caminhões.

---

### Cenário 2: Você JÁ TEM dados de carros no SQLite local

⚠️ **Ação**: Migrar o banco SQLite existente

#### Passos:

1. **Execute o script de migração**:
   ```bash
   python migrar_sqlite.py
   ```

2. **Confirme a operação** quando solicitado

3. **Verifique o resultado**:
   - ✅ Um backup será criado automaticamente (`fipe_local.db.backup`)
   - ✅ Todos os dados existentes serão marcados como tipo 1 (Carros)
   - ✅ O schema será atualizado com campo `tipo_veiculo`

4. **Execute o popular_banco_otimizado.py**:
   ```bash
   python popular_banco_otimizado.py
   ```
   
   Quando perguntado sobre tipos de veículo:
   - Digite `2,3` para baixar apenas **motos e caminhões**
   - Ou `1,2,3` para reprocessar tudo (carros serão pulados se já estiverem completos)

---

### Cenário 3: Você JÁ FEZ upload para o Supabase

⚠️ **Ação**: Migrar o banco Supabase

#### Passos:

1. **Acesse o Supabase SQL Editor**:
   - Vá para https://app.supabase.com/
   - Selecione seu projeto
   - Clique em **SQL Editor**

2. **Execute o script de migração**:
   - Abra o arquivo: `scripts_banco/migrations/adicionar_tipo_veiculo.sql`
   - Copie todo o conteúdo
   - Cole no SQL Editor do Supabase
   - Clique em **Run**

3. **Verifique os resultados**:
   - O script mostrará mensagens de sucesso
   - Verificará a estrutura atualizada
   - Mostrará estatísticas por tipo

4. **Após migrar o SQLite local, faça upload**:
   ```bash
   python upload_para_supabase.py
   ```

---

## 🔍 Verificação

### SQLite Local

```bash
sqlite3 fipe_local.db
```

```sql
-- Verifica estrutura
PRAGMA table_info(marcas);
PRAGMA table_info(modelos);

-- Estatísticas por tipo
SELECT tipo_veiculo, COUNT(*) FROM marcas GROUP BY tipo_veiculo;
SELECT tipo_veiculo, COUNT(*) FROM modelos GROUP BY tipo_veiculo;
```

### Supabase

No SQL Editor:

```sql
-- Estatísticas por tipo
SELECT 
    tipo_veiculo,
    CASE tipo_veiculo 
        WHEN 1 THEN 'Carros'
        WHEN 2 THEN 'Motos'
        WHEN 3 THEN 'Caminhões'
    END as tipo_nome,
    COUNT(*) as total
FROM marcas
GROUP BY tipo_veiculo
ORDER BY tipo_veiculo;
```

---

## 📊 Entendendo o tipo_veiculo

| Código | Tipo | Emoji |
|--------|------|-------|
| 1 | Carros | 🚗 |
| 2 | Motos | 🏍️ |
| 3 | Caminhões | 🚚 |

---

## ⚠️ Problemas Comuns

### Erro: "table marcas already exists"

**Causa**: Tentando criar tabela que já existe com schema antigo

**Solução**: Execute o `migrar_sqlite.py` primeiro

---

### Erro: "FOREIGN KEY constraint failed"

**Causa**: Dados inconsistentes entre marcas e modelos

**Solução**: 
1. Restaure o backup: `cp fipe_local.db.backup fipe_local.db`
2. Execute `migrar_sqlite.py` novamente
3. Se persistir, delete o banco e repopule do zero

---

### Erro no Supabase: "column tipo_veiculo does not exist"

**Causa**: Schema do Supabase não foi atualizado

**Solução**: Execute o script `adicionar_tipo_veiculo.sql` no SQL Editor do Supabase

---

## 🔄 Fluxo Completo Recomendado

### Se você já tem dados de carros:

```bash
# 1. Migrar SQLite local
python migrar_sqlite.py

# 2. Baixar motos e caminhões
python popular_banco_otimizado.py
# Quando perguntado, digite: 2,3

# 3. Migrar Supabase (executar SQL no Supabase SQL Editor)
# scripts_banco/migrations/adicionar_tipo_veiculo.sql

# 4. Upload para Supabase
python upload_para_supabase.py
```

### Se você está começando do zero:

```bash
# 1. Baixar todos os tipos
python popular_banco_otimizado.py
# Quando perguntado, pressione Enter (todos os tipos)

# 2. Criar banco no Supabase (primeira vez)
# Executar scripts_banco/database_schema.sql no SQL Editor

# 3. Upload para Supabase
python upload_para_supabase.py
```

---

## 💾 Backup

Antes de qualquer migração, faça backup:

### SQLite
```bash
cp fipe_local.db fipe_local.db.manual_backup_$(date +%Y%m%d)
```

### Supabase
- Dashboard → Database → Backups
- Ou exporte via `pg_dump` se tiver acesso

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique os logs do script de migração
2. Confira se o backup foi criado
3. Teste com poucos dados primeiro
4. Em último caso, delete o banco e repopule do zero

---

**Última atualização**: 16 de dezembro de 2025
