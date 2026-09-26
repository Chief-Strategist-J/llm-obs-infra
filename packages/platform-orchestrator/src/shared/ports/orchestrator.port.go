/*
Package ports defines the hexagonal boundary interfaces for infrastructure adapters.

ALGORITHM BLUEPRINT:
1. ContainerPort: Abstraction over Docker Engine and Compose execution, isolating business services from raw CLI or API calls.
2. NetworkPort: Abstraction over host socket checks, network creation, and port contention resolution.
3. CertPort: Abstraction for cryptographic X.509 certificate generation, ensuring TLS readiness without external tooling dependencies.
4. HealthPort: Abstraction for parallel health verification across HTTP and TCP transport protocols.
5. TracerPort: Abstraction for OpenTelemetry distributed tracing and W3C context propagation.
6. Invariants:
   - Business services must only interact with infrastructure via these interfaces.
   - Adapters must adhere to single responsibility: Docker adapter manages containers; Cert adapter manages certificates.
*/
package ports

import (
	"context"
	"time"
)

type ComposeOptions struct {
	ComposeFiles []string
	Profiles     []string
	ProjectName  string
	EnvVars      map[string]string
	Services     []string
	Detach       bool
	Timeout      time.Duration
}

type ContainerStatus struct {
	Name    string `json:"name"`
	Service string `json:"service"`
	Status  string `json:"status"`
	Ports   string `json:"ports"`
}

type ContainerPort interface {
	ComposeUp(ctx context.Context, opts ComposeOptions) error
	ComposeDown(ctx context.Context, opts ComposeOptions) error
	ComposeRestart(ctx context.Context, opts ComposeOptions) error
	ComposeScale(ctx context.Context, opts ComposeOptions, service string, replicas int) error
	ComposeStatus(ctx context.Context, opts ComposeOptions) ([]ContainerStatus, error)
	ComposeLogs(ctx context.Context, opts ComposeOptions, tail int) error
}

type NetworkPort interface {
	EnsureNetwork(ctx context.Context, networkName string, subnet string, gateway string) error
	IsPortAvailable(port int) bool
	FreePort(ctx context.Context, port int) error
}

type CertSpec struct {
	CertDir      string
	CertFile     string
	KeyFile      string
	CommonName   string
	Organization string
	ValidDays    int
	SANs         []string
	Force        bool
}

type CertPort interface {
	EnsureCertificates(ctx context.Context, spec CertSpec) (certPath string, keyPath string, generated bool, err error)
}

type HealthProbeTarget struct {
	Service     string        `json:"service"`
	Host        string        `json:"host"`
	Port        int           `json:"port"`
	Protocol    string        `json:"protocol"`
	Path        string        `json:"path,omitempty"`
	Timeout     time.Duration `json:"timeout"`
	Required    bool          `json:"required"`
}

type HealthProbeResult struct {
	Service   string        `json:"service"`
	Target    string        `json:"target"`
	Status    string        `json:"status"`
	Latency   time.Duration `json:"latency"`
	Error     string        `json:"error,omitempty"`
	IsHealthy bool          `json:"isHealthy"`
}

type HealthPort interface {
	ProbeTCP(ctx context.Context, target HealthProbeTarget) HealthProbeResult
	ProbeHTTP(ctx context.Context, target HealthProbeTarget) HealthProbeResult
	ProbeAll(ctx context.Context, targets []HealthProbeTarget) ([]HealthProbeResult, bool)
}

type TracerPort interface {
	StartSpan(ctx context.Context, operationName string) (context.Context, func())
	InjectTraceContext(ctx context.Context) string
}
