FROM golang:1.26-alpine AS builder
WORKDIR /build
COPY runtime/ ./runtime/
WORKDIR /build/runtime
RUN go mod download
RUN go build -o /orchestrator ./services/orchestrator/cmd/

FROM alpine:latest
COPY --from=builder /orchestrator /orchestrator
ENTRYPOINT ["/orchestrator"]
