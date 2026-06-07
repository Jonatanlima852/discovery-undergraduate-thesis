package server

import (
	"context"
	"log/slog"

	"github.com/google/uuid"
	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"

	pb "tg/runtime/gen/go/contract/v1"
	"tg/runtime/services/orchestrator/internal/events"
	"tg/runtime/services/orchestrator/internal/selection"
)

type OrchestratorServer struct {
	pb.UnimplementedOrchestratorServiceServer
	registryAddr string
	logger       *events.Logger
}

func New(registryAddr string, logger *events.Logger) *OrchestratorServer {
	return &OrchestratorServer{registryAddr: registryAddr, logger: logger}
}

func (srv *OrchestratorServer) SubmitTask(ctx context.Context, req *pb.SubmitTaskRequest) (*pb.SubmitTaskResponse, error) {
	task := req.Task
	if task == nil {
		return nil, status.Error(codes.InvalidArgument, "task is required")
	}

	// garante IDs presentes
	if task.TaskId == "" {
		task.TaskId = uuid.NewString()
	}
	if task.Trace == nil {
		task.Trace = &pb.TraceContext{TraceId: uuid.NewString()}
	}

	slog.Info("task received", "task_id", task.TaskId, "goal", task.Goal)
	srv.logger.Log(events.Event{
		EventID: uuid.NewString(),
		TaskID:  task.TaskId,
		Type:    "TASK_CREATED",
		TraceID: task.Trace.TraceId,
	})

	// descobre agentes compatíveis no Registry
	regConn, err := grpc.NewClient(srv.registryAddr,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		return errorResp(pb.ErrorCode_ERROR_CODE_AGENT_UNAVAILABLE, "cannot connect to registry", false), nil
	}
	defer regConn.Close()

	regClient := pb.NewRegistryServiceClient(regConn)
	disc, err := regClient.DiscoverAgents(ctx, &pb.DiscoverAgentsRequest{
		RequiredCapabilities: task.RequiredCapabilities,
	})
	if err != nil || len(disc.Agents) == 0 {
		slog.Warn("no agents found", "task_id", task.TaskId, "required", task.RequiredCapabilities)
		return errorResp(pb.ErrorCode_ERROR_CODE_CAPABILITY_NOT_FOUND, "no compatible agent found", false), nil
	}

	agent := selection.FirstAvailable(disc.Agents)
	task.AssignedAgentId = agent.AgentId

	slog.Info("agent selected", "task_id", task.TaskId, "agent_id", agent.AgentId)
	srv.logger.Log(events.Event{
		EventID: uuid.NewString(),
		TaskID:  task.TaskId,
		Type:    "TASK_ASSIGNED",
		AgentID: agent.AgentId,
		TraceID: task.Trace.TraceId,
	})

	// chama o AgentService no agente selecionado
	agentConn, err := grpc.NewClient(agent.Endpoint.Address,
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		return errorResp(pb.ErrorCode_ERROR_CODE_AGENT_UNAVAILABLE, "cannot connect to agent", true), nil
	}
	defer agentConn.Close()

	agentClient := pb.NewAgentServiceClient(agentConn)
	execResp, err := agentClient.ExecuteTask(ctx, &pb.ExecuteTaskRequest{Task: task})
	if err != nil {
		slog.Error("agent execution error", "task_id", task.TaskId, "agent_id", agent.AgentId, "err", err)
		srv.logger.Log(events.Event{
			EventID: uuid.NewString(),
			TaskID:  task.TaskId,
			Type:    "TASK_FAILED",
			AgentID: agent.AgentId,
			TraceID: task.Trace.TraceId,
			Details: err.Error(),
		})
		return errorResp(pb.ErrorCode_ERROR_CODE_EXECUTION_FAILED, err.Error(), true), nil
	}

	result := execResp.Result
	eventType := "TASK_COMPLETED"
	if result.Status == pb.TaskStatus_TASK_STATUS_FAILED {
		eventType = "TASK_FAILED"
	}

	slog.Info("task finished", "task_id", task.TaskId, "agent_id", agent.AgentId, "status", result.Status)
	srv.logger.Log(events.Event{
		EventID: uuid.NewString(),
		TaskID:  task.TaskId,
		Type:    eventType,
		AgentID: agent.AgentId,
		TraceID: task.Trace.TraceId,
	})

	return &pb.SubmitTaskResponse{Result: result}, nil
}

func errorResp(code pb.ErrorCode, msg string, retryable bool) *pb.SubmitTaskResponse {
	return &pb.SubmitTaskResponse{
		Error: &pb.ErrorInfo{Code: code, Message: msg, Retryable: retryable},
	}
}
