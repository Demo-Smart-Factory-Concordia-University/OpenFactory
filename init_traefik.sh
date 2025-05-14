#!/bin/bash

# --------------------------------------------------------------------
# Traefik Deployment Script for Traefik to the OpenFactory cluster
# --------------------------------------------------------------------
# Sets up the required overlay network and 
# deploys the Traefik reverse proxy stack using Docker Swarm.
#
# Requirements:
#   - Docker Swarm must be initialized
#   - This host must be a Swarm manager
#   - A `traefik.yml` file must be in the current directory
#
# Usage:
#   1. Set the OPENFACTORY_DOMAIN environment variable:
#        export OPENFACTORY_DOMAIN=example.com
#
#   2. Run this script:
#        ./deploy-traefik.sh
#
# Output:
#   - Ensures the traefik-public overlay network exists
#   - Deploys the Traefik stack with the given domain
#   - Shows live status using --detach=false
#
# Dashboard:
#   Access Traefik dashboard at: http://traefik.${OPENFACTORY_DOMAIN}
# --------------------------------------------------------------------

# Exit on error
set -e

# Check that the OPENFACTORY_DOMAIN environment variable is set
if [ -z "$OPENFACTORY_DOMAIN" ]; then
  echo "ERROR: OPENFACTORY_DOMAIN is not set."
  echo "Please set it with: export OPENFACTORY_DOMAIN=example.com"
  exit 1
fi

STACK_NAME=traefik
COMPOSE_FILE=traefik.yml
TRAEFIK_NETWORK=traefik-public

# Step 1: Create overlay network if it doesn't exist
if ! docker network inspect "$TRAEFIK_NETWORK" >/dev/null 2>&1; then
  echo "Creating overlay network: $TRAEFIK_NETWORK"
  docker network create --driver=overlay --attachable "$TRAEFIK_NETWORK"
else
  echo "Overlay network already exists: $TRAEFIK_NETWORK"
fi

# Step 2: Deploy the stack
echo "Deploying stack '$STACK_NAME' with domain '$OPENFACTORY_DOMAIN'"
docker stack deploy -c "$COMPOSE_FILE" --detach=false "$STACK_NAME"
