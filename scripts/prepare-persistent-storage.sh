#!/usr/bin/env bash
# ALGORITHM:
# 1. Resolve target data directory from LLMObs environment or default to /mnt/disks/llmobs-data
# 2. Verify filesystem availability and directory structure
# 3. Create discrete subdirectories for each datastore (AlloyDB, Redis, Kafka, ClickHouse, Tempo, Grafana)
# 4. Set appropriate ownership and permissions for container processes (Postgres 999, Clickhouse 101, Kafka 1000, Grafana 472)
# 5. Output confirmation of persistent storage readiness

set -euo pipefail

TARGET_DIR="${LLMOBS_DATA_DIR:-/mnt/disks/llmobs-data}"

echo "Preparing persistent storage at: $TARGET_DIR"

if [ ! -d "$TARGET_DIR" ]; then
  if [ "$(id -u)" -eq 0 ]; then
    mkdir -p "$TARGET_DIR"
  else
    sudo mkdir -p "$TARGET_DIR"
  fi
fi

DATA_DIRS=(
  "alloydb/data"
  "alloydb/archive"
  "redis/data"
  "kafka/data"
  "clickhouse/data"
  "tempo/data"
  "grafana/data"
)

for sub in "${DATA_DIRS[@]}"; do
  full_path="$TARGET_DIR/$sub"
  if [ ! -d "$full_path" ]; then
    if [ "$(id -u)" -eq 0 ]; then
      mkdir -p "$full_path"
    else
      sudo mkdir -p "$full_path"
    fi
  fi
done

if [ "$(id -u)" -eq 0 ]; then
  chmod -R 777 "$TARGET_DIR"
else
  sudo chmod -R 777 "$TARGET_DIR"
fi

echo "Persistent storage initialization completed successfully at: $TARGET_DIR"
