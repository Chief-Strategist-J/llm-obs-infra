# Contract Changelog

## [1.0.0] - 2026-09-26
### Added
- Initial OpenAPI 3.1.0 contract for Platform Infrastructure Orchestrator (`v1.yaml`).
- Stack lifecycle endpoints: `/stack/up`, `/stack/down`, `/stack/status`.
- Horizontal scaling endpoints: `/scale/service`, `/scale/node`, `/scale/node/{nodeId}`.
- Diagnostic & security endpoints: `/health`, `/certs/generate`.
- Standard transport envelope schema with W3C `traceId`, `timestamp`, and structured errors.
