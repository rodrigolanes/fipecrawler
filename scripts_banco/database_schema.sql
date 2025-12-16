-- ============================================
-- FIPE CRAWLER - Database Schema for Supabase
-- ============================================

-- Tabela de Marcas
-- Armazena todas as marcas de veículos
CREATE TABLE IF NOT EXISTS marcas (
    id BIGSERIAL PRIMARY KEY,
    codigo INTEGER NOT NULL UNIQUE,
    nome VARCHAR(255) NOT NULL,
    tipo_veiculo INTEGER NOT NULL, -- 1=carro, 2=moto, 3=caminhão
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para marcas
CREATE INDEX IF NOT EXISTS idx_marcas_codigo ON marcas(codigo);
CREATE INDEX IF NOT EXISTS idx_marcas_tipo_veiculo ON marcas(tipo_veiculo);

-- ============================================

-- Tabela de Modelos
-- Armazena todos os modelos de veículos
CREATE TABLE IF NOT EXISTS modelos (
    id BIGSERIAL PRIMARY KEY,
    codigo INTEGER NOT NULL,
    nome TEXT NOT NULL,
    codigo_marca INTEGER NOT NULL REFERENCES marcas(codigo) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(codigo, codigo_marca)
);

-- Índices para modelos
CREATE INDEX IF NOT EXISTS idx_modelos_codigo ON modelos(codigo);
CREATE INDEX IF NOT EXISTS idx_modelos_codigo_marca ON modelos(codigo_marca);

-- ============================================

-- Tabela de Anos e Combustíveis
-- Armazena combinações únicas de ano/combustível
-- Códigos de Combustível: 1=Gasolina, 2=Álcool/Etanol, 3=Diesel, 4=Elétrico, 5=Flex, 6=Híbrido, 7=Gás Natural
CREATE TABLE IF NOT EXISTS anos_combustivel (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE, -- ex: "2014-1", "32000-1"
    nome VARCHAR(100) NOT NULL, -- ex: "2014 Gasolina", "Zero Km"
    ano VARCHAR(10), -- ano extraído: "2014" ou "32000"
    codigo_combustivel INTEGER, -- código extraído: 1, 2, 3, 4, 7
    combustivel VARCHAR(50), -- nome do combustível extraído: "Gasolina", "Diesel", "Álcool/Etanol", "Elétrico", "Gás Natural"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para anos_combustivel
CREATE INDEX IF NOT EXISTS idx_anos_combustivel_codigo ON anos_combustivel(codigo);
CREATE INDEX IF NOT EXISTS idx_anos_combustivel_ano ON anos_combustivel(ano);
CREATE INDEX IF NOT EXISTS idx_anos_combustivel_combustivel ON anos_combustivel(codigo_combustivel);

-- ============================================

-- Tabela de Relacionamento N:N entre Modelos e Anos/Combustível
-- Define quais anos/combustíveis estão disponíveis para cada modelo
CREATE TABLE IF NOT EXISTS modelos_anos (
    id BIGSERIAL PRIMARY KEY,
    codigo_marca INTEGER NOT NULL,
    codigo_modelo INTEGER NOT NULL,
    codigo_ano_combustivel VARCHAR(50) NOT NULL REFERENCES anos_combustivel(codigo) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(codigo_marca, codigo_modelo, codigo_ano_combustivel),
    FOREIGN KEY (codigo_modelo, codigo_marca) REFERENCES modelos(codigo, codigo_marca) ON DELETE CASCADE
);

-- Índices para modelos_anos
CREATE INDEX IF NOT EXISTS idx_modelos_anos_modelo ON modelos_anos(codigo_marca, codigo_modelo);
CREATE INDEX IF NOT EXISTS idx_modelos_anos_ano_combustivel ON modelos_anos(codigo_ano_combustivel);

-- ============================================

-- Tabela de Valores FIPE
-- Armazena os valores consultados da tabela FIPE
CREATE TABLE IF NOT EXISTS valores_fipe (
    id BIGSERIAL PRIMARY KEY,
    codigo_marca INTEGER NOT NULL,
    codigo_modelo INTEGER NOT NULL,
    ano_modelo INTEGER NOT NULL,
    codigo_combustivel INTEGER NOT NULL,
    valor VARCHAR(50) NOT NULL, -- "R$ 69.252,00"
    valor_numerico DECIMAL(12, 2), -- 69252.00
    codigo_fipe VARCHAR(20), -- "008153-1"
    mes_referencia VARCHAR(50), -- "dezembro de 2025"
    codigo_referencia INTEGER, -- 328
    data_consulta TIMESTAMP WITH TIME ZONE NOT NULL,
    marca VARCHAR(100),
    modelo TEXT,
    combustivel VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    FOREIGN KEY (codigo_modelo, codigo_marca) REFERENCES modelos(codigo, codigo_marca) ON DELETE CASCADE
);

-- Índices para valores_fipe
CREATE INDEX IF NOT EXISTS idx_valores_fipe_veiculo ON valores_fipe(codigo_marca, codigo_modelo, ano_modelo, codigo_combustivel);
CREATE INDEX IF NOT EXISTS idx_valores_fipe_codigo_fipe ON valores_fipe(codigo_fipe);
CREATE INDEX IF NOT EXISTS idx_valores_fipe_data_consulta ON valores_fipe(data_consulta DESC);
CREATE INDEX IF NOT EXISTS idx_valores_fipe_mes_referencia ON valores_fipe(mes_referencia);

-- ============================================

-- Tabela de Tabelas de Referência
-- Armazena o histórico de tabelas de referência (mês/ano)
CREATE TABLE IF NOT EXISTS tabelas_referencia (
    id BIGSERIAL PRIMARY KEY,
    codigo INTEGER NOT NULL UNIQUE,
    mes VARCHAR(50) NOT NULL, -- "dezembro/2025"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Índices para tabelas_referencia
CREATE INDEX IF NOT EXISTS idx_tabelas_referencia_codigo ON tabelas_referencia(codigo);

-- ============================================
-- COMENTÁRIOS DAS TABELAS
-- ============================================

COMMENT ON TABLE marcas IS 'Armazena todas as marcas de veículos da FIPE';
COMMENT ON TABLE modelos IS 'Armazena todos os modelos de veículos por marca';
COMMENT ON TABLE anos_combustivel IS 'Armazena combinações únicas de ano e combustível';
COMMENT ON TABLE modelos_anos IS 'Relacionamento N:N entre modelos e anos/combustível disponíveis';
COMMENT ON TABLE valores_fipe IS 'Histórico de valores consultados na tabela FIPE';
COMMENT ON TABLE tabelas_referencia IS 'Histórico de tabelas de referência (mês/ano) da FIPE';

-- ============================================
-- FUNÇÕES AUXILIARES
-- ============================================

-- Função para atualizar o campo updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers para atualizar updated_at
CREATE TRIGGER update_marcas_updated_at BEFORE UPDATE ON marcas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_modelos_updated_at BEFORE UPDATE ON modelos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- POLÍTICAS RLS (Row Level Security)
-- ============================================

-- Habilita RLS em todas as tabelas
ALTER TABLE marcas ENABLE ROW LEVEL SECURITY;
ALTER TABLE modelos ENABLE ROW LEVEL SECURITY;
ALTER TABLE anos_combustivel ENABLE ROW LEVEL SECURITY;
ALTER TABLE modelos_anos ENABLE ROW LEVEL SECURITY;
ALTER TABLE valores_fipe ENABLE ROW LEVEL SECURITY;
ALTER TABLE tabelas_referencia ENABLE ROW LEVEL SECURITY;

-- Políticas de leitura pública (qualquer um pode ler)
CREATE POLICY "Permitir leitura pública" ON marcas 
    FOR SELECT USING (true);

CREATE POLICY "Permitir leitura pública" ON modelos 
    FOR SELECT USING (true);

CREATE POLICY "Permitir leitura pública" ON anos_combustivel 
    FOR SELECT USING (true);

CREATE POLICY "Permitir leitura pública" ON modelos_anos 
    FOR SELECT USING (true);

CREATE POLICY "Permitir leitura pública" ON valores_fipe 
    FOR SELECT USING (true);

CREATE POLICY "Permitir leitura pública" ON tabelas_referencia 
    FOR SELECT USING (true);

-- Políticas de inserção (com API key válida)
CREATE POLICY "Permitir inserção com API key" ON marcas 
    FOR INSERT 
    TO authenticated, anon
    WITH CHECK (true);

CREATE POLICY "Permitir inserção com API key" ON modelos 
    FOR INSERT 
    TO authenticated, anon
    WITH CHECK (true);

CREATE POLICY "Permitir inserção com API key" ON anos_combustivel 
    FOR INSERT 
    TO authenticated, anon
    WITH CHECK (true);

CREATE POLICY "Permitir inserção com API key" ON modelos_anos 
    FOR INSERT 
    TO authenticated, anon
    WITH CHECK (true);

CREATE POLICY "Permitir inserção com API key" ON valores_fipe 
    FOR INSERT 
    TO authenticated, anon
    WITH CHECK (true);

CREATE POLICY "Permitir inserção com API key" ON tabelas_referencia 
    FOR INSERT 
    TO authenticated, anon
    WITH CHECK (true);

-- Políticas de atualização (necessário para UPSERT)
CREATE POLICY "Permitir atualização com API key" ON marcas 
    FOR UPDATE 
    TO authenticated, anon
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Permitir atualização com API key" ON modelos 
    FOR UPDATE 
    TO authenticated, anon
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Permitir atualização com API key" ON anos_combustivel 
    FOR UPDATE 
    TO authenticated, anon
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Permitir atualização com API key" ON modelos_anos 
    FOR UPDATE 
    TO authenticated, anon
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Permitir atualização com API key" ON valores_fipe 
    FOR UPDATE 
    TO authenticated, anon
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Permitir atualização com API key" ON tabelas_referencia 
    FOR UPDATE 
    TO authenticated, anon
    USING (true)
    WITH CHECK (true);
