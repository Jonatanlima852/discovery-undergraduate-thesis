package server

import (
	"context"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"

	pb "tg/runtime/gen/go/contract/v1"
	"tg/runtime/services/orchestrator/internal/workflow"
)

type workflowTaskExecutor struct{}

func (workflowTaskExecutor) Execute(_ context.Context, task *pb.Task) (*pb.TaskResult, *pb.ErrorInfo) {
	output, _ := structpb.NewStruct(map[string]any{"goal": task.Goal})
	return &pb.TaskResult{
		TaskId: task.TaskId, AgentId: "fake-agent",
		Status: pb.TaskStatus_TASK_STATUS_COMPLETED, Trace: task.Trace, Output: output,
	}, nil
}

func TestSubmitWorkflowExecutesExplicitWorkflow(t *testing.T) {
	engine := workflow.NewEngine(
		workflowTaskExecutor{},
		workflow.NewValidator(workflow.DefaultValidationLimits()),
		workflow.NewInMemoryStore(),
		nil,
	)
	server := &OrchestratorServer{workflow: engine}
	request := &pb.SubmitWorkflowRequest{
		RootTask: &pb.Task{TaskId: "root", Trace: &pb.TraceContext{TraceId: "trace"}},
		Workflow: &pb.WorkflowDefinition{
			WorkflowId: "test-workflow", FinalStepId: "only",
			Steps: []*pb.WorkflowStep{{
				StepId:       "only",
				TaskTemplate: &pb.Task{Goal: "execute", RequiredCapabilities: []string{"echo"}},
			}},
		},
	}

	response, err := server.SubmitWorkflow(context.Background(), request)

	if err != nil {
		t.Fatal(err)
	}
	if response.Result == nil || response.Result.Status != pb.WorkflowStatus_WORKFLOW_STATUS_COMPLETED {
		t.Fatalf("response = %v", response)
	}
	if response.Result.Output.Fields["goal"].GetStringValue() != "execute" {
		t.Fatalf("output = %v", response.Result.Output)
	}
}

func TestSubmitWorkflowReturnsValidationError(t *testing.T) {
	server := &OrchestratorServer{workflow: workflow.NewEngine(
		workflowTaskExecutor{}, workflow.NewValidator(workflow.DefaultValidationLimits()), workflow.NewInMemoryStore(), nil,
	)}

	response, err := server.SubmitWorkflow(context.Background(), &pb.SubmitWorkflowRequest{
		RootTask: &pb.Task{}, Workflow: &pb.WorkflowDefinition{},
	})

	if err != nil {
		t.Fatal(err)
	}
	if response.Error == nil || response.Error.Code != pb.ErrorCode_ERROR_CODE_INVALID_TASK {
		t.Fatalf("response = %v", response)
	}
}
