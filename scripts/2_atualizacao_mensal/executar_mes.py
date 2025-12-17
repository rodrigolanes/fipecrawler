"""
Script principal para atualização mensal completa.
Executa em sequência:
  1. Atualização de modelos (novos modelos Zero Km)
  2. Atualização de valores (preços do novo mês)

Execute este script no início de cada mês quando a tabela FIPE é atualizada.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

import subprocess
import time
from datetime import datetime


def executar_script(script_path, descricao):
    """
    Executa um script Python e retorna código de saída.
    
    Args:
        script_path: Caminho do script a executar
        descricao: Descrição da etapa
        
    Returns:
        bool: True se sucesso, False se erro
    """
    print("=" * 80)
    print(f"📋 {descricao}")
    print("=" * 80)
    print(f"🚀 Executando: {script_path}")
    print()
    
    inicio = time.time()
    
    try:
        # Executa script e mostra output em tempo real
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=ROOT_DIR,
            check=True,
            text=True
        )
        
        tempo = time.time() - inicio
        print()
        print(f"✅ Concluído em {tempo:.1f}s ({tempo/60:.1f} minutos)")
        print()
        return True
        
    except subprocess.CalledProcessError as e:
        tempo = time.time() - inicio
        print()
        print(f"❌ Erro após {tempo:.1f}s")
        print(f"   Código de saída: {e.returncode}")
        print()
        return False
    except KeyboardInterrupt:
        print()
        print("⚠️  Interrompido pelo usuário")
        print()
        return False


def main():
    """Executa rotina mensal completa"""
    print()
    print("=" * 80)
    print("🗓️  ATUALIZAÇÃO MENSAL FIPE - ROTINA COMPLETA")
    print("=" * 80)
    print()
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    print("ℹ️  Esta rotina executa:")
    print("   1️⃣  Atualização de modelos (novos lançamentos Zero Km)")
    print("   2️⃣  Atualização de valores (preços do novo mês)")
    print()
    print("⏱️  Tempo estimado:")
    print("   • Etapa 1: ~10-15 minutos")
    print("   • Etapa 2: Várias horas (depende da quantidade de veículos)")
    print()
    print("💾 Dados salvos no SQLite local (fipe_local.db)")
    print("💡 Execute sincronizar_supabase.py depois para enviar ao Supabase")
    print()
    
    resposta = input("Deseja continuar? (s/n): ")
    
    if resposta.lower() not in ['s', 'sim', 'y', 'yes']:
        print("\n❌ Operação cancelada.")
        return
    
    print()
    
    # Diretório dos scripts mensais
    scripts_dir = Path(__file__).parent
    
    # Lista de scripts na ordem de execução
    etapas = [
        (scripts_dir / "1_atualizar_modelos.py", "ETAPA 1/2 - Atualização de Modelos"),
        (scripts_dir / "2_atualizar_valores.py", "ETAPA 2/2 - Atualização de Valores")
    ]
    
    # Estatísticas
    inicio_total = time.time()
    sucesso = []
    falhas = []
    
    # Executa cada etapa
    for script_path, descricao in etapas:
        if executar_script(script_path, descricao):
            sucesso.append(descricao)
        else:
            falhas.append(descricao)
            print("❌ Etapa falhou. Deseja continuar para próxima etapa? (s/n): ", end="")
            continuar = input()
            if continuar.lower() not in ['s', 'sim', 'y', 'yes']:
                print("\n⚠️  Processo interrompido")
                break
    
    # Relatório final
    tempo_total = time.time() - inicio_total
    
    print()
    print("=" * 80)
    print("📊 RELATÓRIO FINAL - ATUALIZAÇÃO MENSAL")
    print("=" * 80)
    print()
    print(f"⏱️  Tempo total: {tempo_total:.1f}s ({tempo_total/60:.1f} minutos)")
    print()
    
    if sucesso:
        print(f"✅ Etapas concluídas ({len(sucesso)}):")
        for etapa in sucesso:
            print(f"   • {etapa}")
        print()
    
    if falhas:
        print(f"❌ Etapas com erro ({len(falhas)}):")
        for etapa in falhas:
            print(f"   • {etapa}")
        print()
    
    if len(sucesso) == len(etapas):
        print("🎉 ATUALIZAÇÃO MENSAL CONCLUÍDA COM SUCESSO!")
        print()
        print("📋 PRÓXIMOS PASSOS:")
        print("   1. Verifique os dados no SQLite local:")
        print("      sqlite3 fipe_local.db \"SELECT COUNT(*) FROM valores_fipe;\"")
        print()
        print("   2. Sincronize com Supabase:")
        print("      python scripts/3_sincronizacao/sincronizar_supabase.py")
        print()
    else:
        print("⚠️  Atualização incompleta. Revise os erros acima.")
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    main()
