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
  local check_flag="${VERIFY_CHECK:-}"
  local check_arg=""
  if [ -n "$check_flag" ]; then
    check_arg="--check $check_flag"
  fi
  if [ "$TARGET_SERVICE" = "all" ]; then
    for s in "${KNOWN_SERVICES[@]}"; do
      # shellcheck disable=SC2086
      "$BIN" verify-credentials "$s" $check_arg
    done
  else
    # shellcheck disable=SC2086
    "$BIN" verify-credentials "$TARGET_SERVICE" $check_arg
  fi
}

resolve_profiles() {
  # Priority: CLI args > service .env INFRA_PROFILES > service .env.example INFRA_PROFILES > interactive
  if [ -n "$*" ]; then
    echo "$*"
    return
  fi
  local svc_dir="$SCRIPT_DIR/$TARGET_SERVICE"
  local env_profiles=""
  for env_file in "$svc_dir/.env" "$svc_dir/.env.example"; do
    if [ -f "$env_file" ]; then
      env_profiles=$(grep -E '^INFRA_PROFILES=' "$env_file" 2>/dev/null | head -1 | cut -d'=' -f2-)
      # Strip surrounding quotes only — preserve spaces between profile names
      env_profiles="${env_profiles#\"}" ; env_profiles="${env_profiles%\"}"
      env_profiles="${env_profiles#\'}" ; env_profiles="${env_profiles%\'}"
      env_profiles="${env_profiles# }"  ; env_profiles="${env_profiles% }"
      if [ -n "$env_profiles" ]; then
        echo "$env_profiles"
        return
      fi
    fi
  done
  # Nothing configured — fall through to llmobs interactive selector
  echo ""
}

case "$ACTION" in
  up|start)
    PROFILES=$(resolve_profiles "$@")
    if [ -n "$PROFILES" ]; then
      echo -e "${BLUE}▶ Starting infrastructure for ${BOLD}$TARGET_SERVICE${NC} (Profiles: ${BOLD}$PROFILES${NC})...${NC}"
      # shellcheck disable=SC2086
      "$BIN" up $PROFILES
    else
      echo -e "${BLUE}▶ Starting infrastructure (interactive — set INFRA_PROFILES in $TARGET_SERVICE/.env to skip this)...${NC}"
      "$BIN" up
    fi
    PROFILES_CSV=$(echo "$PROFILES" | tr ' ' ',')
    echo -e "\n${BLUE}▶ Verifying infrastructure health (scoped to: ${BOLD}${PROFILES_CSV:-all}${NC})...${NC}"
    if [ -n "$PROFILES_CSV" ]; then
      "$BIN" health --profiles "$PROFILES_CSV"
    else
      "$BIN" health
    fi
    echo -e "\n${BLUE}▶ Verifying credentials & connectivity for ${BOLD}$TARGET_SERVICE${NC}...${NC}"
    verify_services
    echo -e "\n${GREEN}✓ Infrastructure for ${BOLD}$TARGET_SERVICE${NC} is operational and verified.${NC}"
    ;;
  down|stop)
    echo -e "${YELLOW}■ Stopping platform infrastructure containers...${NC}"
    "$BIN" down
    ;;
  restart)
    PROFILES=$(resolve_profiles "$@")
    if [ -n "$PROFILES" ]; then
      echo -e "${BLUE}⟳ Restarting infrastructure (Profiles: ${BOLD}$PROFILES${NC})...${NC}"
      # shellcheck disable=SC2086
      "$BIN" restart $PROFILES
    else
      echo -e "${BLUE}⟳ Restarting infrastructure (interactive — set INFRA_PROFILES in $TARGET_SERVICE/.env to skip this)...${NC}"
      "$BIN" restart
    fi
    PROFILES_CSV=$(echo "$PROFILES" | tr ' ' ',')
    if [ -n "$PROFILES_CSV" ]; then
      "$BIN" health --profiles "$PROFILES_CSV"
    else
      "$BIN" health
    fi
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
    echo "  $0 [target] [command] [profiles...]"
    echo ""
    echo "Targets:"
    echo "  user | audit | auth | notifications | payment | storage | all"
    echo "  (or any arbitrary label matching a local-services/<label>/.env)"
    echo ""
    echo "Commands:"
    echo "  up [profiles...]     Start specified infrastructure profiles, then verify"
    echo "  down                 Stop all infrastructure containers"
    echo "  restart [profiles..]  Restart profiles and re-verify"
    echo "  status               Show container statuses"
    echo "  health               Health check all platform endpoints"
    echo "  verify               Verify credentials only (no infra start)"
    echo "  logs                 Stream container logs"
    echo "  config               Inspect or tune resource limits"
    echo ""
    echo "Infrastructure profiles (passed directly to 'llmobs up'):"
    echo "  db          AlloyDB (PostgreSQL) + Redis Ledger"
    echo "  streaming   Apache Kafka Event Broker"
    echo "  analytics   ClickHouse Analytics DB"
    echo "  tracing     Tempo + OTel Collector + Grafana"
    echo "  network     Traefik Gateway + Service Registry"
    echo "  stateful    All stateful services"
    echo "  stateless   All stateless services"
    echo "  full        All 10 services"
    echo ""
    echo "Verify options (passed to 'llmobs verify-credentials'):"
    echo "  VERIFY_CHECK=db,redis  $0 user verify   # scope credential checks"
    echo ""
    echo "Examples:"
    echo "  $0 user up db streaming        # start only db+streaming for user target"
    echo "  $0 auth up db                  # start only db profile for auth target"
    echo "  $0 user up                     # interactive llmobs profile selector"
    echo "  $0 all up full                 # start all 10 services"
    echo "  $0 auth verify                 # verify credentials for auth target"
    echo "  VERIFY_CHECK=db $0 user verify # verify only db component"
    echo "  $0 down                        # stop all infrastructure"
    ;;
  *)
    echo "Unknown command: $ACTION"
    echo "Run '$0 --help' for usage."
    exit 1
    ;;
esac
