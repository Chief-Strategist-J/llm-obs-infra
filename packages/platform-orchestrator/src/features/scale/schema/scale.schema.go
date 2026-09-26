/*
Package schema defines data entities and requests for platform scaling.

ALGORITHM BLUEPRINT:
1. ScaleServiceCommand: Entity defining service name and replica target count.
2. LaunchNodeCommand: Entity defining node index, primary data host IP, and Cloudflare tunnel attachment.
3. NodeMetadata: Entity capturing assigned ports, project names, and container prefixes.
4. Invariants:
   - Node IDs must be >= 2 for simulated compute nodes.
   - Replicas must be >= 1.
*/
package schema

type ScaleServiceCommand struct {
	Service  string `json:"service"`
	Replicas int    `json:"replicas"`
}

type LaunchNodeCommand struct {
	NodeID           int    `json:"nodeId"`
	PrimaryDataHost  string `json:"primaryDataHost"`
	EnableCloudflare bool   `json:"enableCloudflare"`
}

type NodeMetadata struct {
	NodeID          int            `json:"nodeId"`
	ProjectName     string         `json:"projectName"`
	ContainerPrefix string         `json:"containerPrefix"`
	PrimaryDataHost string         `json:"primaryDataHost"`
	Ports           map[string]int `json:"ports"`
}
