#!/usr/bin/env bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$USER_DIR/docker-compose.yml"

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
  if [ ! -f "$USER_DIR/.env" ] && [ -f "$USER_DIR/.env.example" ]; then
    echo -e "${BLUE}Copying .env.example to .env...${NC}"
    cp "$USER_DIR/.env.example" "$USER_DIR/.env"
  fi
}

case "${1:-up}" in
  up)
    ensure_env
    echo -e "${BLUE}Launching User Service Stack (Database, Redis, Kafka, OTel, Service Registry)...${NC}"
    $BIN -f "$COMPOSE_FILE" --profile user up -d
    echo -e "${GREEN}✓ User stack container deployment initiated.${NC}"
    bash "$SCRIPT_DIR/health-check.sh" || true
    ;;
  down)
    echo -e "${BLUE}Stopping User Service Stack...${NC}"
    $BIN -f "$COMPOSE_FILE" --profile user down
    echo -e "${GREEN}✓ User stack stopped.${NC}"
    ;;
  restart)
    echo -e "${BLUE}Restarting User Service Stack...${NC}"
    $BIN -f "$COMPOSE_FILE" --profile user restart
    bash "$SCRIPT_DIR/health-check.sh" || true
    ;;
  status|ps)
    $BIN -f "$COMPOSE_FILE" --profile user ps
    ;;
  logs)
    shift || true
    $BIN -f "$COMPOSE_FILE" --profile user logs -f "$@"
    ;;
  health)
    bash "$SCRIPT_DIR/health-check.sh"
    ;;
  *)
    echo "Usage: $0 {up|down|restart|status|health|logs}"
    exit 1
    ;;
esac
