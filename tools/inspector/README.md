# Runtime Inspector

Interface React para explorar localmente as evidências geradas pelo executor
`tg`: estado, tarefas, workflows, participantes, timeline e dados brutos.

## Executar

Na raiz do repositório:

```sh
npm install --prefix tools/inspector
npm run dev --prefix tools/inspector
```

Abra `http://127.0.0.1:4173`. Depois:

1. execute `./tg scenario failure-reassignment` ou outro cenário;
2. use `./tg status` para localizar `.tg/runs/ID/`;
3. arraste os arquivos da execução para a tela ou use **Selecionar arquivos**;
4. navegue por visão geral, etapas, timeline e dados brutos.

O botão **Abrir exemplo** carrega uma execução registrada de recuperação sem
exigir Docker.

## Entradas e privacidade

São reconhecidos `result.json`, `summary.json`, `result.evaluation.json`,
`events.jsonl`, `message-events.jsonl`, `status`, `environment` e `scenario`.
O limite é de 20 MB por seleção.

Os arquivos são processados somente na memória do navegador. A aplicação não
faz upload, persistência ou consulta ao Docker. O estado exibido é um snapshot
e não acompanha serviços vivos.

## Verificar

```sh
npm test --prefix tools/inspector
npm run build --prefix tools/inspector
```

O parser permanece em `model.js` e possui testes sem dependência do DOM. A
interface fica em `src/` e é empacotada com Vite.

[Roteiro para apresentar o trabalho](../../docs/presentation.md)
