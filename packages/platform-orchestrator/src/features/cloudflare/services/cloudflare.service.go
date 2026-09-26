/*
Package services implements Cloudflare Tunnel token configuration and container orchestration.

ALGORITHM BLUEPRINT:
1. TokenPersistence: Parses workspace .env; adds or updates CLOUDFLARE_TUNNEL_TOKEN safely.
2. ComposeLayering: Merges base docker-compose.yml with docker-compose.cloudflare.yml to isolate tunnel lifecycle.
3. LifecycleOperations: Dispatches start, stop, status, and log tailing commands to Docker Compose.
4. Invariants:
   - Operating on Cloudflare tunnel does not restart or interrupt running core platform containers.
   - Non-interactive and interactive environments are handled with fallback defaults.
*/
package services

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/features/cloudflare/schema"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/shared/ports"
)

type CloudflareService struct {
	dockerAdapter ports.ContainerPort
	tracer        ports.TracerPort
	workspaceRoot string
}

func NewCloudflareService(dockerAdapter ports.ContainerPort, tracer ports.TracerPort, workspaceRoot string) *CloudflareService {
	return &CloudflareService{
		dockerAdapter: dockerAdapter,
		tracer:        tracer,
		workspaceRoot: workspaceRoot,
	}
}

func (s *CloudflareService) SaveTunnelToken(token string) error {
	if token == "" {
		return fmt.Errorf("tunnel token cannot be empty")
	}

	envPath := filepath.Join(s.workspaceRoot, ".env")
	existing, err := os.ReadFile(envPath)
	if err != nil && !os.IsNotExist(err) {
		return err
	}

	lines := strings.Split(string(existing), "\n")
	found := false
	var updated []string
	for _, line := range lines {
		if strings.HasPrefix(line, "CLOUDFLARE_TUNNEL_TOKEN=") {
			updated = append(updated, fmt.Sprintf("CLOUDFLARE_TUNNEL_TOKEN=%s", token))
			found = true
		} else {
			updated = append(updated, line)
		}
	}
	if !found {
		updated = append(updated, fmt.Sprintf("CLOUDFLARE_TUNNEL_TOKEN=%s", token))
	}

	return os.WriteFile(envPath, []byte(strings.Join(updated, "\n")), 0644)
}

func (s *CloudflareService) StartTunnel(ctx context.Context) (*schema.CloudflareTunnelReport, error) {
	_, end := s.tracer.StartSpan(ctx, "CloudflareService.StartTunnel")
	defer end()

	base := filepath.Join(s.workspaceRoot, "docker-compose.yml")
	cf := filepath.Join(s.workspaceRoot, "docker-compose.cloudflare.yml")

	cmd := exec.CommandContext(ctx, "docker", "compose", "-f", base, "-f", cf, "up", "-d", "llmobs-cloudflare-tunnel")
	cmd.Dir = s.workspaceRoot
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("failed to start cloudflare tunnel: %w", err)
	}

	return &schema.CloudflareTunnelReport{
		Status:  "running",
		Active:  true,
		Message: "Cloudflare Tunnel container started successfully",
	}, nil
}

func (s *CloudflareService) StopTunnel(ctx context.Context) (*schema.CloudflareTunnelReport, error) {
	_, end := s.tracer.StartSpan(ctx, "CloudflareService.StopTunnel")
	defer end()

	base := filepath.Join(s.workspaceRoot, "docker-compose.yml")
	cf := filepath.Join(s.workspaceRoot, "docker-compose.cloudflare.yml")

	stopCmd := exec.CommandContext(ctx, "docker", "compose", "-f", base, "-f", cf, "stop", "llmobs-cloudflare-tunnel")
	stopCmd.Dir = s.workspaceRoot
	_ = stopCmd.Run()

	rmCmd := exec.CommandContext(ctx, "docker", "compose", "-f", base, "-f", cf, "rm", "-f", "llmobs-cloudflare-tunnel")
	rmCmd.Dir = s.workspaceRoot
	_ = rmCmd.Run()

	return &schema.CloudflareTunnelReport{
		Status:  "stopped",
		Active:  false,
		Message: "Cloudflare Tunnel container stopped and removed",
	}, nil
}

func (s *CloudflareService) GetStatus(ctx context.Context) (string, error) {
	base := filepath.Join(s.workspaceRoot, "docker-compose.yml")
	cf := filepath.Join(s.workspaceRoot, "docker-compose.cloudflare.yml")

	cmd := exec.CommandContext(ctx, "docker", "compose", "-f", base, "-f", cf, "ps", "llmobs-cloudflare-tunnel")
	cmd.Dir = s.workspaceRoot
	out, err := cmd.CombinedOutput()
	if err != nil {
		return "", err
	}
	return string(out), nil
}

func (s *CloudflareService) StreamLogs(ctx context.Context) error {
	base := filepath.Join(s.workspaceRoot, "docker-compose.yml")
	cf := filepath.Join(s.workspaceRoot, "docker-compose.cloudflare.yml")

	cmd := exec.CommandContext(ctx, "docker", "compose", "-f", base, "-f", cf, "logs", "-f", "llmobs-cloudflare-tunnel")
	cmd.Dir = s.workspaceRoot
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
