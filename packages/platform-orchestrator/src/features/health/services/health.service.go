/*
Package services implements concurrent health probe execution across distributed platform endpoints.

ALGORITHM BLUEPRINT:
1. ProbeFanOut: Iterates over the target list, dispatching each probe into an isolated concurrent goroutine.
2. Protocol Dispatch:
   - TCP: Executes net.DialTimeout. Measures socket connection latency; closes socket immediately upon handshake.
   - HTTP: Executes GET request using an isolated http.Client. Evaluates status code < 500.
3. Metric Accumulation: Collects results into a thread-safe slice protected by a sync.Mutex.
4. Report Aggregation: Evaluates whether all required services passed; returns structured HealthCheckReport.
5. Invariants:
   - Probe timeout is strictly bounded to prevent hang states.
   - Individual probe panics or network hangs must not impede other concurrent probes.
*/
package services

import (
	"context"
	"fmt"
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/features/health/schema"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/shared/ports"
)

type HealthService struct {
	tracer ports.TracerPort
}

func NewHealthService(tracer ports.TracerPort) *HealthService {
	return &HealthService{
		tracer: tracer,
	}
}

func (s *HealthService) RunHealthChecks(ctx context.Context, targets []schema.ServiceHealthTarget) schema.HealthCheckReport {
	_, endSpan := s.tracer.StartSpan(ctx, "llmobs.health.check_all")
	defer endSpan()

	if len(targets) == 0 {
		targets = schema.DefaultHealthTargets("localhost")
	}

	var wg sync.WaitGroup
	var mu sync.Mutex
	var results []schema.SingleProbeResult
	overallHealthy := true

	for _, target := range targets {
		wg.Add(1)
		go func(t schema.ServiceHealthTarget) {
			defer wg.Done()
			res := s.probeSingle(ctx, t)

			mu.Lock()
			results = append(results, res)
			if t.Required && !res.IsHealthy {
				overallHealthy = false
			}
			mu.Unlock()
		}(target)
	}

	wg.Wait()

	healthyCount := 0
	for _, r := range results {
		if r.IsHealthy {
			healthyCount++
		}
	}

	return schema.HealthCheckReport{
		Healthy:      overallHealthy,
		CheckedCount: len(results),
		HealthyCount: healthyCount,
		Results:      results,
	}
}

func (s *HealthService) probeSingle(ctx context.Context, t schema.ServiceHealthTarget) schema.SingleProbeResult {
	addr := fmt.Sprintf("%s:%d", t.Host, t.Port)
	start := time.Now()

	if t.Protocol == "tcp" {
		d := net.Dialer{Timeout: t.Timeout}
		conn, err := d.DialContext(ctx, "tcp", addr)
		latency := time.Since(start)
		if err != nil {
			return schema.SingleProbeResult{
				Service:   t.Service,
				Target:    addr,
				Status:    "DOWN",
				LatencyMs: float64(latency.Milliseconds()),
				Error:     err.Error(),
				IsHealthy: false,
				Required:  t.Required,
			}
		}
		_ = conn.Close()
		return schema.SingleProbeResult{
			Service:   t.Service,
			Target:    addr,
			Status:    "HEALTHY",
			LatencyMs: float64(latency.Milliseconds()),
			IsHealthy: true,
			Required:  t.Required,
		}
	}

	url := fmt.Sprintf("http://%s%s", addr, t.Path)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return schema.SingleProbeResult{
			Service:   t.Service,
			Target:    url,
			Status:    "DOWN",
			LatencyMs: 0,
			Error:     err.Error(),
			IsHealthy: false,
			Required:  t.Required,
		}
	}

	client := &http.Client{Timeout: t.Timeout}
	resp, err := client.Do(req)
	latency := time.Since(start)
	if err != nil {
		return schema.SingleProbeResult{
			Service:   t.Service,
			Target:    url,
			Status:    "DOWN",
			LatencyMs: float64(latency.Milliseconds()),
			Error:     err.Error(),
			IsHealthy: false,
			Required:  t.Required,
		}
	}
	defer resp.Body.Close()

	isOk := resp.StatusCode < 500
	statusStr := "HEALTHY"
	if !isOk {
		statusStr = fmt.Sprintf("HTTP_%d", resp.StatusCode)
	}

	return schema.SingleProbeResult{
		Service:   t.Service,
		Target:    url,
		Status:    statusStr,
		LatencyMs: float64(latency.Milliseconds()),
		IsHealthy: isOk,
		Required:  t.Required,
	}
}
