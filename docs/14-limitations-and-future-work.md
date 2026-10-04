# Limitações e trabalhos futuros

## Limitações atuais

- Registry, broker de mensagens e estado dos workflows são mantidos em memória;
  reiniciar os serviços descarta esse estado.
- A mensageria oferece entrega *at-most-once*, sem persistência, confirmação ou
  reentrega após desconexão.
- A detecção de falhas usa timeouts fixos e pode marcar como suspeito um agente
  sob pausa longa ou congestionamento.
- O runtime não implementa autenticação, autorização nem TLS. A topologia foi
  projetada para experimentos locais em rede isolada.
- O desempenho de cenários LLM depende do provedor, modelo, rede e limites da
  conta utilizada.

## Trabalhos futuros

- Persistir registros, workflows e mensagens e estudar garantias de entrega.
- Avaliar detectores de falha adaptativos e políticas de seleção baseadas em
  histórico, custo e qualidade.
- Adicionar segurança de transporte e identidade dos agentes.
- Ampliar os benchmarks com mais repetições, cargas concorrentes e intervalos
  de confiança.
- Avaliar outras arquiteturas de agentes e provedores de modelos mantendo o
  contrato congelado compatível.
