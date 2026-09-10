#!/usr/bin/env bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

CURRENT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$CURRENT_DIR/profile-resolver.sh"
source "$CURRENT_DIR/targeted-health.sh"
source "$CURRENT_DIR/endpoint-reporter.sh"

ensure_external_network() {
  local net_name="llmobs-network"
  if ! docker network inspect "$net_name" >/dev/null 2>&1; then
    echo -e "${BLUE}⚡ Creating external Docker network '${net_name}' with platform network signature...${NC}"
    docker network create \
      --driver bridge \
      --subnet 172.28.0.0/16 \
      --gateway 172.28.0.1 \
      --label "com.llmobs.network.signature=llmobs-net-sig-v1.0" \
      --label "com.llmobs.network.security=isolated-bridge" \
      --label "com.llmobs.network.managed-by=llmobs-infra" \
      "$net_name" >/dev/null 2>&1 || true
  fi
}

start_profile_stack() {
  local bin=$1
  local compose_file=$2
  shift 2
  local user_args=("$@")

  ensure_external_network

  # Resolve profiles and target services dynamically
  local resolved
  resolved=$(resolve_profiles_and_dependencies "${user_args[@]}")

  local profile_flags
  profile_flags=$(echo "$resolved" | grep "^PROFILES=" | cut -d'=' -f2-)
  local target_services
  target_services=$(echo "$resolved" | grep "^SERVICES=" | cut -d'=' -f2-)

  echo -e "${BLUE}⚡ Launching infrastructure stack with flags: ${BOLD}${profile_flags}${NC}"
  echo -e "${BLUE}⚡ Target services: ${BOLD}${target_services}${NC}"

  # Execute compose up with profiles
  # shellcheck disable=SC2086
  $bin -f "$compose_file" $profile_flags up -d $target_services

  # Run targeted health checks for active services
  # shellcheck disable=SC2086
  run_targeted_health_checks $target_services

  # Output active working endpoints and configurations
  # shellcheck disable=SC2086
  print_active_endpoints $target_services
}

main() {
  local bin=$1
  local compose_file=$2
  shift 2 || true
  start_profile_stack "$bin" "$compose_file" "$@"
}

main "$@"
