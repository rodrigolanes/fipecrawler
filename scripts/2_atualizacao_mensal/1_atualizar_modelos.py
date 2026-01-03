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
from src.config import get_delay_padrao, DELAY_RATE_LIMIT_429
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
        'marcas_novas': 0,
        'novos_modelos': 0,
        'novos_anos': 0,
        'erros': 0,
        'tempo_api': 0.0,
        'tempo_db': 0.0,
        'tempo_delays': 0.0
    }
    
    try:
        # Busca todas as marcas da API FIPE
        print("📊 Buscando marcas da API FIPE...")
        print("-" * 70)
        marcas_api = buscar_marcas_carros()
        total_marcas = len(marcas_api)
        print(f"✅ {total_marcas} marcas na API\n")
        
        # Busca marcas já cadastradas no cache local
        print("📦 Verificando marcas no cache local...")
        print("-" * 70)
        marcas_cache = cache.get_all_marcas()
        codigos_cache = {marca['codigo'] for marca in marcas_cache}
        print(f"✅ {len(marcas_cache)} marcas no cache\n")
        
        # Identifica marcas novas (na API mas não no cache)
        marcas_novas = []
        for marca in marcas_api:
            if marca['Value'] not in codigos_cache:
                marcas_novas.append(marca)
        
        if marcas_novas:
            print(f"🆕 {len(marcas_novas)} MARCAS NOVAS encontradas!")
            print("-" * 70)
            for marca in marcas_novas:
                print(f"   • {marca['Label']} (código {marca['Value']})")
            print()
            
            # Salva marcas novas no cache
            print("💾 Salvando marcas novas no cache...")
            cache.save_marcas(marcas_novas)
            stats['marcas_novas'] = len(marcas_novas)
            print(f"✅ Marcas salvas!\n")
        else:
            print("ℹ️  Nenhuma marca nova. Cache está atualizado!\n")
        
        # Atualiza modelos de cada marca
        print("🔄 Buscando novos modelos Zero Km...")
        print("-" * 70)
        
        marcas = marcas_api  # Processa todas as marcas da API
        
        for i, marca in enumerate(marcas, 1):
            codigo_marca = marca['Value']
            nome_marca = marca['Label']
            marca_nova = codigo_marca not in codigos_cache
            
            marcador = "🆕" if marca_nova else "   "
            print(f"{marcador}[{i}/{total_marcas}] {nome_marca} (código {codigo_marca})")
            
            try:
                # Busca modelos existentes no cache
                modelos_cache = cache.get_modelos_marca_dict(codigo_marca)
                
                # Para marcas novas, busca TODOS os modelos; para marcas existentes, apenas Zero Km
                inicio_api = time.time()
                novos = []
                
                if marca_nova:
                    # MARCA NOVA: Busca completa usando endpoint ConsultarModelos
                    print(f"    🆕 Marca nova! Buscando TODOS os modelos...")
                    from src.crawler.fipe_crawler import buscar_modelos
                    resultado = buscar_modelos(codigo_marca, tipo_veiculo=1, nome_marca=nome_marca)
                    
                    if resultado and 'Modelos' in resultado:
                        modelos_api = resultado['Modelos']
                        for modelo in modelos_api:
                            codigo_modelo = str(modelo.get('Value', ''))
                            if codigo_modelo and codigo_modelo not in modelos_cache:
                                novos.append(modelo)
                                modelos_cache[codigo_modelo] = modelo['Label']
                        
                        if novos:
                            print(f"    ✅ {len(novos)} modelos encontrados (marca nova)")
                    else:
                        print(f"    ⚠️  Não foi possível buscar modelos da marca nova")
                else:
                    # MARCA EXISTENTE: Busca apenas modelos Zero Km
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
                        
                        # Delay já implementado em buscar_modelos_por_ano() no fipe_crawler.py
                
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
                            
                            # Delay já implementado em buscar_anos_modelo() no fipe_crawler.py
                        
                        except Exception as e:
                            print(f"        ⚠️ Erro ao buscar anos: {e}")
                            stats['erros'] += 1
                
                # Delay já implementado em buscar_marcas_carros() no fipe_crawler.py
                
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
        if stats['marcas_novas'] > 0:
            print(f"   • 🆕 Marcas novas encontradas: {stats['marcas_novas']}")
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
        
        if stats['marcas_novas'] > 0 or stats['novos_modelos'] > 0:
            print("🎉 Novidades encontradas e salvas no SQLite local!")
            if stats['marcas_novas'] > 0:
                print(f"   • {stats['marcas_novas']} marca(s) nova(s) adicionada(s)")
            if stats['novos_modelos'] > 0:
                print(f"   • {stats['novos_modelos']} modelo(s) novo(s) adicionado(s)")
            print()
            print("💡 Execute upload_para_supabase.py para enviar ao Supabase.")
            print("💡 Depois execute atualizar_valores.py para buscar os preços.")
        else:
            print("ℹ️  Nenhuma novidade encontrada. Banco local está atualizado!")
        print()
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Processo interrompido pelo usuário")
        print(f"📊 Estatísticas parciais:")
        print(f"   • Marcas processadas: {stats['marcas_processadas']}")
        if stats['marcas_novas'] > 0:
            print(f"   • Marcas novas: {stats['marcas_novas']}")
        print(f"   • Novos modelos: {stats['novos_modelos']}")
        print(f"   • Anos carregados: {stats['novos_anos']}")
        print()
    
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        print(f"📊 Estatísticas parciais:")
        print(f"   • Marcas processadas: {stats['marcas_processadas']}")
        if stats['marcas_novas'] > 0:
            print(f"   • Marcas novas: {stats['marcas_novas']}")
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
