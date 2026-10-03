# 13 — Runbook de execução e testes manuais

Este runbook descreve o estado executável atual do repositório e o
procedimento para subir, verificar e encerrar o TG Runtime.

Todos os comandos devem ser executados a partir da raiz do repositório.

## 1. Estado atual

O fluxo integrado disponível hoje é:

```text
cliente submit-task
        |
        v
orchestrator :50052 --> registry :50051
        |
        v
mock-agent :60051
llm-agent :60056 (profile llm)
        |
        v
/data/events.jsonl
```

O `infra/docker-compose.yml` sobe três serviços:

| Serviço | Papel | Porta no host |
|---|---|---:|
| `registry` | registra e descobre agentes em memória | 50051 |
| `orchestrator` | recebe tasks, escolhe o primeiro agente compatível e encaminha a execução | 50052 |
| `mock-agent` | oferece a capability `echo` | 60051 |
| `llm-agent` | oferece `task-decomposition` e `explanation` usando OpenAI | 60056 |

O `llm-agent` pertence ao profile opcional `llm`; o `make up` normal não
o inicia. Também existem agentes de exemplo (`echo-agent`,
`failing-agent`, `bdi-agent` e `meeting-scheduler`) fora do Compose.

Limitações relevantes:

- há testes Go do Registry e testes Python do agente LLM;
- `make test` executa apenas os testes Go; os testes LLM usam `uv`;
- o Registry é somente em memória: reiniciar o contêiner perde os
  registros;
- a seleção é `FIRST_AVAILABLE`, sem retry ou reassignment;
- o Compose usa `depends_on`, mas não possui `healthcheck`; logo, um
  serviço pode ter iniciado sem ainda estar pronto;
- o log de eventos fica em um volume Docker, não diretamente em
  `experiments/results/`;
- o cliente genérico só envia goal, type e uma capability. Ele não monta
  payloads estruturados exigidos pelos exemplos BDI.

## 2. Pré-requisitos

Ferramentas:

- Docker com Docker Compose v2;
- Python 3.11 ou superior;
- `uv`;
- Go 1.22 ou superior para build e checks locais;
- `protoc` e plugins Go somente para regenerar os stubs.

Verifique o ambiente:

```sh
make check-env
docker info
```

`make check-env` usa Homebrew para localizar os includes do protobuf,
portanto o target é orientado ao macOS. Em Linux, verifique as
ferramentas individualmente ou ajuste `PROTO_INCLUDES`.

Os stubs gerados já estão versionados em `runtime/gen/go/contract/v1` e
`sdk/python/src/contract/v1`. Não é necessário rodar `make proto` para
o teste normal.

## 3. Subir o sistema

Construa as imagens e inicie os serviços:

```sh
make up
```

Confira o estado:

```sh
docker compose -f infra/docker-compose.yml ps
```

Os três serviços devem aparecer como `Up`. Como não há healthchecks,
confirme a prontidão pelos logs:

```sh
docker compose -f infra/docker-compose.yml logs registry orchestrator mock-agent
```

Procure por mensagens equivalentes a:

```text
registry service started
orchestrator service started
registered with registry
agent service started
```

Se o mock-agent tentar se registrar antes de o Registry aceitar
conexões, reinicie somente o agente:

```sh
docker compose -f infra/docker-compose.yml restart mock-agent
```

## 4. Teste manual principal: caminho feliz

Execute o cliente usando o ambiente declarado em seu próprio
`pyproject.toml`:

```sh
uv run --directory clients/submit-task python main.py \
  --goal "Teste ponta a ponta" \
  --type TEST \
  --capability echo
```

Resultado esperado:

- o cliente conecta em `localhost:50052`;
- o resultado mostra `status: COMPLETED`;
- `agent_id` é `mock-agent-01`;
- os logs mostram criação, seleção e conclusão da task.

Inspecione os logs:

```sh
docker compose -f infra/docker-compose.yml logs --since=2m orchestrator mock-agent
```

Critérios de aprovação:

- orchestrator registra `task received`;
- orchestrator registra `agent selected`;
- mock-agent registra `task received` e `task completed`;
- orchestrator registra `task finished`.

## 5. Teste negativo: capability inexistente

```sh
uv run --directory clients/submit-task python main.py \
  --goal "Solicitar capability ausente" \
  --capability capability-que-nao-existe
```

Resultado esperado:

- o cliente termina com código diferente de zero;
- a mensagem contém `no compatible agent found`;
- o erro não é marcado como retryable;
- o orchestrator registra `no agents found`.

Esse cenário cria `TASK_CREATED`, mas não cria `TASK_ASSIGNED` nem um
evento final. Nas métricas, a task aparece como `IN_PROGRESS`; isso é
uma limitação do logger atual, não uma execução ainda ativa.

## 6. Teste negativo: falha intencional do agente

O mock-agent suporta `FAIL_RATE`, mas o Compose fixa o valor em `0.0`.
Para testar falha sem editar o Compose, pare a pilha, altere
temporariamente esse valor para `1.0` em `infra/docker-compose.yml` e
suba novamente:

```yaml
FAIL_RATE: "1.0"
```

Depois execute:

```sh
make up
uv run --directory clients/submit-task python main.py \
  --goal "Falha controlada" \
  --capability echo
```

Resultado esperado:

- o mock-agent retorna `TASK_STATUS_FAILED`;
- o cliente exibe `status: FAILED` e o erro `intentional failure`;
- o orchestrator grava `TASK_FAILED`;
- o cliente encerra normalmente, pois a falha está no `TaskResult`, e
  não no campo de erro do runtime.

Ao terminar, restaure `FAIL_RATE: "0.0"` e rode `make up` novamente.

## 7. Inspecionar eventos e calcular métricas

Veja os eventos sem copiá-los:

```sh
docker compose -f infra/docker-compose.yml exec orchestrator \
  cat /data/events.jsonl
```

Copie o JSONL para o host:

```sh
docker compose -f infra/docker-compose.yml exec -T orchestrator \
  cat /data/events.jsonl > experiments/results/events.jsonl
```

Calcule as métricas:

```sh
python3 experiments/scripts/compute_metrics.py \
  --events experiments/results/events.jsonl \
  --output experiments/results/summary.csv
```

O comando imprime quantidade de tasks, taxa de sucesso e latências, e
gera `experiments/results/summary.csv`.

Observação: o volume preserva eventos entre `make down` e `make up`.
Assim, as métricas podem conter execuções anteriores.

## 8. Checks locais de código

Build dos serviços Go:

```sh
make build
```

Check dos pacotes Go:

```sh
make test
```

Estado esperado atual: ambos terminam com sucesso. Os pacotes sem testes
informam `[no test files]`, enquanto os testes do Registry são
executados normalmente.

Para validar que o Compose é sintaticamente válido:

```sh
docker compose -f infra/docker-compose.yml config --quiet
```

Regere os stubs somente após alterar
`proto/contract/v1/contract.proto`:

```sh
make proto
```

Depois de regenerar, rode `make build` e repita o teste ponta a ponta.

## 9. Demos fora do Compose

O exemplo de agendamento pode ser executado sem Registry ou
Orchestrator. Use o ambiente do SDK, que contém as dependências de
desenvolvimento necessárias:

```sh
uv run --directory sdk/python \
  python ../../agents/meeting-scheduler/demo.py
```

Resultado esperado: quatro cenários são impressos, com crenças, planos
avaliados, intenção escolhida e resultado. Essa demo exercita a
deliberação BDI em processo, mas não testa descoberta ou gRPC.

Os agentes independentes podem ser conectados manualmente ao runtime,
porém exigem configuração cuidadosa de `AGENT_HOST`: o endereço
registrado precisa ser alcançável pelo contêiner do orchestrator. Para o
teste integrado padrão, prefira o mock-agent do Compose.

## 10. Testar o agente LLM com OpenAI

### Configurar o ambiente

O teste real exige:

```text
OPENAI_API_KEY
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.6-luna
```

Use um dos arquivos locais:

```text
.env
infra/env/.env
```

Os comandos abaixo usam `.env` na raiz. Para usar o segundo arquivo,
substitua `--env-file .env` por
`--env-file infra/env/.env`.

Nunca mostre, versione ou copie a chave para um Dockerfile.

### Sequência completa

```sh
uv run --project agents/llm-agent \
  python -m unittest discover \
  -s agents/llm-agent \
  -p 'test_*.py' \
  -v
```

Esse comando executa oito testes unitários:

- validação de um plano correto;
- rejeição de task ID fornecido pelo modelo;
- rejeição de capability vazia;
- inferência determinística de rota;
- fallback determinístico;
- conversão da resposta estruturada OpenAI;
- rejeição de `payload_json` que não representa objeto;
- explicação estruturada.

Execute os testes Go:

```sh
(cd runtime && go test ./...)
```

Valide a configuração:

```sh
docker compose --env-file .env \
  -f infra/docker-compose.yml \
  --profile llm \
  config --quiet
```

Construa e inicie o runtime com o agente LLM:

```sh
docker compose --env-file .env \
  -f infra/docker-compose.yml \
  --profile llm \
  up --build -d
```

Confira os serviços:

```sh
docker compose --env-file .env \
  -f infra/docker-compose.yml \
  --profile llm \
  ps
```

Devem aparecer como `Up`:

```text
registry
orchestrator
mock-agent
llm-agent
```

Confirme registro e heartbeat:

```sh
docker compose --env-file .env \
  -f infra/docker-compose.yml \
  logs --tail=50 registry llm-agent
```

Teste decomposição:

```sh
uv run --directory clients/submit-task python main.py \
  --goal "Planeje uma rota segura de A para D e explique as etapas necessarias" \
  --type NATURAL_LANGUAGE \
  --capability task-decomposition
```

Resultado esperado:

- `status: COMPLETED`;
- `agent_id: llm-agent-01`;
- `output.subtasks` contém uma lista não vazia;
- cada subtask possui `goal` e `required_capabilities`;
- `metadata.provider` é `openai`;
- `metadata.model` é `gpt-5.6-luna`.

Teste explicação:

```sh
uv run --directory clients/submit-task python main.py \
  --goal "Explique de forma simples por que uma rota segura deve priorizar vias iluminadas e movimentadas" \
  --type EXPLANATION \
  --capability explanation
```

Resultado esperado:

- `status: COMPLETED`;
- `output.explanation` contém texto em português;
- `output.reasoning_summary` contém somente um resumo público;
- `output.confidence` fica entre 0 e 1;
- os metadados confirmam provider e modelo.

Inspecione o ciclo completo:

```sh
docker compose --env-file .env \
  -f infra/docker-compose.yml \
  logs --since=5m llm-agent orchestrator
```

### Interpretação da validação realizada

O teste de decomposição real retornou três subtasks estruturadas:

1. obter os dados necessários para a rota;
2. comparar trajetos priorizando segurança;
3. explicar a rota e suas precauções.

Isso comprova que:

- o cliente enviou linguagem natural pelo contrato gRPC;
- o orchestrator descobriu o agente pela capability;
- o agente chamou a Responses API;
- o modelo respeitou o schema Pydantic;
- `payload_json` foi convertido e validado localmente;
- o resultado voltou como `TaskResult` protobuf;
- nenhuma seleção operacional foi delegada ao modelo.

O teste de explicação retornou texto em português, confidence `0.99` e
um resumo público. Isso comprova o segundo papel do mesmo agente sem
expor cadeia de pensamento oculta.

O valor incorreto `gpt-5.6-lua` retornou HTTP 400
`model_not_found`. Depois da correção para `gpt-5.6-luna`, ambos os
testes terminaram como `COMPLETED`. Portanto, chave, rede, SDK, modelo,
structured output, validação e integração gRPC funcionaram em conjunto.

Importante: nesta fase o orchestrator devolve o plano ao cliente, mas
ainda não executa automaticamente as subtasks. Esse encadeamento será
implementado posteriormente.

### Cenário heterogêneo LLM + BDI

Suba os dois agentes:

```sh
docker compose --env-file .env \
  -f infra/docker-compose.yml \
  --profile heterogeneous \
  up --build -d
```

Execute o cenário:

```sh
uv run --directory clients/submit-task \
  python ../../examples/demo_scenario/heterogeneous_demo.py
```

Fluxo esperado:

```text
LLM -> task-decomposition
BDI -> route-planning
LLM -> explanation
```

O teste aprova somente se o workflow terminar como `COMPLETED`, os steps de
rota e explicação completarem, o
BDI selecionar `via_intermediate`, retornar `[A, B, D]` e distância
`25`, e a saída terminar com `CENÁRIO APROVADO`.

O script envia uma única pergunta. Planejamento, bindings, descoberta,
seleção e encadeamento são executados pelo orchestrator; o relatório registra
`workflow_id`, `run_id`, duração total e duração por step.

## 11. Encerrar e limpar

Pare e remova os contêineres e a rede, preservando os eventos:

```sh
make down
```

Para também apagar o volume de eventos:

```sh
docker compose -f infra/docker-compose.yml down -v
```

O segundo comando remove permanentemente o histórico armazenado no
volume `infra_events_data`. Copie `events.jsonl` antes, se precisar
preservá-lo.

## 12. Diagnóstico rápido

### Porta já está em uso

```sh
lsof -nP -iTCP:50051 -iTCP:50052 -iTCP:60051 -sTCP:LISTEN
```

Encerre o processo conflitante ou altere o mapeamento de portas.

### Cliente recebe `UNAVAILABLE`

Verifique:

```sh
docker compose -f infra/docker-compose.yml ps
docker compose -f infra/docker-compose.yml logs --tail=100 registry orchestrator mock-agent
```

Reinicie o mock-agent se o registro tiver falhado durante a subida.

### Nenhum agente compatível

Confirme que a task pede `--capability echo` e que o log do mock-agent
contém `registered with registry`.

### Eventos não aparecem em `experiments/results`

Esse é o comportamento esperado no Compose. O arquivo está em
`/data/events.jsonl`, dentro do volume montado no orchestrator. Use o
procedimento da seção 7 para exportá-lo.

### LLM retorna `model_not_found`

Confirme:

```text
LLM_MODEL=gpt-5.6-luna
```

Depois recrie o agente:

```sh
docker compose --env-file .env \
  -f infra/docker-compose.yml \
  --profile llm \
  up -d --force-recreate llm-agent
```

### LLM retorna erro de autenticação

Confirme que `OPENAI_API_KEY` existe no arquivo escolhido e que o mesmo
arquivo foi passado em `--env-file`. Não imprima a chave para depurar.
