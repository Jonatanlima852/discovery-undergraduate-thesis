# Phase 12D — SDK de autoria de agentes e cenários

## Decisão

As abstrações BDI e LLM serão parte pública de `sdk/python`. A unidade
principal de extensão será uma classe Python. YAML e JSON serão opcionais para
configuração e deployment.

O objetivo é que o usuário do SDK escreva lógica de domínio, não código de
infraestrutura:

```text
usuário do SDK
  capabilities
  crenças e planos BDI
  prompts e schemas LLM
  pergunta e expectativas do cenário

SDK
  contrato protobuf
  conversão dict <-> Struct
  registro automático
  heartbeat
  servidor gRPC
  TaskResult e ErrorInfo
  cliente OpenAI e validação estruturada
  rastreabilidade
```

Essa separação é parte da contribuição do projeto: agentes internamente
heterogêneos tornam-se operacionalmente homogêneos através do contrato.

## API pública pretendida

O pacote deve expor:

```python
from tg_sdk import (
    Agent,
    BdiAgent,
    LlmAgent,
    Scenario,
    plan,
    llm_capability,
)
```

Aplicações normais não devem importar `contract_pb2`.

## Abstração BDI

Uma subclasse de `BdiAgent` declara:

- identidade e capabilities, diretamente ou via ambiente;
- crenças iniciais;
- conversão de uma task em desejo;
- planos por métodos decorados;
- opcionalmente revisão de crenças após execução.

Exemplo:

```python
from tg_sdk import BdiAgent, plan


class DeliveryAgent(BdiAgent):
    capabilities = ["delivery-planning"]
    beliefs = {"vehicle_available": True}

    def desire(self, task):
        return task.payload

    @plan(name="deliver_by_vehicle", priority=10)
    def by_vehicle(self, desire, beliefs):
        if not beliefs["vehicle_available"]:
            return None
        return {"delivered_to": desire["destination"]}
```

O SDK é responsável por:

1. descobrir os planos da classe;
2. avaliar sua aplicabilidade;
3. selecionar a intenção por custo, prioridade ou política configurada;
4. executar o plano;
5. devolver `selected_plan`, `intention_id` e resumo de deliberação;
6. mapear ausência de desejo/plano para erro do contrato.

O primeiro incremento pode manter a interface funcional já existente e
adicionar decorators como açúcar sintático, sem implementar um interpretador
AgentSpeak.

## Abstração LLM

Uma subclasse de `LlmAgent` declara capabilities como métodos e associa a cada
uma prompt e schema de saída:

```python
from pydantic import BaseModel
from tg_sdk import LlmAgent, llm_capability


class Classification(BaseModel):
    capability: str
    confidence: float


class ClassifierAgent(LlmAgent):
    @llm_capability("capability-inference", output_schema=Classification)
    def classify(self, task):
        return self.prompt(
            system="Select the capability required by the task.",
            user=task.goal,
        )
```

O SDK é responsável por:

1. escolher o handler a partir da capability solicitada;
2. construir o cliente OpenAI usando a configuração do ambiente;
3. solicitar structured output pela Responses API;
4. validar novamente a resposta localmente;
5. registrar modelo, uso e latência em metadata;
6. impedir que uma saída do modelo injete IDs ou campos operacionais;
7. converter falhas da API para erros estáveis do contrato.

Nesta fase há somente integração OpenAI. Testes injetam um cliente falso no
`LlmAgent`; esse fake não é uma implementação disponível em produção.

## Configuração automática

`Agent.from_env()` fornece convenções comuns:

```text
AGENT_ID
AGENT_NAME
AGENT_HOST
AGENT_PORT
REGISTRY_ADDR
HEARTBEAT_INTERVAL_SECONDS
LLM_MODEL
```

Argumentos fornecidos explicitamente pelo código têm precedência. O SDK deve
validar configuração antes de iniciar e produzir mensagens acionáveis.

“Conectar automaticamente” significa:

```text
carregar configuração
subir o endpoint do agente
registrar descriptor e capabilities
iniciar heartbeat
renovar registro após perda transitória do Registry
encerrar e desregistrar de forma limpa quando possível
```

Não significa descobrir magicamente endereços fora da rede. Docker Compose,
Kubernetes ou o operador ainda fornecem DNS e variáveis de conexão.

## Cenário Python de um arquivo

Um cenário descreve participantes, infraestrutura e a entrada externa. Ele não
deve coordenar manualmente chamadas gRPC entre agentes:

```python
from tg_sdk import Scenario
from agents import DeliveryAgent, PlannerAgent


scenario = Scenario(
    name="heterogeneous-delivery",
    agents=[PlannerAgent, DeliveryAgent],
    entry_capability="task-decomposition",
)

result = scenario.run(
    "Planeje uma entrega no endereço B e explique a decisão."
)

result.assert_completed()
result.assert_agent_kind_used("llm")
result.assert_agent_kind_used("bdi")
```

No modo integrado, `Scenario.run()` submete apenas a pergunta inicial ao
orchestrator. A infraestrutura é responsável por descoberta e execução. O
cenário pode observar e validar o trace, mas não deve substituir o
orchestrator como coordenador permanente.

Enquanto o orchestrator ainda não executa subtasks automaticamente, o runner
pode manter um adaptador temporário de encadeamento. Esse comportamento deve
ser identificado como compatibilidade transitória, pois o estado final
pretendido é:

```text
cliente envia uma pergunta
orchestrator descobre e aciona agentes conectados
agentes cooperam através do contrato
cliente recebe um resultado correlacionado
```

## Infraestrutura por cenário

Cada diretório de cenário possui seu próprio Compose:

```text
scenarios/
  heterogeneous-route/
    scenario.py
    compose.yaml
    Dockerfile
    README.md
```

`compose.yaml` declara a topologia real do experimento:

- Registry e orchestrator;
- agentes A, B, C, D e E;
- modelos OpenAI;
- falhas, delays e limites;
- volume de resultados;
- healthchecks.

O Dockerfile do cenário é necessário somente quando há código/dependências
próprias. Imagens comuns do runtime e SDK devem ser reutilizadas para evitar
duplicação.

Comandos pretendidos:

```sh
docker compose -f scenarios/heterogeneous-route/compose.yaml up --build
uv run scenarios/heterogeneous-route/scenario.py
docker compose -f scenarios/heterogeneous-route/compose.yaml down
```

Depois, um wrapper pode reduzir isso para:

```sh
make scenario NAME=heterogeneous-route
```

## Etapas de implementação

## Progresso

Atualizado em 2026-10-03.

```text
12D.1 Modelos Python amigáveis       CONCLUÍDA
12D.2 BdiAgent declarativo           EM ANDAMENTO
12D.3 LlmAgent declarativo           PARCIAL
12D.4 Runtime de cenário             PARCIAL
12D.5 Deployment por cenário         PENDENTE
```

A 12D.1 introduziu `tg_sdk.Task` e `tg_sdk.TaskResult`, conversões
centralizadas de mappings e `google.protobuf.Struct`, e o hook público
`Agent.handle()`. O adaptador do servidor aceita a API nova e preserva
compatibilidade com subclasses que ainda sobrescrevem `execute_task()` usando
protobuf. `ValueError`, `TimeoutError` e falhas de execução são convertidos em
`ErrorInfo` estável. Os testes cobrem round-trip, compatibilidade e mapeamento
de erros.

Próximo incremento: concluir a 12D.2, migrando os agentes BDI de domínio para
`tg_sdk.Task`/`TaskResult`, removendo imports de protobuf e registrando todos
os planos avaliados na metadata da deliberação.

### 12D.1 — Modelos Python amigáveis

- adicionar wrappers `Task`, `TaskResult` e payload baseado em mappings;
- centralizar conversões protobuf;
- preservar compatibilidade com subclasses atuais;
- testar conversões e mapeamento de exceções.

### 12D.2 — `BdiAgent` declarativo

- adicionar discovery de métodos `@plan`;
- formalizar `desire()`, seleção e revisão de crenças;
- incluir trilha de planos avaliados em metadata;
- migrar route-planning e meeting-scheduler para a API pública.

### 12D.3 — `LlmAgent` declarativo

- mover cliente OpenAI e validação genérica do agente exemplo para o SDK;
- adicionar `@llm_capability`;
- suportar schema tipado;
- migrar o llm-agent atual para uma subclasse pequena.

### 12D.4 — Runtime de cenário

- implementar `Scenario`, `ScenarioResult` e assertions;
- compartilhar um trace por execução;
- salvar relatório e eventos;
- manter adaptador temporário para workflows até o orchestrator suportá-los.

### 12D.5 — Deployment por cenário

- criar testes com cliente falso e um cenário integrado com OpenAI;
- adicionar healthchecks;
- documentar portas, secrets e readiness;
- garantir limpeza isolada por Compose project.

## Definição de pronto

```text
um agente BDI útil exige somente uma pequena subclasse Python
um agente LLM útil exige somente uma pequena subclasse Python
nenhum exemplo de domínio importa protobuf gerado
ambas as classes registram capabilities e heartbeat automaticamente
testes do LLM não fazem chamadas externas
um cenário heterogêneo cabe em um scenario.py legível
cada cenário integrado possui topologia Compose isolada
o cliente envia uma única pergunta no estado arquitetural final
resultados são correlacionados por run_id e trace_id
testes unitários com cliente OpenAI falso e um teste integrado real passam
```

## Fora de escopo

```text
framework BDI formal completo
AgentSpeak/Jason
cadeia de pensamento do LLM
provisionamento genérico de cloud
interface web antes da estabilização da API Python
```
