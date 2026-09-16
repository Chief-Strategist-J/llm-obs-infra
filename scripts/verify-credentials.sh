#!/usr/bin/env bash
set -e

USAGE="Usage: $0 [auth|user|payment|notifications|storage|audit] [options...]"

SERVICE=${1:-auth}

# Check if first arg is an option flag
if [[ "$SERVICE" == --* ]]; then
  SERVICE="auth"
else
  shift || true
fi

SCRIPT_PATH="services/$SERVICE/scripts/verify-credentials.sh"

if [ ! -f "$SCRIPT_PATH" ]; then
  echo "Error: Service '$SERVICE' not found."
  echo "$USAGE"
  exit 1
fi

bash "$SCRIPT_PATH" "$@"
