package server

import (
	"context"
	"log/slog"

	pb "tg/runtime/gen/go/contract/v1"
	"tg/runtime/services/registry/internal/store"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

// RegistryServer implementa pb.RegistryServiceServer.
type RegistryServer struct {
	pb.UnimplementedRegistryServiceServer
	agentStore *store.AgentStore
}

func New(agentStore *store.AgentStore) *RegistryServer {
	return &RegistryServer{agentStore: agentStore}
}

func (srv *RegistryServer) RegisterAgent(_ context.Context, req *pb.RegisterAgentRequest) (*pb.RegisterAgentResponse, error) {
	if req.Agent == nil || req.Agent.AgentId == "" {
		return nil, status.Error(codes.InvalidArgument, "agent and agent_id are required")
	}
	srv.agentStore.Save(req.Agent)
	slog.Info("agent registered", "agent_id", req.Agent.AgentId, "status", req.Agent.Status)
	return &pb.RegisterAgentResponse{Success: true, Message: "registered"}, nil
}

func (srv *RegistryServer) UnregisterAgent(_ context.Context, req *pb.UnregisterAgentRequest) (*pb.UnregisterAgentResponse, error) {
	if err := srv.agentStore.Delete(req.AgentId); err != nil {
		return nil, status.Error(codes.NotFound, err.Error())
	}
	slog.Info("agent unregistered", "agent_id", req.AgentId)
	return &pb.UnregisterAgentResponse{Success: true}, nil
}

func (srv *RegistryServer) GetAgent(_ context.Context, req *pb.GetAgentRequest) (*pb.GetAgentResponse, error) {
	agent, err := srv.agentStore.Get(req.AgentId)
	if err != nil {
		return nil, status.Error(codes.NotFound, err.Error())
	}
	return &pb.GetAgentResponse{Agent: agent}, nil
}

func (srv *RegistryServer) DiscoverAgents(_ context.Context, req *pb.DiscoverAgentsRequest) (*pb.DiscoverAgentsResponse, error) {
	agents := srv.agentStore.List(req.RequiredCapabilities, req.StatusFilter)
	slog.Info("discover agents", "required", req.RequiredCapabilities, "found", len(agents))
	return &pb.DiscoverAgentsResponse{Agents: agents}, nil
}

func (srv *RegistryServer) ReportHealth(_ context.Context, req *pb.ReportHealthRequest) (*pb.ReportHealthResponse, error) {
	if req.Health == nil {
		return nil, status.Error(codes.InvalidArgument, "health is required")
	}
	if err := srv.agentStore.UpdateHealth(req.Health.AgentId, req.Health.Status); err != nil {
		return nil, status.Error(codes.NotFound, err.Error())
	}
	slog.Info("health reported", "agent_id", req.Health.AgentId, "status", req.Health.Status)
	return &pb.ReportHealthResponse{Success: true}, nil
}
