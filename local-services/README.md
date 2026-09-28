# LLMObs Local Domain Microservices

Centralized directory containing local domain microservices configured to run against the LLMObs Platform Infrastructure:
- **`user`**: User profile, identity metadata, and account settings
- **`audit`**: Immutable security trail, compliance logs, and administrative event auditing
- **`auth`**: Authentication, session tokens, JWT issuance, and RBAC policy enforcement
- **`notifications`**: Multi-channel alerting, webhooks, and push notifications
- **`payment`**: Transaction ledgers, invoicing, and balance caches
- **`storage`**: Object metadata, artifact tracking, and upload synchronization

---

## Unified Infrastructure Runner (`run.sh`)

All services share a single, unified runner script located at `local-services/run.sh`. It automatically compiles the orchestrator binary if missing, provisions local `.env` files, boots infrastructure, and validates health & dependencies.

### Common Commands

```bash
# 1. Interactive service selector:
./local-services/run.sh

# 2. Start infrastructure & verify a specific service:
./local-services/run.sh user up
./local-services/run.sh auth up
./local-services/run.sh payment up

# 3. Start infrastructure & verify ALL services at once:
./local-services/run.sh all up

# 4. Verify credentials and connectivity for a service:
./local-services/run.sh user verify
./local-services/run.sh auth verify
./local-services/run.sh all verify

# 5. Check infrastructure health across all platform endpoints:
./local-services/run.sh health

# 6. View running container statuses:
./local-services/run.sh status

# 7. Stop all infrastructure containers cleanly:
./local-services/run.sh down
```

---

## Directory Structure

```
local-services/
├── run.sh                  # Single unified runner for all services
├── README.md               # Unified documentation
├── user/
│   └── .env.example        # User service configuration connecting to platform
├── audit/
│   └── .env.example        # Audit service configuration connecting to platform
├── auth/
│   └── .env.example        # Auth service configuration connecting to platform
├── notifications/
│   └── .env.example        # Notifications service configuration connecting to platform
├── payment/
│   └── .env.example        # Payment service configuration connecting to platform
└── storage/
    └── .env.example        # Storage service configuration connecting to platform
```
