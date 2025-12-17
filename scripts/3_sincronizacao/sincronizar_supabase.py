"""
Script para carregar dados do SQLite local para o Supabase.
Útil após popular o banco localmente com popular_banco_otimizado.py
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

import sqlite3
import time
from datetime import datetime
from src.database.supabase_client import get_supabase_client


class SupabaseUploader:
    """
    Carrega dados do SQLite local para o Supabase.
    Faz upload em lotes para melhor performance.
    """
    
    def __init__(self, db_path='fipe_local.db', batch_size=1000):
        self.db_path = db_path
        self.batch_size = batch_size
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.supabase = get_supabase_client()
        
    def _contar_registros_sqlite(self, tabela):
        """Conta registros em uma tabela SQLite"""
        cursor = self.conn.cursor()
        cursor.execute(f'SELECT COUNT(*) FROM {tabela}')
        return cursor.fetchone()[0]
    
    def _contar_registros_supabase(self, tabela):
        """Conta registros em uma tabela Supabase"""
        try:
            # Supabase não tem COUNT direto, então fazemos select com limit
            response = self.supabase.table(tabela).select('*', count='exact').limit(1).execute()
            return response.count if hasattr(response, 'count') else 0
        except Exception as e:
            print(f"   ⚠️ Erro ao contar {tabela}: {e}")
            return 0
    
    def upload_tabelas_referencia(self):
        """Upload de tabelas de referência"""
        print("\n📋 TABELAS DE REFERÊNCIA")
        print("-" * 60)
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT codigo, mes FROM tabelas_referencia')
        rows = cursor.fetchall()
        
        if not rows:
            print("   ⚠️ Nenhum registro encontrado")
            return 0
        
        print(f"   📊 {len(rows)} registros no SQLite")
        
        # Converte para formato esperado
        data = [{'codigo': row['codigo'], 'mes': row['mes']} for row in rows]
        
        try:
            # Upsert em lote (on_conflict especifica a coluna única)
            self.supabase.table('tabelas_referencia').upsert(data, on_conflict='codigo').execute()
            print(f"   ✅ {len(data)} registros enviados")
            return len(data)
        except Exception as e:
            print(f"   ❌ Erro ao enviar: {e}")
            return 0
    
    def upload_marcas(self):
        """Upload de marcas"""
        print("\n🏭 MARCAS")
        print("-" * 60)
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT codigo, tipo_veiculo, nome FROM marcas')
        rows = cursor.fetchall()
        
        if not rows:
            print("   ⚠️ Nenhum registro encontrado")
            return 0
        
        print(f"   📊 {len(rows)} registros no SQLite")
        
        # Converte para formato esperado
        data = [
            {
                'codigo': row['codigo'], 
                'tipo_veiculo': row['tipo_veiculo'],
                'nome': row['nome']
            } 
            for row in rows
        ]
        
        try:
            # Upsert em lote (on_conflict especifica a PK composta)
            self.supabase.table('marcas').upsert(data, on_conflict='codigo,tipo_veiculo').execute()
            print(f"   ✅ {len(data)} registros enviados")
            return len(data)
        except Exception as e:
            print(f"   ❌ Erro ao enviar: {e}")
            return 0
    
    def upload_modelos(self):
        """Upload de modelos em lotes"""
        print("\n🚗 MODELOS")
        print("-" * 60)
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM modelos')
        total = cursor.fetchone()[0]
        
        if total == 0:
            print("   ⚠️ Nenhum registro encontrado")
            return 0
        
        print(f"   📊 {total} registros no SQLite")
        
        # Upload em lotes
        enviados = 0
        erros = 0
        offset = 0
        
        while offset < total:
            cursor.execute(f'''
                SELECT codigo, codigo_marca, tipo_veiculo, nome 
                FROM modelos 
                LIMIT {self.batch_size} OFFSET {offset}
            ''')
            rows = cursor.fetchall()
            
            if not rows:
                break
            
            data = [
                {
                    'codigo': row['codigo'],
                    'codigo_marca': row['codigo_marca'],
                    'tipo_veiculo': row['tipo_veiculo'],
                    'nome': row['nome']
                }
                for row in rows
            ]
            
            try:
                # Upsert especificando as colunas da PK composta
                self.supabase.table('modelos').upsert(data, on_conflict='codigo,codigo_marca,tipo_veiculo').execute()
                enviados += len(data)
                print(f"   📤 {enviados}/{total} registros enviados ({enviados*100//total}%)")
            except Exception as e:
                erros += len(data)
                print(f"   ❌ Erro no lote {offset}-{offset+len(data)}: {e}")
                # Continua mesmo com erro
            
            offset += self.batch_size
            time.sleep(0.5)  # Pequeno delay entre lotes
        
        print(f"   ✅ {enviados} registros enviados")
        if erros > 0:
            print(f"   ⚠️ {erros} registros com erro")
        return enviados
    
    def upload_anos_combustivel(self):
        """Upload de anos/combustível em lotes"""
        print("\n⛽ ANOS/COMBUSTÍVEL")
        print("-" * 60)
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM anos_combustivel')
        total = cursor.fetchone()[0]
        
        if total == 0:
            print("   ⚠️ Nenhum registro encontrado")
            return 0
        
        print(f"   📊 {total} registros no SQLite")
        
        # Upload em lotes
        enviados = 0
        offset = 0
        
        while offset < total:
            cursor.execute(f'''
                SELECT codigo, nome, ano, codigo_combustivel, combustivel
                FROM anos_combustivel 
                LIMIT {self.batch_size} OFFSET {offset}
            ''')
            rows = cursor.fetchall()
            
            if not rows:
                break
            
            data = [
                {
                    'codigo': row['codigo'],
                    'nome': row['nome'],
                    'ano': row['ano'],
                    'codigo_combustivel': row['codigo_combustivel'],
                    'combustivel': row['combustivel']
                }
                for row in rows
            ]
            
            try:
                # Upsert especificando a coluna única
                self.supabase.table('anos_combustivel').upsert(data, on_conflict='codigo').execute()
                enviados += len(data)
                print(f"   📤 {enviados}/{total} registros enviados ({enviados*100//total}%)")
            except Exception as e:
                print(f"   ❌ Erro no lote {offset}-{offset+len(data)}: {e}")
            
            offset += self.batch_size
            time.sleep(0.5)  # Pequeno delay entre lotes
        
        print(f"   ✅ {enviados} registros enviados")
        return enviados
    
    def upload_modelos_anos(self):
        """Upload de relacionamentos modelo-ano em lotes"""
        print("\n🔗 RELACIONAMENTOS MODELO-ANO")
        print("-" * 60)
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM modelos_anos')
        total = cursor.fetchone()[0]
        
        if total == 0:
            print("   ⚠️ Nenhum registro encontrado")
            return 0
        
        print(f"   📊 {total} registros no SQLite")
        print("   🔍 Filtrando apenas relacionamentos com modelos existentes no Supabase...")
        
        # Upload em lotes
        enviados = 0
        pulados = 0
        offset = 0
        
        while offset < total:
            # Query com JOIN para garantir que o modelo existe
            cursor.execute(f'''
                SELECT DISTINCT
                    ma.codigo_marca, 
                    ma.codigo_modelo, 
                    ma.tipo_veiculo, 
                    ma.codigo_ano_combustivel
                FROM modelos_anos ma
                INNER JOIN modelos m 
                    ON ma.codigo_modelo = m.codigo 
                    AND ma.codigo_marca = m.codigo_marca 
                    AND ma.tipo_veiculo = m.tipo_veiculo
                LIMIT {self.batch_size} OFFSET {offset}
            ''')
            rows = cursor.fetchall()
            
            if not rows:
                break
            
            data = [
                {
                    'codigo_marca': row['codigo_marca'],
                    'codigo_modelo': row['codigo_modelo'],
                    'tipo_veiculo': row['tipo_veiculo'],
                    'codigo_ano_combustivel': row['codigo_ano_combustivel']
                }
                for row in rows
            ]
            
            try:
                # Upsert especificando as colunas da PK composta
                result = self.supabase.table('modelos_anos').upsert(
                    data, 
                    on_conflict='codigo_marca,codigo_modelo,tipo_veiculo,codigo_ano_combustivel'
                ).execute()
                enviados += len(data)
                print(f"   📤 {enviados}/{total} registros processados ({enviados*100//total}%)")
            except Exception as e:
                error_msg = str(e)
                # Se ainda houver erro de FK, conta como pulado
                if '23503' in error_msg or 'foreign key' in error_msg.lower():
                    pulados += len(data)
                    print(f"   ⚠️ Lote {offset}-{offset+len(data)}: {len(data)} registros pulados (modelos não existem no Supabase)")
                else:
                    print(f"   ❌ Erro no lote {offset}-{offset+len(data)}: {e}")
            
            offset += self.batch_size
            time.sleep(0.5)  # Pequeno delay entre lotes
        
        print(f"   ✅ {enviados} registros enviados")
        if pulados > 0:
            print(f"   ⚠️ {pulados} registros pulados (foreign key)")
        return enviados
    
    def upload_valores_fipe(self):
        """Upload de valores FIPE em lotes"""
        print("\n💰 VALORES FIPE")
        print("-" * 60)
        
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM valores_fipe')
        total = cursor.fetchone()[0]
        
        if total == 0:
            print("   ⚠️ Nenhum registro encontrado")
            return 0
        
        print(f"   📊 {total} registros no SQLite")
        
        # Upload em lotes
        enviados = 0
        offset = 0
        
        while offset < total:
            cursor.execute(f'''
                SELECT codigo_marca, codigo_modelo, tipo_veiculo, ano_modelo, 
                       codigo_combustivel, valor, valor_numerico, codigo_fipe, 
                       mes_referencia, codigo_referencia, marca, modelo, 
                       combustivel, data_consulta
                FROM valores_fipe
                LIMIT {self.batch_size} OFFSET {offset}
            ''')
            rows = cursor.fetchall()
            
            if not rows:
                break
            
            data = [
                {
                    'codigo_marca': row['codigo_marca'],
                    'codigo_modelo': row['codigo_modelo'],
                    'tipo_veiculo': row['tipo_veiculo'],
                    'ano_modelo': row['ano_modelo'],
                    'codigo_combustivel': row['codigo_combustivel'],
                    'valor': row['valor'],
                    'valor_numerico': row['valor_numerico'],
                    'codigo_fipe': row['codigo_fipe'],
                    'mes_referencia': row['mes_referencia'],
                    'codigo_referencia': row['codigo_referencia'],
                    'marca': row['marca'],
                    'modelo': row['modelo'],
                    'combustivel': row['combustivel'],
                    'data_consulta': row['data_consulta']
                }
                for row in rows
            ]
            
            try:
                # Upsert com PK composta
                self.supabase.table('valores_fipe').upsert(data, on_conflict='codigo_marca,codigo_modelo,tipo_veiculo,ano_modelo,codigo_combustivel,mes_referencia').execute()
                enviados += len(data)
                print(f"   📤 {enviados}/{total} registros enviados ({enviados*100//total}%)")
            except Exception as e:
                print(f"   ❌ Erro no lote {offset}-{offset+len(data)}: {e}")
            
            offset += self.batch_size
            time.sleep(0.5)  # Pequeno delay entre lotes
        
        print(f"   ✅ {enviados} registros enviados")
        return enviados
    
    def mostrar_estatisticas(self):
        """Mostra estatísticas comparativas SQLite vs Supabase"""
        print("\n" + "=" * 60)
        print("📊 ESTATÍSTICAS COMPARATIVAS")
        print("=" * 60)
        
        tabelas = [
            'tabelas_referencia',
            'marcas',
            'modelos',
            'anos_combustivel',
            'modelos_anos',
            'valores_fipe'
        ]
        
        for tabela in tabelas:
            sqlite_count = self._contar_registros_sqlite(tabela)
            supabase_count = self._contar_registros_supabase(tabela)
            
            status = "✅" if sqlite_count == supabase_count else "⚠️"
            print(f"{status} {tabela:20s} | SQLite: {sqlite_count:6d} | Supabase: {supabase_count:6d}")
    
    def upload_completo(self):
        """Executa upload completo de todas as tabelas"""
        print("=" * 60)
        print("🚀 UPLOAD SQLite → Supabase")
        print("=" * 60)
        print(f"📂 Banco local: {self.db_path}")
        print(f"📦 Tamanho do lote: {self.batch_size}")
        
        inicio = time.time()
        
        # Ordem correta: respeitar foreign keys
        stats = {}
        stats['tabelas_referencia'] = self.upload_tabelas_referencia()
        stats['marcas'] = self.upload_marcas()
        stats['modelos'] = self.upload_modelos()
        stats['anos_combustivel'] = self.upload_anos_combustivel()
        stats['modelos_anos'] = self.upload_modelos_anos()
        stats['valores_fipe'] = self.upload_valores_fipe()
        
        tempo_total = time.time() - inicio
        
        # Estatísticas finais
        self.mostrar_estatisticas()
        
        print("\n" + "=" * 60)
        print("⏱️  TEMPO DE UPLOAD")
        print("=" * 60)
        print(f"Tempo total: {tempo_total:.1f}s ({tempo_total/60:.1f} minutos)")
        print()
        print("✅ Upload concluído!")
    
    def close(self):
        """Fecha conexão SQLite"""
        self.conn.close()


def main():
    """Função principal"""
    uploader = SupabaseUploader(db_path='fipe_local.db', batch_size=1000)
    
    try:
        uploader.upload_completo()
    finally:
        uploader.close()


if __name__ == "__main__":
    main()
