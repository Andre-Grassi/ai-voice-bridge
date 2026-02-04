# Contribuindo

Obrigado pelo interesse! Este é principalmente um projeto pessoal, mas contribuições são bem-vindas.

## Começando

```bash
# Instale com dependências de desenvolvimento
pip install -e ".[dev]"

# Execute os testes
pytest

# Formate o código
black src/
ruff check src/ --fix
```

## Estilo de Código

- Siga o [Guia de Estilo Python do Google](https://google.github.io/styleguide/pyguide.html)
- Comentários em Português (pt-BR)
- Código e documentação em Inglês (en-US)

## Pull Requests

1. Faça um fork do repositório
2. Crie uma branch para sua feature
3. Faça suas alterações
4. Execute `black` e `ruff`
5. Envie o PR

É isso! 🎉
