package workflow

import (
	"context"
	"testing"

	"google.golang.org/protobuf/types/known/structpb"

	pb "tg/runtime/gen/go/contract/v1"
	"tg/runtime/services/orchestrator/internal/events"
)

type engineExecutor struct {
	calls  []*pb.Task
	failAt string
}

func (e *engineExecutor) Execute(_ context.Context, task *pb.Task) (*pb.TaskResult, *pb.ErrorInfo) {
	e.calls = append(e.calls, task)
	if task.Goal == e.failAt {
		failure := &pb.ErrorInfo{Code: pb.ErrorCode_ERROR_CODE_EXECUTION_FAILED, Message: "step failed"}
		return &pb.TaskResult{
			TaskId: task.TaskId, AgentId: "agent-fail",
			Status: pb.TaskStatus_TASK_STATUS_FAILED, Trace: task.Trace, Error: failure,
		}, nil
	}
	output, _ := structpb.NewStruct(map[string]any{"step": task.Goal})
	return &pb.TaskResult{
		TaskId: task.TaskId, AgentId: "agent-" + task.Goal,
		Status: pb.TaskStatus_TASK_STATUS_COMPLETED, Trace: task.Trace, Output: output,
	}, nil
}

type engineLogger struct{ events []events.Event }

func (l *engineLogger) Log(event events.Event) { l.events = append(l.events, event) }

func sequentialDefinition() *pb.WorkflowDefinition {
	first := step("first", "echo")
	second := step("second", "echo")
	second.DependsOn = []string{"first"}
	// Ordem reversa prova que o engine respeita dependências, não a posição.
	return &pb.WorkflowDefinition{
		WorkflowId:  "workflow-1",
		Steps:       []*pb.WorkflowStep{second, first},
		FinalStepId: "second",
	}
}

func TestEngineExecutesSequentialWorkflowAndAggregatesFinalOutput(t *testing.T) {
	executor := &engineExecutor{}
	store := NewInMemoryStore()
	logger := &engineLogger{}
	engine := NewEngine(executor, NewValidator(DefaultValidationLimits()), store, logger)
	root := &pb.Task{TaskId: "root-1", Trace: &pb.TraceContext{TraceId: "trace-1", SpanId: "root-span"}}

	result, failure := engine.Execute(context.Background(), root, sequentialDefinition())

	if failure != nil {
		t.Fatalf("failure = %v", failure)
	}
	if result.Status != pb.WorkflowStatus_WORKFLOW_STATUS_COMPLETED {
		t.Fatalf("status = %v", result.Status)
	}
	if len(executor.calls) != 2 || executor.calls[0].Goal != "first" || executor.calls[1].Goal != "second" {
		t.Fatalf("execution order = %#v", executor.calls)
	}
	for _, task := range executor.calls {
		if task.ParentTaskId != "root-1" || task.Trace.TraceId != "trace-1" || task.Trace.ParentSpanId != "root-span" || task.Trace.CorrelationId != result.RunId {
			t.Fatalf("materialized task correlation = %+v", task)
		}
	}
	if result.Output.Fields["step"].GetStringValue() != "second" {
		t.Fatalf("output = %v", result.Output)
	}
	stored, err := store.Get(result.RunId)
	if err != nil || stored.Status != pb.WorkflowStatus_WORKFLOW_STATUS_COMPLETED || len(stored.StepResults) != 2 {
		t.Fatalf("stored = %v err=%v", stored, err)
	}
	if logger.events[0].Type != "WORKFLOW_CREATED" || logger.events[len(logger.events)-1].Type != "WORKFLOW_COMPLETED" {
		t.Fatalf("events = %#v", logger.events)
	}
}

func TestEngineStopsOnFailureAndSkipsDependents(t *testing.T) {
	executor := &engineExecutor{failAt: "first"}
	engine := NewEngine(executor, NewValidator(DefaultValidationLimits()), NewInMemoryStore(), nil)

	result, failure := engine.Execute(context.Background(), &pb.Task{}, sequentialDefinition())

	if failure != nil {
		t.Fatalf("operational failure = %v", failure)
	}
	if result.Status != pb.WorkflowStatus_WORKFLOW_STATUS_FAILED {
		t.Fatalf("status = %v", result.Status)
	}
	if len(executor.calls) != 1 {
		t.Fatalf("executor calls = %d", len(executor.calls))
	}
	if len(result.StepResults) != 2 || result.StepResults[1].Status != pb.WorkflowStepStatus_WORKFLOW_STEP_STATUS_SKIPPED {
		t.Fatalf("step results = %v", result.StepResults)
	}
}

func TestEngineRejectsBindingsUntilPhase12E4(t *testing.T) {
	definition := validWorkflow()
	engine := NewEngine(&engineExecutor{}, NewValidator(DefaultValidationLimits()), NewInMemoryStore(), nil)

	result, failure := engine.Execute(context.Background(), &pb.Task{}, definition)

	if result != nil || failure == nil || failure.Code != pb.ErrorCode_ERROR_CODE_INVALID_TASK {
		t.Fatalf("result=%v failure=%v", result, failure)
	}
}
