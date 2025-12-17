"""
Cache local SQLite para aceleração da população do banco.
Grava dados localmente primeiro (rápido) e sincroniza com Supabase depois.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from threading import Lock


class FipeLocalCache:
    """
    Cache local em SQLite para gravação rápida durante população do banco.
    Dados são sincronizados com Supabase em lote após coleta completa.
    Thread-safe com locks para operações de escrita.
    """
    
    def __init__(self, db_path='fipe_local.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.write_lock = Lock()  # Lock para operações de escrita
        self._setup_database()
    
    def _setup_database(self):
        """Cria estrutura do banco local (espelho do Supabase)"""
        with self.write_lock:
            cursor = self.conn.cursor()
        
        # Tabela de referências
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tabelas_referencia (
                codigo INTEGER PRIMARY KEY,
                mes VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Marcas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS marcas (
                codigo VARCHAR(10),
                tipo_veiculo INTEGER DEFAULT 1,
                nome VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (codigo, tipo_veiculo)
            )
        ''')
        
        # Modelos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modelos (
                codigo INTEGER,
                codigo_marca VARCHAR(10),
                tipo_veiculo INTEGER DEFAULT 1,
                nome VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (codigo, codigo_marca, tipo_veiculo),
                FOREIGN KEY (codigo_marca, tipo_veiculo) REFERENCES marcas(codigo, tipo_veiculo)
            )
        ''')
        
        # Anos/Combustível
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS anos_combustivel (
                codigo VARCHAR(20) PRIMARY KEY,
                nome VARCHAR(50),
                ano VARCHAR(10),
                codigo_combustivel INTEGER,
                combustivel VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Relacionamento Modelos-Anos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS modelos_anos (
                codigo_marca VARCHAR(10),
                codigo_modelo INTEGER,
                codigo_ano_combustivel VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (codigo_marca, codigo_modelo, codigo_ano_combustivel),
                FOREIGN KEY (codigo_modelo) REFERENCES modelos(codigo),
                FOREIGN KEY (codigo_marca) REFERENCES marcas(codigo),
                FOREIGN KEY (codigo_ano_combustivel) REFERENCES anos_combustivel(codigo)
            )
        ''')
        
        # Índices para performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_modelos_marca ON modelos(codigo_marca)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_modelos_anos_modelo ON modelos_anos(codigo_marca, codigo_modelo)')
        
        # Tabela de Valores FIPE
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS valores_fipe (
                codigo_marca INTEGER NOT NULL,
                codigo_modelo INTEGER NOT NULL,
                ano_modelo INTEGER NOT NULL,
                codigo_combustivel INTEGER NOT NULL,
                valor VARCHAR(50) NOT NULL,
                valor_numerico REAL,
                codigo_fipe VARCHAR(20),
                mes_referencia VARCHAR(50),
                codigo_referencia INTEGER,
                data_consulta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                marca VARCHAR(100),
                modelo TEXT,
                combustivel VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (codigo_marca, codigo_modelo, tipo_veiculo, ano_modelo, codigo_combustivel, mes_referencia),
                FOREIGN KEY (codigo_modelo, codigo_marca, tipo_veiculo) REFERENCES modelos(codigo, codigo_marca, tipo_veiculo) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_valores_fipe_tipo_veiculo ON valores_fipe(tipo_veiculo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_valores_fipe_mes ON valores_fipe(mes_referencia)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_valores_fipe_codigo_fipe ON valores_fipe(codigo_fipe)')
    
    def limpar_cache(self):
        """Remove todos os dados do cache local"""
        with self.write_lock:
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM modelos_anos')
            cursor.execute('DELETE FROM anos_combustivel')
            cursor.execute('DELETE FROM modelos')
            cursor.execute('DELETE FROM marcas')
            cursor.execute('DELETE FROM tabelas_referencia')
    
    def save_tabela_referencia(self, codigo, mes):
        """Salva tabela de referência localmente"""
        with self.write_lock:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO tabelas_referencia (codigo, mes)
                VALUES (?, ?)
            ''', (codigo, mes))
    
    def save_marcas(self, marcas, tipo_veiculo=1):
        """Salva múltiplas marcas em lote
        
        Args:
            marcas: Lista de marcas da API
            tipo_veiculo: Tipo de veículo (1=Carros, 2=Motos, 3=Caminhões)
        """
        with self.write_lock:
            cursor = self.conn.cursor()
            dados = [(m['Value'], tipo_veiculo, m['Label']) for m in marcas]
            cursor.executemany('''
                INSERT OR REPLACE INTO marcas (codigo, tipo_veiculo, nome)
                VALUES (?, ?, ?)
            ''', dados)
    
    def save_modelos(self, modelos, codigo_marca, tipo_veiculo=1):
        """Salva múltiplos modelos de uma marca em lote
        
        Args:
            modelos: Lista de modelos da API
            codigo_marca: Código da marca
            tipo_veiculo: Tipo de veículo (1=Carros, 2=Motos, 3=Caminhões)
        """
        with self.write_lock:
            cursor = self.conn.cursor()
            dados = [(m['Value'], codigo_marca, tipo_veiculo, m['Label']) for m in modelos]
            cursor.executemany('''
                INSERT OR REPLACE INTO modelos (codigo, codigo_marca, tipo_veiculo, nome)
                VALUES (?, ?, ?, ?)
            ''', dados)
    
    def save_anos_modelo(self, anos, codigo_marca, codigo_modelo, tipo_veiculo=1):
        """Salva anos/combustível de um modelo
        
        Args:
            anos: Lista de dicionários com Value e Label dos anos
            codigo_marca: Código da marca
            codigo_modelo: Código do modelo
            tipo_veiculo: Tipo de veículo (1=Carros, 2=Motos, 3=Caminhões). Padrão: 1
        """
        # Mapeamento de códigos para nomes de combustível
        combustiveis_map = {
            1: "Gasolina",
            2: "Álcool/Etanol",
            3: "Diesel",
            4: "Elétrico",
            5: "Flex",
            6: "Híbrido",
            7: "Gás Natural"
        }
        
        with self.write_lock:
            cursor = self.conn.cursor()
            
            # Salva anos_combustivel únicos
            for ano in anos:
                codigo_ano = ano['Value']  # Ex: "2024-1" ou "32000"
                nome_ano = ano['Label']    # Ex: "2024 Gasolina" ou "Zero Km"
                
                # Extrai ano e código do combustível
                if '-' in codigo_ano:
                    ano_valor, combustivel_valor = codigo_ano.split('-')
                    combustivel_valor = int(combustivel_valor)
                    combustivel_nome = combustiveis_map.get(combustivel_valor, None)
                else:
                    # Zero Km ou formato antigo
                    ano_valor = codigo_ano
                    combustivel_valor = None
                    combustivel_nome = None
                
                cursor.execute('''
                    INSERT OR IGNORE INTO anos_combustivel (codigo, nome, ano, codigo_combustivel, combustivel)
                    VALUES (?, ?, ?, ?, ?)
                ''', (codigo_ano, nome_ano, ano_valor, combustivel_valor, combustivel_nome))
            
            # Salva relacionamento modelo-ano com tipo_veiculo
            dados = [(codigo_marca, codigo_modelo, tipo_veiculo, ano['Value']) for ano in anos]
            cursor.executemany('''
                INSERT OR IGNORE INTO modelos_anos (codigo_marca, codigo_modelo, tipo_veiculo, codigo_ano_combustivel)
                VALUES (?, ?, ?, ?)
            ''', dados)
    
    def save_valor_fipe(self, valor_data, commit=True):
        """Salva um valor FIPE no cache local
        
        Args:
            valor_data: Dicionário com dados do valor
            commit: Se True, faz commit imediato (padrão). Se False, deixa para commit em lote.
        """
        with self.write_lock:
            cursor = self.conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO valores_fipe (
                    codigo_marca, codigo_modelo, tipo_veiculo, ano_modelo, codigo_combustivel,
                    valor, valor_numerico, codigo_fipe, mes_referencia, codigo_referencia,
                    marca, modelo, combustivel, data_consulta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                valor_data['codigo_marca'],
                valor_data['codigo_modelo'],
                valor_data.get('tipo_veiculo', 1),  # Default para carros se não especificado
                valor_data['ano_modelo'],
                valor_data['codigo_combustivel'],
                valor_data['valor'],
                valor_data['valor_numerico'],
                valor_data['codigo_fipe'],
                valor_data['mes_referencia'],
                valor_data['codigo_referencia'],
                valor_data['marca'],
                valor_data['modelo'],
                valor_data['combustivel'],
                valor_data.get('data_consulta', 'CURRENT_TIMESTAMP')
            ))
            
            if commit:
                self.conn.commit()
    
    def get_estatisticas(self):
        """Retorna estatísticas do cache local"""
        cursor = self.conn.cursor()
        
        stats = {}
        stats['tabelas_referencia'] = cursor.execute('SELECT COUNT(*) FROM tabelas_referencia').fetchone()[0]
        stats['marcas'] = cursor.execute('SELECT COUNT(*) FROM marcas').fetchone()[0]
        stats['modelos'] = cursor.execute('SELECT COUNT(*) FROM modelos').fetchone()[0]
        stats['anos_combustivel'] = cursor.execute('SELECT COUNT(*) FROM anos_combustivel').fetchone()[0]
        stats['modelos_anos'] = cursor.execute('SELECT COUNT(*) FROM modelos_anos').fetchone()[0]
        
        return stats
    
    def get_all_tabelas_referencia(self):
        """Retorna todas as tabelas de referência para upload"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT codigo, mes FROM tabelas_referencia')
        return [{'Codigo': row[0], 'Mes': row[1]} for row in cursor.fetchall()]
    
    def get_all_marcas(self):
        """Retorna todas as marcas para upload"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT codigo, nome FROM marcas')
        return [{'codigo': row[0], 'nome': row[1]} for row in cursor.fetchall()]
    
    def get_all_modelos(self):
        """Retorna todos os modelos para upload"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT codigo, codigo_marca, nome FROM modelos')
        return [{'codigo': row[0], 'codigo_marca': row[1], 'nome': row[2]} for row in cursor.fetchall()]
    
    def get_all_anos_combustivel(self):
        """Retorna todos os anos/combustível para upload"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT codigo, nome FROM anos_combustivel')
        return [{'codigo': row[0], 'nome': row[1]} for row in cursor.fetchall()]
    
    def get_all_modelos_anos(self):
        """Retorna todos os relacionamentos modelo-ano para upload"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT codigo_marca, codigo_modelo, codigo_ano_combustivel FROM modelos_anos')
        return [{'codigo_marca': row[0], 'codigo_modelo': row[1], 'codigo_ano_combustivel': row[2]} for row in cursor.fetchall()]
    
    def get_all_valores_fipe(self):
        """Retorna todos os valores FIPE para upload"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT codigo_marca, codigo_modelo, ano_modelo, codigo_combustivel, codigo_ano_combustivel,
                   valor, valor_numerico, codigo_fipe, mes_referencia, codigo_referencia,
                   marca, modelo, combustivel, data_consulta
            FROM valores_fipe
        ''')
        return [
            {
                'codigo_marca': row[0],
                'codigo_modelo': row[1],
                'ano_modelo': row[2],
                'codigo_combustivel': row[3],
                'codigo_ano_combustivel': row[4],
                'valor': row[5],
                'valor_numerico': row[6],
                'codigo_fipe': row[7],
                'mes_referencia': row[8],
                'codigo_referencia': row[9],
                'marca': row[10],
                'modelo': row[11],
                'combustivel': row[12],
                'data_consulta': row[13]
            }
            for row in cursor.fetchall()
        ]
    
    def carregar_do_supabase(self, supabase):
        """
        Carrega dados existentes do Supabase para o cache local.
        Usado na primeira execução para sincronizar estado inicial.
        """
        print("🔄 Sincronizando SQLite local com Supabase...")
        
        with self.write_lock:
            cursor = self.conn.cursor()
            
            # 1. Carregar tabelas de referência
            try:
                result = supabase.table('tabelas_referencia').select('*').execute()
                if result.data:
                    dados = [(r['codigo'], r['mes']) for r in result.data]
                    cursor.executemany('''
                        INSERT OR REPLACE INTO tabelas_referencia (codigo, mes)
                        VALUES (?, ?)
                    ''', dados)
                    print(f"   ✅ {len(dados)} tabelas de referência carregadas")
            except Exception as e:
                print(f"   ⚠️ Tabelas referência: {e}")
            
            # 2. Carregar marcas
            try:
                result = supabase.table('marcas').select('*').execute()
                if result.data:
                    dados = [(r['codigo'], r['nome']) for r in result.data]
                    cursor.executemany('''
                        INSERT OR REPLACE INTO marcas (codigo, nome)
                        VALUES (?, ?)
                    ''', dados)
                    print(f"   ✅ {len(dados)} marcas carregadas")
            except Exception as e:
                print(f"   ⚠️ Marcas: {e}")
            
            # 3. Carregar modelos
            try:
                result = supabase.table('modelos').select('*').execute()
                if result.data:
                    dados = [(r['codigo'], r['codigo_marca'], r['nome']) for r in result.data]
                    cursor.executemany('''
                        INSERT OR REPLACE INTO modelos (codigo, codigo_marca, nome)
                        VALUES (?, ?, ?)
                    ''', dados)
                    print(f"   ✅ {len(dados)} modelos carregados")
            except Exception as e:
                print(f"   ⚠️ Modelos: {e}")
            
            # 4. Carregar anos/combustível
            try:
                result = supabase.table('anos_combustivel').select('*').execute()
                if result.data:
                    dados = [(r['codigo'], r['nome']) for r in result.data]
                    cursor.executemany('''
                        INSERT OR REPLACE INTO anos_combustivel (codigo, nome)
                        VALUES (?, ?)
                    ''', dados)
                    print(f"   ✅ {len(dados)} anos/combustível carregados")
            except Exception as e:
                print(f"   ⚠️ Anos/combustível: {e}")
            
            # 5. Carregar relacionamentos modelos_anos
            try:
                result = supabase.table('modelos_anos').select('*').execute()
                if result.data:
                    dados = [(r['modelo_codigo'], r['ano_codigo']) for r in result.data]
                    cursor.executemany('''
                        INSERT OR IGNORE INTO modelos_anos (modelo_codigo, ano_codigo)
                        VALUES (?, ?)
                    ''', dados)
                    print(f"   ✅ {len(dados)} relacionamentos carregados")
            except Exception as e:
                print(f"   ⚠️ Relacionamentos: {e}")
        
        print("✅ Sincronização inicial concluída\n")
    
    def verificar_marca_completa(self, codigo_marca):
        """
        Verifica se uma marca já tem todos os modelos e anos carregados.
        Retorna True se está completa, False se precisa atualizar.
        """
        cursor = self.conn.cursor()
        
        # Verifica se marca existe
        cursor.execute('SELECT COUNT(*) FROM marcas WHERE codigo = ?', (codigo_marca,))
        if cursor.fetchone()[0] == 0:
            return False  # Marca não existe
        
        # Verifica se tem modelos
        cursor.execute('SELECT COUNT(*) FROM modelos WHERE codigo_marca = ?', (codigo_marca,))
        if cursor.fetchone()[0] == 0:
            return False  # Marca sem modelos
        
        return True  # Marca tem modelos (consideramos completa)
    
    def get_modelos_sem_anos(self, codigo_marca):
        """
        Retorna modelos de uma marca que ainda não têm anos cadastrados.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT m.codigo, m.nome
            FROM modelos m
            WHERE m.codigo_marca = ?
            AND NOT EXISTS (
                SELECT 1 FROM modelos_anos ma
                WHERE ma.codigo_modelo = m.codigo
                AND ma.codigo_marca = m.codigo_marca
            )
        ''', (codigo_marca,))
        
        return [{'Value': row[0], 'Label': row[1]} for row in cursor.fetchall()]
    
    def get_modelos_sem_anos_marca(self, codigo_marca):
        """
        Verifica se uma marca tem modelos sem anos.
        Retorna lista de códigos de modelos sem anos.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT m.codigo
            FROM modelos m
            WHERE m.codigo_marca = ?
            AND NOT EXISTS (
                SELECT 1 FROM modelos_anos ma
                WHERE ma.codigo_modelo = m.codigo
                AND ma.codigo_marca = m.codigo_marca
            )
        ''', (codigo_marca,))
        
        return [row[0] for row in cursor.fetchall()]
    
    def get_marcas_sem_modelos(self):
        """
        Retorna marcas que ainda não têm modelos cadastrados.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT m.codigo, m.nome
            FROM marcas m
            WHERE NOT EXISTS (
                SELECT 1 FROM modelos mod
                WHERE mod.codigo_marca = m.codigo
            )
        ''')
        
        return [{'Value': row[0], 'Label': row[1]} for row in cursor.fetchall()]
    
    def get_modelos_marca_dict(self, codigo_marca):
        """
        Retorna modelos de uma marca como dicionário {codigo: nome}.
        Útil para verificação rápida de existência.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT codigo, nome
            FROM modelos
            WHERE codigo_marca = ?
        ''', (codigo_marca,))
        
        return {str(row[0]): row[1] for row in cursor.fetchall()}
    
    def close(self):
        """Fecha conexão com banco local"""
        self.conn.close()
    
    def __del__(self):
        """Fecha conexão ao destruir objeto"""
        if hasattr(self, 'conn'):
            self.conn.close()
