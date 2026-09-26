/*
Package schema defines data entities and specifications for stack port management.

ALGORITHM BLUEPRINT:
1. PortCheckResult: Entity representing individual port check outcome with process metadata.
2. PortRangeSpec: Entity specifying the lower and upper bounds of platform assigned ports.
3. Invariants:
   - Port numbers must fall within 1024-65535 unprivileged range.
*/
package schema

type PortCheckResult struct {
	Port      int    `json:"port"`
	Available bool   `json:"available"`
	Process   string `json:"process,omitempty"`
}

type PortRangeSpec struct {
	StartPort int   `json:"startPort"`
	EndPort   int   `json:"endPort"`
	Specific  []int `json:"specific,omitempty"`
}

func DefaultStackPorts() []int {
	return []int{
		31410, // Traefik HTTP
		31411, // Traefik Dashboard
		31412, // Service Registry (internal)
		31413, // Redis
		31414, // Kafka
		31415, // Grafana
		31416, // Tempo HTTP
		31417, // OTel HTTP
		31418, // OTel gRPC
		31419, // Traefik HTTPS
		31420, // AlloyDB
		31421, // ClickHouse HTTP
		31422, // ClickHouse Native
		31424, // Temporal gRPC
		31425, // Temporal UI
		31426, // Service Registry
	}
}
