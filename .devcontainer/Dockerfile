# Use a base image that supports Docker
FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu

# Install Docker only if it's not already installed
RUN if ! command -v docker &> /dev/null; then \
    apt-get update && \
    apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg2 \
    lsb-release \
    sudo && \
    curl -fsSL https://get.docker.com -o get-docker.sh && \
    sh get-docker.sh && \
    rm get-docker.sh && \
    usermod -aG docker vscode; \
    fi

# Install Docker Compose if needed
RUN if ! command -v docker-compose &> /dev/null; then \
    curl -L "https://github.com/docker/compose/releases/download/$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r .tag_name)/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose; \
    fi
