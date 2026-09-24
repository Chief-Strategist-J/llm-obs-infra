#!/usr/bin/env bash
# ALGORITHM:
# 1. Route stdout and stderr to startup-script.log and syslog
# 2. Update apt and install required utility packages
# 3. Import Docker GPG keyring and configure repository
# 4. Install Docker Engine, CLI, and Compose plugin
# 5. Configure Docker daemon log rotation and enable service

set -euo pipefail

exec > >(tee -a /var/log/startup-script.log | logger -t startup-script -s 2>/dev/console) 2>&1

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    netcat-openbsd \
    jq \
    htop \
    ufw

mkdir -p /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
fi

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y --no-install-recommends docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl enable docker
systemctl start docker

mkdir -p /etc/docker
cat <<'DOCKER_CFG' > /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  }
}
DOCKER_CFG

systemctl restart docker
