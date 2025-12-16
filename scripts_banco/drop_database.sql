-- ============================================
-- FIPE CRAWLER - Drop All Database Objects
-- ============================================
-- ⚠️ ATENÇÃO: Este script DELETA TUDO do banco!
-- Execute apenas se quiser recomeçar do zero
-- ============================================

-- ============================================
-- 1. REMOVER POLÍTICAS RLS
-- ============================================

-- Políticas de SELECT (leitura)
DROP POLICY IF EXISTS "Permitir leitura pública" ON marcas;
DROP POLICY IF EXISTS "Permitir leitura pública" ON modelos;
DROP POLICY IF EXISTS "Permitir leitura pública" ON anos_combustivel;
DROP POLICY IF EXISTS "Permitir leitura pública" ON modelos_anos;
DROP POLICY IF EXISTS "Permitir leitura pública" ON valores_fipe;
DROP POLICY IF EXISTS "Permitir leitura pública" ON tabelas_referencia;

-- Políticas de INSERT
DROP POLICY IF EXISTS "Permitir inserção autenticada" ON marcas;
DROP POLICY IF EXISTS "Permitir inserção autenticada" ON modelos;
DROP POLICY IF EXISTS "Permitir inserção autenticada" ON anos_combustivel;
DROP POLICY IF EXISTS "Permitir inserção autenticada" ON modelos_anos;
DROP POLICY IF EXISTS "Permitir inserção autenticada" ON valores_fipe;
DROP POLICY IF EXISTS "Permitir inserção autenticada" ON tabelas_referencia;

DROP POLICY IF EXISTS "Permitir inserção com API key" ON marcas;
DROP POLICY IF EXISTS "Permitir inserção com API key" ON modelos;
DROP POLICY IF EXISTS "Permitir inserção com API key" ON anos_combustivel;
DROP POLICY IF EXISTS "Permitir inserção com API key" ON modelos_anos;
DROP POLICY IF EXISTS "Permitir inserção com API key" ON valores_fipe;
DROP POLICY IF EXISTS "Permitir inserção com API key" ON tabelas_referencia;

-- Políticas de UPDATE
DROP POLICY IF EXISTS "Permitir atualização com API key" ON marcas;
DROP POLICY IF EXISTS "Permitir atualização com API key" ON modelos;
DROP POLICY IF EXISTS "Permitir atualização com API key" ON anos_combustivel;
DROP POLICY IF EXISTS "Permitir atualização com API key" ON modelos_anos;
DROP POLICY IF EXISTS "Permitir atualização com API key" ON valores_fipe;
DROP POLICY IF EXISTS "Permitir atualização com API key" ON tabelas_referencia;

-- ============================================
-- 2. REMOVER TRIGGERS
-- ============================================

DROP TRIGGER IF EXISTS update_marcas_updated_at ON marcas;
DROP TRIGGER IF EXISTS update_modelos_updated_at ON modelos;

-- ============================================
-- 3. REMOVER FUNÇÕES
-- ============================================

DROP FUNCTION IF EXISTS update_updated_at_column();

-- ============================================
-- 4. REMOVER TABELAS
-- ============================================
-- Ordem: respeita foreign keys (dependentes primeiro)

-- Remove tabela de valores FIPE
DROP TABLE IF EXISTS valores_fipe CASCADE;

-- Remove tabela de relacionamento modelos_anos
DROP TABLE IF EXISTS modelos_anos CASCADE;

-- Remove tabela de anos/combustível
DROP TABLE IF EXISTS anos_combustivel CASCADE;

-- Remove tabela de modelos
DROP TABLE IF EXISTS modelos CASCADE;

-- Remove tabela de marcas
DROP TABLE IF EXISTS marcas CASCADE;

-- Remove tabela de tabelas de referência
DROP TABLE IF EXISTS tabelas_referencia CASCADE;

-- ============================================
-- 5. VERIFICAÇÃO
-- ============================================

-- Lista todas as tabelas restantes no schema public
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- Se não aparecer nenhuma tabela, a limpeza foi bem-sucedida!
