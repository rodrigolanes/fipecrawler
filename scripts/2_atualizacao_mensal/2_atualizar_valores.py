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
from datetime import datetime
from src.config import DELAY_RATE_LIMIT_429, mes_pt_para_yyyymm, yyyymm_para_mes_display
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
    mes_referencia_api = tabelas[0]['Mes'] if tabelas else "desconhecido"
    
    # Converte para formato YYYYMM (202601)
    mes_referencia = mes_pt_para_yyyymm(mes_referencia_api)
    
    # Formato legível para exibição
    mes_display = yyyymm_para_mes_display(mes_referencia)
    
    print(f"📅 Tabela de referência: {mes_display} (código {codigo_ref})")
    print()
    print("ℹ️  Este script atualiza os valores FIPE de TODOS os veículos cadastrados.")
    print("ℹ️  A FIPE publica novos valores mensalmente para veículos novos e antigos.")
    print("ℹ️  Pode levar várias horas dependendo da quantidade de veículos.")
    print()
    
    # Estatísticas
    stats = {
        'total_veiculos': 0,      # Total de veículos cadastrados (combinações marca+modelo+ano)
        'ja_atualizados': 0,      # Já possuem valor no mês atual
        'faltam_atualizar': 0,    # Faltam atualizar no mês atual
        'processados': 0,         # Realmente tentados
        'valores_salvos': 0,      # Salvos com sucesso
        'erros': 0                # Erros durante o processo
    }
    
    try:
        # Busca todos os modelos_anos cadastrados (combinações de marca+modelo+ano)
        print("📊 Buscando veículos cadastrados no banco local...")
        print("-" * 70)
        
        conn = cache.conn
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM modelos_anos')
        total_veiculos = cursor.fetchone()[0]
        
        if total_veiculos == 0:
            print("⚠️ Nenhum veículo cadastrado!")
            print("💡 Execute popular_completo.py primeiro para popular o banco.")
            return
        
        print(f"✅ {total_veiculos} veículos cadastrados (combinações de marca+modelo+ano)\n")
        stats['total_veiculos'] = total_veiculos
        
        # Verifica quantos JÁ TÊM valores para o mês de referência atual
        # IMPORTANTE: Cada veículo pode ter múltiplos valores (um por mês)
        print(f"🔍 Verificando valores já cadastrados para {mes_display}...")
        print("-" * 70)
        
        cursor.execute('''
            SELECT COUNT(DISTINCT ma.codigo_marca || '-' || ma.codigo_modelo || '-' || ma.codigo_ano_combustivel)
            FROM modelos_anos ma
            INNER JOIN valores_fipe vf 
                ON vf.codigo_marca = ma.codigo_marca
                AND vf.codigo_modelo = ma.codigo_modelo
                AND vf.tipo_veiculo = ma.tipo_veiculo
                AND vf.mes_referencia = ?
            WHERE ma.codigo_ano_combustivel = 
                CAST(vf.ano_modelo AS TEXT) || '-' || CAST(vf.codigo_combustivel AS TEXT)
        ''', (mes_referencia,))
        ja_atualizados = cursor.fetchone()[0]
        
        faltam_atualizar = total_veiculos - ja_atualizados
        
        print(f"✅ Já atualizados ({mes_display}): {ja_atualizados}")
        print(f"⏳ Faltam atualizar: {faltam_atualizar}")
        print()
        
        stats['ja_atualizados'] = ja_atualizados
        stats['faltam_atualizar'] = faltam_atualizar
        
        if faltam_atualizar == 0:
            print("🎉 Todos os veículos já possuem valores atualizados para este mês!")
            print(f"   Mês de referência: {mes_display}")
            print("   Nada a fazer.")
            return
        
        # Busca APENAS os veículos que NÃO TÊM valor para o mês atual
        # Isso permite que o script seja retomado se interrompido
        print(f"🔄 Buscando valores de {faltam_atualizar} veículos...")
        print("-" * 70)
        
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
            ORDER BY 
                CAST(SUBSTR(ma.codigo_ano_combustivel, 1, INSTR(ma.codigo_ano_combustivel, '-') - 1) AS INTEGER) DESC,
                ma.codigo_marca, 
                ma.codigo_modelo
        ''', (mes_referencia,))
        veiculos = cursor.fetchall()
        
        print(f"🚗 {len(veiculos)} veículos para processar\n")
        
        # Pré-processa veículos para contar por ano
        print("📊 Analisando distribuição por ano...")
        veiculos_por_ano = {}
        for veiculo in veiculos:
            codigo_ano_combustivel = veiculo[3]
            if '-' in codigo_ano_combustivel:
                ano_modelo = codigo_ano_combustivel.split('-')[0]
                veiculos_por_ano[ano_modelo] = veiculos_por_ano.get(ano_modelo, 0) + 1
        
        # Mostra distribuição
        print(f"{'='*70}")
        for ano_cod in sorted(veiculos_por_ano.keys(), reverse=True):
            ano_display = "Zero Km" if ano_cod == "32000" else ano_cod
            print(f"  • {ano_display}: {veiculos_por_ano[ano_cod]} veículos")
        print(f"{'='*70}\n")
        
        # Controle de ano atual para logs informativos
        ano_atual_processamento = None
        contador_ano_atual = 0
        total_ano_atual = 0
        
        for i, veiculo in enumerate(veiculos, 1):
                codigo_marca = veiculo[0]
                codigo_modelo = veiculo[1]
                tipo_veiculo = veiculo[2]
                codigo_ano_combustivel = veiculo[3]
                
                # Extrai ano e combustível do código (formato: "2024-1" ou "32000-6")
                if '-' in codigo_ano_combustivel:
                    ano_modelo, codigo_combustivel = codigo_ano_combustivel.split('-')
                    
                    # Log quando mudar de ano
                    if ano_modelo != ano_atual_processamento:
                        if ano_atual_processamento is not None:
                            # Mostra estatísticas do ano anterior
                            ano_display_anterior = "Zero Km" if ano_atual_processamento == "32000" else ano_atual_processamento
                            print(f"\n    ✅ Ano {ano_display_anterior}: {contador_ano_atual}/{total_ano_atual} veículos processados")
                            print()
                        
                        ano_atual_processamento = ano_modelo
                        contador_ano_atual = 0
                        total_ano_atual = veiculos_por_ano.get(ano_modelo, 0)
                        
                        # Nome amigável do ano
                        ano_display = "Zero Km" if ano_modelo == "32000" else ano_modelo
                        print(f"\n{'='*70}")
                        print(f"🚗 Processando veículos: {ano_display} ({total_ano_atual} veículos)")
                        print(f"{'='*70}\n")
                    
                    # Incrementa contador do ano
                    contador_ano_atual += 1
                else:
                    print(f"    ⚠️ Formato inválido: {codigo_ano_combustivel}")
                    stats['erros'] += 1
                    continue
                
                # Incrementa contador de processados
                stats['processados'] += 1
                
                # Mostra progresso a cada 10 veículos (relativo ao ano)
                if contador_ano_atual % 10 == 0 or contador_ano_atual == 1:
                    percentual = (contador_ano_atual * 100) // total_ano_atual if total_ano_atual > 0 else 0
                    print(f"    📊 [{contador_ano_atual}/{total_ano_atual}] {percentual}% | ✅ {stats['valores_salvos']} salvos | ❌ {stats['erros']} erros")
                    
                    # Debug: mostra último mes_referencia salvo
                    if i == 1:
                        cursor.execute('SELECT mes_referencia FROM valores_fipe ORDER BY data_consulta DESC LIMIT 1')
                        ultimo_mes = cursor.fetchone()
                        if ultimo_mes:
                            print(f"    🔍 Último mês salvo no banco: {ultimo_mes[0]}")
                
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
                            'mes_referencia': mes_pt_para_yyyymm(valor.get('MesReferencia')),  # Converte para YYYYMM
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
                        stats['valores_salvos'] += 1
                        
                        # Commit a cada 10 registros para salvar progresso
                        if stats['valores_salvos'] % 10 == 0:
                            cache.conn.commit()
                    else:
                        # API retornou mas sem valor (veículo descontinuado ou sem preço)
                        stats['erros'] += 1
                    
                    # Delay já implementado em buscar_valor_veiculo() no fipe_crawler.py
                
                except Exception as e:
                    if "429" in str(e) or "too many" in str(e).lower():
                        # Rate limit atingido - espera mais tempo
                        print(f"    ⚠️ Rate limit atingido. Aguardando {DELAY_RATE_LIMIT_429}s...")
                        time.sleep(DELAY_RATE_LIMIT_429)
                        
                        # Tenta novamente
                        try:
                            valor = buscar_valor_veiculo(
                                codigo_marca, 
                                codigo_modelo, 
                                ano_modelo, 
                                codigo_combustivel,
                                tipo_veiculo,  # IMPORTANTE: faltava tipo_veiculo no retry!
                                codigo_ref  # Passa codigo_ref também no retry
                            )
                            if valor:
                                valor_data = {
                                    'codigo_marca': int(codigo_marca),
                                    'codigo_modelo': int(codigo_modelo),
                                    'tipo_veiculo': int(tipo_veiculo),  # IMPORTANTE: faltava!
                                    'ano_modelo': int(ano_modelo),
                                    'codigo_combustivel': int(codigo_combustivel),
                                    'valor': valor.get('Valor'),
                                    'marca': valor.get('Marca'),
                                    'modelo': valor.get('Modelo'),
                                    'combustivel': valor.get('Combustivel'),
                                    'codigo_fipe': valor.get('CodigoFipe'),
                                    'mes_referencia': mes_pt_para_yyyymm(valor.get('MesReferencia')),  # Converte para YYYYMM
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
                                stats['valores_salvos'] += 1
                                
                                # Commit a cada 10 registros
                                if stats['valores_salvos'] % 10 == 0:
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
        
        # Log do último ano processado
        if ano_atual_processamento:
            ano_display = "Zero Km" if ano_atual_processamento == "32000" else ano_atual_processamento
            print(f"\n    ✅ Ano {ano_display}: {contador_ano_atual}/{total_ano_atual} veículos processados")
        
        # COMMIT FINAL - CRUCIAL para persistir dados!
        print("\n💾 Salvando todos os dados no banco...")
        cache.conn.commit()
        print("✅ Commit final realizado!\n")
        
        # Resumo final
        print("\n" + "=" * 70)
        print("✅ ATUALIZAÇÃO DE VALORES CONCLUÍDA!")
        print("=" * 70)
        print()
        print(f"📊 ESTATÍSTICAS:")
        print(f"   • Veículos cadastrados: {stats['total_veiculos']}")
        print(f"   • Já atualizados ({mes_display}): {stats['ja_atualizados']}")
        print(f"   • Processados agora: {stats['processados']}")
        print(f"   • Valores salvos: {stats['valores_salvos']}")
        print(f"   • Erros: {stats['erros']}")
        print()
        
        # Mostra resumo por ano
        if veiculos_por_ano:
            print(f"📅 VEÍCULOS PROCESSADOS POR ANO:")
            for ano_cod in sorted(veiculos_por_ano.keys(), reverse=True):
                ano_display = "Zero Km" if ano_cod == "32000" else ano_cod
                qtd = veiculos_por_ano[ano_cod]
                print(f"   • {ano_display}: {qtd} veículos")
            print()
        print(f"📅 Referência: {mes_display}")
        print("💾 Todos os valores foram salvos no SQLite local (fipe_local.db)!")
        print("💡 Execute upload_para_supabase.py para enviar ao Supabase.")
        print()
    
    except KeyboardInterrupt:
        print("\n\n⚠️ Processo interrompido pelo usuário")
        print(f"📊 Estatísticas parciais:")
        print(f"   • Processados: {stats['processados']}")
        print(f"   • Valores salvos: {stats['valores_salvos']}")
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
        print(f"   • Processados: {stats['processados']}")
        print(f"   • Valores salvos: {stats['valores_salvos']}")
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
