package events

import (
	"encoding/json"
	"log/slog"
	"os"
	"sync"
	"time"
)

// Event é a estrutura gravada em cada linha do JSONL.
type Event struct {
	EventID    string `json:"event_id"`
	TaskID     string `json:"task_id,omitempty"`
	Type       string `json:"type"`
	Timestamp  string `json:"timestamp"`
	AgentID    string `json:"agent_id,omitempty"`
	TraceID    string `json:"trace_id,omitempty"`
	WorkflowID string `json:"workflow_id,omitempty"`
	RunID      string `json:"run_id,omitempty"`
	StepID     string `json:"step_id,omitempty"`
	Attempt    int32  `json:"attempt,omitempty"`
	Details    string `json:"details,omitempty"`
}

// Logger grava eventos em um arquivo JSONL com append thread-safe.
type Logger struct {
	mu   sync.Mutex
	file *os.File
}

func NewLogger(path string) (*Logger, error) {
	if err := os.MkdirAll(filepath(path), 0755); err != nil {
		return nil, err
	}
	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return nil, err
	}
	return &Logger{file: f}, nil
}

func (l *Logger) Log(e Event) {
	e.Timestamp = time.Now().UTC().Format(time.RFC3339Nano)
	l.mu.Lock()
	defer l.mu.Unlock()

	line, err := json.Marshal(e)
	if err != nil {
		slog.Error("failed to marshal event", "err", err)
		return
	}
	l.file.Write(append(line, '\n'))
}

func (l *Logger) Close() {
	l.file.Close()
}

// filepath retorna o diretório de um caminho de arquivo.
func filepath(path string) string {
	for i := len(path) - 1; i >= 0; i-- {
		if path[i] == '/' {
			return path[:i]
		}
	}
	return "."
}
