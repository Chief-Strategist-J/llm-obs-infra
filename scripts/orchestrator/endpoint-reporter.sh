#!/usr/bin/env bash

# SRP: Endpoint Reporter Module
# Responsibilities:
# 1. Inspect running services dynamically.
# 2. Print active working URLs and configuration connection strings strictly for running services.

set -e

GREEN='\033[0;32m'
BOLD='\033[1m'
CYAN='\033[0;36m'
NC='\033[0m'

get_env_var() {
  local var_name=$1
  local default_val=$2
  if [ -f ".env" ]; then
    local val
    val=$(grep -E "^${var_name}=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "")
    if [ -n "$val" ]; then
      echo "$val"
      return 0
    fi
  fi
  echo "$default_val"
}

print_active_endpoints() {
  local active_services=("$@")
  local services_str=" ${active_services[*]} "

  echo -e "\n${BOLD}${GREEN}=====================================================${NC}"
  echo -e "${BOLD}${GREEN}  Active Services & Configurations                   ${NC}"
  echo -e "${BOLD}${GREEN}=====================================================${NC}"

  # Database endpoints
  if [[ "$services_str" =~ "llmobs-alloydb" ]]; then
    local port_alloydb
    port_alloydb=$(get_env_var "PORT_ALLOYDB" "31420")
    local db_user
    db_user=$(get_env_var "ALLOYDB_USER" "admin")
    local db_name
    db_name=$(get_env_var "ALLOYDB_DB" "llm_observability")
    echo -e "  ${BOLD}• AlloyDB (PostgreSQL):${NC} postgresql://${db_user}:***@localhost:${port_alloydb}/${db_name}"
  fi

  if [[ "$services_str" =~ "llmobs-redis" ]]; then
    local port_redis
    port_redis=$(get_env_var "PORT_REDIS" "31413")
    echo -e "  ${BOLD}• Redis Ledger:${NC}       redis://:***@localhost:${port_redis}/0"
  fi

  # Analytics endpoint
  if [[ "$services_str" =~ "llmobs-clickhouse" ]]; then
    local port_ch_http
    port_ch_http=$(get_env_var "PORT_CLICKHOUSE_HTTP" "31421")
    local port_ch_native
    port_ch_native=$(get_env_var "PORT_CLICKHOUSE_NATIVE" "31422")
    echo -e "  ${BOLD}• ClickHouse Analytics:${NC} HTTP: http://localhost:${port_ch_http} | Native TCP: localhost:${port_ch_native}"
  fi

  # Streaming endpoint
  if [[ "$services_str" =~ "llmobs-kafka" ]]; then
    local port_kafka
    port_kafka=$(get_env_var "PORT_KAFKA" "31414")
    echo -e "  ${BOLD}• Kafka Broker:${NC}        localhost:${port_kafka}"
  fi

  # Workflows endpoints
  if [[ "$services_str" =~ "llmobs-temporal" ]]; then
    local port_temp_grpc
    port_temp_grpc=$(get_env_var "PORT_TEMPORAL_GRPC" "31424")
    local port_temp_ui
    port_temp_ui=$(get_env_var "PORT_TEMPORAL_UI" "31425")
    echo -e "  ${BOLD}• Temporal gRPC Engine:${NC} localhost:${port_temp_grpc}"
    echo -e "  ${BOLD}• Temporal Web UI:${NC}      http://localhost:${port_temp_ui}"
  fi

  # Tracing endpoints
  if [[ "$services_str" =~ "llmobs-grafana" ]]; then
    local port_grafana
    port_grafana=$(get_env_var "PORT_GRAFANA" "31415")
    echo -e "  ${BOLD}• Grafana Dashboard:${NC}    http://localhost:${port_grafana}"
  fi

  if [[ "$services_str" =~ "llmobs-otel-collector" ]]; then
    local port_otel_http
    port_otel_http=$(get_env_var "PORT_OTEL_HTTP" "31417")
    local port_otel_grpc
    port_otel_grpc=$(get_env_var "PORT_OTEL_GRPC" "31418")
    echo -e "  ${BOLD}• OTel Collector:${NC}      HTTP: http://localhost:${port_otel_http} | gRPC: localhost:${port_otel_grpc}"
  fi

  if [[ "$services_str" =~ "llmobs-tempo" ]]; then
    local port_tempo
    port_tempo=$(get_env_var "PORT_TEMPO" "31416")
    echo -e "  ${BOLD}• Grafana Tempo:${NC}        http://localhost:${port_tempo}"
  fi

  # Gateway & Network endpoints
  if [[ "$services_str" =~ "llmobs-traefik" ]]; then
    local port_tr_http
    port_tr_http=$(get_env_var "PORT_TRAEFIK_HTTP" "31410")
    local port_tr_dash
    port_tr_dash=$(get_env_var "PORT_TRAEFIK_DASHBOARD" "31411")
    local port_tr_https
    port_tr_https=$(get_env_var "PORT_TRAEFIK_HTTPS" "31419")
    echo -e "  ${BOLD}• Traefik HTTP Gateway:${NC} http://localhost:${port_tr_http} (→ HTTPS:${port_tr_https})"
    echo -e "  ${BOLD}• Traefik Dashboard:${NC}    http://localhost:${port_tr_dash}"
  fi

  if [[ "$services_str" =~ "llmobs-service-registry" ]]; then
    local port_reg
    port_reg=$(get_env_var "PORT_SERVICE_REGISTRY" "31426")
    echo -e "  ${BOLD}• Service Registry API:${NC} http://localhost:${port_reg}"
  fi

  echo -e "${BOLD}${GREEN}=====================================================${NC}\n"
}
