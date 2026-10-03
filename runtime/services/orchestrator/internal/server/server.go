package server

import (
	"context"
	"log/slog"
	"time"

	"github.com/google/uuid"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"

	pb "tg/runtime/gen/go/contract/v1"
	"tg/runtime/services/orchestrator/internal/events"
	"tg/runtime/services/orchestrator/internal/execution"
)

type OrchestratorServer struct {
	pb.UnimplementedOrchestratorServiceServer
	logger   *events.Logger
	executor *execution.Executor
}

func New(registryAddr string, logger *events.Logger, timeout ...time.Duration) *OrchestratorServer {
	defaultTimeout := 30 * time.Second
	if len(timeout) > 0 {
		defaultTimeout = timeout[0]
	}
	return &OrchestratorServer{
		logger: logger,
		executor: execution.New(
			execution.GRPCDiscoverer{RegistryAddr: registryAddr},
			execution.GRPCRunner{},
			logger,
			defaultTimeout,
		),
	}
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

	result, failure := srv.executor.Execute(ctx, task)
	if failure != nil {
		slog.Warn("task execution failed", "task_id", task.TaskId, "code", failure.Code, "error", failure.Message)
		return &pb.SubmitTaskResponse{Error: failure}, nil
	}

	slog.Info("task finished", "task_id", task.TaskId, "agent_id", result.AgentId, "status", result.Status, "attempt", task.Attempt)
	return &pb.SubmitTaskResponse{Result: result}, nil
}
