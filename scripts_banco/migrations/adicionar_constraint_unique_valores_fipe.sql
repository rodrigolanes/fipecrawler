-- ============================================
-- Script: adicionar_constraint_unique_valores_fipe.sql
-- Descrição: Adiciona constraint UNIQUE na tabela valores_fipe
--            para evitar valores duplicados do mesmo veículo no mesmo mês
-- Data: 2025-12-16
-- ============================================

-- Adicionar constraint UNIQUE
-- Garante que não haverá valores duplicados para:
-- - Mesmo veículo (marca + modelo + ano + combustível)
-- - No mesmo mês de referência
ALTER TABLE valores_fipe 
ADD CONSTRAINT valores_fipe_unique 
UNIQUE (codigo_marca, codigo_modelo, ano_modelo, codigo_combustivel, mes_referencia);

-- Comentário
COMMENT ON CONSTRAINT valores_fipe_unique ON valores_fipe IS 
'Previne inserção de valores duplicados do mesmo veículo no mesmo mês de referência';

-- ============================================
-- Resultado esperado:
-- ✅ Constraint criada
-- ✅ Valores duplicados bloqueados
-- ✅ UPSERT agora funciona corretamente
-- ============================================

-- Nota: Esta constraint é essencial para operações de UPSERT,
-- permitindo que o Supabase atualize valores existentes ao invés
-- de gerar erro de duplicidade.
