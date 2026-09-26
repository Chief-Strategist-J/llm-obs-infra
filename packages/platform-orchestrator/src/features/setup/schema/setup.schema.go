/*
Package schema defines data contracts for end-to-end platform environment bootstrapping.

ALGORITHM BLUEPRINT:
1. SetupStep: Tracks individual step index, description, status, and duration.
2. SetupReport: Aggregates execution results across all 7 bootstrapping phases.
3. Invariants:
   - Setup validates system prerequisites before performing credential or filesystem mutations.
   - Bootstrapping is idempotent: re-running on an initialized platform does not overwrite user credentials.
*/
package schema

import "time"

type SetupStep struct {
	Index       int           `json:"index"`
	Name        string        `json:"name"`
	Passed      bool          `json:"passed"`
	Description string        `json:"description"`
	Duration    time.Duration `json:"duration"`
	Error       string        `json:"error,omitempty"`
}

type SetupReport struct {
	TotalSteps  int         `json:"totalSteps"`
	PassedSteps int         `json:"passedSteps"`
	Success     bool        `json:"success"`
	Steps       []SetupStep `json:"steps"`
	Message     string      `json:"message"`
}
