/*
Package rules implements deterministic scaling calculations and port offset formulas.

ALGORITHM BLUEPRINT:
1. CalculateNodeMetadata:
   - Derives ProjectName = 'llmobs-compute-{nodeId}'.
   - Derives ContainerPrefix = 'node{nodeId}-'.
   - Offset Formula: offset = (nodeId - 1) * 100.
   - Calculates non-colliding host ports:
     PORT_TRAEFIK_HTTP = 31410 + offset
     PORT_TRAEFIK_DASHBOARD = 31411 + offset
     PORT_GRAFANA = 31415 + offset
     PORT_OTEL_HTTP = 31417 + offset
     PORT_OTEL_GRPC = 31418 + offset
     PORT_TRAEFIK_HTTPS = 31419 + offset
     PORT_TEMPORAL_GRPC = 31424 + offset
     PORT_SERVICE_REGISTRY = 31426 + offset
2. Invariants:
   - Port offsets must never collide across distinct node indices.
*/
package rules

import (
	"fmt"
	"strconv"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/features/scale/schema"
)

func DeriveNodeMetadata(cmd schema.LaunchNodeCommand) schema.NodeMetadata {
	offset := (cmd.NodeID - 1) * 100
	host := cmd.PrimaryDataHost
	if host == "" {
		host = "host.docker.internal"
	}

	ports := map[string]int{
		"PORT_TRAEFIK_HTTP":      31410 + offset,
		"PORT_TRAEFIK_DASHBOARD": 31411 + offset,
		"PORT_GRAFANA":           31415 + offset,
		"PORT_OTEL_HTTP":         31417 + offset,
		"PORT_OTEL_GRPC":         31418 + offset,
		"PORT_TRAEFIK_HTTPS":     31419 + offset,
		"PORT_TEMPORAL_GRPC":     31424 + offset,
		"PORT_TEMPORAL_UI":       31425 + offset,
		"PORT_SERVICE_REGISTRY":  31426 + offset,
	}

	return schema.NodeMetadata{
		NodeID:          cmd.NodeID,
		ProjectName:     fmt.Sprintf("llmobs-compute-%d", cmd.NodeID),
		ContainerPrefix: fmt.Sprintf("node%d-", cmd.NodeID),
		PrimaryDataHost: host,
		Ports:           ports,
	}
}

func ConvertPortsToEnv(meta schema.NodeMetadata) map[string]string {
	env := map[string]string{
		"COMPOSE_PROJECT_NAME":     meta.ProjectName,
		"CONTAINER_PREFIX":         meta.ContainerPrefix,
		"LLMOBS_PRIMARY_DATA_HOST": meta.PrimaryDataHost,
	}
	for k, v := range meta.Ports {
		env[k] = strconv.Itoa(v)
	}
	return env
}
