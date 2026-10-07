# Fase 11B — Messaging Service

Status: concluída em 2026-10-03.

## Decisão

Os benchmarks mostraram `message_count = 0` porque workflows usam chamadas
diretas ao `AgentService`. Isso não elimina a necessidade documentada de
comunicação iniciada por agentes. Foi implementado o menor serviço que cumpre
essa necessidade, sem introduzir Kafka, RabbitMQ ou persistência externa.

## Contrato e fluxo

O contrato passou a expor:

```text
PublishMessage(PublishMessageRequest) -> PublishMessageResponse
StreamMessages(StreamMessagesRequest) -> stream MessageEnvelope
```

`MessageEnvelope` preserva `conversation_id`, `correlation_id`, `reply_to`,
`task_id` e `trace`. A publicação valida IDs, tipo, timestamp, trace e TTL. O
broker mantém uma fila em memória por destinatário e permite um stream ativo
por `receiver_id`. Mensagens publicadas antes da conexão são entregues em ordem;
mensagens expiradas são descartadas/rejeitadas.

Eventos `MESSAGE_SENT` e `MESSAGE_RECEIVED` são gravados com message, task,
receiver e trace correlacionáveis. O logger foi movido para um pacote interno
compartilhado pelos serviços.

## SDK e execução

O SDK Python oferece `MessagingClient.publish()` e `stream()`, retornando o
modelo público `Message`. O Compose baseline inclui o serviço na porta 50053.
O cenário isolado `scenarios/messaging-basic` valida:

```text
agent-a -> MessagingService -> agent-b
```

Validação integrada realizada em 2026-10-03: `agent-b` recebeu o mesmo payload,
message ID, conversation, correlation, task e trace enviados por `agent-a`.

## Garantias e limitações

- semântica: at-most-once;
- armazenamento: memória, perdido em reinício;
- ordenação: preservada por destinatário dentro de uma instância;
- backpressure: publicação é rejeitada se o buffer do stream estiver cheio;
- uma conexão consumidora ativa por `receiver_id`;
- sem autenticação, autorização, broker distribuído ou redelivery;
- workflows continuam usando `AgentService`; mensageria é complementar.

Essas limitações são deliberadas e suficientes para a Definition of Done. Uma
fila durável seria trabalho futuro caso os experimentos exijam entrega após
reinício ou múltiplos consumidores.

Próximo incremento: auditar o contrato completo, remover ambiguidades,
documentar compatibilidade e congelar a versão usada na monografia.
