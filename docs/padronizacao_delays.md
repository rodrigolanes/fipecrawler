# Padronização de Delays da API FIPE

## 📅 Data da Alteração
2 de janeiro de 2026

## 🎯 Objetivo
Centralizar e padronizar os delays entre requisições à API FIPE em todo o projeto, eliminando inconsistências e duplicação de código.

## 🔍 Problema Identificado

### Situação Anterior
- **fipe_crawler.py** (módulo base): NENHUM delay implementado
- **popular_completo.py**: Delays fixos de 2.0s (10-20x maiores que padrão recomendado)
- **atualizar_modelos.py**: Delays randomizados (0.3-3.0s) sem padrão
- **atualizar_valores.py**: Delays randomizados (0.8-1.2s) ✅ padrão escolhido
- **corrigir_relacionamentos.py**: Delays fixos de 2.0s

### Consequências
- ❌ Inconsistência entre arquivos
- ❌ Código duplicado
- ❌ Execuções muito lentas (delays superdimensionados)
- ❌ Difícil manutenção

## ✅ Solução Implementada

### 1. Arquivo de Configuração Centralizado

**Novo arquivo**: `src/config.py`

```python
import random

def get_delay_padrao():
    """Retorna delay randomizado entre 0.8 e 1.2 segundos"""
    return random.uniform(0.8, 1.2)

DELAY_RATE_LIMIT_429 = 30  # segundos
MAX_RETRIES = 3
RETRY_BASE_WAIT = 5  # segundos (5s, 10s, 20s exponencial)
```

**Vantagens do padrão escolhido (0.8-1.2s)**:
- ✅ Já testado e funcionando em produção (atualizar_valores.py)
- ✅ Randomização torna comportamento mais natural
- ✅ Conservador o suficiente para evitar rate limits
- ✅ Mais rápido que os 2.0s fixos anteriores

### 2. Delays e Retry Implementados no Módulo Base

**Arquivo**: `src/crawler/fipe_crawler.py`

**TODAS as 6 funções HTTP agora têm**:
1. ✅ **Delay padrão** (0.8-1.2s) após cada requisição bem-sucedida
2. ✅ **Retry automático** com exponential backoff em caso de erro 429
3. ✅ **Até 3 tentativas** (configurável via `MAX_RETRIES`)
4. ✅ **Tempos de espera**: 5s, 10s, 20s (configurável via `RETRY_BASE_WAIT`)

**Funções atualizadas**:
- ✅ `buscar_tabela_referencia()` 
- ✅ `buscar_marcas_carros()`
- ✅ `buscar_modelos()`
- ✅ `buscar_anos_modelo()`
- ✅ `buscar_modelos_por_ano()`
- ✅ `buscar_valor_veiculo()`

**Implementação padrão**:
```python
from config import MAX_RETRIES, RETRY_BASE_WAIT

for retry in range(MAX_RETRIES):
    try:
        response = session.post(url, data=payload, verify=False)
        response.raise_for_status()
        
        dados = response.json()
        time.sleep(get_delay_padrao())  # Delay padrão
        return dados
    
    except requests.exceptions.HTTPError as e:
        if '429' in str(e):
            if retry < MAX_RETRIES - 1:
                wait_time = RETRY_BASE_WAIT * (2 ** retry)  # 5s, 10s, 20s
                print(f"⚠️ Rate limit. Aguardando {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ Rate limit persistente após {MAX_RETRIES} tentativas")
                return None
```

### 3. Remoção de Delays Duplicados

**Arquivos modificados**:

#### `scripts/1_carga_inicial/popular_completo.py`
- ❌ Removido: `time.sleep(2.0)` após buscar modelos (linha 102)
- ❌ Removido: `time.sleep(2.0)` após buscar modelos por ano (linha 150)
- ❌ Removido: `time.sleep(2.0)` entre modelos (linha 225)
- ❌ Removido: `time.sleep(2.0)` entre marcas (linha 344)
- ✅ Mantido: Delays de retry para rate limit 429

#### `scripts/2_atualizacao_mensal/1_atualizar_modelos.py`
- ❌ Removido: `time.sleep(random.uniform(0.3, 0.5))` entre combustíveis
- ❌ Removido: `time.sleep(random.uniform(0.5, 1.0))` entre modelos
- ❌ Removido: `time.sleep(random.uniform(2.0, 3.0))` entre marcas
- ✅ Agora usa delays do módulo base

#### `scripts/2_atualizacao_mensal/2_atualizar_valores.py`
- ❌ Removido: `time.sleep(random.uniform(0.8, 1.2))` entre valores
- ✅ Agora usa `DELAY_RATE_LIMIT_429` da config para rate limit
- ✅ Agora usa delay do módulo base

#### `scripts/1_carga_inicial/corrigir_relacionamentos.py`
- ❌ Removido: `time.sleep(2.0)` entre modelos
- ✅ Atualizado: Funções de retry usam `MAX_RETRIES` e `RETRY_BASE_WAIT` da config

### 4. Atualização de Funções de Retry

**Padrão anterior**:
```python
max_retries=3  # Hardcoded
wait_time = 5 * (2 ** retry)  # Hardcoded
```

**Padrão novo**:
```python
from src.config import MAX_RETRIES, RETRY_BASE_WAIT

max_retries=MAX_RETRIES  # 3 (configurável)
wait_time = RETRY_BASE_WAIT * (2 ** retry)  # 5s, 10s, 20s
```

**Arquivos atualizados**:
- ✅ `popular_completo.py`: 3 funções de retry
- ✅ `corrigir_relacionamentos.py`: 4 funções de retry

## 📊 Impacto Esperado

### Performance
- ⚡ **Redução de 50-60% no tempo total de execução** (delays de 2.0s → 0.8-1.2s)
- 🚀 Popular banco completo: ~2-4h → ~1-2h (estimativa)
- 🚀 Atualizar modelos: ~10-15 min → ~5-7 min (estimativa)
- 🚀 Atualizar valores: Redução proporcional no tempo total

### Manutenibilidade
- ✅ **Single source of truth**: Configuração centralizada
- ✅ **DRY**: Sem duplicação de delays
- ✅ **Flexibilidade**: Ajustar delay em um único lugar

### Confiabilidade
- ✅ **Consistência**: Mesmo padrão em todo o projeto
- ✅ **Testado**: Padrão 0.8-1.2s já funcionava em produção
- ⚠️ **Monitoramento necessário**: Observar taxa de erros 429 nos próximos dias

## 🔄 Como Usar

### Para Desenvolvedores

**Importar configuração**:
```python
from src.config import get_delay_padrao, DELAY_RATE_LIMIT_429, MAX_RETRIES, RETRY_BASE_WAIT
```

**Usar delay padrão**:
```python
import time
time.sleep(get_delay_padrao())  # 0.8-1.2s randomizado
```

**Usar delay para rate limit**:
```python
time.sleep(DELAY_RATE_LIMIT_429)  # 30s
```

**Implementar retry com exponential backoff**:
```python
for retry in range(MAX_RETRIES):
    try:
        # ... sua requisição ...
    except Exception as e:
        if "429" in str(e):
            wait_time = RETRY_BASE_WAIT * (2 ** retry)  # 5s, 10s, 20s
            time.sleep(wait_time)
```

### Ajustando Delays (se necessário)

**Se houver muitos erros 429**, edite `src/config.py`:
```python
def get_delay_padrao():
    return random.uniform(1.0, 1.5)  # Aumentar para 1.0-1.5s
```

**Se houver poucos erros 429**, pode reduzir:
```python
def get_delay_padrao():
    return random.uniform(0.5, 0.8)  # Reduzir para 0.5-0.8s
```

## 📝 Checklist de Validação

Após deploy, monitorar por 7 dias:

- [ ] Executar `atualizar_modelos.py` e verificar tempo vs antes
- [ ] Executar `atualizar_valores.py` em amostra e verificar taxa de erros 429
- [ ] Monitorar logs de `popular_completo.py` se executado
- [ ] Comparar tempo total de execução com execuções anteriores
- [ ] Verificar se há aumento significativo de erros 429 (>5% das requisições)

**Critérios de sucesso**:
- ✅ Tempo de execução reduzido em pelo menos 40%
- ✅ Taxa de erros 429 < 5% das requisições
- ✅ Sem erros de execução relacionados a delays

**Se taxa de erros 429 > 5%**: Aumentar delays em `src/config.py`

## 🎓 Lições Aprendidas

1. **Delay no módulo base**: Sempre implementar delays nas funções que fazem requisições HTTP, não nos scripts que as chamam
2. **Configuração centralizada**: Evita duplicação e facilita ajustes
3. **Randomização**: Torna comportamento mais natural e reduz detecção de bot
4. **Padrão testado**: Usar valores já validados em produção
5. **Monitoramento**: Sempre monitorar após mudanças de performance

## 📚 Referências

- Issue relacionada: Análise de delays inconsistentes
- Commit: Centralização de delays (2 jan 2026)
- Documentação anterior: `.github/copilot-instructions.md` (delays recomendados originais)
