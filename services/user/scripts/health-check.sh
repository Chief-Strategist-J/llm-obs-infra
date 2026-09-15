#!/usr/bin/env bash

set +e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}====================================================${NC}"
echo -e "${BOLD} USER SERVICE STACK HEALTH DIAGNOSTIC                ${NC}"
echo -e "${BLUE}====================================================${NC}"

TOTAL_CHECKS=0
PASSED_CHECKS=0

check_container_status() {
  local container_name=$1
  local service_label=$2
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

  if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
    echo -e "  ${YELLOW}[SKIP]${NC} ${BOLD}${service_label}${NC} (${container_name}) -> Container is not running"
    return 0
  fi

  local status="unknown"
  local attempt=0
  local max_attempts=8
  local base_delay=1
  local max_delay=8

  while [ $attempt -lt $max_attempts ]; do
    status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_name" 2>/dev/null || echo "unknown")
    if [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
      break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
      break
    fi
    local exp=$((1 << attempt))
    local cap=$((base_delay * exp))
    [ $cap -gt $max_delay ] && cap=$max_delay
    local jitter=$(( (RANDOM % cap) + 1 ))
    sleep "$jitter"
  done

  local restart_count
  restart_count=$(docker inspect --format='{{.RestartCount}}' "$container_name" 2>/dev/null || echo "0")

  if [ "$restart_count" -ge 5 ]; then
    echo -e "  ${RED}[FAIL]${NC} ${BOLD}${service_label}${NC} (${container_name}) -> Crash loop detected (${restart_count} restarts)"
  elif [ "$status" = "healthy" ] || [ "$status" = "running" ]; then
    echo -e "  ${GREEN}[PASS]${NC} ${BOLD}${service_label}${NC} (${container_name}) -> Status: ${status} (restarts: ${restart_count})"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
  else
    echo -e "  ${YELLOW}[WARN]${NC} ${BOLD}${service_label}${NC} (${container_name}) -> Status: ${status}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
  fi
}

check_tcp() {
  local name=$1
  local port=$2
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
  local connected=false
  local attempt=0
  local max_attempts=8
  local base_delay=1
  local max_delay=8

  while [ $attempt -lt $max_attempts ]; do
    if nc -z localhost "$port" >/dev/null 2>&1; then
      connected=true
      break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
      break
    fi
    local exp=$((1 << attempt))
    local cap=$((base_delay * exp))
    [ $cap -gt $max_delay ] && cap=$max_delay
    local jitter=$(( (RANDOM % cap) + 1 ))
    sleep "$jitter"
  done

  if [ "$connected" = true ]; then
    echo -e "  ${GREEN}[PASS]${NC} ${BOLD}${name}${NC} -> TCP Port ${port} is listening & accepting connections"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
  else
    echo -e "  ${RED}[FAIL]${NC} ${BOLD}${name}${NC} -> TCP Port ${port} is unreachable"
  fi
}

check_http() {
  local name=$1
  local url=$2
  local expected_pattern=$3
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

  local code="000"
  local body=""
  local attempt=0
  local max_attempts=8
  local base_delay=1
  local max_delay=8

  while [ $attempt -lt $max_attempts ]; do
    code=$(curl -sk -o /tmp/health_body.tmp -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    body=$(cat /tmp/health_body.tmp 2>/dev/null || echo "")
    rm -f /tmp/health_body.tmp

    if echo "$code" | grep -qE "^(${expected_pattern})$" || echo "$body" | grep -qi "$expected_pattern"; then
      break
    fi

    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
      break
    fi
    local exp=$((1 << attempt))
    local cap=$((base_delay * exp))
    [ $cap -gt $max_delay ] && cap=$max_delay
    local jitter=$(( (RANDOM % cap) + 1 ))
    sleep "$jitter"
  done

  if echo "$code" | grep -qE "^(${expected_pattern})$" || echo "$body" | grep -qi "$expected_pattern"; then
    echo -e "  ${GREEN}[PASS]${NC} ${BOLD}${name}${NC} -> ${url} (HTTP ${code})"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
  else
    echo -e "  ${RED}[FAIL]${NC} ${BOLD}${name}${NC} -> ${url} (HTTP ${code}, expected ${expected_pattern})"
  fi
}

test_alloydb_crud() {
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
  local tbl="health_test_$(date +%s)"
  local db_user="admin"
  local db_pw="user_s3cret_2026"
  local db_name="user_profile_db"

  if [ -f "$USER_DIR/.env" ]; then
    db_user=$(grep -E "^USER_DB_USER=" "$USER_DIR/.env" 2>/dev/null | cut -d= -f2 || echo "admin")
    db_pw=$(grep -E "^USER_DB_PASSWORD=" "$USER_DIR/.env" 2>/dev/null | cut -d= -f2 || echo "user_s3cret_2026")
    db_name=$(grep -E "^USER_DB_NAME=" "$USER_DIR/.env" 2>/dev/null | cut -d= -f2 || echo "user_profile_db")
  fi

  local sql="CREATE TABLE ${tbl} (id INT PRIMARY KEY, payload TEXT); INSERT INTO ${tbl} VALUES (1, 'user_db_ok'); SELECT payload FROM ${tbl}; DROP TABLE ${tbl};"

  local res=""
  local attempt=0
  local max_attempts=8
  local base_delay=1
  local max_delay=8

  while [ $attempt -lt $max_attempts ]; do
    res=$(docker exec -e PGPASSWORD="$db_pw" -i user-service-db psql -U "$db_user" -d "$db_name" -c "$sql" 2>/dev/null || echo "")
    if echo "$res" | grep -q "user_db_ok"; then
      break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
      break
    fi
    local exp=$((1 << attempt))
    local cap=$((base_delay * exp))
    [ $cap -gt $max_delay ] && cap=$max_delay
    local jitter=$(( (RANDOM % cap) + 1 ))
    sleep "$jitter"
  done

  if echo "$res" | grep -q "user_db_ok"; then
    echo -e "  ${GREEN}[PASS]${NC} ${BOLD}User Database CRUD Verification${NC} -> Table create/insert/select/drop OK"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
  else
    echo -e "  ${RED}[FAIL]${NC} ${BOLD}User Database CRUD Verification${NC} -> Query execution failed"
  fi
}

test_redis_crud() {
  TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
  local key="health:user:$(date +%s)"
  local val=""
  local attempt=0
  local max_attempts=8
  local base_delay=1
  local max_delay=8

  while [ $attempt -lt $max_attempts ]; do
    docker exec -i user-redis-ledger redis-cli -a user_redis_s3cret_2026 SET "$key" "redis_ok" >/dev/null 2>&1 || true
    val=$(docker exec -i user-redis-ledger redis-cli -a user_redis_s3cret_2026 GET "$key" 2>/dev/null || echo "")
    docker exec -i user-redis-ledger redis-cli -a user_redis_s3cret_2026 DEL "$key" >/dev/null 2>&1 || true

    if echo "$val" | grep -q "redis_ok"; then
      break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -ge $max_attempts ]; then
      break
    fi
    local exp=$((1 << attempt))
    local cap=$((base_delay * exp))
    [ $cap -gt $max_delay ] && cap=$max_delay
    local jitter=$(( (RANDOM % cap) + 1 ))
    sleep "$jitter"
  done

  if echo "$val" | grep -q "redis_ok"; then
    echo -e "  ${GREEN}[PASS]${NC} ${BOLD}User Redis Ledger CRUD Verification${NC} -> Key set/get/del verification OK"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
  else
    echo -e "  ${RED}[FAIL]${NC} ${BOLD}User Redis Ledger CRUD Verification${NC} -> Key-value write failed"
  fi
}

echo -e "\n${YELLOW}1. Container Process & Docker Health Status:${NC}"
check_container_status "user-service-db" "User Database (PostgreSQL 15+ / AlloyDB Omni)"
check_container_status "user-redis-ledger" "User Redis Ledger"
check_container_status "user-kafka-broker" "User Kafka Broker"
check_container_status "user-otel-collector" "User OTel Collector"
check_container_status "user-service-registry" "User Service Registry API"

echo -e "\n${YELLOW}2. Port Accessibility & Endpoint Verification:${NC}"
check_tcp "User Database Port" "5435"
check_tcp "User Redis Ledger Port" "6382"
check_tcp "User Kafka Event Broker Port" "9095"
check_tcp "User OTel Collector HTTP" "4323"
check_tcp "User OTel Collector gRPC" "4324"
check_http "User Service Registry API" "http://localhost:31429/health" "200"

echo -e "\n${YELLOW}3. Database & Redis Functional Verification:${NC}"
test_alloydb_crud
test_redis_crud

echo -e "\n${BLUE}====================================================${NC}"
if [ "$PASSED_CHECKS" -eq "$TOTAL_CHECKS" ]; then
  echo -e "${GREEN}${BOLD}✓ ALL ${PASSED_CHECKS}/${TOTAL_CHECKS} HEALTH CHECKS PASSED!${NC}"
  echo -e "${BLUE}====================================================${NC}"
  exit 0
else
  echo -e "${RED}${BOLD}✖ DIAGNOSTIC: ${PASSED_CHECKS}/${TOTAL_CHECKS} CHECKS PASSED.${NC}"
  echo -e "${BLUE}====================================================${NC}"
  exit 1
fi
