"""
Script de migração: Converte mes_referencia de formato português para YYYYMM no SQLite local.

Converte:
- "janeiro de 2026" → "202601"
- "dezembro de 2025" → "202512"

IMPORTANTE: 
- Faça backup do banco antes de executar!
- Este script modifica dados existentes
- Processo é reversível apenas com restore do backup
"""
import sys
from pathlib import Path
import shutil
from datetime import datetime

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.config import mes_pt_para_yyyymm, yyyymm_para_mes_display
from src.cache.fipe_local_cache import FipeLocalCache


def fazer_backup(db_path='fipe_local.db'):
    """Cria backup do banco antes da migração"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def migrar_mes_referencia():
    """
    Migra todos os valores de mes_referencia para formato YYYYMM
    """
    print("=" * 70)
    print("MIGRAÇÃO: mes_referencia → formato YYYYMM")
    print("=" * 70)
    print()
    
    # Backup automático
    print("📦 Criando backup do banco...")
    try:
        backup_path = fazer_backup()
        print(f"✅ Backup criado: {backup_path}")
        print()
    except Exception as e:
        print(f"❌ Erro ao criar backup: {e}")
        print("⚠️  Continuando sem backup (não recomendado)...")
        print()
    
    cache = FipeLocalCache()
    conn = cache.conn
    cursor = conn.cursor()
    
    try:
        # 1. Análise pré-migração
        print("📊 ANÁLISE PRÉ-MIGRAÇÃO")
        print("-" * 70)
        
        cursor.execute('SELECT COUNT(*) FROM valores_fipe')
        total_registros = cursor.fetchone()[0]
        print(f"Total de registros: {total_registros}")
        
        cursor.execute('SELECT DISTINCT mes_referencia FROM valores_fipe')
        meses_distintos = cursor.fetchall()
        print(f"Meses distintos: {len(meses_distintos)}")
        
        print("\nMeses encontrados:")
        meses_contagem = {}
        for (mes,) in meses_distintos:
            cursor.execute('SELECT COUNT(*) FROM valores_fipe WHERE mes_referencia = ?', (mes,))
            qtd = cursor.fetchone()[0]
            meses_contagem[mes] = qtd
            print(f"  • {mes}: {qtd} registros")
        
        print()
        
        # 2. Migração
        print("🔄 INICIANDO MIGRAÇÃO")
        print("-" * 70)
        
        registros_atualizados = 0
        registros_erro = 0
        
        # Processa cada mês distinto
        for mes_antigo in meses_contagem.keys():
            mes_novo = mes_pt_para_yyyymm(mes_antigo)
            
            if not mes_novo:
                print(f"❌ Erro ao converter: {mes_antigo}")
                registros_erro += meses_contagem[mes_antigo]
                continue
            
            # Se já está no formato correto, pula
            if mes_novo == mes_antigo:
                print(f"⏭️  Já convertido: {mes_antigo}")
                continue
            
            qtd = meses_contagem[mes_antigo]
            mes_display = yyyymm_para_mes_display(mes_novo)
            
            print(f"🔄 {mes_antigo} → {mes_novo} ({mes_display}) - {qtd} registros...")
            
            try:
                # Atualiza em lote
                cursor.execute('''
                    UPDATE valores_fipe 
                    SET mes_referencia = ? 
                    WHERE mes_referencia = ?
                ''', (mes_novo, mes_antigo))
                
                registros_atualizados += qtd
                print(f"   ✅ Convertidos: {qtd}")
            
            except Exception as e:
                print(f"   ❌ Erro: {e}")
                registros_erro += qtd
                conn.rollback()
                raise
        
        # Commit final
        conn.commit()
        print()
        
        # 3. Verificação pós-migração
        print("✅ VERIFICAÇÃO PÓS-MIGRAÇÃO")
        print("-" * 70)
        
        cursor.execute('SELECT COUNT(*) FROM valores_fipe')
        total_pos = cursor.fetchone()[0]
        
        cursor.execute('SELECT DISTINCT mes_referencia FROM valores_fipe')
        meses_pos = cursor.fetchall()
        
        print(f"Total de registros: {total_pos}")
        print(f"Meses distintos: {len(meses_pos)}")
        print("\nMeses após migração:")
        
        for (mes,) in meses_pos:
            cursor.execute('SELECT COUNT(*) FROM valores_fipe WHERE mes_referencia = ?', (mes,))
            qtd = cursor.fetchone()[0]
            mes_display = yyyymm_para_mes_display(mes)
            print(f"  • {mes} ({mes_display}): {qtd} registros")
        
        print()
        
        # Validação de integridade
        if total_registros == total_pos:
            print("✅ INTEGRIDADE VERIFICADA: Nenhum registro perdido")
        else:
            print(f"⚠️  AVISO: Total de registros diferente!")
            print(f"   Antes: {total_registros}")
            print(f"   Depois: {total_pos}")
            print(f"   Diferença: {total_pos - total_registros}")
        
        print()
        print("=" * 70)
        print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 70)
        print()
        print(f"📊 Resumo:")
        print(f"   • Registros atualizados: {registros_atualizados}")
        print(f"   • Erros: {registros_erro}")
        print(f"   • Backup: {backup_path if 'backup_path' in locals() else 'N/A'}")
        print()
        print("💡 Próximos passos:")
        print("   1. Teste o script 2_atualizar_valores.py")
        print("   2. Verifique que novos valores são salvos no formato YYYYMM")
        print("   3. Execute sincronizar_supabase.py para enviar ao Supabase")
        print()
    
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERRO DURANTE MIGRAÇÃO")
        print("=" * 70)
        print(f"Erro: {e}")
        print()
        print("🔄 Para restaurar backup:")
        if 'backup_path' in locals():
            print(f"   1. Feche todos os scripts que usam o banco")
            print(f"   2. Substitua fipe_local.db por {backup_path}")
        print()
        
        conn.rollback()
        raise


if __name__ == "__main__":
    print()
    print("⚠️  ATENÇÃO: Esta migração irá modificar TODOS os registros do banco!")
    print("⚠️  Um backup automático será criado antes da migração.")
    print()
    
    resposta = input("Deseja continuar? (s/n): ")
    
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        print()
        migrar_mes_referencia()
    else:
        print("\n❌ Migração cancelada.")
