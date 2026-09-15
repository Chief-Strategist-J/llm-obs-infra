#!/usr/bin/env bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYMENT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PAYMENT_DIR/docker-compose.yml"

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
  if [ ! -f "$PAYMENT_DIR/.env" ] && [ -f "$PAYMENT_DIR/.env.example" ]; then
    echo -e "${BLUE}Copying .env.example to .env...${NC}"
    cp "$PAYMENT_DIR/.env.example" "$PAYMENT_DIR/.env"
  fi
}

case "${1:-up}" in
  up)
    ensure_env
    echo -e "${BLUE}Launching Payment Service Stack (Database, Redis, Kafka, OTel, Service Registry)...${NC}"
    $BIN -f "$COMPOSE_FILE" --profile payment up -d
    echo -e "${GREEN}✓ Payment stack container deployment initiated.${NC}"
    bash "$SCRIPT_DIR/health-check.sh" || true
    ;;
  down)
    echo -e "${BLUE}Stopping Payment Service Stack...${NC}"
    $BIN -f "$COMPOSE_FILE" --profile payment down
    echo -e "${GREEN}✓ Payment stack stopped.${NC}"
    ;;
  restart)
    echo -e "${BLUE}Restarting Payment Service Stack...${NC}"
    $BIN -f "$COMPOSE_FILE" --profile payment restart
    bash "$SCRIPT_DIR/health-check.sh" || true
    ;;
  status|ps)
    $BIN -f "$COMPOSE_FILE" --profile payment ps
    ;;
  logs)
    shift || true
    $BIN -f "$COMPOSE_FILE" --profile payment logs -f "$@"
    ;;
  health)
    bash "$SCRIPT_DIR/health-check.sh"
    ;;
  *)
    echo "Usage: $0 {up|down|restart|status|health|logs}"
    exit 1
    ;;
esac
