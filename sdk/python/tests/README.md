# Testes do SDK

Cobrem modelos Python/protobuf, API de autoria, saída LLM com cliente falso,
mensageria e chamadas de cenários. Não exigem serviços ativos ou chave de LLM.

Da raiz do repositório:

```sh
uv run --directory sdk/python --with pytest python -m pytest tests -q
```

Para outras verificações e integrações, veja o
[guia de desenvolvimento](../../../docs/development.md#preparar-e-verificar).
