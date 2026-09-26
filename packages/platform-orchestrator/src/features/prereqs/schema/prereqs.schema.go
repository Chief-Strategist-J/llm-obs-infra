/*
Package schema defines data entities and validation specifications for system prerequisites.

ALGORITHM BLUEPRINT:
1. SystemPrereqCheck: Entity capturing check name, status (PASS/WARN/FAIL), details, and requirement.
2. PrereqReport: Aggregated report indicating whether all mandatory prerequisites are met.
3. Invariants:
   - Mandatory checks include Docker Engine availability, Docker Compose availability, and sufficient memory.
*/
package schema

type SystemPrereqCheck struct {
	Name      string `json:"name"`
	Passed    bool   `json:"passed"`
	Critical  bool   `json:"critical"`
	Message   string `json:"message"`
	RemedyMsg string `json:"remedyMsg,omitempty"`
}

type PrereqReport struct {
	Passed bool                `json:"passed"`
	Checks []SystemPrereqCheck `json:"checks"`
}
