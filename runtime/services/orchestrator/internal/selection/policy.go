package selection

import pb "tg/runtime/gen/go/contract/v1"

// FirstAvailable retorna o primeiro agente da lista.
// Assume que a lista já foi filtrada pelo Registry (só agentes compatíveis).
func FirstAvailable(agents []*pb.AgentDescriptor) *pb.AgentDescriptor {
	if len(agents) == 0 {
		return nil
	}
	return agents[0]
}
