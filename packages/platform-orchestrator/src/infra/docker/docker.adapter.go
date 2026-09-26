/*
Package docker provides the concrete infrastructure adapter for Docker Engine and Docker Compose.

ALGORITHM BLUEPRINT:
1. Binary Resolution: Resolves 'docker compose' (Compose V2 plugin) or falls back to legacy 'docker-compose'.
2. Execution Flow: Formats Compose arguments (-f files, --profile flags, -p project), sets execution environment variables, and executes via os/exec.
3. Network Provisioning: Idempotently inspects Docker bridge networks; creates the isolated 'llmobs-network' with security signatures if missing.
4. Port Contention Detection: Tests socket listenability via net.Listen; terminates stale processes holding locked ports via OS signals.
5. Invariants:
   - Output from docker commands is streamed and surfaced with descriptive error wrapping.
   - Child process execution adheres strictly to passed context timeouts and cancellation signals.
*/
package docker

import (
	"bytes"
	"context"
	"fmt"
	"net"
	"os"
	"os/exec"
	"strconv"
	"strings"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/shared/ports"
)

type DockerAdapter struct {
	baseWorkDir string
}

func NewDockerAdapter(baseWorkDir string) *DockerAdapter {
	return &DockerAdapter{
		baseWorkDir: baseWorkDir,
	}
}

func (d *DockerAdapter) resolveComposeCmd() ([]string, error) {
	if _, err := exec.LookPath("docker"); err == nil {
		check := exec.Command("docker", "compose", "version")
		if err := check.Run(); err == nil {
			return []string{"docker", "compose"}, nil
		}
	}
	if p, err := exec.LookPath("docker-compose"); err == nil {
		return []string{p}, nil
	}
	return nil, fmt.Errorf("neither 'docker compose' nor 'docker-compose' binary found in PATH")
}

func (d *DockerAdapter) buildArgs(opts ports.ComposeOptions, subcmd string, extra ...string) []string {
	var args []string
	if opts.ProjectName != "" {
		args = append(args, "-p", opts.ProjectName)
	}
	for _, f := range opts.ComposeFiles {
		args = append(args, "-f", f)
	}
	for _, p := range opts.Profiles {
		args = append(args, "--profile", p)
	}
	args = append(args, subcmd)
	args = append(args, extra...)
	args = append(args, opts.Services...)
	return args
}

func (d *DockerAdapter) runCompose(ctx context.Context, opts ports.ComposeOptions, subcmd string, extra ...string) ([]byte, error) {
	cmdPrefix, err := d.resolveComposeCmd()
	if err != nil {
		return nil, err
	}

	args := d.buildArgs(opts, subcmd, extra...)
	fullArgs := append(cmdPrefix[1:], args...)

	cmd := exec.CommandContext(ctx, cmdPrefix[0], fullArgs...)
	cmd.Dir = d.baseWorkDir

	cmd.Env = os.Environ()
	for k, v := range opts.EnvVars {
		cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
	}

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	runErr := cmd.Run()
	if runErr != nil {
		return stdout.Bytes(), fmt.Errorf("docker compose %s failed: %w (stderr: %s)", subcmd, runErr, strings.TrimSpace(stderr.String()))
	}

	return stdout.Bytes(), nil
}

func (d *DockerAdapter) ComposeUp(ctx context.Context, opts ports.ComposeOptions) error {
	extra := []string{}
	if opts.Detach {
		extra = append(extra, "-d")
	}
	_, err := d.runCompose(ctx, opts, "up", extra...)
	return err
}

func (d *DockerAdapter) ComposeDown(ctx context.Context, opts ports.ComposeOptions) error {
	_, err := d.runCompose(ctx, opts, "down")
	return err
}

func (d *DockerAdapter) ComposeRestart(ctx context.Context, opts ports.ComposeOptions) error {
	_, err := d.runCompose(ctx, opts, "restart")
	return err
}

func (d *DockerAdapter) ComposeScale(ctx context.Context, opts ports.ComposeOptions, service string, replicas int) error {
	scaleArg := fmt.Sprintf("%s=%d", service, replicas)
	extra := []string{"-d", "--scale", scaleArg, "--no-recreate"}
	_, err := d.runCompose(ctx, opts, "up", extra...)
	return err
}

func (d *DockerAdapter) ComposeStatus(ctx context.Context, opts ports.ComposeOptions) ([]ports.ContainerStatus, error) {
	out, err := d.runCompose(ctx, opts, "ps", "--format", "{{.Name}}|{{.Service}}|{{.Status}}|{{.Ports}}")
	if err != nil {
		return nil, err
	}

	var results []ports.ContainerStatus
	lines := strings.Split(strings.TrimSpace(string(out)), "\n")
	for _, line := range lines {
		if strings.TrimSpace(line) == "" {
			continue
		}
		parts := strings.Split(line, "|")
		status := ports.ContainerStatus{}
		if len(parts) > 0 {
			status.Name = parts[0]
		}
		if len(parts) > 1 {
			status.Service = parts[1]
		}
		if len(parts) > 2 {
			status.Status = parts[2]
		}
		if len(parts) > 3 {
			status.Ports = parts[3]
		}
		results = append(results, status)
	}

	return results, nil
}

func (d *DockerAdapter) ComposeLogs(ctx context.Context, opts ports.ComposeOptions, tail int) error {
	extra := []string{"--tail", strconv.Itoa(tail)}
	cmdPrefix, err := d.resolveComposeCmd()
	if err != nil {
		return err
	}

	args := d.buildArgs(opts, "logs", extra...)
	fullArgs := append(cmdPrefix[1:], args...)

	cmd := exec.CommandContext(ctx, cmdPrefix[0], fullArgs...)
	cmd.Dir = d.baseWorkDir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	return cmd.Run()
}

func (d *DockerAdapter) EnsureNetwork(ctx context.Context, networkName string, subnet string, gateway string) error {
	inspectCmd := exec.CommandContext(ctx, "docker", "network", "inspect", networkName)
	if err := inspectCmd.Run(); err == nil {
		return nil
	}

	createCmd := exec.CommandContext(ctx, "docker", "network", "create",
		"--driver", "bridge",
		"--subnet", subnet,
		"--gateway", gateway,
		"--label", "com.llmobs.network.signature=llmobs-net-sig-v1.0",
		"--label", "com.llmobs.network.managed-by=llmobs-platform-orchestrator",
		networkName,
	)
	var stderr bytes.Buffer
	createCmd.Stderr = &stderr

	if err := createCmd.Run(); err != nil {
		return fmt.Errorf("failed to create docker network '%s': %w (%s)", networkName, err, strings.TrimSpace(stderr.String()))
	}
	return nil
}

func (d *DockerAdapter) IsPortAvailable(port int) bool {
	addr := fmt.Sprintf("0.0.0.0:%d", port)
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return false
	}
	ln.Close()
	return true
}

func (d *DockerAdapter) FreePort(ctx context.Context, port int) error {
	if d.IsPortAvailable(port) {
		return nil
	}
	cmd := exec.CommandContext(ctx, "fuser", "-k", fmt.Sprintf("%d/tcp", port))
	_ = cmd.Run()
	return nil
}
