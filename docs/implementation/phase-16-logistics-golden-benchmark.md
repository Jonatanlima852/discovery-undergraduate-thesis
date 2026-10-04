# Fase 16 — Benchmark de missão logística LLM, BDI e híbrido

Status: concluída e executada em 2026-10-04.

## Pergunta experimental

Uma LLM forte consegue produzir planos plausíveis para uma missão logística,
mas sua saída isolada oferece as mesmas propriedades de otimalidade e
reprodutibilidade de um executor simbólico? A combinação LLM + BDI preserva a
entrada natural enquanto restringe a execução a transições válidas e
determinísticas?

O experimento não parte da hipótese de que o híbrido será mais rápido que o
BDI. A hipótese é que a LLM resolve a fronteira linguística e o BDI fornece
planejamento verificável, rejeição de missões impossíveis e desempate estável.

## Domínio

O robô começa em A com 65% de bateria e um pacote em A. O mundo versionado em
`logistics/world.json` contém oito locais, onze conexões bidirecionais, custos
de tempo e energia, chave em D, carregador em E e porta de F destrancável a
partir de E.

As ações válidas são `PICK_UP_PACKAGE`, `PICK_UP_KEY`, `MOVE`, `RECHARGE`,
`UNLOCK_DOOR` e `DELIVER_PACKAGE`. Cada ação tem precondições e efeitos
explícitos. O simulador rejeita conexão inexistente, origem diferente da
posição, local proibido, bateria insuficiente, entrada em F sem destrancar,
entrega sem pacote e violação do estado final.

O planejador BDI usa busca de custo uniforme com ordenação determinística. O
objetivo exige entrega, destino correto, deadline, reserva de bateria e visita
a todos os locais obrigatórios. Se não houver plano, a resposta correta é
rejeitar a missão.

## Estratégias comparadas

- **BDI-only:** recebe a missão já estruturada; é o baseline simbólico.
- **LLM-only:** recebe pedido natural e mundo completo e produz sozinha a lista
  de ações. Todas as regras são informadas e nenhum componente corrige o plano.
- **LLM + BDI:** `logistics-interpret` extrai as restrições e um `ResultBinding`
  entrega `output.mission` a `logistics-execution`; a LLM não escolhe ações.

## Dataset e execução

`logistics/cases.json` possui oito casos: cinco viáveis e três impossíveis.
Eles cobrem entrega simples, contaminação, chave e porta, reserva de energia,
visita obrigatória, deadline impossível, grafo bloqueado e reserva impossível.

A campanha final usou o modelo `gpt-5.6-luna`, oito casos, duas repetições,
dezesseis execuções por estratégia e 48 execuções totais.

Comando reproduzível:

```sh
LOGISTICS_REPETITIONS=2 ./benchmarks/run-logistics.sh
```

O runner sobe Registry, Orchestrator, agente LLM e agente BDI, intercala as
estratégias, simula todas as respostas e grava JSON bruto, CSV, SVG e eventos.
A chave é lida de `.env` e não entra nos artefatos.

## Métricas

- **validade:** todas as ações são aplicáveis e o estado final satisfaz o
  pedido, ou uma missão realmente impossível é rejeitada;
- **segurança:** nenhuma transição inválida foi executada;
- **otimalidade:** tempo final igual ao menor tempo encontrado pelo oráculo;
- **consistência:** repetições do mesmo caso produziram o mesmo plano;
- **acurácia de interpretação:** igualdade estrutural estrita com a referência;
- **latência:** tempo cliente a cliente pelo runtime;
- **tokens:** `total_tokens` reportado pelo provedor.

## Resultados finais

Execução `logistics-20261004T-final-v2`:

| Estratégia | Válidos/seguros | Ótimos | Consistência | Latência média | p95 | Tokens |
|---|---:|---:|---:|---:|---:|---:|
| BDI-only | 100% | 100% | 100% | 25,7 ms | 42,2 ms | 0 |
| LLM-only | 100% | 56,25% | 25% | 4.869,5 ms | 7.004,2 ms | 17.170 |
| LLM + BDI | 100% | 100% | 100% | 1.956,9 ms | 2.632,1 ms | 5.282 |

As três estratégias concluíram os cinco casos viáveis e rejeitaram os três
impossíveis nas duas repetições. Portanto, esta amostra não é evidência de que
a LLM escolhida produza planos inseguros nesse domínio.

A diferença aparece nas propriedades mais fortes:

- sete das dezesseis respostas LLM-only foram válidas, mas não ótimas;
- os gaps observados foram de um ou dois minutos;
- somente dois dos oito casos LLM-only foram idênticos nas duas repetições;
- BDI-only e híbrido foram ótimos e idênticos em todos os casos;
- o híbrido consumiu 69,2% menos tokens e teve latência média 59,8% menor que
  LLM-only, pois a LLM extrai campos em vez de buscar toda a sequência;
- BDI-only permaneceu cerca de 76 vezes mais rápido que o híbrido.

A acurácia estrita da interpretação híbrida foi 87,5%. Nos dois desvios, a LLM
adicionou A como local obrigatório na entrega simples; como A é o estado
inicial, isso é semanticamente redundante e não alterou o plano. Mantemos a
métrica estrita para não ocultar variação do modelo.

## Conclusão permitida

O resultado não sustenta que toda LLM falhará nem que o híbrido entende sempre
a intenção corretamente. Ele sustenta uma afirmação mais precisa:

> Mesmo quando uma LLM produz planos válidos, sua saída não carrega por si só
> uma garantia de otimalidade ou repetibilidade. No híbrido, somente o plano
> derivado das regras e precondições do domínio é executável; entradas sem
> solução são rejeitadas deterministicamente.

A garantia é limitada à missão estruturada. Uma interpretação errada ainda
pode representar a intenção humana incorretamente; por isso essa etapa é
medida separadamente e poderia exigir confirmação em uma aplicação real.

## Artefatos e limitações

O domínio, mundo, dataset e testes estão em `logistics/`; runner e automação em
`benchmarks/`; exemplo em `scenarios/logistics-mission/`; resultados escolhidos
em `benchmarks/results/logistics-20261004T-final-v2/`.

São limitações: oito casos e duas repetições, um único modelo e prompt, mundo
pequeno e observável, consistência estrita sensível ao texto da rejeição e
ausência de custo monetário (tokens foram preservados). Trabalhos futuros podem
usar mundos gerados por seed, mais modelos e bloqueios durante a execução.
