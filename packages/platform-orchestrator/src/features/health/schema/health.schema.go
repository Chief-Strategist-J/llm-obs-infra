/*
Package schema defines entities and reporting models for platform health verification.

ALGORITHM BLUEPRINT:
1. ServiceHealthTarget: Specification of target address, port, protocol, path, and criticality.
2. HealthCheckReport: Aggregated report indicating overall health status, latency, and individual probe results.
3. Invariants:
   - Target timeout defaults to 3 seconds if unspecified.
   - Overall healthy status is true if and only if all required targets pass.
*/
package schema

import "time"

type ServiceHealthTarget struct {
	Service  string        `json:"service"`
	Host     string        `json:"host"`
	Port     int           `json:"port"`
	Protocol string        `json:"protocol"`
	Path     string        `json:"path,omitempty"`
	Timeout  time.Duration `json:"timeout"`
	Required bool          `json:"required"`
}

type SingleProbeResult struct {
	Service   string  `json:"service"`
	Target    string  `json:"target"`
	Status    string  `json:"status"`
	LatencyMs float64 `json:"latencyMs"`
	Error     string  `json:"error,omitempty"`
	IsHealthy bool    `json:"isHealthy"`
	Required  bool    `json:"required"`
}

type HealthCheckReport struct {
	Healthy      bool                `json:"healthy"`
	CheckedCount int                 `json:"checkedCount"`
	HealthyCount int                 `json:"healthyCount"`
	Results      []SingleProbeResult `json:"results"`
}

func DefaultHealthTargets(primaryHost string) []ServiceHealthTarget {
	if primaryHost == "" {
		primaryHost = "localhost"
	}
	return []ServiceHealthTarget{
		{Service: "traefik", Host: "localhost", Port: 31410, Protocol: "http", Path: "/ping", Timeout: 3 * time.Second, Required: true},
		{Service: "service-registry", Host: "localhost", Port: 31426, Protocol: "http", Path: "/health", Timeout: 3 * time.Second, Required: true},
		{Service: "otel-collector", Host: "localhost", Port: 31417, Protocol: "http", Path: "/", Timeout: 3 * time.Second, Required: true},
		{Service: "grafana", Host: "localhost", Port: 31415, Protocol: "http", Path: "/api/health", Timeout: 3 * time.Second, Required: false},
		{Service: "redis", Host: primaryHost, Port: 31413, Protocol: "tcp", Timeout: 3 * time.Second, Required: true},
		{Service: "kafka", Host: primaryHost, Port: 31414, Protocol: "tcp", Timeout: 3 * time.Second, Required: true},
		{Service: "tempo", Host: primaryHost, Port: 31416, Protocol: "http", Path: "/ready", Timeout: 3 * time.Second, Required: false},
		{Service: "alloydb", Host: primaryHost, Port: 31420, Protocol: "tcp", Timeout: 3 * time.Second, Required: true},
		{Service: "clickhouse", Host: primaryHost, Port: 31421, Protocol: "http", Path: "/ping", Timeout: 3 * time.Second, Required: false},
		{Service: "temporal", Host: primaryHost, Port: 31424, Protocol: "tcp", Timeout: 3 * time.Second, Required: false},
	}
}
