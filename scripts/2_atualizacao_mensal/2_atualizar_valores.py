"""
Script para atualização completa de valores FIPE.
Busca os valores atualizados de TODOS os veículos já cadastrados no banco.
Deve ser executado mensalmente quando a tabela FIPE é atualizada.
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

import time
import random
from datetime import datetime
from src.crawler.fipe_crawler import buscar_valor_veiculo, obter_codigo_referencia_atual, buscar_tabela_referencia
from src.cache.fipe_local_cache import FipeLocalCache


def atualizar_valores():
    """
    Atualiza os valores FIPE de todos os veículos cadastrados no SQLite local.
    Busca apenas veículos que já têm marca+modelo+ano cadastrados.
    Depois execute upload_para_supabase.py para enviar ao Supabase.
    """
    cache = FipeLocalCache()
    
    print("=" * 70)
    print("FIPE CRAWLER - Atualização Completa de Valores")
    print("=" * 70)
    print()
    
    # Verifica tabela de referência atual
    codigo_ref = obter_codigo_referencia_atual()
    tabelas = buscar_tabela_referencia()
    mes_referencia = tabelas[0]['Mes'] if tabelas else "desconhecido"
    
    print(f"📅 Tabela de referência: {mes_referencia} (código {codigo_ref})")
    print()
    print("ℹ️  Este script atualiza os valores de TODOS os veículos cadastrados.")
    print("ℹ️  Pode levar várias horas dependendo da quantidade de veículos.")
    print()
    
    # Estatísticas
    stats = {
        'total_cadastrados': 0,  # Total de veículos cadastrados
        'total_processar': 0,     # Total a processar (sem valor)
        'processados': 0,         # Realmente tentados
        'valores_atualizados': 0,
        'valores_novos': 0,
        'erros': 0
    }
    
    try:
        # Busca todos os modelos_anos cadastrados (combinações de marca+modelo+ano)
        print("📊 Buscando veículos cadastrados no banco local...")
        print("-" * 70)
        
        # Busca do SQLite local
        conn = cache.conn
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM modelos_anos')
        total_veiculos = cursor.fetchone()[0]
        
        if total_veiculos == 0:
            print("⚠️ Nenhum veículo cadastrado!")
            return
        
        # Busca o mes_referencia real que está sendo usado (pode ser diferente do formato da API de tabelas)
        # Pega o que realmente está salvo nos valores_fipe mais recentes
        cursor.execute('SELECT mes_referencia FROM valores_fipe ORDER BY data_consulta DESC LIMIT 1')
        mes_salvo = cursor.fetchone()
        mes_referencia_real = mes_salvo[0] if mes_salvo else mes_referencia
        
        # Conta quantos já têm valores cadastrados (usando o formato real do banco)
        # Nota: valores_fipe usa ano_modelo + codigo_combustivel, não codigo_ano_combustivel
        cursor.execute('''
            SELECT COUNT(*)
            FROM modelos_anos ma
            INNER JOIN valores_fipe vf 
                ON vf.codigo_marca = ma.codigo_marca
                AND vf.codigo_modelo = ma.codigo_modelo
                AND vf.tipo_veiculo = ma.tipo_veiculo
                AND vf.mes_referencia = ?
            WHERE ma.codigo_ano_combustivel = 
                CAST(vf.ano_modelo AS TEXT) || '-' || CAST(vf.codigo_combustivel AS TEXT)
        ''', (mes_referencia_real,))
        ja_cadastrados = cursor.fetchone()[0]
        
        # Busca apenas veículos SEM valores cadastrados no mês atual
        cursor.execute('''
            SELECT ma.codigo_marca, ma.codigo_modelo, ma.tipo_veiculo, ma.codigo_ano_combustivel
            FROM modelos_anos ma
            LEFT JOIN valores_fipe vf 
                ON vf.codigo_marca = ma.codigo_marca
                AND vf.codigo_modelo = ma.codigo_modelo
                AND vf.tipo_veiculo = ma.tipo_veiculo
                AND vf.mes_referencia = ?
                AND ma.codigo_ano_combustivel = 
                    CAST(vf.ano_modelo AS TEXT) || '-' || CAST(vf.codigo_combustivel AS TEXT)
            WHERE vf.codigo_marca IS NULL
        ''', (mes_referencia_real,))
        veiculos = cursor.fetchall()
        
        total_processar = len(veiculos)
        
        print(f"📊 Total de veículos cadastrados: {total_veiculos}")
        print(f"✅ Já possuem valores ({mes_referencia_real}): {ja_cadastrados}")
        print(f"⏳ Faltam processar: {total_processar}")
        print()
        
        if total_processar == 0:
            print("🎉 Todos os veículos já possuem valores atualizados!")
            print("   Nada a fazer.")
            return
        
        stats['total_cadastrados'] = total_veiculos
        stats['total_processar'] = total_processar
        
        print(f"🔄 Processando {total_processar} veículos sem valores...")
        print("-" * 70)
        
        for i, veiculo in enumerate(veiculos, 1):
                codigo_marca = veiculo[0]
                codigo_modelo = veiculo[1]
                tipo_veiculo = veiculo[2]
                codigo_ano_combustivel = veiculo[3]
                
                # Extrai ano e combustível do código (formato: "2024-1" ou "32000-6")
                if '-' in codigo_ano_combustivel:
                    ano_modelo, codigo_combustivel = codigo_ano_combustivel.split('-')
                else:
                    print(f"    ⚠️ Formato inválido: {codigo_ano_combustivel}")
                    stats['erros'] += 1
                    continue
                
                # Incrementa contador de processados
                stats['processados'] += 1
                
                # Mostra progresso a cada 10 veículos
                if i % 10 == 0 or i == 1:
                    percentual = (i * 100) // total_processar
                    processados = stats['valores_atualizados'] + stats['erros']
                    print(f"    📊 Progresso: {i}/{total_processar} ({percentual}%) | ✅ {stats['valores_atualizados']} salvos | ❌ {stats['erros']} erros | 🔄 {i - processados} em andamento")
                
                try:
                    # Busca valor atualizado da API FIPE (passa codigo_ref para evitar chamadas extras)
                    valor = buscar_valor_veiculo(
                        codigo_marca, 
                        codigo_modelo, 
                        ano_modelo, 
                        codigo_combustivel,
                        tipo_veiculo,  # IMPORTANTE: passa tipo_veiculo
                        codigo_ref  # Passa codigo_ref já obtido no início
                    )
                    
                    if valor and valor.get('Valor'):
                        # Valida que o valor principal está presente
                        valor_texto = valor.get('Valor')
                        
                        # Prepara dados para salvar
                        valor_data = {
                            'codigo_marca': int(codigo_marca),
                            'codigo_modelo': int(codigo_modelo),
                            'tipo_veiculo': int(tipo_veiculo),
                            'ano_modelo': int(ano_modelo),
                            'codigo_combustivel': int(codigo_combustivel),
                            'valor': valor_texto,
                            'marca': valor.get('Marca'),
                            'modelo': valor.get('Modelo'),
                            'combustivel': valor.get('Combustivel'),
                            'codigo_fipe': valor.get('CodigoFipe'),
                            'mes_referencia': valor.get('MesReferencia'),
                            'codigo_referencia': codigo_ref,
                            'data_consulta': datetime.now().isoformat()
                        }
                        
                        # Extrai valor numérico
                        valor_limpo = valor_texto.replace('R$', '').replace('.', '').replace(',', '.').strip()
                        try:
                            valor_data['valor_numerico'] = float(valor_limpo)
                        except:
                            valor_data['valor_numerico'] = 0.0
                        
                        # Salva no SQLite local (sem commit imediato)
                        cache.save_valor_fipe(valor_data, commit=False)
                        stats['valores_atualizados'] += 1
                        
                        # Commit a cada 10 registros para salvar progresso
                        if stats['valores_atualizados'] % 10 == 0:
                            cache.conn.commit()
                    else:
                        # API retornou mas sem valor (veículo descontinuado ou sem preço)
                        stats['erros'] += 1
                    
                    # Delay entre requisições (0.8-1.2s - reduzido após otimização)
                    time.sleep(random.uniform(0.8, 1.2))
                
                except Exception as e:
                    if "429" in str(e) or "too many" in str(e).lower():
                        # Rate limit atingido - espera mais tempo
                        print(f"    ⚠️ Rate limit atingido. Aguardando 30s...")
                        time.sleep(30)
                        
                        # Tenta novamente
                        try:
                            valor = buscar_valor_veiculo(
                                codigo_marca, 
                                codigo_modelo, 
                                ano_modelo, 
                                codigo_combustivel,
                                codigo_ref  # Passa codigo_ref também no retry
                            )
                            if valor:
                                valor_data = {
                                    'codigo_marca': int(codigo_marca),
                                    'codigo_modelo': int(codigo_modelo),
                                    'ano_modelo': int(ano_modelo),
                                    'codigo_combustivel': int(codigo_combustivel),
                                    'valor': valor.get('Valor'),
                                    'marca': valor.get('Marca'),
                                    'modelo': valor.get('Modelo'),
                                    'combustivel': valor.get('Combustivel'),
                                    'codigo_fipe': valor.get('CodigoFipe'),
                                    'mes_referencia': valor.get('MesReferencia'),
                                    'codigo_referencia': codigo_ref,
                                    'data_consulta': datetime.now().isoformat()
                                }
                                valor_texto = valor.get('Valor', 'R$ 0,00')
                                valor_limpo = valor_texto.replace('R$', '').replace('.', '').replace(',', '.').strip()
                                try:
                                    valor_data['valor_numerico'] = float(valor_limpo)
                                except:
                                    valor_data['valor_numerico'] = 0.0
                                cache.save_valor_fipe(valor_data, commit=False)
                                stats['valores_atualizados'] += 1
                                
                                # Commit a cada 10 registros
                                if stats['valores_atualizados'] % 10 == 0:
                                    cache.conn.commit()
                        except Exception as retry_error:
                            print(f"    ❌ Erro após retry: {retry_error}")
                            stats['erros'] += 1
                    else:
                        print(f"    ❌ Erro ao buscar valor: {e}")
                        stats['erros'] += 1
                    
                    # Incrementa processados mesmo em caso de erro
                    stats['processados'] += 1
                    continue
        
        # Resumo final
        print("\n" + "=" * 70)
        print("✅ ATUALIZAÇÃO DE VALORES CONCLUÍDA!")
        print("=" * 70)
        print()
        print(f"📊 ESTATÍSTICAS:")
        print(f"   • Veículos cadastrados: {stats['total_cadastrados']}")
        print(f"   • Faltavam processar: {stats['total_processar']}")
        print(f"   • Realmente processados: {stats['processados']}")
        print(f"   • Valores atualizados: {stats['valores_atualizados']}")
        print(f"   • Erros: {stats['erros']}")
        print()
        print(f"📅 Referência: {mes_referencia}")
        print("💾 Todos os valores foram salvos no SQLite local (fipe_local.db)!")
        print("💡 Execute upload_para_supabase.py para enviar ao Supabase.")
        print()
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Processo interrompido pelo usuário")
        print(f"📊 Estatísticas parciais:")
        print(f"   • Realmente processados: {stats['processados']}")
        print(f"   • Valores atualizados: {stats['valores_atualizados']}")
        print(f"   • Erros: {stats['erros']}")
        print()
        
        # Commit final para garantir que tudo foi salvo
        print("💾 Salvando alterações finais...")
        cache.conn.commit()
        print("✅ Dados salvos no SQLite!")
    
    except Exception as e:
        print(f"\n\n❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()
        
        # Salvar progresso parcial antes de sair
        print("\n💾 Salvando progresso parcial...")
        try:
            cache.conn.commit()
            print("✅ Progresso salvo!")
        except:
            print("❌ Não foi possível salvar o progresso")
        
        print()
        print(f"📊 Estatísticas parciais:")
        print(f"   • Realmente processados: {stats['processados']}")
        print(f"   • Valores atualizados: {stats['valores_atualizados']}")
        print()


if __name__ == "__main__":
    print()
    print("⚠️  ATENÇÃO: Este processo pode levar VÁRIAS HORAS!")
    print("⚠️  Certifique-se de ter uma conexão estável com a internet.")
    print("⚠️  O processo pode ser interrompido (Ctrl+C) e retomado depois.")
    print()
    
    resposta = input("Deseja continuar? (s/n): ")
    
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        print()
        atualizar_valores()
    else:
        print("\n❌ Operação cancelada.")
