# Catálogo de cenários

Comece pelos casos determinísticos. Os READMEs vinculados contêm comandos,
topologia e encerramento. Execute-os da raiz do repositório.

| Cenário | O que observar | Requisitos adicionais ao Docker | Resultado esperado |
|---|---|---|---|
| [Echo básico](quickstart.md) | Descoberta e tarefa simples | Nenhum no caminho Docker | `COMPLETED`, agente `mock-agent-01` |
| [Workflow sequencial](../scenarios/workflow-sequential/README.md) | Dependência `first → second` | Python e uv | `CENÁRIO APROVADO`, saída `echo: second` |
| [Falha e reassignment](../scenarios/failure-reassignment/README.md) | Timeout de `a-slow` e nova atribuição | Python e uv | `CENÁRIO APROVADO agent_id=b-healthy` |
| [Mensageria](../scenarios/messaging-basic/README.md) | Envelope e correlação preservados | Python e uv | `CENÁRIO APROVADO`, mesmo message ID |
| [Rota heterogênea](../scenarios/heterogeneous-route/README.md) | Planner LLM, rota BDI e explicação LLM | Python, uv, chave e acesso ao modelo configurado | Rota `A → B → D`, distância 25 e relatório JSON |
| [Missão logística](../scenarios/logistics-mission/README.md) | Interpretação LLM e plano BDI com restrições | Python, uv, chave e acesso ao modelo configurado | Plano aceito pelo avaliador do domínio |

## Como escolher

- Para estudar o runtime: echo, workflow e falha.
- Para estudar comunicação iniciada por agentes: mensageria.
- Para observar o raciocínio BDI sem serviços: [demo do agendador](../agents/meeting-scheduler/demo.py).
- Para observar interoperabilidade LLM/BDI: rota heterogênea e missão logística.
- Para comparar resultados sistematicamente: [guia de avaliação](evaluation.md).

A demo do agendador roda com o ambiente do SDK:

```sh
uv run --directory sdk/python python ../../agents/meeting-scheduler/demo.py
```

## Endereços e isolamento

| Topologia | Endereço de entrada padrão no host |
|---|---|
| Básica e rota heterogênea | Orchestrator `localhost:50052` |
| Falha | Orchestrator `localhost:52052` |
| Workflow sequencial | Orchestrator `localhost:53052` |
| Benchmarks e missão logística | Orchestrator `localhost:54052` |
| Mensageria isolada | Messaging `localhost:55053` |

A básica e a rota heterogênea compartilham portas padrão: encerre uma antes
de iniciar a outra ou configure as portas do cenário. A missão logística
reutiliza o Compose de benchmarks; não possui topologia independente.

Não envie tarefas de decomposição pelo cliente genérico esperando que ele
mostre um workflow. Use o script da rota heterogênea ou `Scenario` do SDK.

[Índice](README.md)
