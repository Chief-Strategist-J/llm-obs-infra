/*
Package services implements stack lifecycle management (up, down, restart, status, logs).

ALGORITHM BLUEPRINT:
1. StartStack:
   - Resolves profiles and selects compose files via rules.
   - Ensures docker bridge network 'llmobs-network' exists.
   - Prepares persistent data storage directories unless running in pure stateless profile.
   - Executes ComposeUp through ContainerPort.
2. StopStack: Executes ComposeDown across all profiles.
3. RestartStack: Executes ComposeRestart.
4. GetStatus: Returns active container statuses.
5. Invariants:
   - Stateless profiles must skip local persistent storage directory creation.
   - Operations must emit OpenTelemetry spans with W3C trace context.
*/
package services

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

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
	}
	return nil
}

func (s *StackService) StartStack(ctx context.Context, cmd schema.StackUpCommand) (schema.StackActionOutcome, error) {
	_, endSpan := s.tracer.StartSpan(ctx, "llmobs.stack.up")
	defer endSpan()

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
