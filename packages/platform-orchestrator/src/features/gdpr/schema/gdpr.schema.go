/*
Package schema defines data contracts for GDPR and CCPA right-to-erasure workflows.

ALGORITHM BLUEPRINT:
1. ErasureRequest: Encapsulates target identity criteria (user ID or customer ID).
2. ErasureReport: Tracks successful record deletions across ClickHouse Analytics and AlloyDB relational stores.
3. Invariants:
   - Target identifiers must be non-empty and sanitized against SQL injection.
   - Erasure operations produce an immutable audit log entry.
*/
package schema

type ErasureRequest struct {
	UserID     string `json:"userId,omitempty"`
	CustomerID string `json:"customerId,omitempty"`
}

type ErasureReport struct {
	TargetID         string `json:"targetId"`
	ClickHousePurged bool   `json:"clickHousePurged"`
	AlloyDBPurged    bool   `json:"alloyDbPurged"`
	AuditRecorded    bool   `json:"auditRecorded"`
	Success          bool   `json:"success"`
	Message          string `json:"message"`
}
