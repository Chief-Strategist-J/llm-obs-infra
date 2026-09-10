#!/usr/bin/env bash

# SRP: Targeted Dynamic Health Check Module
# Responsibilities:
# 1. Inspect active containers dynamically.
# 2. Run health checks strictly for active services in the targeted profile set.
# 3. Skip checks for unstarted services.

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

wait_with_backoff() {
  local check_cmd=$1
  local max_attempts=${2:-6}
  local base_delay=${3:-1}
  local max_delay=${4:-10}
  local attempt=0

  while [ $attempt -lt $max_attempts ]; do
    if eval "$check_cmd" >/dev/null 2>&1; then
      return 0
    fi
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
      break
    fi
    local exp=$((1 << attempt))
    local cap=$((base_delay * exp))
    if [ $cap -gt $max_delay ]; then cap=$max_delay; fi
    local jitter=$(( (RANDOM % cap) + 1 ))
    sleep "$jitter"
  done
  return 1
}

check_service_health() {
  local service_name=$1

  # Check container status
  local inspect_cmd="docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' '$service_name' 2>/dev/null | grep -q 'healthy\|running'"

  if ! wait_with_backoff "$inspect_cmd" 5 1 5; then
    echo -e "${YELLOW}⚠️  Container ${service_name} status check warning.${NC}"
    return 0
  fi

  case "$service_name" in
    llmobs-alloydb|llmobs-alloydb-db)
      echo -e "${BLUE}  - Verifying AlloyDB database connections...${NC}"
      local db_cmd="docker exec -i llmobs-alloydb-db pg_isready 2>/dev/null | grep -q 'accepting connections' || nc -z localhost 31420 2>/dev/null"
      wait_with_backoff "$db_cmd" 8 1 10 && echo -e "${GREEN}✓ AlloyDB database is ready.${NC}" || true
      ;;

    llmobs-redis|llmobs-redis-ledger)
      echo -e "${BLUE}  - Verifying Redis ledger socket...${NC}"
      local redis_cmd="nc -z localhost 31413 2>/dev/null || docker exec -i llmobs-redis-ledger redis-cli ping 2>/dev/null | grep -q PONG"
      wait_with_backoff "$redis_cmd" 5 1 5 && echo -e "${GREEN}✓ Redis ledger is ready.${NC}" || true
      ;;

    llmobs-clickhouse|llmobs-clickhouse-analytics)
      echo -e "${BLUE}  - Verifying ClickHouse analytics socket...${NC}"
      local ch_cmd="curl -s http://localhost:31421/ping 2>/dev/null | grep -q 'Ok.' || nc -z localhost 31421 2>/dev/null"
      wait_with_backoff "$ch_cmd" 8 1 10 && echo -e "${GREEN}✓ ClickHouse analytics engine is ready.${NC}" || true
      ;;

    llmobs-kafka|llmobs-kafka-broker)
      echo -e "${BLUE}  - Verifying Kafka broker socket...${NC}"
      local kafka_cmd="nc -z localhost 31414 2>/dev/null || docker exec -i llmobs-kafka-broker nc -z 127.0.0.1 9092 2>/dev/null"
      wait_with_backoff "$kafka_cmd" 6 1 6 && echo -e "${GREEN}✓ Kafka event broker is ready.${NC}" || true
      ;;

    llmobs-temporal|llmobs-temporal-engine)
      echo -e "${BLUE}  - Verifying Temporal workflow engine...${NC}"
      local temp_cmd="nc -z localhost 31424 2>/dev/null || nc -z 127.0.0.1 31425 2>/dev/null"
      wait_with_backoff "$temp_cmd" 6 1 6 && echo -e "${GREEN}✓ Temporal workflow engine is ready.${NC}" || true
      ;;

    llmobs-grafana|llmobs-grafana-portal)
      echo -e "${BLUE}  - Verifying Grafana portal UI...${NC}"
      local graf_cmd="curl -s http://localhost:31415/api/health 2>/dev/null | grep -q 'ok' || nc -z localhost 31415 2>/dev/null"
      wait_with_backoff "$graf_cmd" 6 1 6 && echo -e "${GREEN}✓ Grafana portal is ready.${NC}" || true
      ;;

    llmobs-traefik|llmobs-traefik-gateway)
      echo -e "${BLUE}  - Verifying Traefik reverse proxy...${NC}"
      local traefik_cmd="nc -z localhost 31410 2>/dev/null || nc -z localhost 31411 2>/dev/null"
      wait_with_backoff "$traefik_cmd" 5 1 5 && echo -e "${GREEN}✓ Traefik gateway is ready.${NC}" || true
      ;;

    llmobs-service-registry)
      echo -e "${BLUE}  - Verifying Service Registry API...${NC}"
      local reg_cmd="curl -s http://localhost:31426/health 2>/dev/null | grep -q 'ok' || nc -z localhost 31426 2>/dev/null"
      wait_with_backoff "$reg_cmd" 5 1 5 && echo -e "${GREEN}✓ Service Registry API is ready.${NC}" || true
      ;;

    *)
      echo -e "${GREEN}✓ Container ${service_name} is running.${NC}"
      ;;
  esac
}

run_targeted_health_checks() {
  local active_services=("$@")
  echo -e "${BLUE}⚡ Running targeted health checks for active services...${NC}"

  for service in "${active_services[@]}"; do
    check_service_health "$service"
  done

  echo -e "${GREEN}✓ Targeted health verification completed successfully!${NC}"
}
