package store

import (
	"fmt"
	"sync"
	"time"

	pb "tg/runtime/gen/go/contract/v1"
	"google.golang.org/protobuf/types/known/timestamppb"
)

// AgentStore mantém os agentes registrados em memória.
type AgentStore struct {
	mu     sync.RWMutex
	agents map[string]*pb.AgentDescriptor
}

func New() *AgentStore {
	return &AgentStore{
		agents: make(map[string]*pb.AgentDescriptor),
	}
}

func (st *AgentStore) Save(agent *pb.AgentDescriptor) {
	st.mu.Lock()
	defer st.mu.Unlock()

	now := timestamppb.New(time.Now())
	if _, exists := st.agents[agent.AgentId]; !exists {
		agent.CreatedAt = now
	}
	agent.UpdatedAt = now
	st.agents[agent.AgentId] = agent
}

func (st *AgentStore) Delete(agentID string) error {
	st.mu.Lock()
	defer st.mu.Unlock()

	if _, exists := st.agents[agentID]; !exists {
		return fmt.Errorf("agent %q not found", agentID)
	}
	delete(st.agents, agentID)
	return nil
}

func (st *AgentStore) Get(agentID string) (*pb.AgentDescriptor, error) {
	st.mu.RLock()
	defer st.mu.RUnlock()

	agent, exists := st.agents[agentID]
	if !exists {
		return nil, fmt.Errorf("agent %q not found", agentID)
	}
	return agent, nil
}

// List retorna todos os agentes que satisfazem o filtro.
// Se requiredCapabilities estiver vazio, retorna todos os agentes não-DEAD.
func (st *AgentStore) List(requiredCapabilities []string, statusFilter pb.AgentStatus) []*pb.AgentDescriptor {
	st.mu.RLock()
	defer st.mu.RUnlock()

	var result []*pb.AgentDescriptor
	for _, agent := range st.agents {
		if agent.Status == pb.AgentStatus_AGENT_STATUS_DEAD {
			continue
		}
		if statusFilter != pb.AgentStatus_AGENT_STATUS_UNKNOWN && agent.Status != statusFilter {
			continue
		}
		if !hasAllCapabilities(agent, requiredCapabilities) {
			continue
		}
		result = append(result, agent)
	}
	return result
}

func (st *AgentStore) UpdateHealth(agentID string, newStatus pb.AgentStatus) error {
	st.mu.Lock()
	defer st.mu.Unlock()

	agent, exists := st.agents[agentID]
	if !exists {
		return fmt.Errorf("agent %q not found", agentID)
	}
	agent.Status = newStatus
	agent.UpdatedAt = timestamppb.New(time.Now())
	return nil
}

// hasAllCapabilities verifica se o agente possui todas as capabilities pedidas.
func hasAllCapabilities(agent *pb.AgentDescriptor, required []string) bool {
	if len(required) == 0 {
		return true
	}
	have := make(map[string]bool, len(agent.Capabilities))
	for _, cap := range agent.Capabilities {
		have[cap.CapabilityId] = true
	}
	for _, req := range required {
		if !have[req] {
			return false
		}
	}
	return true
}
