# Use Microsoft Dev Containers Python base image (includes dev tools, non-root user, etc.)
FROM mcr.microsoft.com/devcontainers/python:3.11

# Optional: install additional tools you may need
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
 && rm -rf /var/lib/apt/lists/*

# Set working directory (Microsoft's base already sets this to /workspaces/<repo>, but you can override)
WORKDIR /workspace
