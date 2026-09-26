/*
Package rest implements the HTTP presentation layer and REST controller handlers.

ALGORITHM BLUEPRINT:
1. Envelope Wrapping: All successful responses are formatted via types.NewSuccessResponse(data, "v1").
2. Error Handling: All failures map to HTTP status codes with structured types.NewErrorResponse(code, msg, target, "v1").
3. Input Decoding: Request JSON bodies are decoded into feature commands without business branching.
4. Invariants:
   - Handlers must not contain domain business logic or direct persistence calls.
   - Trace context is derived and injected into response envelopes.
*/
package rest

import (
	"encoding/json"
	"net/http"
	"strconv"
	"strings"

	certsSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/certs/schema"
	certsService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/certs/services"
	healthSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/health/schema"
	healthService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/health/services"
	scaleSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/scale/schema"
	scaleService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/scale/services"
	stackSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/stack/schema"
	stackService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/stack/services"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/shared/types"
)

type OrchestratorHandler struct {
	stackService  *stackService.StackService
	scaleService  *scaleService.ScaleService
	healthService *healthService.HealthService
	certsService  *certsService.CertService
	baseDir       string
}

func NewOrchestratorHandler(
	stackSvc *stackService.StackService,
	scaleSvc *scaleService.ScaleService,
	healthSvc *healthService.HealthService,
	certsSvc *certsService.CertService,
	baseDir string,
) *OrchestratorHandler {
	return &OrchestratorHandler{
		stackService:  stackSvc,
		scaleService:  scaleSvc,
		healthService: healthSvc,
		certsService:  certsSvc,
		baseDir:       baseDir,
	}
}

func (h *OrchestratorHandler) writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func (h *OrchestratorHandler) HandleStackUp(w http.ResponseWriter, r *http.Request) {
	var cmd stackSchema.StackUpCommand
	if err := json.NewDecoder(r.Body).Decode(&cmd); err != nil && err.Error() != "EOF" {
		h.writeJSON(w, http.StatusBadRequest, types.NewErrorResponse[any]("ERR_INVALID_PAYLOAD", err.Error(), "body", "v1"))
		return
	}

	outcome, err := h.stackService.StartStack(r.Context(), cmd)
	if err != nil {
		h.writeJSON(w, http.StatusInternalServerError, types.NewErrorResponse[any]("ERR_STACK_UP", err.Error(), "stack", "v1"))
		return
	}

	h.writeJSON(w, http.StatusOK, types.NewSuccessResponse(outcome, "v1"))
}

func (h *OrchestratorHandler) HandleStackDown(w http.ResponseWriter, r *http.Request) {
	outcome, err := h.stackService.StopStack(r.Context())
	if err != nil {
		h.writeJSON(w, http.StatusInternalServerError, types.NewErrorResponse[any]("ERR_STACK_DOWN", err.Error(), "stack", "v1"))
		return
	}
	h.writeJSON(w, http.StatusOK, types.NewSuccessResponse(outcome, "v1"))
}

func (h *OrchestratorHandler) HandleStackStatus(w http.ResponseWriter, r *http.Request) {
	statuses, err := h.stackService.GetStatus(r.Context())
	if err != nil {
		h.writeJSON(w, http.StatusInternalServerError, types.NewErrorResponse[any]("ERR_STACK_STATUS", err.Error(), "status", "v1"))
		return
	}
	h.writeJSON(w, http.StatusOK, types.NewSuccessResponse(map[string]any{"services": statuses}, "v1"))
}

func (h *OrchestratorHandler) HandleScaleService(w http.ResponseWriter, r *http.Request) {
	var cmd scaleSchema.ScaleServiceCommand
	if err := json.NewDecoder(r.Body).Decode(&cmd); err != nil {
		h.writeJSON(w, http.StatusBadRequest, types.NewErrorResponse[any]("ERR_INVALID_PAYLOAD", err.Error(), "body", "v1"))
		return
	}

	if err := h.scaleService.ScaleService(r.Context(), cmd); err != nil {
		h.writeJSON(w, http.StatusInternalServerError, types.NewErrorResponse[any]("ERR_SCALE_SERVICE", err.Error(), "service", "v1"))
		return
	}

	h.writeJSON(w, http.StatusOK, types.NewSuccessResponse(map[string]any{
		"service":  cmd.Service,
		"replicas": cmd.Replicas,
		"message":  "Service scale command applied",
	}, "v1"))
}

func (h *OrchestratorHandler) HandleScaleNode(w http.ResponseWriter, r *http.Request) {
	var cmd scaleSchema.LaunchNodeCommand
	if err := json.NewDecoder(r.Body).Decode(&cmd); err != nil {
		h.writeJSON(w, http.StatusBadRequest, types.NewErrorResponse[any]("ERR_INVALID_PAYLOAD", err.Error(), "body", "v1"))
		return
	}

	meta, err := h.scaleService.LaunchComputeNode(r.Context(), cmd)
	if err != nil {
		h.writeJSON(w, http.StatusInternalServerError, types.NewErrorResponse[any]("ERR_LAUNCH_NODE", err.Error(), "nodeId", "v1"))
		return
	}

	h.writeJSON(w, http.StatusOK, types.NewSuccessResponse(meta, "v1"))
}

func (h *OrchestratorHandler) HandleTerminateNode(w http.ResponseWriter, r *http.Request) {
	path := r.URL.Path
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) < 4 {
		h.writeJSON(w, http.StatusBadRequest, types.NewErrorResponse[any]("ERR_INVALID_URL", "missing node ID", "nodeId", "v1"))
		return
	}

	nodeID, err := strconv.Atoi(parts[3])
	if err != nil {
		h.writeJSON(w, http.StatusBadRequest, types.NewErrorResponse[any]("ERR_INVALID_NODE_ID", "nodeId must be integer", "nodeId", "v1"))
		return
	}

	if err := h.scaleService.TerminateComputeNode(r.Context(), nodeID); err != nil {
		h.writeJSON(w, http.StatusInternalServerError, types.NewErrorResponse[any]("ERR_TERMINATE_NODE", err.Error(), "nodeId", "v1"))
		return
	}

	h.writeJSON(w, http.StatusOK, types.NewSuccessResponse(map[string]any{
		"message": "Compute node terminated",
		"nodeId":  nodeID,
	}, "v1"))
}

func (h *OrchestratorHandler) HandleHealth(w http.ResponseWriter, r *http.Request) {
	primaryHost := r.URL.Query().Get("primaryHost")
	targets := healthSchema.DefaultHealthTargets(primaryHost)
	report := h.healthService.RunHealthChecks(r.Context(), targets)

	status := http.StatusOK
	if !report.Healthy {
		status = http.StatusServiceUnavailable
	}
	h.writeJSON(w, status, types.NewSuccessResponse(report, "v1"))
}

func (h *OrchestratorHandler) HandleGenerateCerts(w http.ResponseWriter, r *http.Request) {
	spec := certsSchema.DefaultCertSpec(h.baseDir)
	res, err := h.certsService.EnsureCertificates(r.Context(), spec)
	if err != nil {
		h.writeJSON(w, http.StatusInternalServerError, types.NewErrorResponse[any]("ERR_GENERATE_CERTS", err.Error(), "certs", "v1"))
		return
	}
	h.writeJSON(w, http.StatusOK, types.NewSuccessResponse(res, "v1"))
}
