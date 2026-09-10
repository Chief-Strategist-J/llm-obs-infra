#!/usr/bin/env bash

# SRP: Profile Resolver Module
# Responsibilities:
# 1. Resolve user profile choices or CLI profile args into Docker compose --profile flags.
# 2. Resolve logical inter-profile dependencies (e.g. workflows -> db).
# 3. Provide an interactive stack selection menu when invoked without arguments in a TTY.

set -e

BOLD='\033[1m'
CYAN='\033[0;36m'
NC='\033[0m'

prompt_interactive_profile_selection() {
  if [ ! -t 0 ]; then
    # Non-interactive shell (e.g. CI/CD or piped script): default to full stack
    echo "full"
    return 0
  fi

  echo -e "\n${BOLD}${CYAN}=====================================================${NC}" >&2
  echo -e "${BOLD}${CYAN}  LLM Observability Infrastructure Stack Selector    ${NC}" >&2
  echo -e "${BOLD}${CYAN}=====================================================${NC}" >&2
  echo -e "Select the infrastructure stack profile you want to launch:\n" >&2
  echo -e "  ${BOLD}[1] Full Stack${NC}      - All 10 services (Default)" >&2
  echo -e "  ${BOLD}[2] Database Stack${NC}  - AlloyDB (PostgreSQL) + Redis Ledger" >&2
  echo -e "  ${BOLD}[3] Analytics Stack${NC} - ClickHouse Analytics DB" >&2
  echo -e "  ${BOLD}[4] Streaming Stack${NC} - Apache Kafka Event Broker" >&2
  echo -e "  ${BOLD}[5] Workflows Engine${NC}- Temporal Engine (+ auto-includes Database dependency)" >&2
  echo -e "  ${BOLD}[6] Tracing Stack${NC}   - Tempo + OpenTelemetry Collector + Grafana UI" >&2
  echo -e "  ${BOLD}[7] Network Gateway${NC} - Traefik Gateway + Service Registry" >&2
  echo -e "  ${BOLD}[8] Custom Profiles${NC} - Specify custom profiles (e.g. 'db streaming')" >&2
  echo -e "-----------------------------------------------------" >&2

  read -r -p "Enter choice [1-8] (default: 1): " choice >&2

  case "$choice" in
    2) echo "db" ;;
    3) echo "analytics" ;;
    4) echo "streaming" ;;
    5) echo "workflows" ;;
    6) echo "tracing" ;;
    7) echo "network" ;;
    8)
      read -r -p "Enter profiles separated by space (e.g. db streaming): " custom_profiles >&2
      echo "${custom_profiles:-full}"
      ;;
    *) echo "full" ;;
  esac
}

resolve_profiles_and_dependencies() {
  local raw_input=("$@")
  local profiles=()
  local services=()

  if [ ${#raw_input[@]} -eq 0 ] || [ "${raw_input[0]}" = "full" ] || [ "${raw_input[0]}" = "all" ]; then
    echo "PROFILES=--profile full"
    echo "SERVICES=llmobs-alloydb llmobs-redis llmobs-clickhouse llmobs-kafka llmobs-tempo llmobs-otel-collector llmobs-grafana llmobs-traefik llmobs-temporal llmobs-service-registry"
    return 0
  fi

  local req_db=false
  local req_analytics=false
  local req_streaming=false
  local req_workflows=false
  local req_tracing=false
  local req_network=false

  for item in "${raw_input[@]}"; do
    case "$item" in
      db|database|postgres|redis) req_db=true ;;
      analytics|clickhouse) req_analytics=true ;;
      streaming|kafka) req_streaming=true ;;
      workflows|temporal) req_workflows=true; req_db=true ;; # Logical dependency: Workflows requires DB
      tracing|telemetry|otel|grafana|tempo) req_tracing=true ;;
      network|gateway|traefik|registry) req_network=true ;;
    esac
  done

  local profile_flags=()

  if [ "$req_db" = true ]; then
    profile_flags+=("--profile" "db")
    services+=("llmobs-alloydb" "llmobs-redis")
  fi

  if [ "$req_analytics" = true ]; then
    profile_flags+=("--profile" "analytics")
    services+=("llmobs-clickhouse")
  fi

  if [ "$req_streaming" = true ]; then
    profile_flags+=("--profile" "streaming")
    services+=("llmobs-kafka")
  fi

  if [ "$req_workflows" = true ]; then
    profile_flags+=("--profile" "workflows")
    services+=("llmobs-temporal")
  fi

  if [ "$req_tracing" = true ]; then
    profile_flags+=("--profile" "tracing")
    services+=("llmobs-tempo" "llmobs-otel-collector" "llmobs-grafana")
  fi

  if [ "$req_network" = true ]; then
    profile_flags+=("--profile" "network")
    services+=("llmobs-traefik" "llmobs-service-registry")
  fi

  if [ ${#profile_flags[@]} -eq 0 ]; then
    # Fallback to full if unmatched
    profile_flags=("--profile" "full")
    services=("llmobs-alloydb" "llmobs-redis" "llmobs-clickhouse" "llmobs-kafka" "llmobs-tempo" "llmobs-otel-collector" "llmobs-grafana" "llmobs-traefik" "llmobs-temporal" "llmobs-service-registry")
  fi

  # Deduplicate services
  local unique_services
  unique_services=$(echo "${services[*]}" | tr ' ' '\n' | sort -u | tr '\n' ' ')

  echo "PROFILES=${profile_flags[*]}"
  echo "SERVICES=$unique_services"
}
