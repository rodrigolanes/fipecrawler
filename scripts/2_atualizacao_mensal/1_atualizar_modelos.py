"""
Script para atualização incremental de modelos.
Busca novos modelos Zero Km por marca para descobrir lançamentos.
Muito mais rápido que popular_banco.py pois só busca novidades.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

import time
import random
from src.crawler.fipe_crawler import buscar_marcas_carros, buscar_modelos_por_ano, buscar_anos_modelo
from src.cache.fipe_local_cache import FipeLocalCache


def atualizar_modelos():
    """
    Atualiza modelos de todas as marcas buscando por Zero Km.
    Descobre novos lançamentos sem precisar reprocessar tudo.
    Salva no SQLite local (fipe_local.db).
    """
    cache = FipeLocalCache()
    
    print("=" * 70)
    print("FIPE CRAWLER - Atualização Incremental de Modelos")
    print("=" * 70)
    print()
    print("ℹ️  Este script busca apenas modelos Zero Km para descobrir lançamentos.")
    print("ℹ️  É muito mais rápido que popular_banco.py e deve ser executado mensalmente.")
    print()
    
    # Estatísticas
    stats = {
        'marcas_processadas': 0,
        'novos_modelos': 0,
        'novos_anos': 0,
        'erros': 0,
        'tempo_api': 0.0,
        'tempo_db': 0.0,
        'tempo_delays': 0.0
    }
    
    try:
        # Busca todas as marcas
        print("📊 Buscando marcas cadastradas...")
        print("-" * 70)
        marcas = buscar_marcas_carros()
        total_marcas = len(marcas)
        print(f"✅ {total_marcas} marcas encontradas\n")
        
        # Atualiza modelos de cada marca
        print("🔄 Buscando novos modelos Zero Km...")
        print("-" * 70)
        
        for i, marca in enumerate(marcas, 1):
            codigo_marca = marca['Value']
            nome_marca = marca['Label']
            
            print(f"[{i}/{total_marcas}] {nome_marca} (código {codigo_marca})")
            
            try:
                # Busca modelos existentes no cache
                modelos_cache = cache.get_modelos_marca_dict(codigo_marca)
                
                # Busca novos modelos Zero Km em todos os combustíveis
                inicio_api = time.time()
                novos = []
                combustiveis = [1, 2, 3, 4, 5, 6, 7]  # Todos os tipos
                
                for combustivel in combustiveis:
                    modelos_api = buscar_modelos_por_ano(
                        codigo_marca, 
                        ano_modelo="32000",
                        codigo_combustivel=combustivel,
                        nome_marca=nome_marca
                    )
                    
                    if modelos_api:
                        for modelo in modelos_api:
                            codigo_modelo = str(modelo.get('Value', ''))
                            if codigo_modelo and codigo_modelo not in modelos_cache:
                                novos.append(modelo)
                                modelos_cache[codigo_modelo] = modelo['Label']
                    
                    time.sleep(random.uniform(0.3, 0.5))
                
                stats['tempo_api'] += time.time() - inicio_api
                
                # Salva novos modelos
                if novos:
                    cache.save_modelos(novos, codigo_marca)
                    print(f"    ✅ {len(novos)} novos modelos encontrados!")
                    stats['novos_modelos'] += len(novos)
                
                stats['marcas_processadas'] += 1
                
                # Para cada novo modelo, busca os anos disponíveis
                if novos:
                    print(f"    📅 Buscando anos dos novos modelos...")
                    for modelo in novos:
                        codigo_modelo = modelo['Value']
                        
                        try:
                            inicio_anos = time.time()
                            anos = buscar_anos_modelo(codigo_marca, codigo_modelo, tipo_veiculo=1)
                            stats['tempo_api'] += time.time() - inicio_anos
                            
                            if anos:
                                cache.save_anos_modelo(anos, codigo_marca, codigo_modelo, tipo_veiculo=1)
                                stats['novos_anos'] += len(anos)
                            
                            # Delay entre modelos
                            inicio_delay = time.time()
                            time.sleep(random.uniform(0.5, 1.0))
                            stats['tempo_delays'] += time.time() - inicio_delay
                        
                        except Exception as e:
                            print(f"        ⚠️ Erro ao buscar anos: {e}")
                            stats['erros'] += 1
                
                # Delay entre marcas
                inicio_delay = time.time()
                time.sleep(random.uniform(2.0, 3.0))
                stats['tempo_delays'] += time.time() - inicio_delay
                
            except Exception as e:
                print(f"    ❌ Erro ao processar marca {nome_marca}: {e}")
                stats['erros'] += 1
                continue
        
        # Resumo final
        print("\n" + "=" * 70)
        print("✅ ATUALIZAÇÃO CONCLUÍDA!")
        print("=" * 70)
        print()
        print(f"📊 ESTATÍSTICAS:")
        print(f"   • Marcas processadas: {stats['marcas_processadas']}/{total_marcas}")
        print(f"   • Novos modelos encontrados: {stats['novos_modelos']}")
        print(f"   • Anos/Combustível carregados: {stats['novos_anos']}")
        print(f"   • Erros: {stats['erros']}")
        print()
        print(f"⏱️  TEMPO:")
        print(f"   • API FIPE + Supabase: {stats['tempo_api']:.1f}s")
        print(f"   • Delays (rate limiting): {stats['tempo_delays']:.1f}s")
        print(f"   • Total: {stats['tempo_api'] + stats['tempo_delays']:.1f}s")
        print()
        
        # Análise do gargalo
        total_tempo = stats['tempo_api'] + stats['tempo_delays']
        if total_tempo > 0:
            perc_api = (stats['tempo_api'] / total_tempo) * 100
            perc_delays = (stats['tempo_delays'] / total_tempo) * 100
            print(f"📈 ANÁLISE:")
            print(f"   • API/DB: {perc_api:.1f}% do tempo")
            print(f"   • Delays: {perc_delays:.1f}% do tempo")
            print()
            
            if perc_delays > 70:
                print("💡 Gargalo: Delays de segurança (rate limiting)")
                print("   → Delays são necessários para evitar bloqueio da API")
            elif perc_api > 70:
                print("💡 Gargalo: Requisições de rede (API FIPE + Supabase)")
                print("   → Tempo gasto em comunicação com servidores")
        print()
        
        if stats['novos_modelos'] > 0:
            print("🎉 Novos modelos foram adicionados ao SQLite local!")
            print("💡 Execute upload_para_supabase.py para enviar ao Supabase.")
            print("💡 Depois execute atualizar_valores.py para buscar os preços.")
        else:
            print("ℹ️  Nenhum modelo novo encontrado. Banco local está atualizado!")
        print()
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Processo interrompido pelo usuário")
        print(f"📊 Estatísticas parciais:")
        print(f"   • Marcas processadas: {stats['marcas_processadas']}")
        print(f"   • Novos modelos: {stats['novos_modelos']}")
        print(f"   • Anos carregados: {stats['novos_anos']}")
        print()
    
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        print(f"📊 Estatísticas parciais:")
        print(f"   • Marcas processadas: {stats['marcas_processadas']}")
        print(f"   • Novos modelos: {stats['novos_modelos']}")
        print()


if __name__ == "__main__":
    print()
    print("⚠️  Este processo busca novos modelos Zero Km de todas as marcas.")
    print("⚠️  Tempo estimado: 10-15 minutos.")
    print()
    
    resposta = input("Deseja continuar? (s/n): ")
    
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        print()
        atualizar_modelos()
    else:
        print("\n❌ Operação cancelada.")
