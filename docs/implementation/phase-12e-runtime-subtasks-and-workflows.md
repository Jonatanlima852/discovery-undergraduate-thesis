# Fase 12E — Subtasks e workflows no runtime

## Motivação

O runtime atual executa uma única `Task` por chamada:

```text
cliente -> orchestrator -> descoberta -> agente -> TaskResult
```

O cenário heterogêneo já demonstra uma cooperação mais rica:

```text
pergunta
  -> LLM decompõe
  -> BDI executa uma subtask
  -> LLM explica o resultado
```

Porém, hoje esse encadeamento é controlado pelo script do cenário. O cliente
precisa interpretar a saída do LLM, construir novas tasks, transportar os
resultados entre etapas e decidir quando o fluxo terminou.

Esse modelo é útil como prova de conceito, mas não representa o objetivo final
do runtime. No estado pretendido, o cliente envia uma pergunta e a
infraestrutura coordena os agentes conectados automaticamente:

```text
cliente
  |
  | uma pergunta
  v
orchestrator
  | descobre planner LLM
  | valida o plano
  | cria subtasks
  | descobre agentes BDI/LLM compatíveis
  | controla dependências, falhas e resultados
  v
resultado final
```

A principal motivação desta fase é mover o controle operacional do workflow
para o orchestrator, mantendo o raciocínio semântico nos agentes.

## Princípio arquitetural

O LLM pode propor um plano, mas não controla diretamente a infraestrutura.

```text
LLM planner
  produz uma descrição estruturada de trabalho

orchestrator
  valida, materializa e executa o workflow deterministicamente

agentes especializados
  executam as subtasks atribuídas
```

Essa separação preserva:

- previsibilidade operacional;
- limites de retry e timeout;
- descoberta por capability;
- rastreabilidade;
- possibilidade de benchmark;
- independência entre arquitetura BDI, LLM e runtime;
- rejeição de planos inválidos ou inseguros.

O orchestrator não deve interpretar linguagem natural nem escolher uma rota de
negócio. Ele deve interpretar somente uma estrutura de workflow validada.

## Conceitos necessários

### Root task

É a solicitação original recebida do cliente.

Exemplo:

```text
Planeje uma rota de A para D e explique a decisão.
```

A root task identifica a execução externa e dá origem a zero ou mais subtasks.

### Subtask

É uma `Task` normal criada como parte de outra task.

Ela continua usando:

- `task_id`;
- `goal`;
- `payload`;
- `required_capabilities`;
- `retry_policy`;
- `selection_policy`;
- extensões BDI ou LLM;
- `trace`.

O campo existente `parent_task_id` liga a subtask à sua origem imediata.

### Workflow

É a representação operacional das subtasks e suas dependências.

Exemplo:

```text
decompose
    |
    v
plan_route
    |
    v
explain
```

O workflow pode ser representado como um DAG — grafo direcionado sem ciclos.
Um DAG permite tanto sequências quanto etapas paralelas:

```text
                   -> check_weather  -
decompose -------->                  +-> synthesize
                   -> plan_route    -
```

O primeiro incremento deve suportar sequência e paralelismo simples, sem
loops, condições arbitrárias ou compensações distribuídas.

### Workflow run

É uma execução concreta de um workflow.

Deve possuir:

```text
workflow_id       identidade da definição/materialização
run_id            identidade da execução
root_task_id      solicitação original
trace_id          rastreamento distribuído
status            estado agregado
created_at
completed_at
```

### Step

É um nó do workflow. Um step materializa uma subtask quando todas as suas
dependências são satisfeitas.

## Contrato de decomposição

A saída atual do agente LLM já contém `subtasks`, mas precisa evoluir de uma
lista informal para um plano operacional explícito.

Formato conceitual:

```json
{
  "steps": [
    {
      "step_id": "plan_route",
      "goal": "Planejar rota de A para D",
      "required_capabilities": ["route-planning"],
      "payload": {
        "origin": "A",
        "destination": "D"
      },
      "depends_on": [],
      "input_bindings": {}
    },
    {
      "step_id": "explain",
      "goal": "Explicar a rota escolhida",
      "required_capabilities": ["explanation"],
      "payload": {},
      "depends_on": ["plan_route"],
      "input_bindings": {
        "route_result": {
          "step_id": "plan_route",
          "path": "output"
        },
        "route_metadata": {
          "step_id": "plan_route",
          "path": "metadata"
        }
      }
    }
  ],
  "final_output": {
    "step_id": "explain",
    "path": "output"
  }
}
```

`input_bindings` não executa código nem expressões livres. Ele apenas copia
campos permitidos de resultados anteriores para o payload da próxima task.

## Mudanças recomendadas no protobuf

O contrato atual já possui `parent_task_id`, `trace_id` e `TaskResult`, mas não
representa dependências ou uma execução agregada.

Adicionar mensagens equivalentes a:

```protobuf
message ResultBinding {
  string source_step_id = 1;
  string source_path = 2;
  string target_field = 3;
}

message WorkflowStep {
  string step_id = 1;
  Task task_template = 2;
  repeated string depends_on = 3;
  repeated ResultBinding input_bindings = 4;
}

message WorkflowDefinition {
  string workflow_id = 1;
  repeated WorkflowStep steps = 2;
  string final_step_id = 3;
}

message SubmitWorkflowRequest {
  Task root_task = 1;
  WorkflowDefinition workflow = 2;
}

message WorkflowResult {
  string workflow_id = 1;
  string run_id = 2;
  string root_task_id = 3;
  TaskStatus status = 4;
  repeated TaskResult step_results = 5;
  google.protobuf.Struct output = 6;
  ErrorInfo error = 7;
  TraceContext trace = 8;
}
```

Há duas alternativas para a API externa.

### Alternativa A — `SubmitWorkflow`

O cliente ou planner entrega explicitamente o workflow:

```protobuf
rpc SubmitWorkflow(SubmitWorkflowRequest) returns (WorkflowResult);
```

Vantagem: separa claramente task simples de workflow.

### Alternativa B — `SubmitTask` sempre pode expandir

O cliente chama `SubmitTask`; o orchestrator decide se precisa consultar um
planner e expandir a task.

Vantagem: experiência externa mais simples.

### Recomendação

Implementar internamente as duas operações separadas, mas manter
`SubmitTask` como entrada principal para o usuário:

```text
SubmitTask
  task já estruturada e executável -> executar diretamente
  task natural/ambígua             -> obter e executar workflow

SubmitWorkflow
  endpoint explícito para testes, benchmarks e clientes avançados
```

Assim a API simples não impede testes determinísticos da camada de workflow.

## Componentes internos

O serviço deve deixar de concentrar todo o comportamento em `SubmitTask`.

Estrutura sugerida:

```text
runtime/services/orchestrator/internal/
  server/
    server.go
  execution/
    task_executor.go
  workflow/
    engine.go
    validator.go
    scheduler.go
    bindings.go
    state.go
  planning/
    planner.go
    schema.go
  selection/
    policy.go
  events/
    logger.go
```

### Task executor

Encapsula o fluxo já existente:

```text
descobrir agentes
selecionar agente
executar task
aplicar timeout/retry
retornar TaskResult
```

Ele deve ser reutilizado tanto por `SubmitTask` quanto pelo workflow engine.

### Planner adapter

Responsável por:

1. construir uma task com capability `task-decomposition`;
2. executá-la pelo mesmo `TaskExecutor`;
3. validar o resultado contra o schema do workflow;
4. devolver uma `WorkflowDefinition`.

O adapter não chama OpenAI diretamente. Ele chama um agente registrado que
oferece a capability necessária.

### Workflow validator

Deve rejeitar:

- `step_id` vazio ou duplicado;
- capability ausente;
- dependência inexistente;
- ciclos;
- binding apontando para step futuro ou não dependente;
- paths não permitidos;
- quantidade excessiva de steps;
- profundidade excessiva;
- payload acima do limite;
- tentativa de definir IDs, agentes atribuídos ou estados operacionais;
- workflow que não possui saída final;
- subtask que tenta solicitar nova decomposição sem limite explícito.

Limites iniciais sugeridos:

```text
máximo de steps por workflow: 10
máximo de profundidade: 5
máximo de expansões por root task: 1
timeout total obrigatório
```

Esses limites evitam recursão descontrolada e explosão de custo.

### Workflow scheduler

Mantém os estados dos steps:

```text
PENDING
READY
RUNNING
COMPLETED
FAILED
SKIPPED
CANCELLED
```

Algoritmo:

```text
1. Validar o DAG.
2. Marcar steps sem dependências como READY.
3. Materializar tasks READY.
4. Executar até o limite de paralelismo.
5. Armazenar cada TaskResult.
6. Resolver bindings dos dependentes.
7. Marcar novos steps como READY.
8. Em falha, aplicar a política do step/workflow.
9. Quando não houver steps pendentes, montar WorkflowResult.
```

### Binding resolver

O resolver deve suportar somente caminhos explicitamente permitidos:

```text
output
output.<campo>
metadata
metadata.<campo>
status
agent_id
```

Não deve existir:

- avaliação de Python;
- template arbitrário;
- acesso ao filesystem;
- interpolação de ambiente;
- seleção por expressões não validadas.

## Estados do workflow

Estado agregado:

```text
CREATED
PLANNING
VALIDATING
RUNNING
COMPLETED
FAILED
CANCELLED
TIMEOUT
```

Transição principal:

```text
CREATED
  -> PLANNING
  -> VALIDATING
  -> RUNNING
  -> COMPLETED
```

Falhas possíveis:

```text
PLANNING   -> FAILED
VALIDATING -> FAILED
RUNNING    -> FAILED | TIMEOUT | CANCELLED
```

Uma root task só pode terminar como `COMPLETED` depois que o step final tiver
resultado válido.

## Política de falha

O workflow precisa distinguir três níveis.

### Falha da tentativa

Uma execução contra um agente falha. O `TaskExecutor` pode tentar novamente ou
selecionar outro agente.

### Falha do step

As tentativas se esgotaram. Por padrão:

```text
step -> FAILED
dependentes -> SKIPPED
workflow -> FAILED
```

### Falha do workflow

O resultado final deve conter:

- step que falhou;
- erro original padronizado;
- attempts;
- agentes tentados;
- steps concluídos;
- steps ignorados;
- trace completo.

No primeiro incremento, não implementar compensações ou rollback. Tasks com
efeitos externos devem ser consideradas futuras e exigir idempotência.

## Persistência e concorrência

O runtime atual responde sincronicamente e guarda Registry em memória. Um
workflow com múltiplas etapas pode sobreviver por mais tempo e precisa de
estado explícito.

### Primeiro incremento

Pode usar armazenamento em memória, desde que:

- o estado esteja isolado atrás de uma interface `WorkflowStore`;
- concorrência seja protegida;
- testes não dependam de sleeps;
- perda de estado ao reiniciar seja documentada.

Interface conceitual:

```go
type WorkflowStore interface {
    Create(run WorkflowRun) error
    Get(runID string) (WorkflowRun, error)
    SaveStep(runID string, step StepRun) error
    Complete(runID string, result WorkflowResult) error
}
```

### Evolução posterior

SQLite é suficiente para persistência local e experimentos. Não é necessário
introduzir Kafka, Redis ou banco distribuído nesta fase.

## API síncrona e assíncrona

Workflows reais podem ultrapassar o timeout de uma chamada gRPC.

Implementação incremental:

### 12E.1 — Síncrona

```text
SubmitWorkflow -> aguarda WorkflowResult
```

Adequada para o cenário atual e para validar semântica.

### 12E.2 — Assíncrona

```protobuf
rpc StartWorkflow(...) returns (StartWorkflowResponse);
rpc GetWorkflow(...) returns (GetWorkflowResponse);
rpc WatchWorkflow(...) returns (stream WorkflowEvent);
rpc CancelWorkflow(...) returns (CancelWorkflowResponse);
```

O cliente recebe `run_id` imediatamente e acompanha o progresso.

## Eventos e observabilidade

Adicionar eventos:

```text
WORKFLOW_CREATED
WORKFLOW_PLANNING
WORKFLOW_VALIDATED
WORKFLOW_STARTED
WORKFLOW_COMPLETED
WORKFLOW_FAILED
WORKFLOW_TIMEOUT
STEP_READY
STEP_STARTED
STEP_COMPLETED
STEP_FAILED
STEP_SKIPPED
```

Cada evento deve conter:

```text
workflow_id
run_id
root_task_id
step_id, quando aplicável
task_id, quando materializado
agent_id, quando atribuído
trace_id
timestamp
attempt
details
```

Cada subtask deve compartilhar o `trace_id` da root task e receber:

```text
span_id novo
parent_span_id do step que a originou
parent_task_id
correlation_id = run_id
```

## Fluxo heterogêneo pretendido

```text
1. Cliente chama SubmitTask com a pergunta.
2. Orchestrator classifica a task como não executável diretamente.
3. Planner adapter solicita decomposição a um agente LLM.
4. LLM devolve WorkflowDefinition estruturada.
5. Validator verifica limites, DAG, capabilities e bindings.
6. Scheduler libera plan_route.
7. TaskExecutor descobre e executa o agente BDI.
8. Resultado BDI é armazenado.
9. Binding resolver injeta resultado e metadata em explain.
10. Scheduler libera explain.
11. TaskExecutor descobre e executa o agente LLM.
12. Workflow engine monta o resultado final.
13. Cliente recebe WorkflowResult.
```

O script `heterogeneous_demo.py` deixa de coordenar as três chamadas e passa a
fazer somente:

```python
result = scenario.ask(
    "Planeje uma rota de A para D e explique por que ela foi escolhida"
)
result.assert_completed()
```

## Relação com mensageria

Subtasks não exigem inicialmente um Messaging Service.

O orchestrator pode executar cada step diretamente por `AgentService`, como já
faz hoje. Mensageria é útil para:

- conversas longas entre agentes;
- eventos espontâneos;
- negociação;
- streaming;
- agentes que iniciam comunicação sem uma task atribuída.

Portanto:

```text
workflow orchestration
  pode ser implementada antes da mensageria

messaging
  complementa workflows, mas não é pré-requisito
```

## Relação com retry e reassignment

O workflow engine não deve reimplementar retry. Primeiro, extrair o executor de
task e estabilizar:

```text
timeout
retry
exclude_failed_agent
reassignment
```

Depois, cada step usa esse executor. Assim as políticas operacionais continuam
iguais para tasks simples e subtasks.

## Ordem de implementação

## Progresso

Atualizado em 2026-10-03.

```text
12E.1 Extrair TaskExecutor             CONCLUÍDA (Fase 10)
12E.2 Contrato e validação             CONCLUÍDA
12E.3 Workflow síncrono explícito      CONCLUÍDA
12E.4 Dependências e paralelismo       CONCLUÍDA
12E.5 Planejamento automático          CONCLUÍDA
12E.6 API assíncrona e persistência    CONCLUÍDA
12E.7 Migrar cenário heterogêneo       PENDENTE
```

A 12E.2 adicionou ao `contract.v1`, ainda com status experimental,
`WorkflowDefinition`, `WorkflowStep`, `ResultBinding`, `WorkflowStepResult`,
`WorkflowResult`, estados agregados e `SubmitWorkflow`. Os stubs Go e Python
foram regenerados.

O `workflow.Validator` aplica os limites iniciais de 10 steps, profundidade 5
e payload de 64 KiB. Ele rejeita IDs e estado operacionais, capabilities
vazias, decomposição recursiva, dependências ausentes ou repetidas, ciclos,
bindings fora da allowlist e fontes que não sejam ancestrais do step. Onze
testes unitários cobrem esses casos sem sleeps ou serviços externos.

A 12E.3 implementou `SubmitWorkflow` síncrono, `WorkflowStore` em memória,
materialização de tasks, agregação do step final e eventos de workflow e step.
A API `Scenario.submit_workflow()` expõe o endpoint usando somente valores
Python.

A 12E.4 substituiu a execução estritamente sequencial por um scheduler de DAG.
Steps independentes em estado `READY` executam com paralelismo configurável
(padrão 4), enquanto o workflow possui timeout global (padrão 30 segundos).
Bindings copiam apenas `output`, `metadata`, `status` ou `agent_id` de um
ancestral para campos não operacionais do payload, inclusive por caminhos
aninhados, sem avaliação de código. Uma falha marca apenas seus descendentes
como `SKIPPED`; branches independentes terminam normalmente, e os resultados
são agregados em ordem topológica determinística. Testes com detector de races
cobrem binding aninhado, execução concorrente limitada e propagação seletiva
de falhas.

A 12E.5 adicionou o `planning.Planner`, que transforma uma task de entrada com
capability única `task-decomposition` em uma solicitação interna
`WORKFLOW_PLANNING`. O planner é descoberto e executado pelo mesmo
`TaskExecutor` dos demais agentes; o orchestrator não conhece provedores LLM.
A saída estruturada é decodificada com schema fechado, convertida para
`WorkflowDefinition` e submetida novamente ao validator antes de chegar ao
engine. O limite é de uma expansão por root task e steps não podem solicitar
`task-decomposition`, impedindo recursão. `SubmitTaskResponse` ganhou o campo
compatível `workflow_result`, preservando `result` para tasks simples. O agente
LLM passou a produzir o DAG completo, incluindo dependências, bindings e a
extensão BDI necessária.

A 12E.6 adicionou `StartWorkflow`, `GetWorkflow` e `CancelWorkflow` ao contrato
e ao SDK Python. O `AsyncRunner` usa um contexto independente da chamada gRPC,
mantém os canceladores ativos de forma concorrente e aguarda o estado terminal
ao cancelar. O `WorkflowStore` registra criação, `RUNNING`, resultados por step
e conclusão, permitindo acompanhamento por polling de snapshots defensivos.
O store em memória permanece a implementação padrão; SQLite foi avaliado como
uma troca futura da interface, não necessária para os experimentos locais e
evitada agora para não introduzir uma dependência operacional antes dos
benchmarks. Os testes com race detector cobrem início, consulta, conclusão,
cancelamento e rejeição antes de iniciar.

Validação integrada realizada em 2026-10-03: o cenário isolado
`scenarios/workflow-sequential` executou `first -> second`, ambos pelo agente
`workflow-echo`, e retornou a saída do segundo step. Os eventos correlacionaram
workflow, run, step, task e trace, e o ambiente Docker foi removido após a
verificação. Testes adicionais cobrem endpoint, store defensivo, ordem
topológica, agregação, falha e propagação de `SKIPPED`.

Próximo incremento: 12E.7, reduzindo o cenário heterogêneo a uma única pergunta
e validando o fluxo real planner LLM -> agente BDI -> explicação LLM, com
métricas e correlação por workflow e step.

### 12E.1 — Extrair `TaskExecutor`

- remover execução de negócio de dentro do handler gRPC;
- criar testes unitários do executor;
- preservar exatamente o comportamento de `SubmitTask`.

### 12E.2 — Contrato de workflow

- definir `WorkflowDefinition`, `WorkflowStep` e bindings;
- gerar stubs;
- implementar validação de DAG e limites;
- criar testes de ciclos e referências inválidas.

### 12E.3 — Workflow síncrono explícito

- implementar `SubmitWorkflow`;
- executar steps sequenciais;
- agregar resultados;
- emitir eventos.

### 12E.4 — Dependências e paralelismo

- liberar steps READY;
- executar branches independentes com limite;
- resolver bindings;
- propagar falhas.

### 12E.5 — Planejamento automático

- integrar capability `task-decomposition`;
- validar a saída antes de executar;
- fazer `SubmitTask` expandir tasks naturais;
- limitar expansão e custo.

### 12E.6 — API assíncrona e persistência

- adicionar `run_id`;
- implementar consulta, acompanhamento e cancelamento;
- introduzir `WorkflowStore`;
- avaliar SQLite.

### 12E.7 — Migrar cenário heterogêneo

- reduzir o cenário a uma pergunta;
- remover coordenador transitório;
- validar LLM -> BDI -> LLM;
- registrar métricas por workflow e por step.

## Testes necessários

### Unitários

```text
DAG válido
step duplicado
dependência inexistente
ciclo
binding permitido
binding proibido
materialização de parent_task_id e trace
propagação de output
propagação de falha
limite de steps
limite de profundidade
timeout total
```

### Integração determinística

O workflow engine pode ser testado com agentes mock, sem LLM:

```text
mock planner -> workflow fixo
mock worker A
mock worker B
assert WorkflowResult
```

Isso testa o runtime sem chamadas externas.

### Integração heterogênea real

```text
OpenAI LLM planner
BDI route-planning
OpenAI LLM explanation
uma única pergunta do cliente
```

Esse teste deve ser separado por depender de credencial, custo e variabilidade.

## Critérios de pronto

```text
cliente envia uma única pergunta
planner LLM devolve um workflow estruturado
runtime rejeita workflows inválidos
orchestrator cria e correlaciona subtasks
steps são executados apenas quando dependências terminam
outputs anteriores chegam aos steps dependentes
retry e timeout funcionam por step
falha impede execução incorreta de dependentes
resultado final agrega a execução
eventos permitem reconstruir todo o workflow
cenário heterogêneo não coordena chamadas gRPC
task simples continua funcionando sem regressão
```

## Fora de escopo inicial

```text
loops arbitrários
scripts ou expressões executáveis em bindings
rollback distribuído
transações entre agentes
workflow visual
Kubernetes
Kafka
negociação autônoma entre agentes
recursão ilimitada de planners
```

## Decisões adotadas para o primeiro incremento

```text
mensagens experimentais dentro de contract.v1 até o freeze
SubmitWorkflow explícito primeiro; planejamento automático entra na 12E.5
WorkflowResult separado com WorkflowStepResult correlacionado por step_id
bindings: output[.campo], metadata[.campo], status e agent_id
targets somente no payload e nunca em campos operacionais
store em memória atrás de WorkflowStore
paralelismo padrão 4 na 12E.4
uma única expansão de planner por root task
```
