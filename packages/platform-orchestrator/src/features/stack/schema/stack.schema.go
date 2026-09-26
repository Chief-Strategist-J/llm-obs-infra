/*
Package schema defines data entities and commands for stack orchestration.

ALGORITHM BLUEPRINT:
1. StackUpCommand: Entity defining requested profiles, detach flag, and environment overrides.
2. StackActionOutcome: Result entity returning status, message, and affected service names.
3. Invariants:
   - Valid profile names include: stateful, stateless, data, compute, network, edge, db, workflows, streaming, analytics, tracing, portal, full.
*/
package schema

type StackUpCommand struct {
	Profiles []string          `json:"profiles"`
	Detach   bool              `json:"detach"`
	EnvVars  map[string]string `json:"envVars,omitempty"`
}

type StackActionOutcome struct {
	Status         string   `json:"status"`
	Message        string   `json:"message"`
	ActiveServices []string `json:"activeServices"`
}
