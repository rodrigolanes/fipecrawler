"""
Script para verificar e remover veículos descontinuados da API FIPE.

Este script:
1. Lê o CSV gerado por 2_atualizar_valores.py com veículos descontinuados
2. Para cada veículo, verifica na API FIPE se realmente não existe mais
3. Se confirmado que não existe, remove de modelos_anos no SQLite local
4. Gera relatório final com ações executadas

IMPORTANTE: Este script evita que veículos inexistentes sejam consultados todos os meses.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

import csv
import time
from datetime import datetime
from src.crawler.fipe_crawler import buscar_marcas_carros, buscar_modelos, buscar_anos_modelo
from src.cache.fipe_local_cache import FipeLocalCache
from src.config import get_delay_padrao


def verificar_veiculo_existe_api(codigo_marca, codigo_modelo, ano_modelo, codigo_combustivel, tipo_veiculo=1):
    """
    Verifica se um veículo específico existe na API FIPE.
    
    Busca: Marca → Modelo → Anos
    
    Returns:
        bool: True se existe, False se não existe
    """
    try:
        # 1. Busca o modelo específico
        resultado = buscar_modelos(codigo_marca, tipo_veiculo)
        
        if not resultado or not resultado.get('Modelos'):
            return False
        
        # Verifica se o modelo existe
        modelo_existe = any(m['Value'] == str(codigo_modelo) for m in resultado['Modelos'])
        
        if not modelo_existe:
            return False
        
        time.sleep(get_delay_padrao())
        
        # 2. Busca os anos disponíveis para esse modelo
        anos = buscar_anos_modelo(codigo_marca, codigo_modelo, tipo_veiculo)
        
        if not anos:
            return False
        
        # 3. Verifica se o ano/combustível específico existe
        codigo_ano_combustivel = f"{ano_modelo}-{codigo_combustivel}"
        ano_existe = any(a['Value'] == codigo_ano_combustivel for a in anos)
        
        return ano_existe
    
    except Exception as e:
        print(f"    ⚠️ Erro ao verificar: {e}")
        return None  # None = erro, não conseguimos verificar


def verificar_descontinuados(csv_path):
    """
    Processa arquivo CSV de veículos descontinuados.
    
    Para cada veículo:
    1. Verifica na API se realmente não existe
    2. Se confirmado, remove de modelos_anos
    3. Registra em relatório
    """
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        print(f"❌ Arquivo não encontrado: {csv_path}")
        return
    
    cache = FipeLocalCache()
    conn = cache.conn
    cursor = conn.cursor()
    
    print("=" * 70)
    print("VERIFICAÇÃO DE VEÍCULOS DESCONTINUADOS")
    print("=" * 70)
    print()
    print(f"📂 Arquivo: {csv_path.name}")
    print()
    
    # Lê CSV
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        veiculos = list(reader)
    
    total = len(veiculos)
    print(f"📊 Total de veículos a verificar: {total}")
    print()
    
    # Estatísticas
    stats = {
        'verificados': 0,
        'confirmados_inexistentes': 0,
        'ainda_existem': 0,
        'erros': 0,
        'removidos': 0
    }
    
    # Arquivo de relatório
    relatorio_path = csv_path.parent / f'relatorio_{csv_path.stem}.txt'
    relatorio = open(relatorio_path, 'w', encoding='utf-8')
    relatorio.write(f"RELATÓRIO DE VERIFICAÇÃO DE DESCONTINUADOS\n")
    relatorio.write(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    relatorio.write(f"Arquivo origem: {csv_path.name}\n")
    relatorio.write(f"=" * 70 + "\n\n")
    
    try:
        for i, veiculo in enumerate(veiculos, 1):
            codigo_marca = veiculo['codigo_marca']
            codigo_modelo = veiculo['codigo_modelo']
            tipo_veiculo = int(veiculo['tipo_veiculo'])
            ano_modelo = veiculo['ano_modelo']
            codigo_combustivel = veiculo['codigo_combustivel']
            nome_marca = veiculo['nome_marca']
            nome_modelo = veiculo['nome_modelo']
            
            ano_display = "Zero Km" if ano_modelo == "32000" else ano_modelo
            
            print(f"🔍 [{i}/{total}] Verificando: {nome_marca} {nome_modelo} {ano_display}")
            
            stats['verificados'] += 1
            
            # Verifica na API
            existe = verificar_veiculo_existe_api(
                codigo_marca, codigo_modelo, ano_modelo, 
                codigo_combustivel, tipo_veiculo
            )
            
            if existe is None:
                # Erro na verificação
                stats['erros'] += 1
                print(f"    ⚠️ Erro ao verificar - mantendo no banco por segurança")
                relatorio.write(f"ERRO: {nome_marca} {nome_modelo} {ano_display}\n")
                relatorio.write(f"  Não foi possível verificar na API\n\n")
                
            elif existe:
                # Ainda existe na API (falso positivo - pode ter voltado)
                stats['ainda_existem'] += 1
                print(f"    ✅ Ainda existe na API - mantendo no banco")
                relatorio.write(f"MANTIDO: {nome_marca} {nome_modelo} {ano_display}\n")
                relatorio.write(f"  Veículo ainda está disponível na API FIPE\n\n")
                
            else:
                # Confirmado: não existe na API
                stats['confirmados_inexistentes'] += 1
                print(f"    ❌ Confirmado: não existe na API - REMOVENDO do banco")
                
                # Remove de modelos_anos
                cursor.execute('''
                    DELETE FROM modelos_anos 
                    WHERE codigo_marca = ? 
                    AND codigo_modelo = ? 
                    AND tipo_veiculo = ?
                    AND codigo_ano_combustivel = ?
                ''', (codigo_marca, codigo_modelo, tipo_veiculo, f"{ano_modelo}-{codigo_combustivel}"))
                
                if cursor.rowcount > 0:
                    stats['removidos'] += 1
                    relatorio.write(f"REMOVIDO: {nome_marca} {nome_modelo} {ano_display}\n")
                    relatorio.write(f"  Marca: {codigo_marca} | Modelo: {codigo_modelo} | Ano: {ano_modelo} | Combustível: {codigo_combustivel}\n")
                    relatorio.write(f"  Confirmado que não existe mais na API FIPE\n\n")
                else:
                    relatorio.write(f"JÁ REMOVIDO: {nome_marca} {nome_modelo} {ano_display}\n\n")
            
            # Commit a cada 10 registros
            if stats['verificados'] % 10 == 0:
                conn.commit()
                print(f"\n    💾 Progresso salvo ({stats['verificados']}/{total})\n")
        
        # Commit final
        conn.commit()
        
        print()
        print("=" * 70)
        print("✅ VERIFICAÇÃO CONCLUÍDA!")
        print("=" * 70)
        print()
        print(f"📊 ESTATÍSTICAS:")
        print(f"   • Veículos verificados: {stats['verificados']}")
        print(f"   • Confirmados inexistentes: {stats['confirmados_inexistentes']}")
        print(f"   • Ainda existem na API: {stats['ainda_existem']}")
        print(f"   • Erros de verificação: {stats['erros']}")
        print(f"   • Removidos do banco: {stats['removidos']}")
        print()
        
        relatorio.write("\n" + "=" * 70 + "\n")
        relatorio.write("ESTATÍSTICAS FINAIS\n")
        relatorio.write("=" * 70 + "\n")
        relatorio.write(f"Veículos verificados: {stats['verificados']}\n")
        relatorio.write(f"Confirmados inexistentes: {stats['confirmados_inexistentes']}\n")
        relatorio.write(f"Ainda existem na API: {stats['ainda_existem']}\n")
        relatorio.write(f"Erros de verificação: {stats['erros']}\n")
        relatorio.write(f"Removidos do banco: {stats['removidos']}\n")
        
        print(f"📝 Relatório detalhado salvo em:")
        print(f"   {relatorio_path}")
        print()
        print("💡 Próximos passos:")
        print("   1. Revise o relatório para confirmar remoções")
        print("   2. Execute sincronizar_supabase.py para sincronizar com Supabase")
        print()
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Processo interrompido pelo usuário")
        print(f"📊 Estatísticas parciais:")
        print(f"   • Verificados: {stats['verificados']}")
        print(f"   • Removidos: {stats['removidos']}")
        
        conn.commit()
        print("💾 Alterações salvas!")
    
    except Exception as e:
        print(f"\n\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        relatorio.close()


def listar_csvs_disponiveis():
    """Lista arquivos CSV de descontinuados disponíveis"""
    logs_dir = ROOT_DIR / 'logs'
    
    if not logs_dir.exists():
        print("❌ Diretório logs/ não existe")
        return []
    
    csvs = sorted(logs_dir.glob('descontinuados_*.csv'), reverse=True)
    
    if not csvs:
        print("❌ Nenhum arquivo de descontinuados encontrado em logs/")
        return []
    
    print("📂 Arquivos disponíveis:")
    print()
    for i, csv_path in enumerate(csvs, 1):
        size = csv_path.stat().st_size
        mtime = datetime.fromtimestamp(csv_path.stat().st_mtime)
        print(f"  {i}. {csv_path.name}")
        print(f"     Data: {mtime.strftime('%Y-%m-%d %H:%M:%S')} | Tamanho: {size:,} bytes")
    
    return csvs


if __name__ == "__main__":
    print()
    
    # Lista CSVs disponíveis
    csvs = listar_csvs_disponiveis()
    
    if not csvs:
        print("\n💡 Execute primeiro: python scripts\\2_atualizacao_mensal\\2_atualizar_valores.py")
        sys.exit(1)
    
    print()
    
    if len(csvs) == 1:
        print(f"📌 Usando arquivo mais recente: {csvs[0].name}")
        csv_escolhido = csvs[0]
    else:
        escolha = input(f"\nEscolha o arquivo (1-{len(csvs)}) ou Enter para o mais recente: ").strip()
        
        if not escolha:
            csv_escolhido = csvs[0]
        else:
            try:
                idx = int(escolha) - 1
                if 0 <= idx < len(csvs):
                    csv_escolhido = csvs[idx]
                else:
                    print("❌ Opção inválida")
                    sys.exit(1)
            except ValueError:
                print("❌ Entrada inválida")
                sys.exit(1)
    
    print()
    print("⚠️  ATENÇÃO: Este processo irá:")
    print("   1. Verificar cada veículo na API FIPE (pode demorar)")
    print("   2. Remover registros confirmados como inexistentes")
    print("   3. Modificar o banco de dados SQLite local")
    print()
    
    resposta = input("Deseja continuar? (s/n): ")
    
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        print()
        verificar_descontinuados(csv_escolhido)
    else:
        print("\n❌ Operação cancelada.")
