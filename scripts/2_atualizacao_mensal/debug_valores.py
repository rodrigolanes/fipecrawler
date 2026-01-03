"""
Script de debug para verificar valores salvos no banco.
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.cache.fipe_local_cache import FipeLocalCache
from src.crawler.fipe_crawler import buscar_tabela_referencia

cache = FipeLocalCache()
conn = cache.conn
cursor = conn.cursor()

# Busca mês de referência atual
tabelas = buscar_tabela_referencia()
mes_referencia = tabelas[0]['Mes'] if tabelas else "desconhecido"

print("="*70)
print("DEBUG - Valores FIPE no Banco")
print("="*70)
print(f"\n📅 Mês de referência atual: {mes_referencia}\n")

# 1. Total de modelos_anos
cursor.execute('SELECT COUNT(*) FROM modelos_anos')
total_modelos_anos = cursor.fetchone()[0]
print(f"📊 Total de registros em modelos_anos: {total_modelos_anos}")

# 2. Total de valores_fipe
cursor.execute('SELECT COUNT(*) FROM valores_fipe')
total_valores = cursor.fetchone()[0]
print(f"📊 Total de registros em valores_fipe: {total_valores}")

# 3. Total de valores_fipe para o mês atual
cursor.execute('SELECT COUNT(*) FROM valores_fipe WHERE mes_referencia = ?', (mes_referencia,))
total_valores_mes = cursor.fetchone()[0]
print(f"📊 Valores para {mes_referencia}: {total_valores_mes}")

# 4. Meses de referência distintos
cursor.execute('SELECT mes_referencia, COUNT(*) FROM valores_fipe GROUP BY mes_referencia')
meses = cursor.fetchall()
print(f"\n📅 Meses de referência no banco:")
for mes, qtd in meses:
    print(f"   • {mes}: {qtd} valores")

# 5. Amostra de 5 valores recentes
print(f"\n🔍 Últimos 5 valores salvos:")
cursor.execute('''
    SELECT codigo_marca, codigo_modelo, ano_modelo, codigo_combustivel, 
           mes_referencia, valor, data_consulta
    FROM valores_fipe 
    ORDER BY data_consulta DESC 
    LIMIT 5
''')
valores_recentes = cursor.fetchall()
for v in valores_recentes:
    print(f"   • Marca:{v[0]} Modelo:{v[1]} Ano:{v[2]}-{v[3]} | {v[4]} | {v[5]} | {v[6]}")

# 6. Teste da query que o script usa
print(f"\n🔍 Testando query do script (veículos SEM valor para {mes_referencia}):")
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
    LIMIT 10
''', (mes_referencia,))
veiculos_sem_valor = cursor.fetchall()
print(f"   Encontrados: {len(veiculos_sem_valor)} veículos (mostrando primeiros 10)")
for v in veiculos_sem_valor[:5]:
    print(f"   • Marca:{v[0]} Modelo:{v[1]} Ano:{v[3]}")

# 7. Teste de um veículo específico que deveria ter sido salvo
print(f"\n🔍 Verificando primeiro veículo da lista:")
if veiculos_sem_valor:
    v = veiculos_sem_valor[0]
    codigo_marca = v[0]
    codigo_modelo = v[1]
    tipo_veiculo = v[2]
    codigo_ano_combustivel = v[3]
    
    if '-' in codigo_ano_combustivel:
        ano_modelo, codigo_combustivel = codigo_ano_combustivel.split('-')
        
        print(f"   Marca: {codigo_marca}")
        print(f"   Modelo: {codigo_modelo}")
        print(f"   Tipo: {tipo_veiculo}")
        print(f"   Ano: {ano_modelo}")
        print(f"   Combustível: {codigo_combustivel}")
        
        # Verifica se existe valor para este veículo
        cursor.execute('''
            SELECT mes_referencia, valor, data_consulta
            FROM valores_fipe
            WHERE codigo_marca = ? 
            AND codigo_modelo = ?
            AND tipo_veiculo = ?
            AND ano_modelo = ?
            AND codigo_combustivel = ?
            ORDER BY data_consulta DESC
        ''', (codigo_marca, codigo_modelo, tipo_veiculo, int(ano_modelo), int(codigo_combustivel)))
        
        valores_veiculo = cursor.fetchall()
        
        if valores_veiculo:
            print(f"\n   ✅ Este veículo TEM valores no banco:")
            for val in valores_veiculo:
                print(f"      • {val[0]}: {val[1]} ({val[2]})")
        else:
            print(f"\n   ❌ Este veículo NÃO tem valores no banco")

print("\n" + "="*70)
