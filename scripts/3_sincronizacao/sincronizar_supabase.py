"""
Script para carregar dados do SQLite local para o Supabase.
Útil após popular o banco localmente com popular_banco_otimizado.py
"""
import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para o stdout (Windows)
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

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
    
    def limpar_valores_fipe_orfaos(self):
        """Remove valores FIPE que não existem mais no SQLite"""
        print("\n🧹 LIMPEZA DE VALORES FIPE")
        print("-" * 60)
        
        try:
            # Busca todas as PKs do SQLite
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT codigo_marca, codigo_modelo, tipo_veiculo, ano_modelo, 
                       codigo_combustivel, mes_referencia
                FROM valores_fipe
            ''')
            sqlite_keys = {
                (row['codigo_marca'], row['codigo_modelo'], row['tipo_veiculo'], 
                 row['ano_modelo'], row['codigo_combustivel'], row['mes_referencia'])
                for row in cursor.fetchall()
            }
            print(f"   📊 {len(sqlite_keys)} registros no SQLite")
            
            # Busca todos os registros do Supabase (em lotes)
            print("   🌐 Buscando registros do Supabase...")
            supabase_data = []
            offset = 0
            batch_size = 1000
            
            while True:
                response = self.supabase.table('valores_fipe').select(
                    'codigo_marca,codigo_modelo,tipo_veiculo,ano_modelo,codigo_combustivel,mes_referencia'
                ).range(offset, offset + batch_size - 1).execute()
                
                if not response.data:
                    break
                    
                supabase_data.extend(response.data)
                offset += batch_size
                
                if len(response.data) < batch_size:
                    break
            
            supabase_keys = {
                (r['codigo_marca'], r['codigo_modelo'], r['tipo_veiculo'],
                 r['ano_modelo'], r['codigo_combustivel'], r['mes_referencia'])
                for r in supabase_data
            }
            print(f"   📊 {len(supabase_keys)} registros no Supabase")
            
            # Registros que existem no Supabase mas não no SQLite
            para_deletar = supabase_keys - sqlite_keys
            
            if not para_deletar:
                print("   ✅ Nenhum registro órfão encontrado")
                return 0
            
            print(f"   🗑️  {len(para_deletar)} registros para deletar")
            
            # Deleta em lotes
            deletados = 0
            for keys in para_deletar:
                try:
                    self.supabase.table('valores_fipe').delete().match({
                        'codigo_marca': keys[0],
                        'codigo_modelo': keys[1],
                        'tipo_veiculo': keys[2],
                        'ano_modelo': keys[3],
                        'codigo_combustivel': keys[4],
                        'mes_referencia': keys[5]
                    }).execute()
                    deletados += 1
                    if deletados % 100 == 0:
                        print(f"   🗑️  {deletados}/{len(para_deletar)} deletados ({deletados*100//len(para_deletar)}%)")
                except Exception as e:
                    print(f"   ❌ Erro ao deletar {keys}: {e}")
            
            print(f"   ✅ {deletados} registros deletados")
            return deletados
            
        except Exception as e:
            print(f"   ❌ Erro ao limpar valores FIPE: {e}")
            return 0
    
    def limpar_modelos_anos_orfaos(self):
        """Remove relacionamentos modelo-ano que não existem mais no SQLite"""
        print("\n🧹 LIMPEZA DE RELACIONAMENTOS MODELO-ANO")
        print("-" * 60)
        
        try:
            # Busca todas as PKs do SQLite
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT codigo_marca, codigo_modelo, tipo_veiculo, codigo_ano_combustivel
                FROM modelos_anos
            ''')
            sqlite_keys = {
                (row['codigo_marca'], row['codigo_modelo'], row['tipo_veiculo'], row['codigo_ano_combustivel'])
                for row in cursor.fetchall()
            }
            print(f"   📊 {len(sqlite_keys)} registros no SQLite")
            
            # Busca todos os registros do Supabase (em lotes)
            print("   🌐 Buscando registros do Supabase...")
            supabase_data = []
            offset = 0
            batch_size = 1000
            
            while True:
                response = self.supabase.table('modelos_anos').select(
                    'codigo_marca,codigo_modelo,tipo_veiculo,codigo_ano_combustivel'
                ).range(offset, offset + batch_size - 1).execute()
                
                if not response.data:
                    break
                    
                supabase_data.extend(response.data)
                offset += batch_size
                print(f"      Carregados {len(supabase_data)} registros...")
                
                if len(response.data) < batch_size:
                    break
            
            supabase_keys = {
                (r['codigo_marca'], r['codigo_modelo'], r['tipo_veiculo'], r['codigo_ano_combustivel'])
                for r in supabase_data
            }
            print(f"   📊 {len(supabase_keys)} registros no Supabase")
            
            # Registros que existem no Supabase mas não no SQLite
            para_deletar = supabase_keys - sqlite_keys
            
            if not para_deletar:
                print("   ✅ Nenhum registro órfão encontrado")
                return 0
            
            print(f"   🗑️  {len(para_deletar)} registros para deletar")
            
            # Deleta em lotes
            deletados = 0
            for keys in para_deletar:
                try:
                    self.supabase.table('modelos_anos').delete().match({
                        'codigo_marca': keys[0],
                        'codigo_modelo': keys[1],
                        'tipo_veiculo': keys[2],
                        'codigo_ano_combustivel': keys[3]
                    }).execute()
                    deletados += 1
                    if deletados % 100 == 0:
                        print(f"   🗑️  {deletados}/{len(para_deletar)} deletados ({deletados*100//len(para_deletar)}%)")
                except Exception as e:
                    print(f"   ❌ Erro ao deletar {keys}: {e}")
            
            print(f"   ✅ {deletados} registros deletados")
            return deletados
            
        except Exception as e:
            print(f"   ❌ Erro ao limpar modelos_anos: {e}")
            return 0
    
    def limpar_modelos_orfaos(self):
        """Remove modelos que não existem mais no SQLite"""
        print("\n🧹 LIMPEZA DE MODELOS")
        print("-" * 60)
        
        try:
            # Busca todas as PKs do SQLite
            cursor = self.conn.cursor()
            cursor.execute('SELECT codigo, codigo_marca, tipo_veiculo FROM modelos')
            sqlite_keys = {
                (row['codigo'], row['codigo_marca'], row['tipo_veiculo'])
                for row in cursor.fetchall()
            }
            print(f"   📊 {len(sqlite_keys)} registros no SQLite")
            
            # Busca todos os registros do Supabase (em lotes)
            print("   🌐 Buscando registros do Supabase...")
            supabase_data = []
            offset = 0
            batch_size = 1000
            
            while True:
                response = self.supabase.table('modelos').select(
                    'codigo,codigo_marca,tipo_veiculo'
                ).range(offset, offset + batch_size - 1).execute()
                
                if not response.data:
                    break
                    
                supabase_data.extend(response.data)
                offset += batch_size
                
                if len(response.data) < batch_size:
                    break
            
            supabase_keys = {
                (r['codigo'], r['codigo_marca'], r['tipo_veiculo'])
                for r in supabase_data
            }
            print(f"   📊 {len(supabase_keys)} registros no Supabase")
            
            # Registros que existem no Supabase mas não no SQLite
            para_deletar = supabase_keys - sqlite_keys
            
            if not para_deletar:
                print("   ✅ Nenhum registro órfão encontrado")
                return 0
            
            print(f"   🗑️  {len(para_deletar)} registros para deletar")
            
            # Deleta individualmente
            deletados = 0
            for keys in para_deletar:
                try:
                    self.supabase.table('modelos').delete().match({
                        'codigo': keys[0],
                        'codigo_marca': keys[1],
                        'tipo_veiculo': keys[2]
                    }).execute()
                    deletados += 1
                    if deletados % 50 == 0:
                        print(f"   🗑️  {deletados}/{len(para_deletar)} deletados ({deletados*100//len(para_deletar)}%)")
                except Exception as e:
                    print(f"   ❌ Erro ao deletar {keys}: {e}")
            
            print(f"   ✅ {deletados} registros deletados")
            return deletados
            
        except Exception as e:
            print(f"   ❌ Erro ao limpar modelos: {e}")
            return 0
    
    def upload_completo(self):
        """Executa sincronização completa: upload + limpeza"""
        print("=" * 60)
        print("🔄 SINCRONIZAÇÃO SQLite ↔ Supabase")
        print("=" * 60)
        print(f"📂 Banco local: {self.db_path}")
        print(f"📦 Tamanho do lote: {self.batch_size}")
        
        inicio = time.time()
        
        # FASE 1: Upload (adicionar/atualizar)
        print("\n" + "=" * 60)
        print("📤 FASE 1: UPLOAD DE DADOS")
        print("=" * 60)
        
        stats = {}
        stats['tabelas_referencia'] = self.upload_tabelas_referencia()
        stats['marcas'] = self.upload_marcas()
        stats['modelos'] = self.upload_modelos()
        stats['anos_combustivel'] = self.upload_anos_combustivel()
        stats['modelos_anos'] = self.upload_modelos_anos()
        stats['valores_fipe'] = self.upload_valores_fipe()
        
        # FASE 2: Limpeza (remover órfãos)
        print("\n" + "=" * 60)
        print("🧹 FASE 2: LIMPEZA DE DADOS ÓRFÃOS")
        print("=" * 60)
        
        deletados = {}
        deletados['valores_fipe'] = self.limpar_valores_fipe_orfaos()
        deletados['modelos_anos'] = self.limpar_modelos_anos_orfaos()
        deletados['modelos'] = self.limpar_modelos_orfaos()
        
        tempo_total = time.time() - inicio
        
        # Estatísticas finais
        self.mostrar_estatisticas()
        
        print("\n" + "=" * 60)
        print("📊 RESUMO DA SINCRONIZAÇÃO")
        print("=" * 60)
        print("\n📤 Registros enviados:")
        for tabela, count in stats.items():
            print(f"   {tabela:25s}: {count:6d}")
        
        print("\n🗑️  Registros deletados:")
        for tabela, count in deletados.items():
            print(f"   {tabela:25s}: {count:6d}")
        
        print("\n" + "=" * 60)
        print("⏱️  TEMPO DE SINCRONIZAÇÃO")
        print("=" * 60)
        print(f"Tempo total: {tempo_total:.1f}s ({tempo_total/60:.1f} minutos)")
        print()
        print("✅ Sincronização concluída!")
    
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
