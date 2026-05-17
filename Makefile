# Makefile — TG Runtime
# Rode qualquer target com: make <target>
# Exemplo: make proto

# Adiciona GOPATH/bin ao PATH para que o protoc encontre os plugins Go
export PATH := $(PATH):$(shell go env GOPATH)/bin

# Diretorios
PROTO_DIR      := proto
GO_OUT_DIR     := runtime/gen/go
PYTHON_OUT_DIR := sdk/python/src
PROTO_INCLUDES := $(shell brew --prefix protobuf)/include

PROTO_FILES    := $(shell find $(PROTO_DIR) -name "*.proto")

# check-env — verifica se todas as ferramentas estao prontas

.PHONY: check-env
check-env:
	@echo "Verificando ferramentas..."
	@which go > /dev/null 2>&1 || (echo "ERRO: go nao encontrado" && exit 1)
	@which protoc > /dev/null 2>&1 || (echo "ERRO: protoc nao encontrado" && exit 1)
	@which protoc-gen-go > /dev/null 2>&1 || (echo "ERRO: protoc-gen-go nao encontrado. Rode: go install google.golang.org/protobuf/cmd/protoc-gen-go@latest" && exit 1)
	@which protoc-gen-go-grpc > /dev/null 2>&1 || (echo "ERRO: protoc-gen-go-grpc nao encontrado. Rode: go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest" && exit 1)
	@which uv > /dev/null 2>&1 || (echo "ERRO: uv nao encontrado. Rode: brew install uv" && exit 1)
	@which docker > /dev/null 2>&1 || (echo "ERRO: docker nao encontrado" && exit 1)
	@echo "Tudo ok."

# proto — gera stubs Go e Python a partir dos .proto

.PHONY: proto
proto: check-env
	@echo "Criando diretorios de saida..."
	@mkdir -p $(GO_OUT_DIR)
	@mkdir -p $(PYTHON_OUT_DIR)
	@echo "Gerando stubs Go..."
	protoc \
		--proto_path=$(PROTO_DIR) \
		--proto_path=$(PROTO_INCLUDES) \
		--go_out=$(GO_OUT_DIR) \
		--go_opt=paths=source_relative \
		--go-grpc_out=$(GO_OUT_DIR) \
		--go-grpc_opt=paths=source_relative \
		$(PROTO_FILES)
	@echo "Gerando stubs Python..."
	uv run --directory sdk/python python3 -m grpc_tools.protoc \
		--proto_path=$(CURDIR)/$(PROTO_DIR) \
		--python_out=$(CURDIR)/$(PYTHON_OUT_DIR) \
		--grpc_python_out=$(CURDIR)/$(PYTHON_OUT_DIR) \
		$(CURDIR)/$(PROTO_FILES)
	@echo "Proto gerado com sucesso."

# build — compila os servicos Go

.PHONY: build
build:
	@echo "Compilando servicos Go..."
	cd runtime && go build ./...

# test — roda os testes Go

.PHONY: test
test:
	cd runtime && go test ./...

# up / down / logs — Docker Compose

.PHONY: up
up:
	docker compose -f infra/docker-compose.yml up --build -d

.PHONY: down
down:
	docker compose -f infra/docker-compose.yml down

.PHONY: logs
logs:
	docker compose -f infra/docker-compose.yml logs -f

# help — lista todos os targets

.PHONY: help
help:
	@echo ""
	@echo "Targets disponiveis:"
	@echo "  make check-env   Verifica se todas as ferramentas estao instaladas"
	@echo "  make proto       Gera stubs Go e Python a partir dos .proto"
	@echo "  make build       Compila os servicos Go"
	@echo "  make test        Roda os testes Go"
	@echo "  make up          Sobe o sistema via Docker Compose"
	@echo "  make down        Para e remove os conteineres"
	@echo "  make logs        Mostra logs de todos os servicos"
	@echo ""
