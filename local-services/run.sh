#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# LLMObs Local Services Unified Runner
# Centralized CLI orchestrating infrastructure for all microservices.
# ─────────────────────────────────────────────────────────────

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ORCHESTRATOR_DIR="$REPO_ROOT/packages/platform-orchestrator"
BIN="$REPO_ROOT/bin/llmobs"

KNOWN_SERVICES=("user" "audit" "auth" "notifications" "payment" "storage")

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

ensure_binary() {
  if [ ! -f "$BIN" ]; then
    echo -e "${YELLOW}Compiling orchestrator binary...${NC}"
    (cd "$ORCHESTRATOR_DIR" && make build >/dev/null 2>&1)
  fi
}

ensure_service_env() {
  local svc="$1"
  local svc_dir="$SCRIPT_DIR/$svc"
  if [ -d "$svc_dir" ] && [ ! -f "$svc_dir/.env" ] && [ -f "$svc_dir/.env.example" ]; then
    cp "$svc_dir/.env.example" "$svc_dir/.env"
    echo -e "${GREEN}✓ Created local .env for ${BOLD}$svc${NC} from .env.example"
  fi
}

select_service_interactive() {
  echo -e "\n${BLUE}=====================================================${NC}"
  echo -e "${BOLD}  LLMObs Local Services Runner                        ${NC}"
  echo -e "${BLUE}=====================================================${NC}"
  echo -e "Select target microservice:"
  echo -e "  [1] user          - User profile & identity store"
  echo -e "  [2] audit         - Immutable security & audit logs"
  echo -e "  [3] auth          - Authentication & RBAC policies"
  echo -e "  [4] notifications - Multi-channel alerting & webhooks"
  echo -e "  [5] payment       - Payment processing & ledger"
  echo -e "  [6] storage       - Object metadata & file records"
  echo -e "  [7] all           - All local domain services"
  echo -e "-----------------------------------------------------"
  read -r -p "Enter choice [1-7] (default: 1): " choice
  case "$choice" in
    2) TARGET_SERVICE="audit" ;;
    3) TARGET_SERVICE="auth" ;;
    4) TARGET_SERVICE="notifications" ;;
    5) TARGET_SERVICE="payment" ;;
    6) TARGET_SERVICE="storage" ;;
    7) TARGET_SERVICE="all" ;;
    *) TARGET_SERVICE="user" ;;
  esac
}

ensure_binary

# Check if first argument is a known service or 'all'
TARGET_SERVICE=""
ACTION=""

if [ $# -eq 0 ]; then
  select_service_interactive
  ACTION="up"
else
  FIRST_ARG="$1"
  for s in "${KNOWN_SERVICES[@]}" "all"; do
    if [ "$FIRST_ARG" = "$s" ]; then
      TARGET_SERVICE="$FIRST_ARG"
      shift
      ACTION="${1:-up}"
      shift || true
      break
    fi
  done

  # If first arg was not a service name, treat it as action and default to 'all'
  if [ -z "$TARGET_SERVICE" ]; then
    TARGET_SERVICE="all"
    ACTION="$FIRST_ARG"
    shift || true
  fi
fi

# Prepare environment files
if [ "$TARGET_SERVICE" = "all" ]; then
  for s in "${KNOWN_SERVICES[@]}"; do
    ensure_service_env "$s"
  done
else
  ensure_service_env "$TARGET_SERVICE"
fi

verify_services() {
  if [ "$TARGET_SERVICE" = "all" ]; then
    for s in "${KNOWN_SERVICES[@]}"; do
      "$BIN" verify-credentials "$s"
    done
  else
    "$BIN" verify-credentials "$TARGET_SERVICE"
  fi
}

case "$ACTION" in
  up|start)
    PROFILES="${1:-full}"
    echo -e "${BLUE}▶ Starting infrastructure for ${BOLD}$TARGET_SERVICE${NC} (Profiles: $PROFILES)...${NC}"
    "$BIN" up $PROFILES
    echo -e "\n${BLUE}▶ Verifying infrastructure health across platform endpoints...${NC}"
    "$BIN" health
    echo -e "\n${BLUE}▶ Verifying credentials & connectivity for ${BOLD}$TARGET_SERVICE${NC}...${NC}"
    verify_services
    echo -e "\n${GREEN}✓ Infrastructure for ${BOLD}$TARGET_SERVICE${NC} is operational and verified.${NC}"
    ;;
  down|stop)
    echo -e "${YELLOW}■ Stopping platform infrastructure containers...${NC}"
    "$BIN" down
    ;;
  restart)
    PROFILES="${1:-full}"
    echo -e "${BLUE}⟳ Restarting infrastructure (Profiles: $PROFILES)...${NC}"
    "$BIN" restart $PROFILES
    "$BIN" health
    verify_services
    ;;
  status|ps)
    "$BIN" status
    ;;
  health|check)
    "$BIN" health
    verify_services
    ;;
  verify)
    verify_services
    ;;
  logs)
    "$BIN" logs "$@"
    ;;
  config)
    "$BIN" config "$@"
    ;;
  help|-h|--help)
    echo "LLMObs Local Services Unified Runner"
    echo ""
    echo "Usage:"
    echo "  $0 [service] [command] [args...]"
    echo ""
    echo "Services:"
    echo "  user | audit | auth | notifications | payment | storage | all"
    echo ""
    echo "Commands:"
    echo "  up [profiles]    Start infrastructure, check health, and verify credentials"
    echo "  down             Stop all infrastructure containers"
    echo "  restart [prof]   Restart infrastructure and re-verify"
    echo "  status           Show container statuses"
    echo "  health           Check platform endpoint health and verify service dependencies"
    echo "  verify           Verify database and cache credentials"
    echo "  logs [tail]      Stream infrastructure container logs"
    echo "  config [args]    Inspect or tune Docker resource limits"
    echo ""
    echo "Examples:"
    echo "  $0 user up             # Start full stack and verify user service"
    echo "  $0 auth verify          # Verify auth service credentials"
    echo "  $0 all up               # Start full stack and verify all 6 services"
    echo "  $0 all health           # Health check and verify all services"
    echo "  $0 down                 # Stop infrastructure"
    ;;
  *)
    echo "Unknown command: $ACTION"
    echo "Run '$0 --help' for usage."
    exit 1
    ;;
esac
