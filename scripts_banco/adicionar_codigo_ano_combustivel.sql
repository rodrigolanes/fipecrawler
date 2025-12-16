-- ============================================
-- Script: adicionar_codigo_ano_combustivel.sql
-- Descrição: Adiciona coluna codigo_ano_combustivel à tabela valores_fipe
--            para melhorar performance de queries (JOIN direto ao invés de LIKE)
-- Data: 2025-12-15
-- ============================================

-- Adicionar coluna codigo_ano_combustivel
ALTER TABLE valores_fipe 
ADD COLUMN IF NOT EXISTS codigo_ano_combustivel VARCHAR(20);

-- Popular coluna com dados existentes (formato: "2024-1")
UPDATE valores_fipe 
SET codigo_ano_combustivel = ano_modelo || '-' || codigo_combustivel
WHERE codigo_ano_combustivel IS NULL;

-- Criar índice para performance
CREATE INDEX IF NOT EXISTS idx_valores_fipe_codigo_ano_combustivel 
ON valores_fipe(codigo_ano_combustivel);

-- Comentários
COMMENT ON COLUMN valores_fipe.codigo_ano_combustivel IS 'Código combinado ano + combustível (ex: "2024-1") para JOIN direto com modelos_anos';
COMMENT ON INDEX idx_valores_fipe_codigo_ano_combustivel IS 'Índice para melhorar performance de queries que juntam valores_fipe com modelos_anos';

-- ============================================
-- Resultado esperado:
-- ✅ Coluna adicionada
-- ✅ Dados existentes populados
-- ✅ Índice criado
-- ============================================
