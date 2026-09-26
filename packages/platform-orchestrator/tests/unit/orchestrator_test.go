/*
Package unit implements unit verification tests for orchestrator rules and schemas.

ALGORITHM BLUEPRINT:
1. TestDeriveNodeMetadata: Validates port offset math, project name generation, and container prefix calculation.
2. TestResolveProfiles: Verifies deduplication and default profile fallback.
3. TestSelectComposeFiles: Asserts that stateless profiles dynamically attach docker-compose.stateless.yml.
4. TestEnvelopes: Verifies standard API envelope generation according to api-request-response-structure.md.
*/
package unit

import (
	"testing"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/features/scale/rules"
	scaleSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/scale/schema"
	stackRules "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/stack/rules"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/shared/types"
)

func TestDeriveNodeMetadata(t *testing.T) {
	cmd := scaleSchema.LaunchNodeCommand{
		NodeID:          2,
		PrimaryDataHost: "10.0.10.5",
	}

	meta := rules.DeriveNodeMetadata(cmd)

	if meta.ProjectName != "llmobs-compute-2" {
		t.Fatalf("expected project 'llmobs-compute-2', got %s", meta.ProjectName)
	}

	if meta.ContainerPrefix != "node2-" {
		t.Fatalf("expected prefix 'node2-', got %s", meta.ContainerPrefix)
	}

	if meta.Ports["PORT_TRAEFIK_HTTP"] != 31510 {
		t.Fatalf("expected traefik port 31510, got %d", meta.Ports["PORT_TRAEFIK_HTTP"])
	}

	if meta.Ports["PORT_GRAFANA"] != 31515 {
		t.Fatalf("expected grafana port 31515, got %d", meta.Ports["PORT_GRAFANA"])
	}
}

func TestResolveProfiles(t *testing.T) {
	empty := stackRules.ResolveProfiles(nil)
	if len(empty) != 1 || empty[0] != "full" {
		t.Fatalf("expected default profile 'full', got %v", empty)
	}

	deduped := stackRules.ResolveProfiles([]string{"stateful", "data", "stateful"})
	if len(deduped) != 2 {
		t.Fatalf("expected 2 unique profiles, got %d", len(deduped))
	}
}

func TestSelectComposeFiles(t *testing.T) {
	statelessFiles := stackRules.SelectComposeFiles(".", []string{"stateless"})
	if len(statelessFiles) != 2 {
		t.Fatalf("expected 2 files for stateless profile, got %d", len(statelessFiles))
	}

	statefulFiles := stackRules.SelectComposeFiles(".", []string{"stateful"})
	if len(statefulFiles) != 2 {
		t.Fatalf("expected 2 files for stateful profile, got %d", len(statefulFiles))
	}
}

func TestEnvelopeGeneration(t *testing.T) {
	resp := types.NewSuccessResponse(map[string]string{"key": "value"}, "v1")
	if resp.Meta.TraceID == "" {
		t.Fatalf("expected non-empty traceId")
	}
	if resp.Meta.Version != "v1" {
		t.Fatalf("expected version v1, got %s", resp.Meta.Version)
	}
	if resp.Data["key"] != "value" {
		t.Fatalf("expected data key=value")
	}

	errResp := types.NewErrorResponse[any]("ERR_TEST", "Test error", "field", "v1")
	if len(errResp.Errors) != 1 {
		t.Fatalf("expected 1 error, got %d", len(errResp.Errors))
	}
	if errResp.Errors[0].Code != "ERR_TEST" {
		t.Fatalf("expected code ERR_TEST, got %s", errResp.Errors[0].Code)
	}
}
