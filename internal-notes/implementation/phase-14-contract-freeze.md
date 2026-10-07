# Fase 14 — Congelamento do contrato

Status: concluída em 2026-10-04.

## Release

O contrato usado na avaliação do TG é `contract.v1`, release semântica
`1.0.0`. A versão está registrada em `proto/contract/v1/VERSION` e os agentes
do SDK anunciam `1.0.0` por padrão.

O Registry aceita versões `1.x.y` bem formadas e rejeita versões semânticas
inválidas ou majors 0/2+ com `FAILED_PRECONDITION`. Assim a declaração de
compatibilidade deixou de ser apenas documental.

## Superfície congelada

- entidades: agentes, capabilities, health, tasks, resultados, erros e trace;
- seleção, retry e extensões BDI/LLM;
- eventos e `MessageEnvelope`;
- Registry, Orchestrator, Agent e Messaging services;
- workflow explícito, automático e assíncrono.

Workflows deixaram de ser marcados como experimentais no `.proto`. Os stubs Go
e Python foram regenerados a partir da mesma fonte.

## Regra de mudança

`make contract-check` calcula SHA-256 de `contract.proto` e compara com
`contract.sha256`. Uma alteração exige deliberadamente:

1. classificar a mudança como compatível ou breaking;
2. preservar números de campos existentes e reservar os removidos;
3. atualizar `VERSION` conforme SemVer;
4. regenerar todos os stubs;
5. executar testes Go/Python e cenários afetados;
6. atualizar o checksum e este registro de decisão.

Campos opcionais novos podem entrar em uma versão minor compatível. Remoção,
renumeração, mudança de tipo/semântica ou alteração incompatível de RPC exige
novo major e novo package protobuf.

## Evidências

- validação unitária de versões compatíveis, ausentes, inválidas e majors
  incompatíveis;
- Registry testa aceitação/rejeição no endpoint real;
- geração repetida de stubs não produz diferenças;
- checksum do `.proto` passa em macOS (`shasum`) e Linux (`sha256sum`);
- todas as suítes Go e Python passam após o freeze.

Próximo passo: auditoria final da Definition of Done e das instruções de fresh
clone, corrigindo somente lacunas comprovadas antes de declarar o roadmap
funcional concluído.
