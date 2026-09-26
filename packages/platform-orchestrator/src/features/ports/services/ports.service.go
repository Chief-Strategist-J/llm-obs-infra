/*
Package services implements port inspection, contention diagnosis, and automated port freeing.

ALGORITHM BLUEPRINT:
1. CheckAllPorts: Iterates over the stack port list, testing availability via the NetworkPort adapter.
2. FreeAllContestedPorts: For any port that is unavailable, invokes FreePort to terminate orphaned processes.
3. Invariants:
   - Port verification must not block or hang indefinitely.
   - Operations must log all occupied ports prior to termination.
*/
package services

import (
	"context"
	"fmt"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/features/ports/schema"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/shared/ports"
)

type PortService struct {
	networkPort ports.NetworkPort
	tracer      ports.TracerPort
}

func NewPortService(networkPort ports.NetworkPort, tracer ports.TracerPort) *PortService {
	return &PortService{
		networkPort: networkPort,
		tracer:      tracer,
	}
}

func (s *PortService) CheckPorts(ctx context.Context, portList []int) []schema.PortCheckResult {
	_, endSpan := s.tracer.StartSpan(ctx, "llmobs.ports.check")
	defer endSpan()

	if len(portList) == 0 {
		portList = schema.DefaultStackPorts()
	}

	var results []schema.PortCheckResult
	for _, p := range portList {
		avail := s.networkPort.IsPortAvailable(p)
		results = append(results, schema.PortCheckResult{
			Port:      p,
			Available: avail,
		})
	}
	return results
}

func (s *PortService) FreePorts(ctx context.Context, portList []int) error {
	_, endSpan := s.tracer.StartSpan(ctx, "llmobs.ports.free")
	defer endSpan()

	if len(portList) == 0 {
		portList = schema.DefaultStackPorts()
	}

	for _, p := range portList {
		if !s.networkPort.IsPortAvailable(p) {
			if err := s.networkPort.FreePort(ctx, p); err != nil {
				return fmt.Errorf("failed to free port %d: %w", p, err)
			}
		}
	}
	return nil
}
