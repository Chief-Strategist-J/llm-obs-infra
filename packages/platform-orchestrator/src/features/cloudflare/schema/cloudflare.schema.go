/*
Package schema defines data contracts for Cloudflare Tunnel configuration and lifecycle execution.

ALGORITHM BLUEPRINT:
1. CloudflareAction: Enumerates valid lifecycle operations (setup, start, stop, status, logs).
2. CloudflareTunnelOptions: Captures tunnel authentication tokens and operational modes.
3. Invariants:
   - Tunnel tokens must be non-empty when provisioning ingress.
   - Credentials are saved to .env under CLOUDFLARE_TUNNEL_TOKEN.
*/
package schema

type CloudflareTunnelOptions struct {
	Action string `json:"action"`
	Token  string `json:"token,omitempty"`
}

type CloudflareTunnelReport struct {
	Status  string `json:"status"`
	Active  bool   `json:"active"`
	Message string `json:"message"`
}
