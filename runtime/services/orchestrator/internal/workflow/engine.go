package workflow

import (
	"context"

	"github.com/google/uuid"
	"google.golang.org/protobuf/proto"
	"google.golang.org/protobuf/types/known/timestamppb"

	pb "tg/runtime/gen/go/contract/v1"
	"tg/runtime/services/orchestrator/internal/events"
)

type TaskExecutor interface {
	Execute(context.Context, *pb.Task) (*pb.TaskResult, *pb.ErrorInfo)
}

type EventLogger interface {
	Log(events.Event)
}

type Engine struct {
	executor  TaskExecutor
	validator *Validator
	store     Store
	logger    EventLogger
}

func NewEngine(executor TaskExecutor, validator *Validator, store Store, logger EventLogger) *Engine {
	return &Engine{executor: executor, validator: validator, store: store, logger: logger}
}

func (e *Engine) Execute(ctx context.Context, root *pb.Task, definition *pb.WorkflowDefinition) (*pb.WorkflowResult, *pb.ErrorInfo) {
	if root == nil {
		return nil, workflowError(pb.ErrorCode_ERROR_CODE_INVALID_TASK, "root_task is required", false)
	}
	if err := e.validator.Validate(definition); err != nil {
		return nil, workflowError(pb.ErrorCode_ERROR_CODE_INVALID_TASK, err.Error(), false)
	}
	for _, step := range definition.Steps {
		if len(step.InputBindings) > 0 {
			return nil, workflowError(pb.ErrorCode_ERROR_CODE_INVALID_TASK, "input_bindings require workflow engine phase 12E.4", false)
		}
	}

	ensureRootIdentity(root)
	workflowID := definition.WorkflowId
	if workflowID == "" {
		workflowID = uuid.NewString()
	}
	runID := uuid.NewString()
	result := &pb.WorkflowResult{
		WorkflowId: workflowID,
		RunId:      runID,
		RootTaskId: root.TaskId,
		Status:     pb.WorkflowStatus_WORKFLOW_STATUS_CREATED,
		Trace:      proto.Clone(root.Trace).(*pb.TraceContext),
		CreatedAt:  timestamppb.Now(),
	}
	if err := e.store.Create(result); err != nil {
		return nil, workflowError(pb.ErrorCode_ERROR_CODE_EXECUTION_FAILED, err.Error(), true)
	}
	e.log(result, root.TaskId, "WORKFLOW_CREATED", "", "", 0)
	e.log(result, root.TaskId, "WORKFLOW_VALIDATED", "", "", 0)
	result.Status = pb.WorkflowStatus_WORKFLOW_STATUS_RUNNING
	e.log(result, root.TaskId, "WORKFLOW_STARTED", "", "", 0)

	ordered := topologicalOrder(definition)
	for index, step := range ordered {
		e.log(result, root.TaskId, "STEP_READY", step.StepId, "", 0)
		task := materializeTask(root, runID, step)
		e.log(result, task.TaskId, "STEP_STARTED", step.StepId, "", 0)
		taskResult, failure := e.executor.Execute(ctx, task)
		stepResult := &pb.WorkflowStepResult{StepId: step.StepId}
		if failure != nil {
			stepResult.Status = pb.WorkflowStepStatus_WORKFLOW_STEP_STATUS_FAILED
			stepResult.Result = failedTaskResult(task, failure)
		} else {
			stepResult.Result = taskResult
			if taskResult != nil && taskResult.Status == pb.TaskStatus_TASK_STATUS_COMPLETED {
				stepResult.Status = pb.WorkflowStepStatus_WORKFLOW_STEP_STATUS_COMPLETED
			} else {
				stepResult.Status = pb.WorkflowStepStatus_WORKFLOW_STEP_STATUS_FAILED
			}
		}
		result.StepResults = append(result.StepResults, stepResult)
		if err := e.store.SaveStep(runID, stepResult); err != nil {
			return nil, workflowError(pb.ErrorCode_ERROR_CODE_EXECUTION_FAILED, err.Error(), true)
		}

		if stepResult.Status == pb.WorkflowStepStatus_WORKFLOW_STEP_STATUS_FAILED {
			e.log(result, task.TaskId, "STEP_FAILED", step.StepId, stepResult.Result.AgentId, task.Attempt)
			for _, pending := range ordered[index+1:] {
				skipped := &pb.WorkflowStepResult{StepId: pending.StepId, Status: pb.WorkflowStepStatus_WORKFLOW_STEP_STATUS_SKIPPED}
				result.StepResults = append(result.StepResults, skipped)
				_ = e.store.SaveStep(runID, skipped)
				e.log(result, root.TaskId, "STEP_SKIPPED", pending.StepId, "", 0)
			}
			result.Status = pb.WorkflowStatus_WORKFLOW_STATUS_FAILED
			result.Error = stepResult.Result.Error
			if result.Error == nil {
				result.Error = workflowError(pb.ErrorCode_ERROR_CODE_EXECUTION_FAILED, "workflow step failed", false)
			}
			result.CompletedAt = timestamppb.Now()
			_ = e.store.Complete(runID, result)
			e.log(result, root.TaskId, "WORKFLOW_FAILED", step.StepId, stepResult.Result.AgentId, task.Attempt)
			return result, nil
		}
		e.log(result, task.TaskId, "STEP_COMPLETED", step.StepId, taskResult.AgentId, task.Attempt)
	}

	final := findStepResult(result.StepResults, definition.FinalStepId)
	if final == nil || final.Result == nil {
		return nil, workflowError(pb.ErrorCode_ERROR_CODE_EXECUTION_FAILED, "final step did not produce a result", false)
	}
	result.Status = pb.WorkflowStatus_WORKFLOW_STATUS_COMPLETED
	result.Output = final.Result.Output
	result.CompletedAt = timestamppb.Now()
	if err := e.store.Complete(runID, result); err != nil {
		return nil, workflowError(pb.ErrorCode_ERROR_CODE_EXECUTION_FAILED, err.Error(), true)
	}
	e.log(result, root.TaskId, "WORKFLOW_COMPLETED", definition.FinalStepId, final.Result.AgentId, 0)
	return result, nil
}

func ensureRootIdentity(root *pb.Task) {
	if root.TaskId == "" {
		root.TaskId = uuid.NewString()
	}
	if root.Trace == nil {
		root.Trace = &pb.TraceContext{}
	}
	if root.Trace.TraceId == "" {
		root.Trace.TraceId = uuid.NewString()
	}
}

func materializeTask(root *pb.Task, runID string, step *pb.WorkflowStep) *pb.Task {
	task := proto.Clone(step.TaskTemplate).(*pb.Task)
	task.TaskId = uuid.NewString()
	task.ParentTaskId = root.TaskId
	task.Status = pb.TaskStatus_TASK_STATUS_CREATED
	task.CreatedAt = timestamppb.Now()
	parentSpan := root.Trace.SpanId
	task.Trace = &pb.TraceContext{
		TraceId:       root.Trace.TraceId,
		SpanId:        uuid.NewString(),
		ParentSpanId:  parentSpan,
		CorrelationId: runID,
	}
	return task
}

func topologicalOrder(definition *pb.WorkflowDefinition) []*pb.WorkflowStep {
	completed := map[string]bool{}
	ordered := make([]*pb.WorkflowStep, 0, len(definition.Steps))
	for len(ordered) < len(definition.Steps) {
		for _, step := range definition.Steps {
			if completed[step.StepId] || !dependenciesCompleted(step, completed) {
				continue
			}
			ordered = append(ordered, step)
			completed[step.StepId] = true
		}
	}
	return ordered
}

func dependenciesCompleted(step *pb.WorkflowStep, completed map[string]bool) bool {
	for _, dependency := range step.DependsOn {
		if !completed[dependency] {
			return false
		}
	}
	return true
}

func findStepResult(results []*pb.WorkflowStepResult, stepID string) *pb.WorkflowStepResult {
	for _, result := range results {
		if result.StepId == stepID {
			return result
		}
	}
	return nil
}

func failedTaskResult(task *pb.Task, failure *pb.ErrorInfo) *pb.TaskResult {
	return &pb.TaskResult{
		TaskId:      task.TaskId,
		Status:      pb.TaskStatus_TASK_STATUS_FAILED,
		CompletedAt: timestamppb.Now(),
		Trace:       task.Trace,
		Error:       failure,
	}
}

func workflowError(code pb.ErrorCode, message string, retryable bool) *pb.ErrorInfo {
	return &pb.ErrorInfo{Code: code, Message: message, Retryable: retryable}
}

func (e *Engine) log(result *pb.WorkflowResult, taskID, eventType, stepID, agentID string, attempt int32) {
	if e.logger == nil {
		return
	}
	e.logger.Log(events.Event{
		EventID: uuid.NewString(), TaskID: taskID, Type: eventType,
		AgentID: agentID, TraceID: result.Trace.TraceId,
		WorkflowID: result.WorkflowId, RunID: result.RunId, StepID: stepID,
		Attempt: attempt,
	})
}
