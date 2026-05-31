package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gaokao-agent/matrix-mother/internal/agentregistry"
	"github.com/gaokao-agent/matrix-mother/internal/capabilityissuer"
	"github.com/gaokao-agent/matrix-mother/internal/revocationservice"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	store := agentregistry.NewMemoryStore()
	registry := agentregistry.NewService(store)
	issuer := capabilityissuer.NewService(store)
	revoker := revocationservice.NewService(store)

	mux := http.NewServeMux()

	registry.RegisterRoutes(mux)
	issuer.RegisterRoutes(mux)
	revoker.RegisterRoutes(mux)

	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"ok"}`))
	})

	addr := os.Getenv("MATRIX_MOTHER_ADDR")
	if addr == "" {
		addr = ":18080"
	}

	srv := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	errCh := make(chan error, 1)
	go func() {
		log.Printf("Matrix Mother Agent starting on %s", addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errCh <- err
		}
	}()

	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)

	select {
	case err := <-errCh:
		log.Fatalf("server error: %v", err)
	case sig := <-sigCh:
		log.Printf("received signal %v, shutting down", sig)
		cancel()
		shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer shutdownCancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			log.Fatalf("shutdown error: %v", err)
		}
	}
}
