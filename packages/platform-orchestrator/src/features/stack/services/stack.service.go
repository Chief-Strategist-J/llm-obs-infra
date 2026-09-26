/*
Package services implements stack lifecycle management (up, down, restart, status, logs) and endpoint reporting.

ALGORITHM BLUEPRINT:
1. StartStack:
   - Ensures workspace .env exists; copies from .env.example if missing.
   - Resolves profiles and selects compose files via rules.
   - Ensures docker bridge network 'llmobs-network' exists.
   - Prepares persistent data storage directories unless running in pure stateless profile.
   - Executes ComposeUp through ContainerPort and renders active endpoint URLs.
2. StopStack: Executes ComposeDown across all profiles.
3. RestartStack: Executes ComposeRestart.
4. GetStatus: Returns active container statuses.
5. PrintEndpoints: Inspects active profiles and prints database connection strings, dashboard URLs, and gateway endpoints.
6. Invariants:
   - Stateless profiles skip local persistent storage directory creation.
   - Zero inline comments inside function bodies.
*/
package services

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/features/stack/rules"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/features/stack/schema"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/shared/ports"
)

type StackService struct {
	containerPort ports.ContainerPort
	networkPort   ports.NetworkPort
	tracer        ports.TracerPort
	baseDir       string
}

func NewStackService(
	containerPort ports.ContainerPort,
	networkPort ports.NetworkPort,
	tracer ports.TracerPort,
	baseDir string,
) *StackService {
	return &StackService{
		containerPort: containerPort,
		networkPort:   networkPort,
		tracer:        tracer,
		baseDir:       baseDir,
	}
}

func (s *StackService) ensureEnvFile() error {
	envPath := filepath.Join(s.baseDir, ".env")
	if _, err := os.Stat(envPath); err == nil {
		return nil
	}

	examplePath := filepath.Join(s.baseDir, ".env.example")
	data, err := os.ReadFile(examplePath)
	if err != nil {
		return nil
	}
	return os.WriteFile(envPath, data, 0644)
}

func (s *StackService) ensureStorageDirectories(dataDir string) error {
	subdirs := []string{
		"alloydb/data",
		"alloydb/archive",
		"redis/data",
		"kafka/data",
		"clickhouse/data",
		"tempo/data",
		"grafana/data",
	}
	for _, sub := range subdirs {
		p := filepath.Join(dataDir, sub)
		if err := os.MkdirAll(p, 0777); err != nil {
			return fmt.Errorf("failed to create data dir %s: %w", p, err)
		}
		_ = os.Chmod(p, 0777)
	}
	return nil
}

func (s *StackService) getEnv(key string, fallback string) string {
	envPath := filepath.Join(s.baseDir, ".env")
	data, err := os.ReadFile(envPath)
	if err != nil {
		return fallback
	}
	lines := strings.Split(string(data), "\n")
	for _, l := range lines {
		if strings.HasPrefix(l, key+"=") {
			val := strings.TrimPrefix(l, key+"=")
			return strings.Trim(val, `"' `)
		}
	}
	return fallback
}

func (s *StackService) StartStack(ctx context.Context, cmd schema.StackUpCommand) (schema.StackActionOutcome, error) {
	_, endSpan := s.tracer.StartSpan(ctx, "llmobs.stack.up")
	defer endSpan()

	_ = s.ensureEnvFile()

	profiles := rules.ResolveProfiles(cmd.Profiles)
	composeFiles := rules.SelectComposeFiles(s.baseDir, profiles)

	if err := s.networkPort.EnsureNetwork(ctx, "llmobs-network", "172.28.0.0/16", "172.28.0.1"); err != nil {
		return schema.StackActionOutcome{}, fmt.Errorf("network initialization failed: %w", err)
	}

	isStateless := false
	for _, p := range profiles {
		if p == "stateless" || p == "compute" {
			isStateless = true
			break
		}
	}

	if !isStateless {
		dataDir := os.Getenv("LLMOBS_DATA_DIR")
		if dataDir == "" {
			dataDir = filepath.Join(s.baseDir, "data")
		}
		if err := s.ensureStorageDirectories(dataDir); err != nil {
			return schema.StackActionOutcome{}, fmt.Errorf("storage directory initialization failed: %w", err)
		}
	}

	opts := ports.ComposeOptions{
		ComposeFiles: composeFiles,
		Profiles:     profiles,
		EnvVars:      cmd.EnvVars,
		Detach:       cmd.Detach,
	}

	if err := s.containerPort.ComposeUp(ctx, opts); err != nil {
		return schema.StackActionOutcome{}, fmt.Errorf("compose up failed: %w", err)
	}

	s.PrintEndpoints(profiles)

	return schema.StackActionOutcome{
		Status:         "RUNNING",
		Message:        "Stack started successfully",
		ActiveServices: profiles,
	}, nil
}

func (s *StackService) StopStack(ctx context.Context) (schema.StackActionOutcome, error) {
	_, endSpan := s.tracer.StartSpan(ctx, "llmobs.stack.down")
	defer endSpan()

	composeFiles := []string{filepath.Join(s.baseDir, "docker-compose.yml")}
	opts := ports.ComposeOptions{
		ComposeFiles: composeFiles,
		Profiles:     []string{"*"},
	}

	if err := s.containerPort.ComposeDown(ctx, opts); err != nil {
		return schema.StackActionOutcome{}, fmt.Errorf("compose down failed: %w", err)
	}

	return schema.StackActionOutcome{
		Status:         "STOPPED",
		Message:        "All stack containers stopped",
		ActiveServices: []string{},
	}, nil
}

func (s *StackService) RestartStack(ctx context.Context, profiles []string) (schema.StackActionOutcome, error) {
	_, endSpan := s.tracer.StartSpan(ctx, "llmobs.stack.restart")
	defer endSpan()

	resolved := rules.ResolveProfiles(profiles)
	composeFiles := rules.SelectComposeFiles(s.baseDir, resolved)

	opts := ports.ComposeOptions{
		ComposeFiles: composeFiles,
		Profiles:     resolved,
	}

	if err := s.containerPort.ComposeRestart(ctx, opts); err != nil {
		return schema.StackActionOutcome{}, fmt.Errorf("compose restart failed: %w", err)
	}

	return schema.StackActionOutcome{
		Status:         "RESTARTED",
		Message:        "Stack restarted successfully",
		ActiveServices: resolved,
	}, nil
}

func (s *StackService) GetStatus(ctx context.Context) ([]ports.ContainerStatus, error) {
	_, endSpan := s.tracer.StartSpan(ctx, "llmobs.stack.status")
	defer endSpan()

	composeFiles := []string{filepath.Join(s.baseDir, "docker-compose.yml")}
	opts := ports.ComposeOptions{
		ComposeFiles: composeFiles,
		Profiles:     []string{"*"},
	}

	return s.containerPort.ComposeStatus(ctx, opts)
}

func (s *StackService) StreamLogs(ctx context.Context, tail int) error {
	composeFiles := []string{filepath.Join(s.baseDir, "docker-compose.yml")}
	opts := ports.ComposeOptions{
		ComposeFiles: composeFiles,
		Profiles:     []string{"*"},
	}
	return s.containerPort.ComposeLogs(ctx, opts, tail)
}

func (s *StackService) PrintEndpoints(profiles []string) {
	profMap := make(map[string]bool)
	isFull := false
	for _, p := range profiles {
		profMap[p] = true
		if p == "full" {
			isFull = true
		}
	}

	fmt.Println("\n=====================================================")
	fmt.Println("  Active Services & Configurations                   ")
	fmt.Println("=====================================================")

	if isFull || profMap["db"] || profMap["stateful"] {
		portAlloy := s.getEnv("PORT_ALLOYDB", "31420")
		dbUser := s.getEnv("ALLOYDB_USER", "admin")
		dbName := s.getEnv("ALLOYDB_DB", "llm_observability")
		fmt.Printf("  • AlloyDB (PostgreSQL): postgresql://%s:***@localhost:%s/%s\n", dbUser, portAlloy, dbName)

		portRedis := s.getEnv("PORT_REDIS", "31413")
		fmt.Printf("  • Redis Ledger:         redis://:***@localhost:%s/0\n", portRedis)
	}

	if isFull || profMap["analytics"] || profMap["stateful"] {
		pHttp := s.getEnv("PORT_CLICKHOUSE_HTTP", "31421")
		pNative := s.getEnv("PORT_CLICKHOUSE_NATIVE", "31422")
		fmt.Printf("  • ClickHouse Analytics: HTTP: http://localhost:%s | Native TCP: localhost:%s\n", pHttp, pNative)
	}

	if isFull || profMap["streaming"] || profMap["stateful"] {
		pKafka := s.getEnv("PORT_KAFKA", "31414")
		fmt.Printf("  • Kafka Broker:          localhost:%s\n", pKafka)
	}

	if isFull || profMap["workflows"] || profMap["stateless"] {
		pGrpc := s.getEnv("PORT_TEMPORAL_GRPC", "31424")
		pUI := s.getEnv("PORT_TEMPORAL_UI", "31425")
		fmt.Printf("  • Temporal gRPC Engine:  localhost:%s\n", pGrpc)
		fmt.Printf("  • Temporal Web UI:       http://localhost:%s\n", pUI)
	}

	if isFull || profMap["tracing"] || profMap["stateful"] || profMap["stateless"] {
		pGraf := s.getEnv("PORT_GRAFANA", "31415")
		fmt.Printf("  • Grafana Dashboard:     http://localhost:%s\n", pGraf)

		pOtelHttp := s.getEnv("PORT_OTEL_HTTP", "31417")
		pOtelGrpc := s.getEnv("PORT_OTEL_GRPC", "31418")
		fmt.Printf("  • OTel Collector:        HTTP: http://localhost:%s | gRPC: localhost:%s\n", pOtelHttp, pOtelGrpc)

		pTempo := s.getEnv("PORT_TEMPO", "31416")
		fmt.Printf("  • Grafana Tempo:         http://localhost:%s\n", pTempo)
	}

	if isFull || profMap["network"] || profMap["stateless"] {
		pTrHttp := s.getEnv("PORT_TRAEFIK_HTTP", "31410")
		pTrDash := s.getEnv("PORT_TRAEFIK_DASHBOARD", "31411")
		pTrHttps := s.getEnv("PORT_TRAEFIK_HTTPS", "31419")
		fmt.Printf("  • Traefik HTTP Gateway:  http://localhost:%s (→ HTTPS:%s)\n", pTrHttp, pTrHttps)
		fmt.Printf("  • Traefik Dashboard:     http://localhost:%s\n", pTrDash)

		pReg := s.getEnv("PORT_SERVICE_REGISTRY", "31426")
		fmt.Printf("  • Service Registry API:  http://localhost:%s\n", pReg)
	}

	fmt.Println("=====================================================")
}
