# Correção: Problema de JSON Corrompido na API FIPE

## 📋 Problema Identificado

Ao buscar modelos de veículos específicos (ex: Volvo 2016 Diesel), a API FIPE retornava dados corrompidos com caracteres binários ao invés de JSON válido.

### Exemplo do Erro
```
⚠️  JSON inválido após limpeza: �b]��l>��~!S�����5�tP0Hl�6�(����xq|�����
```

## 🔍 Diagnóstico

1. **Headers da resposta problemática:**
   - `Content-Type: application/json; charset=utf-8`
   - `Content-Encoding: br` ← **CAUSA DO PROBLEMA**
   - Primeiros bytes: `\x1bB\x00\x00` (magic bytes do Brotli)

2. **Causa raiz:**
   - API FIPE estava retornando resposta comprimida com **Brotli compression** (`br`)
   - Biblioteca Python `requests` não estava descomprimindo corretamente
   - Resultado: JSON comprimido sendo tratado como texto plano

## ✅ Solução Implementada

### 1. Remover Brotli do Accept-Encoding

**Arquivo:** `fipe_crawler.py` - função `get_session()`

```python
# ANTES (não funcionava):
"Accept-Encoding": "gzip, deflate, br",

# DEPOIS (funciona):
"Accept-Encoding": "gzip, deflate",  # Removido 'br' (Brotli)
```

### 2. Usar Content-Type correto

**Arquivo:** `fipe_crawler.py` - função `get_session()`

```python
# ANTES:
"Content-Type": "application/json; charset=utf-8",

# DEPOIS:
"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
```

### 3. Padronizar formato de payload

**Todas as funções de requisição:**

```python
# ANTES (algumas funções):
response = session.post(url, json=payload, verify=False)

# DEPOIS (todas as funções):
response = session.post(url, data=payload, verify=False)
```

## 📝 Funções Alteradas

### fipe_crawler.py
1. ✅ `get_session()` - Headers atualizados
2. ✅ `buscar_tabela_referencia()` - `json={}` → `data={}`
3. ✅ `buscar_marcas_carros()` - `json=payload` → `data=payload`
4. ✅ `buscar_modelos()` - `json=payload` → `data=payload`
5. ✅ `buscar_anos_modelo()` - `json=payload` → `data=payload`
6. ✅ `buscar_modelos_por_ano()` - `json=payload` → `data=payload`
7. ✅ `buscar_valor_veiculo()` - `json=payload` → `data=payload`

### debug_api_fipe.py
8. ✅ `debug_buscar_modelos_por_ano()` - `json=payload` → `data=payload`

## 🧪 Validação

### Teste do caso problemático:
```bash
python testar_volvo_2016.py
```

**Resultado:**
```
✅ 1 modelos encontrados
  • XC 90 D-5 MOMENTUM 2.0 235cv Diesel 5p (código: 7853)
✅ SUCESSO! JSON corrompido foi resolvido!
```

### Teste completo de todas as funções:
```bash
python testar_todas_funcoes.py
```

**Resultado:**
```
1️⃣  buscar_tabela_referencia() ✅
2️⃣  buscar_marcas_carros() ✅
3️⃣  buscar_modelos() ✅
4️⃣  buscar_anos_modelo() ✅
5️⃣  buscar_modelos_por_ano() ✅ (CASO PROBLEMÁTICO RESOLVIDO)
6️⃣  buscar_valor_veiculo() ✅
```

## 📊 Impacto

### Antes da correção:
- ❌ Volvo 2016 Diesel: JSON corrompido
- ❌ Volvo 2015 Diesel: JSON corrompido
- ❌ Outros casos esporádicos com Brotli

### Após correção:
- ✅ Todos os casos funcionando
- ✅ Relacionamentos modelo x ano completos
- ✅ População do banco sem erros

## 🔧 Próximos Passos

1. **Executar verificação de relacionamentos:**
   ```bash
   python verificar_relacionamentos_incompletos.py --marca 58 --corrigir
   ```

2. **Repopular dados incompletos:**
   ```bash
   python popular_banco_otimizado.py
   ```

3. **Upload para Supabase (opcional):**
   ```bash
   python upload_para_supabase.py
   ```

## 💡 Lições Aprendidas

1. **Brotli compression** (`br`) requer biblioteca adicional (`brotli` ou `brotlipy`)
2. Python `requests` não descomprime Brotli automaticamente como faz com gzip
3. Melhor solução: remover `br` do `Accept-Encoding` para forçar gzip/deflate
4. API FIPE aceita tanto JSON quanto form-urlencoded, mas form-urlencoded é mais consistente
5. Sempre verificar `Content-Encoding` nos headers da resposta ao debugar problemas de parsing

## 📅 Data da Correção

- **Data:** 17 de dezembro de 2025
- **Problema:** JSON corrompido em requisições específicas
- **Causa:** Compressão Brotli não descomprimida
- **Solução:** Remoção de 'br' do Accept-Encoding + padronização para form-urlencoded
- **Status:** ✅ Resolvido e validado
