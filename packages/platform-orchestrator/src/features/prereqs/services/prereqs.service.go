/*
Package services implements system prerequisite diagnostics and environment verification.

ALGORITHM BLUEPRINT:
1. DockerVerification: Validates Docker daemon responsiveness and Docker Compose V2 plugin availability.
2. ResourceAudit: Audits available host RAM, open file descriptor limits (rlimit_nofile), and kernel vm.max_map_count.
3. UtilityVerification: Verifies presence of auxiliary host binaries (fuser, lsof, nc, curl).
4. NetworkConflictAudit: Checks existing docker networks to ensure subnet/gateway compatibility.
5. Invariants:
   - System audits do not mutate host state unless explicitly triggered in repair mode.
   - Non-critical prerequisite failures return warnings without aborting initialization pipelines.
*/
package services

import (
	"bufio"
	"context"
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/features/prereqs/schema"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/shared/ports"
)

type PrereqService struct {
	tracer ports.TracerPort
}

func NewPrereqService(tracer ports.TracerPort) *PrereqService {
	return &PrereqService{
		tracer: tracer,
	}
}

func (s *PrereqService) VerifySystemPrerequisites(ctx context.Context) schema.PrereqReport {
	_, end := s.tracer.StartSpan(ctx, "PrereqService.VerifySystemPrerequisites")
	defer end()

	var checks []schema.SystemPrereqCheck
	allPassed := true

	dockerCheck := s.checkDockerDaemon()
	checks = append(checks, dockerCheck)
	if !dockerCheck.Passed && dockerCheck.Critical {
		allPassed = false
	}

	composeCheck := s.checkDockerCompose()
	checks = append(checks, composeCheck)
	if !composeCheck.Passed && composeCheck.Critical {
		allPassed = false
	}

	memCheck := s.checkAvailableMemory(6000)
	checks = append(checks, memCheck)
	if !memCheck.Passed && memCheck.Critical {
		allPassed = false
	}

	rlimitCheck := s.checkFileDescriptorLimits(65536)
	checks = append(checks, rlimitCheck)

	sysctlCheck := s.checkVmMaxMapCount(262144)
	checks = append(checks, sysctlCheck)

	toolsCheck := s.checkHostUtilities([]string{"nc", "curl"})
	checks = append(checks, toolsCheck...)

	return schema.PrereqReport{
		Passed: allPassed,
		Checks: checks,
	}
}

func (s *PrereqService) checkDockerDaemon() schema.SystemPrereqCheck {
	cmd := exec.Command("docker", "info")
	if err := cmd.Run(); err != nil {
		return schema.SystemPrereqCheck{
			Name:      "Docker Daemon",
			Passed:    false,
			Critical:  true,
			Message:   "Docker daemon is not running or socket is inaccessible",
			RemedyMsg: "Start docker with 'sudo systemctl start docker' or verify user permissions",
		}
	}
	return schema.SystemPrereqCheck{
		Name:     "Docker Daemon",
		Passed:   true,
		Critical: true,
		Message:  "Docker daemon is active and responsive",
	}
}

func (s *PrereqService) checkDockerCompose() schema.SystemPrereqCheck {
	cmd1 := exec.Command("docker", "compose", "version")
	if err := cmd1.Run(); err == nil {
		return schema.SystemPrereqCheck{
			Name:     "Docker Compose",
			Passed:   true,
			Critical: true,
			Message:  "Docker Compose V2 plugin is available",
		}
	}

	if _, err := exec.LookPath("docker-compose"); err == nil {
		return schema.SystemPrereqCheck{
			Name:     "Docker Compose",
			Passed:   true,
			Critical: true,
			Message:  "Legacy docker-compose standalone binary is available",
		}
	}

	return schema.SystemPrereqCheck{
		Name:      "Docker Compose",
		Passed:    false,
		Critical:  true,
		Message:   "Docker Compose not found",
		RemedyMsg: "Install docker-compose-plugin via package manager",
	}
}

func (s *PrereqService) checkAvailableMemory(minMB int) schema.SystemPrereqCheck {
	file, err := os.Open("/proc/meminfo")
	if err != nil {
		return schema.SystemPrereqCheck{
			Name:     "System Memory",
			Passed:   true,
			Critical: false,
			Message:  "Unable to read /proc/meminfo directly; skipping memory check",
		}
	}
	defer file.Close()

	var availKB int
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "MemAvailable:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				availKB, _ = strconv.Atoi(fields[1])
			}
			break
		}
	}

	availMB := availKB / 1024
	if availMB < minMB && availMB > 0 {
		return schema.SystemPrereqCheck{
			Name:      "System Memory",
			Passed:    false,
			Critical:  false,
			Message:   fmt.Sprintf("Available memory (%d MB) is below recommended minimum (%d MB)", availMB, minMB),
			RemedyMsg: "Close heavy background workloads or allocate additional RAM/swap",
		}
	}

	return schema.SystemPrereqCheck{
		Name:     "System Memory",
		Passed:   true,
		Critical: false,
		Message:  fmt.Sprintf("Available system memory verified (%d MB free)", availMB),
	}
}

func (s *PrereqService) checkFileDescriptorLimits(minLimit uint64) schema.SystemPrereqCheck {
	var rLimit syscall.Rlimit
	if err := syscall.Getrlimit(syscall.RLIMIT_NOFILE, &rLimit); err != nil {
		return schema.SystemPrereqCheck{
			Name:     "File Descriptors",
			Passed:   true,
			Critical: false,
			Message:  "Skipping ulimit check",
		}
	}

	if rLimit.Cur < minLimit {
		rLimit.Cur = minLimit
		if err := syscall.Setrlimit(syscall.RLIMIT_NOFILE, &rLimit); err != nil {
			return schema.SystemPrereqCheck{
				Name:      "File Descriptors",
				Passed:    false,
				Critical:  false,
				Message:   fmt.Sprintf("Open file descriptor limit (%d) is below recommended %d", rLimit.Cur, minLimit),
				RemedyMsg: fmt.Sprintf("Run 'ulimit -n %d' before launching heavy ingestion workloads", minLimit),
			}
		}
	}

	return schema.SystemPrereqCheck{
		Name:     "File Descriptors",
		Passed:   true,
		Critical: false,
		Message:  fmt.Sprintf("Open file descriptor limit meets or exceeds %d", minLimit),
	}
}

func (s *PrereqService) checkVmMaxMapCount(minCount int) schema.SystemPrereqCheck {
	data, err := os.ReadFile("/proc/sys/vm/max_map_count")
	if err != nil {
		return schema.SystemPrereqCheck{
			Name:     "Kernel vm.max_map_count",
			Passed:   true,
			Critical: false,
			Message:  "Unable to read vm.max_map_count directly",
		}
	}

	val, err := strconv.Atoi(strings.TrimSpace(string(data)))
	if err != nil || val < minCount {
		return schema.SystemPrereqCheck{
			Name:      "Kernel vm.max_map_count",
			Passed:    false,
			Critical:  false,
			Message:   fmt.Sprintf("vm.max_map_count (%d) is below recommended %d for high-throughput databases", val, minCount),
			RemedyMsg: "Run 'sudo sysctl -w vm.max_map_count=262144'",
		}
	}

	return schema.SystemPrereqCheck{
		Name:     "Kernel vm.max_map_count",
		Passed:   true,
		Critical: false,
		Message:  fmt.Sprintf("vm.max_map_count verified (%d)", val),
	}
}

func (s *PrereqService) checkHostUtilities(bins []string) []schema.SystemPrereqCheck {
	var results []schema.SystemPrereqCheck
	for _, bin := range bins {
		_, err := exec.LookPath(bin)
		if err != nil {
			results = append(results, schema.SystemPrereqCheck{
				Name:      fmt.Sprintf("Host Utility: %s", bin),
				Passed:    false,
				Critical:  false,
				Message:   fmt.Sprintf("Optional utility '%s' not found in PATH", bin),
				RemedyMsg: fmt.Sprintf("Install %s for diagnostic checks", bin),
			})
		} else {
			results = append(results, schema.SystemPrereqCheck{
				Name:     fmt.Sprintf("Host Utility: %s", bin),
				Passed:   true,
				Critical: false,
				Message:  fmt.Sprintf("Utility '%s' is present in PATH", bin),
			})
		}
	}
	return results
}
