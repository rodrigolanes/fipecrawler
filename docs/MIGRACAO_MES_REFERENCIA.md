# Guia de Migração: mes_referencia para formato YYYYMM

## 📋 Visão Geral

Esta migração converte o campo `mes_referencia` de formato português legível ("janeiro de 2026") para formato internacional YYYYMM ("202601").

### Benefícios
- ✅ Independente de idioma
- ✅ Ordenação cronológica natural
- ✅ Comparações simples (>, <, BETWEEN)
- ✅ Padrão internacional (ISO 8601 parcial)
- ✅ Mais compacto (6 vs 20+ caracteres)

---

## 🔄 Ordem de Execução

### Fase 1: Preparação (5 minutos)

1. **Backup completo**
   ```powershell
   # SQLite local
   copy fipe_local.db fipe_local.db.backup_antes_migracao
   
   # Supabase: usar backup automático do painel
   ```

2. **Testar funções de conversão**
   ```powershell
   python -c "from src.config import mes_pt_para_yyyymm, yyyymm_para_mes_display; print(mes_pt_para_yyyymm('janeiro de 2026')); print(yyyymm_para_mes_display('202601'))"
   ```
   
   Deve retornar:
   ```
   202601
   Janeiro/2026
   ```

---

### Fase 2: Migração SQLite Local (10-15 minutos)

1. **Executar migração local**
   ```powershell
   python scripts\migracoes\migrar_mes_referencia_sqlite.py
   ```

2. **Verificar resultados**
   - Script cria backup automático
   - Mostra análise antes/depois
   - Valida integridade dos dados

3. **Testar com debug**
   ```powershell
   python scripts\2_atualizacao_mensal\debug_valores.py
   ```
   
   Deve mostrar meses no formato YYYYMM:
   ```
   📅 Meses de referência no banco:
      • 202512: 49524 valores
      • 202601: 11662 valores
   ```

---

### Fase 3: Testar Novo Código (10 minutos)

1. **Testar atualização de valores**
   ```powershell
   # Executa apenas os primeiros 20 veículos para teste
   python scripts\2_atualizacao_mensal\2_atualizar_valores.py
   ```
   
   Após 20 registros, pressione Ctrl+C para interromper.

2. **Verificar que salvou no formato correto**
   ```powershell
   python scripts\2_atualizacao_mensal\debug_valores.py
   ```
   
   Novos valores devem ter `mes_referencia` como "202601" (não "janeiro de 2026").

3. **Verificar display amigável**
   - Nos prints do script, deve mostrar "Janeiro/2026" (formato legível)
   - No banco, deve estar salvo como "202601"

---

### Fase 4: Migração PostgreSQL/Supabase (15-20 minutos)

⚠️ **ATENÇÃO: Execute APENAS após validar que SQLite local está funcionando!**

#### 4.1. Acesse o Supabase SQL Editor

1. Abra: https://supabase.com/dashboard/project/frnfahrjfmnggeaccyty/sql/new
2. Cole o conteúdo de: `fipe_database/migrations/004_converter_mes_referencia_yyyymm.sql`

#### 4.2. Crie Backup Manual (CRUCIAL!)

Antes de executar a migration:

1. Painel Supabase → Database → Backups
2. Clique em "Create backup now"
3. Aguarde conclusão (alguns minutos)

#### 4.3. Execute a Migration

1. Cole o SQL no editor
2. Clique em "Run" (▶️)
3. Aguarde conclusão (pode levar 5-10 minutos se houver muitos dados)

#### 4.4. Verifique os LOGs

A migration mostra progresso detalhado:

```
========================================
Migration 004: mes_referencia → YYYYMM
========================================

Total de registros: 61186

ETAPA 1/7: Adicionando coluna temporária...
  ✓ Coluna mes_referencia_novo criada

ETAPA 2/7: Convertendo valores...
  ✓ 61186 registros convertidos

ETAPA 3/7: Removendo PRIMARY KEY antiga...
  ✓ Constraint valores_fipe_pkey removida

...

✓ MIGRATION 004 CONCLUÍDA COM SUCESSO!
```

#### 4.5. Validação Pós-Migration

Execute no SQL Editor:

```sql
-- Verificar total de registros
SELECT COUNT(*) FROM valores_fipe;

-- Verificar meses distintos (devem estar em formato YYYYMM)
SELECT mes_referencia, COUNT(*) 
FROM valores_fipe 
GROUP BY mes_referencia 
ORDER BY mes_referencia DESC;

-- Verificar que PRIMARY KEY foi recriada
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'valores_fipe'::regclass;
```

Deve retornar:
```
mes_referencia | count
---------------+-------
202601         | 11662
202512         | 49524
```

---

### Fase 5: Sincronização (15-30 minutos)

1. **Upload de dados novos do SQLite para Supabase**
   ```powershell
   python scripts\3_sincronizacao\sincronizar_supabase.py
   ```

2. **Verificar sincronização**
   - Todos os valores devem estar com mes_referencia em formato YYYYMM
   - Totais devem bater: SQLite local == Supabase

---

## 🔍 Troubleshooting

### Erro: "ERRO: % registros não puderam ser convertidos"

**Causa**: Algum valor de mes_referencia não está no formato esperado.

**Solução**:
```sql
-- Identificar valores problemáticos
SELECT DISTINCT mes_referencia 
FROM valores_fipe 
WHERE mes_referencia_novo IS NULL;
```

Adicione regra de conversão específica na migration.

---

### Erro: "ERRO: Total de registros diferente"

**Causa**: Dados foram perdidos durante migração.

**Solução**:
1. A transação é revertida automaticamente
2. Restaure backup
3. Investigue causa (pode ser constraint violada)

---

### Script Python dá erro ao salvar

**Causa**: Código tentando salvar formato antigo após migração do banco.

**Solução**:
```powershell
# Verifique que está usando a versão atualizada
git status

# Force reinstalação do módulo config
python -c "import sys; sys.path.insert(0, '.'); from src.config import mes_pt_para_yyyymm; print(mes_pt_para_yyyymm.__doc__)"
```

---

## ✅ Checklist Final

Marque cada item após conclusão:

### SQLite Local
- [ ] Backup criado
- [ ] Migration executada
- [ ] Debug mostra formato YYYYMM
- [ ] Teste salvou novos valores corretamente
- [ ] Display mostra formato legível

### PostgreSQL/Supabase
- [ ] Backup manual criado no painel
- [ ] Migration 004 executada sem erros
- [ ] Validação SQL confirmou formato YYYYMM
- [ ] PRIMARY KEY recriada
- [ ] Índices recriados

### Integração
- [ ] Sincronização SQLite → Supabase OK
- [ ] Totais batem (SQLite == Supabase)
- [ ] Aplicação fipe_app testada (se aplicável)
- [ ] Queries antigas ainda funcionam

---

## 🔄 Rollback (Se Necessário)

### SQLite Local
```powershell
# Feche todos os scripts/conexões
# Restaure backup
copy fipe_local.db.backup_antes_migracao fipe_local.db
```

### PostgreSQL/Supabase
1. Painel Supabase → Database → Backups
2. Selecione backup pré-migration
3. Clique em "Restore"
4. Confirme operação

---

## 📊 Estatísticas Esperadas

### Antes da Migração
```
mes_referencia          | count
------------------------+-------
dezembro de 2025        | 49524
janeiro de 2026         | 11662
```

### Depois da Migração
```
mes_referencia | count
---------------+-------
202512         | 49524
202601         | 11662
```

---

## 📞 Suporte

Se encontrar problemas:

1. Consulte logs detalhados da migration
2. Verifique que backup existe antes de qualquer ação
3. Não force continuação se houver erros
4. Em caso de dúvida, restaure backup e reavalie

---

**Última atualização**: 2026-01-02
**Versão**: 1.0
