#!/usr/bin/env bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STORAGE_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$STORAGE_DIR/docker-compose.yml"

get_docker_compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
  else
    echo ""
  fi
}

BIN=$(get_docker_compose_cmd)
if [ -z "$BIN" ]; then
  echo -e "${RED}Error: Docker Compose is not installed.${NC}"
  exit 1
fi

ensure_env() {
  if [ ! -f "$STORAGE_DIR/.env" ] && [ -f "$STORAGE_DIR/.env.example" ]; then
    echo -e "${BLUE}Copying .env.example to .env...${NC}"
    cp "$STORAGE_DIR/.env.example" "$STORAGE_DIR/.env"
  fi
}

ensure_data_storage() {
  local data_dir="${LLMOBS_DATA_DIR:-$STORAGE_DIR/data}"
  local subdirs=("db/data" "db/archive" "redis/data" "kafka/data")
  local created=0
  for sub in "${subdirs[@]}"; do
    if [ ! -d "$data_dir/$sub" ]; then
      mkdir -p "$data_dir/$sub"
      chmod 777 "$data_dir/$sub" 2>/dev/null || true
      created=1
    fi
  done
  if [ "$created" -eq 1 ]; then
    echo -e "${GREEN}✓ Initialized persistent storage directories in $data_dir${NC}"
  else
    echo -e "${BLUE}✓ Reusing existing persistent storage from $data_dir${NC}"
  fi
}

case "${1:-up}" in
  up)
    ensure_env
    ensure_data_storage
    echo -e "${BLUE}Launching Storage Service Stack (Database, Redis, Kafka, OTel, Service Registry)...${NC}"
    $BIN -f "$COMPOSE_FILE" --profile storage up -d
    echo -e "${GREEN}✓ Storage stack container deployment initiated.${NC}"
    bash "$SCRIPT_DIR/health-check.sh" || true
    ;;
  down)
    echo -e "${BLUE}Stopping Storage Service Stack...${NC}"
    $BIN -f "$COMPOSE_FILE" --profile storage down
    echo -e "${GREEN}✓ Storage stack stopped.${NC}"
    ;;
  restart)
    ensure_data_storage
    echo -e "${BLUE}Restarting Storage Service Stack...${NC}"
    $BIN -f "$COMPOSE_FILE" --profile storage restart
    bash "$SCRIPT_DIR/health-check.sh" || true
    ;;
  status|ps)
    $BIN -f "$COMPOSE_FILE" --profile storage ps
    ;;
  logs)
    shift || true
    $BIN -f "$COMPOSE_FILE" --profile storage logs -f "$@"
    ;;
  health)
    bash "$SCRIPT_DIR/health-check.sh"
    ;;
  *)
    echo "Usage: $0 {up|down|restart|status|health|logs}"
    exit 1
    ;;
esac
