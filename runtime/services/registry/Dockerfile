FROM golang:1.26-alpine AS builder
WORKDIR /build
COPY runtime/ ./runtime/
WORKDIR /build/runtime
RUN go mod download
RUN go build -o /registry ./services/registry/cmd/

FROM alpine:latest
COPY --from=builder /registry /registry
ENTRYPOINT ["/registry"]
