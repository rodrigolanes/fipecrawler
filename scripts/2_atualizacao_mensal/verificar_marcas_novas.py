"""
Script para verificar se há marcas novas na API FIPE.
Rápido e simples - não processa modelos, apenas verifica marcas.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.crawler.fipe_crawler import buscar_marcas_carros
from src.cache.fipe_local_cache import FipeLocalCache


def verificar_marcas_novas():
    """
    Verifica se há marcas novas na API FIPE comparando com o cache local.
    Opcionalmente salva as marcas novas no cache.
    """
    cache = FipeLocalCache()
    
    print("=" * 70)
    print("FIPE CRAWLER - Verificação Rápida de Marcas Novas")
    print("=" * 70)
    print()
    
    try:
        # Busca marcas da API FIPE
        print("🌐 Buscando marcas da API FIPE...")
        marcas_api = buscar_marcas_carros()
        total_api = len(marcas_api)
        print(f"✅ {total_api} marcas encontradas na API\n")
        
        # Busca marcas do cache local
        print("📦 Buscando marcas do cache local...")
        marcas_cache = cache.get_all_marcas()
        total_cache = len(marcas_cache)
        codigos_cache = {marca['codigo'] for marca in marcas_cache}
        print(f"✅ {total_cache} marcas encontradas no cache\n")
        
        # Identifica marcas novas
        marcas_novas = []
        for marca in marcas_api:
            if marca['Value'] not in codigos_cache:
                marcas_novas.append(marca)
        
        # Mostra resultado
        print("=" * 70)
        print("📊 RESULTADO")
        print("=" * 70)
        print()
        
        if marcas_novas:
            print(f"🆕 {len(marcas_novas)} MARCA(S) NOVA(S) ENCONTRADA(S)!")
            print("-" * 70)
            for marca in marcas_novas:
                print(f"   • {marca['Label']} (código {marca['Value']})")
            print()
            
            # Pergunta se deseja salvar
            resposta = input("💾 Deseja salvar as marcas novas no cache local? (s/n): ")
            
            if resposta.lower() in ['s', 'sim', 'y', 'yes']:
                cache.save_marcas(marcas_novas)
                print("✅ Marcas salvas no cache local!")
                print()
                print("💡 Próximos passos:")
                print("   1. Execute atualizar_modelos.py para buscar os modelos dessas marcas")
                print("   2. Execute upload_para_supabase.py para sincronizar com Supabase")
                print("   3. Execute atualizar_valores.py para buscar os preços")
            else:
                print("⚠️  Marcas NÃO foram salvas.")
                print("   Execute este script novamente quando quiser salvá-las.")
        else:
            print("✅ NENHUMA MARCA NOVA!")
            print("   O cache local está atualizado com todas as marcas da API FIPE.")
        
        print()
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Processo interrompido pelo usuário")
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    verificar_marcas_novas()
