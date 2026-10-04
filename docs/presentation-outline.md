# Roteiro de apresentação

1. Problema: agentes heterogêneos possuem ciclos internos distintos e precisam
   cooperar sem compartilhar implementação.
2. Contribuição: contrato `contract.v1` e runtime mínimo para descoberta,
   seleção, execução, workflows, saúde, reassignment e mensageria.
3. Arquitetura: apresentar o diagrama de `03-architecture.md` e a separação
   entre contrato, runtime, SDK e agentes.
4. Demonstração: executar `make demo`; em seguida mostrar o cenário heterogêneo
   e os eventos correlacionados por trace.
5. Avaliação: explicar os cenários A-E, métricas, resultados de referência e
   condições da máquina/provedor.
6. Limitações: estado em memória, mensageria at-most-once, timeouts fixos e
   ausência de segurança para produção.
7. Encerramento: evidenciar interoperabilidade sem impor a arquitetura interna
   e apresentar os trabalhos futuros.
