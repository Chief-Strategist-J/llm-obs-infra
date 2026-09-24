#!/usr/bin/env bash
# ALGORITHM:
# 1. Resolve service name dynamically from Terraform outputs or directory structure
# 2. Query Managed Instance Group members and zone from Terraform outputs
# 3. Wait for VM instance connectivity and remote Docker daemon availability
# 4. Sync service compose definitions, environment files, and configurations to remote VM
# 5. Execute docker compose up on target VM to deploy containerized application stack
# 6. Query remote container health status and display endpoint connection details

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_DIR="$(dirname "$INFRA_DIR")"
ROOT_DIR="$(dirname "$(dirname "$SERVICE_DIR")")"
cd "$INFRA_DIR"

command -v terraform >/dev/null 2>&1 || { echo "Error: terraform is not installed"; exit 1; }
command -v gcloud >/dev/null 2>&1 || { echo "Error: gcloud is not installed"; exit 1; }

SERVICE_NAME=$(terraform output -raw service_name 2>/dev/null || basename "$SERVICE_DIR")
PROJECT_ID=$(terraform output -raw service_account_email 2>/dev/null | awk -F'@' '{print $2}' | cut -d'.' -f1 || gcloud config get-value project 2>/dev/null)
IGM_NAME=$(terraform output -raw instance_group_manager_name 2>/dev/null || echo "llmobs-${SERVICE_NAME}-node-igm")
ZONE=$(grep -E '^[[:space:]]*gcp_zone[[:space:]]*=' terraform.tfvars | sed -E 's/.*=[[:space:]]*"([^"]+)".*/\1/' || echo "us-central1-a")

echo "Resolving instances for service '${SERVICE_NAME}' from IGM '${IGM_NAME}' in zone '${ZONE}'..."

INSTANCES=()
for i in {1..30}; do
  INSTANCES=($(gcloud compute instance-groups list-instances "$IGM_NAME" --zone="$ZONE" --project="$PROJECT_ID" --format="value(NAME)" 2>/dev/null || true))
  if [ ${#INSTANCES[@]} -gt 0 ]; then
    break
  fi
  echo "Waiting for compute instances to be provisioned by instance group... (attempt $i/30)"
  sleep 5
done

if [ ${#INSTANCES[@]} -eq 0 ]; then
  echo "Error: No instances currently running in instance group $IGM_NAME"
  exit 1
fi

TARGET_INSTANCE="${INSTANCES[0]}"
echo "Target compute instance selected: $TARGET_INSTANCE"

echo "Waiting for SSH and Docker daemon readiness on $TARGET_INSTANCE..."
for i in {1..30}; do
  if gcloud compute ssh "$TARGET_INSTANCE" --zone="$ZONE" --project="$PROJECT_ID" --command="docker info >/dev/null 2>&1" >/dev/null 2>&1; then
    echo "Docker daemon is ready on $TARGET_INSTANCE"
    break
  fi
  echo "Waiting for startup script to finish installing Docker... ($i/30)"
  sleep 10
done

REMOTE_DIR="/opt/llmobs/services/${SERVICE_NAME}"
gcloud compute ssh "$TARGET_INSTANCE" --zone="$ZONE" --project="$PROJECT_ID" --command="sudo mkdir -p $REMOTE_DIR/config && sudo chown -R \$(whoami) /opt/llmobs"

echo "Transferring service configuration files to $TARGET_INSTANCE..."
if [ -f "$SERVICE_DIR/docker-compose.yml" ]; then
  gcloud compute scp "$SERVICE_DIR/docker-compose.yml" "${TARGET_INSTANCE}:${REMOTE_DIR}/docker-compose.yml" --zone="$ZONE" --project="$PROJECT_ID"
fi

if [ -f "$SERVICE_DIR/.env" ]; then
  gcloud compute scp "$SERVICE_DIR/.env" "${TARGET_INSTANCE}:${REMOTE_DIR}/.env" --zone="$ZONE" --project="$PROJECT_ID"
elif [ -f "$SERVICE_DIR/.env.example" ]; then
  gcloud compute scp "$SERVICE_DIR/.env.example" "${TARGET_INSTANCE}:${REMOTE_DIR}/.env" --zone="$ZONE" --project="$PROJECT_ID"
fi

if [ -d "$ROOT_DIR/config" ]; then
  gcloud compute scp --recurse "$ROOT_DIR/config" "${TARGET_INSTANCE}:${REMOTE_DIR}/config/" --zone="$ZONE" --project="$PROJECT_ID" || true
fi

echo "Deploying ${SERVICE_NAME} service stack on $TARGET_INSTANCE..."
gcloud compute ssh "$TARGET_INSTANCE" --zone="$ZONE" --project="$PROJECT_ID" --command="cd $REMOTE_DIR && docker compose --profile ${SERVICE_NAME} up -d || docker compose up -d"

echo "Verifying running containers on $TARGET_INSTANCE:"
gcloud compute ssh "$TARGET_INSTANCE" --zone="$ZONE" --project="$PROJECT_ID" --command="cd $REMOTE_DIR && docker compose ps"

EXTERNAL_IP=$(gcloud compute instances describe "$TARGET_INSTANCE" --zone="$ZONE" --project="$PROJECT_ID" --format="get(networkInterfaces[0].accessConfigs[0].natIP)" 2>/dev/null || echo "N/A")
INTERNAL_IP=$(gcloud compute instances describe "$TARGET_INSTANCE" --zone="$ZONE" --project="$PROJECT_ID" --format="get(networkInterfaces[0].networkIP)" 2>/dev/null || echo "N/A")

echo "============================================================"
echo "Service '${SERVICE_NAME}' deployment succeeded!"
echo "Instance:     $TARGET_INSTANCE"
echo "Public IP:    $EXTERNAL_IP"
echo "Private IP:   $INTERNAL_IP"
echo "SSH Command:  gcloud compute ssh $TARGET_INSTANCE --zone=$ZONE --project=$PROJECT_ID"
echo "============================================================"
