package main

import (
	"log/slog"
	"net"
	"os"

	pb "tg/runtime/gen/go/contract/v1"
	"tg/runtime/services/registry/internal/server"
	"tg/runtime/services/registry/internal/store"
	"google.golang.org/grpc"
)

func main() {
	addr := os.Getenv("REGISTRY_ADDR")
	if addr == "" {
		addr = ":50051"
	}

	lis, err := net.Listen("tcp", addr)
	if err != nil {
		slog.Error("failed to listen", "addr", addr, "err", err)
		os.Exit(1)
	}

	grpcServer := grpc.NewServer()
	pb.RegisterRegistryServiceServer(grpcServer, server.New(store.New()))

	slog.Info("registry service started", "addr", addr)
	if err := grpcServer.Serve(lis); err != nil {
		slog.Error("server stopped", "err", err)
		os.Exit(1)
	}
}
