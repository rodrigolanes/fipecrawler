# 🤝 Guia de Contribuição - FIPE Crawler

Obrigado por considerar contribuir com o FIPE Crawler! Este guia irá ajudá-lo a começar.

## 📋 Índice

- [Código de Conduta](#código-de-conduta)
- [Como Posso Contribuir?](#como-posso-contribuir)
- [Processo de Contribuição](#processo-de-contribuição)
- [Diretrizes de Código](#diretrizes-de-código)
- [Convenções de Commit](#convenções-de-commit)
- [Documentação](#documentação)
- [Testes](#testes)

## 📜 Código de Conduta

Este projeto adota um código de conduta que todos os contribuidores devem seguir:

- **Seja respeitoso**: Trate todos com respeito e empatia
- **Seja colaborativo**: Ajude outros contribuidores
- **Seja construtivo**: Críticas devem ser construtivas
- **Seja paciente**: Lembre-se que este é um projeto open source

## 💡 Como Posso Contribuir?

### Reportar Bugs

Encontrou um bug? Siga estes passos:

1. **Verifique** se o bug já foi reportado nas Issues
2. **Crie uma nova Issue** com:
   - Título descritivo
   - Passos para reproduzir
   - Comportamento esperado vs atual
   - Versão do Python e sistema operacional
   - Logs de erro (se houver)

**Exemplo de Issue de Bug**:
```markdown
**Descrição**: Script popular_banco_otimizado.py trava após 50 marcas

**Passos para reproduzir**:
1. Execute `python popular_banco_otimizado.py`
2. Configure 5 workers
3. Aguarde processar ~50 marcas
4. Script para de responder

**Comportamento esperado**: Script deveria continuar até o final

**Ambiente**:
- Python: 3.13.2
- OS: Windows 11
- RAM: 8GB

**Logs**:
```
[W3] [50/100] 🔄 Processando: Volkswagen (59)
(trava aqui)
```
```

### Sugerir Melhorias

Tem uma ideia para melhorar o projeto? Abra uma Issue:

1. **Título**: Descrição clara da melhoria
2. **Motivação**: Por que essa melhoria é útil?
3. **Proposta**: Como você imagina a implementação?
4. **Alternativas**: Considerou outras abordagens?

### Contribuir com Código

1. **Issues abertas**: Veja Issues marcadas com `good first issue` ou `help wanted`
2. **Novos recursos**: Discuta primeiro em uma Issue antes de começar a codificar
3. **Documentação**: Sempre bem-vinda!

## 🔄 Processo de Contribuição

### 1. Fork e Clone

```bash
# Fork no GitHub (botão "Fork")
git clone https://github.com/SEU_USUARIO/fipecrawler.git
cd fipecrawler
```

### 2. Configure o Ambiente

```bash
# Crie ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Instale dependências
pip install -r requirements.txt
```

### 3. Crie uma Branch

```bash
# Nomeie branches descritivamente
git checkout -b feature/nova-funcionalidade
git checkout -b fix/correcao-bug
git checkout -b docs/melhoria-readme
```

### 4. Faça suas Alterações

- Siga as [Diretrizes de Código](#diretrizes-de-código)
- Teste suas alterações
- Atualize documentação se necessário

### 5. Commit

```bash
# Use commits descritivos em PT-BR
git add .
git commit -m "feat: adiciona suporte a motos e caminhões"
git commit -m "fix: corrige parsing de valores com centavos"
git commit -m "docs: atualiza README com novos comandos"
```

Veja [Convenções de Commit](#convenções-de-commit) para detalhes.

### 6. Push e Pull Request

```bash
# Push para seu fork
git push origin feature/nova-funcionalidade

# Abra Pull Request no GitHub
# Preencha o template de PR com:
# - Descrição das alterações
# - Issue relacionada (se houver)
# - Screenshots (se aplicável)
# - Checklist de testes
```

## 📝 Diretrizes de Código

### Idioma

- **Código**: Português (variáveis, funções, classes, comentários)
- **Commits**: Português
- **Issues/PRs**: Português
- **Documentação**: Português

**Por quê?** Projeto brasileiro, API brasileira, equipe brasileira.

### Estilo Python

Seguimos [PEP 8](https://peps.python.org/pep-0008/):

```python
# ✅ BOM: Nomes descritivos em português
def buscar_modelos_marca(codigo_marca: int) -> list:
    """Busca modelos disponíveis de uma marca."""
    pass

# ❌ EVITAR: Nomes genéricos ou em inglês
def get_data(id: int) -> list:
    """Get some data."""
    pass
```

### Nomenclatura

**Variáveis e Funções**: `snake_case`
```python
codigo_marca = "6"
nome_modelo = "Gol 1.0"

def buscar_anos_modelo(codigo_marca, codigo_modelo):
    pass
```

**Classes**: `PascalCase`
```python
class FipeLocalCache:
    pass

class SupabaseUploader:
    pass
```

**Constantes**: `UPPER_SNAKE_CASE`
```python
TIPO_VEICULO_CARRO = 1
TIPO_VEICULO_MOTO = 2
MAX_RETRIES = 3
```

### Docstrings

Use [Google Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings):

```python
def buscar_valor_veiculo(codigo_marca: int, codigo_modelo: int, 
                         ano_modelo: int, codigo_combustivel: int) -> dict:
    """
    Busca o valor FIPE de um veículo específico.
    
    Args:
        codigo_marca: Código da marca (ex: 6 para Audi)
        codigo_modelo: Código do modelo (ex: 5496 para A1)
        ano_modelo: Ano do veículo (ex: 2014 ou 32000 para Zero Km)
        codigo_combustivel: Código do combustível (1=Gasolina, 5=Flex, etc)
    
    Returns:
        Dicionário com dados completos do veículo incluindo valor FIPE.
        Retorna None se houver erro na requisição.
    
    Raises:
        requests.RequestException: Se houver erro de rede
    
    Example:
        >>> valor = buscar_valor_veiculo(6, 5496, 2014, 1)
        >>> print(valor['Valor'])
        'R$ 69.252,00'
    """
    pass
```

### Type Hints

Use sempre que possível:

```python
from typing import List, Dict, Optional

def buscar_marcas() -> List[Dict[str, str]]:
    pass

def get_modelo(codigo: int) -> Optional[Dict]:
    pass
```

### Tratamento de Erros

Sempre capture exceções específicas:

```python
# ✅ BOM: Captura específica
try:
    response = requests.post(url, json=payload, verify=False)
    response.raise_for_status()
except requests.RequestException as e:
    print(f"❌ Erro na requisição: {e}")
    return None

# ❌ EVITAR: Captura genérica
try:
    # código
except:
    pass
```

### Logs

Use emojis para melhor visualização:

```python
print("✅ Sucesso: 100 modelos salvos")
print("❌ Erro: Falha na conexão")
print("⚠️ Aviso: Rate limit atingido")
print("📊 Estatística: 50% concluído")
print("🔄 Progresso: Processando marca 10/50")
print("💾 Cache: Dados salvos no SQLite")
print("🌐 API: Buscando da FIPE...")
```

## 📌 Convenções de Commit

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

### Formato

```
<tipo>(<escopo>): <descrição>

[corpo opcional]

[rodapé opcional]
```

### Tipos

- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Documentação
- `style`: Formatação (não afeta funcionalidade)
- `refactor`: Refatoração de código
- `perf`: Melhoria de performance
- `test`: Adição de testes
- `chore`: Manutenção geral

### Exemplos

```bash
# Feature
feat(crawler): adiciona suporte a motos e caminhões
feat(cache): implementa cache em Redis

# Fix
fix(api): corrige parsing de valores com centavos
fix(ssl): resolve erro de certificado em ambiente corporativo

# Docs
docs(readme): adiciona seção de troubleshooting
docs(api): documenta endpoint de modelos por ano

# Refactor
refactor(uploader): simplifica lógica de upload em lote
refactor(cache): remove código duplicado

# Performance
perf(paralelo): aumenta workers padrão de 3 para 5
perf(query): adiciona índice em modelos_anos

# Chore
chore(deps): atualiza requests para 2.31.0
chore(gitignore): adiciona *.db
```

### Escopo (Opcional)

Especifica o módulo afetado:

- `crawler`: fipe_crawler.py
- `cache`: fipe_cache.py ou fipe_local_cache.py
- `api`: Endpoints da API FIPE
- `db`: Schema do banco
- `scripts`: Scripts de população/atualização
- `docs`: Documentação

### Corpo e Rodapé

```bash
feat(cache): adiciona método para limpar cache antigo

Remove valores FIPE com mais de 6 meses para economizar espaço.
Útil para manutenção periódica do banco.

Closes #42
```

## 📚 Documentação

### Atualizações Obrigatórias

Ao alterar código, atualize:

1. **Docstrings**: Funções/classes modificadas
2. **README.md**: Se adicionar novos recursos
3. **docs/**: Documentação específica
4. **copilot-instructions.md**: Se alterar arquitetura

### Schema do Banco

**CRÍTICO**: Alterações no banco requerem atualizar AMBOS:

1. `scripts_banco/database_schema.sql` (executável)
2. `docs/database_schema.md` (documentação)

Qualquer divergência é considerada um bug.

## 🧪 Testes

### Testes Manuais

Antes de submeter PR, teste:

1. **Funcionalidade**: A feature funciona como esperado?
2. **Casos extremos**: Trata erros corretamente?
3. **Performance**: Não causa lentidão excessiva?
4. **Logs**: Mensagens são claras?

### Checklist de PR

Marque como concluído no PR:

- [ ] Código segue diretrizes de estilo
- [ ] Docstrings atualizadas
- [ ] README atualizado (se necessário)
- [ ] Testado em ambiente local
- [ ] Commits seguem convenção
- [ ] Sem conflitos com main

## ❓ Dúvidas?

- **Issues**: Abra uma Issue para discussão
- **Discussões**: Use GitHub Discussions
- **Email**: (se disponível)

## 🙏 Agradecimentos

Agradecemos a todos os contribuidores que dedicam seu tempo para melhorar este projeto!

---

**Última atualização**: 16 de dezembro de 2025
