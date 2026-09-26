#!/usr/bin/env bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

scale_service() {
  local bin=$1
  local compose_file=$2
  local service_name=$3
  local replicas=$4

  if [ -z "$service_name" ]; then
    echo -e "${YELLOW}Stateless services available for in-stack replication:${NC}"
    echo "  1) llmobs-temporal        (Workflow execution worker engine)"
    echo "  2) llmobs-otel-collector   (Telemetry ingestion agent)"
    echo "  3) Custom service..."
    echo ""
    read -rp "Enter service name to scale [default: llmobs-temporal]: " input_svc
    service_name="${input_svc:-llmobs-temporal}"
  fi

  if [ -z "$replicas" ]; then
    read -rp "Enter desired replica count for '$service_name' [e.g. 2, 3, 5]: " input_rep
    replicas="${input_rep:-2}"
  fi

  if ! [[ "$replicas" =~ ^[0-9]+$ ]] || [ "$replicas" -lt 1 ]; then
    echo -e "${RED}Error: Replicas must be a positive integer.${NC}" >&2
    exit 1
  fi

  echo -e "${BLUE}⚡ Scaling '${BOLD}${service_name}${NC}${BLUE}' to ${BOLD}${replicas}${NC}${BLUE} replicas...${NC}"

  # Unset fixed container_name to allow multiple replicas in the same project
  CONTAINER_PREFIX="" $bin -f "$compose_file" up -d --scale "${service_name}=${replicas}" --no-recreate

  echo -e "${GREEN}✓ Successfully scaled '${service_name}' to ${replicas} replicas.${NC}"
  echo -e "${BLUE}ℹ Service discovery will detect all replica endpoints and Traefik will round-robin load balance them.${NC}"
}

scale_node() {
  local bin=$1
  local compose_file=$2
  local pkg_dir=$3
  local node_id=$4
  local primary_host=$5

  if [ -z "$node_id" ]; then
    read -rp "Enter simulated compute node number [e.g. 2, 3]: " input_node
    node_id="${input_node:-2}"
  fi

  if ! [[ "$node_id" =~ ^[0-9]+$ ]] || [ "$node_id" -lt 2 ]; then
    echo -e "${RED}Error: Node number must be an integer >= 2 (Node 1 is the primary/default compute stack).${NC}" >&2
    exit 1
  fi

  if [ -z "$primary_host" ]; then
    read -rp "Enter IP or host of primary data plane [default: host.docker.internal]: " input_host
    primary_host="${input_host:-host.docker.internal}"
  fi

  local project_name="llmobs-compute-${node_id}"
  local container_prefix="node${node_id}-"
  local port_offset=$(( (node_id - 1) * 100 ))

  export COMPOSE_PROJECT_NAME="$project_name"
  export CONTAINER_PREFIX="$container_prefix"
  export LLMOBS_PRIMARY_DATA_HOST="$primary_host"

  # Offset host ports to prevent collisions on single-machine local test
  export PORT_TRAEFIK_HTTP=$(( 31410 + port_offset ))
  export PORT_TRAEFIK_DASHBOARD=$(( 31411 + port_offset ))
  export PORT_TRAEFIK_HTTPS=$(( 31419 + port_offset ))
  export PORT_GRAFANA=$(( 31415 + port_offset ))
  export PORT_OTEL_HTTP=$(( 31417 + port_offset ))
  export PORT_OTEL_GRPC=$(( 31418 + port_offset ))
  export PORT_TEMPORAL_GRPC=$(( 31424 + port_offset ))
  export PORT_TEMPORAL_UI=$(( 31425 + port_offset ))
  export PORT_SERVICE_REGISTRY=$(( 31426 + port_offset ))

  echo -e "${BLUE}===============================================================${NC}"
  echo -e "${BOLD} Launching Simulated Compute Node ${node_id}${NC}"
  echo -e "${BLUE}===============================================================${NC}"
  echo -e "  • Project Name:         ${BOLD}${project_name}${NC}"
  echo -e "  • Container Prefix:     ${BOLD}${container_prefix}${NC}"
  echo -e "  • Primary Data Host:    ${BOLD}${primary_host}${NC} (DB, Kafka, Redis)"
  echo -e "  • Traefik HTTP Port:    ${BOLD}${PORT_TRAEFIK_HTTP}${NC}"
  echo -e "  • Traefik HTTPS Port:   ${BOLD}${PORT_TRAEFIK_HTTPS}${NC}"
  echo -e "  • Traefik Dashboard:    ${BOLD}${PORT_TRAEFIK_DASHBOARD}${NC}"
  echo -e "  • Grafana Portal:       ${BOLD}${PORT_GRAFANA}${NC}"
  echo -e "  • Service Registry:     ${BOLD}${PORT_SERVICE_REGISTRY}${NC}"
  echo ""

  local compose_args=("-f" "$compose_file" "-f" "$pkg_dir/docker-compose.stateless.yml" "--profile" "stateless")

  read -rp "Enable Cloudflare Tunnel connector on Node ${node_id}? (y/n) [default: n]: " enable_cf
  if [[ "$enable_cf" =~ ^[Yy]$ ]]; then
    if [ -f "$pkg_dir/docker-compose.cloudflare.yml" ]; then
      compose_args+=("-f" "$pkg_dir/docker-compose.cloudflare.yml" "--profile" "cloudflare")
      echo -e "${BLUE}ℹ Attaching Cloudflare multi-connector mesh to Node ${node_id}...${NC}"
    fi
  fi

  $bin "${compose_args[@]}" up -d

  echo ""
  echo -e "${GREEN}✓ Compute Node ${node_id} is running and connected to central data host '${primary_host}'.${NC}"
  echo -e "${BLUE}ℹ Local Service Discovery on Node ${node_id} has resolved all database connections to '${primary_host}'.${NC}"
}

down_node() {
  local bin=$1
  local compose_file=$2
  local node_id=$3

  if [ -z "$node_id" ]; then
    read -rp "Enter compute node number to terminate [e.g. 2, 3]: " input_node
    node_id="${input_node:-2}"
  fi

  local project_name="llmobs-compute-${node_id}"
  echo -e "${YELLOW}Stopping and removing simulated compute node '${project_name}'...${NC}"
  COMPOSE_PROJECT_NAME="$project_name" $bin -f "$compose_file" --profile "*" down
  echo -e "${GREEN}✓ Compute Node ${node_id} removed.${NC}"
}

list_nodes() {
  echo -e "${BLUE}===============================================================${NC}"
  echo -e "${BOLD} Active Scaled Compute Nodes & Services${NC}"
  echo -e "${BLUE}===============================================================${NC}"
  docker ps --filter "name=llmobs" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

interactive_scale_menu() {
  local bin=$1
  local compose_file=$2
  local pkg_dir=$3

  echo -e "${BLUE}===============================================================${NC}"
  echo -e "${BOLD}           LLMOBS Infrastructure Scaling Manager               ${NC}"
  echo -e "${BLUE}===============================================================${NC}"
  echo "Select scaling operation:"
  echo "  1) Scale a specific stateless service (in-stack worker replication)"
  echo "  2) Launch an additional simulated compute node (Node 2, Node 3...)"
  echo "  3) List active scaled nodes & containers"
  echo "  4) Stop a simulated compute node"
  echo "  5) Exit"
  echo ""
  read -rp "Enter choice [1-5]: " choice

  case "$choice" in
    1)
      scale_service "$bin" "$compose_file"
      ;;
    2)
      scale_node "$bin" "$compose_file" "$pkg_dir"
      ;;
    3)
      list_nodes
      ;;
    4)
      down_node "$bin" "$compose_file"
      ;;
    *)
      echo "Exiting scaling manager."
      exit 0
      ;;
  esac
}

main() {
  local bin=$1
  local compose_file=$2
  local scripts_root=$3
  local pkg_dir=$4
  shift 4 || true

  local subcmd=${1:-""}
  shift || true

  case "$subcmd" in
    service)
      scale_service "$bin" "$compose_file" "$@"
      ;;
    node)
      scale_node "$bin" "$compose_file" "$pkg_dir" "$@"
      ;;
    down-node)
      down_node "$bin" "$compose_file" "$@"
      ;;
    list)
      list_nodes
      ;;
    "")
      interactive_scale_menu "$bin" "$compose_file" "$pkg_dir"
      ;;
    *)
      # If first argument is a service name like llmobs-temporal
      if [ -n "$1" ]; then
        scale_service "$bin" "$compose_file" "$subcmd" "$1"
      else
        scale_service "$bin" "$compose_file" "$subcmd"
      fi
      ;;
  esac
}

main "$@"
