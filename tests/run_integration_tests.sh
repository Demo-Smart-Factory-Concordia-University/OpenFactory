#!/bin/bash
# Runs integration tests

# setup needed environment
docker compose -f tests/integration-tests/docker-compose.yml up -d
python tests/integration-tests/wait_ksql_ready.py

# build Docker images
docker build -f tests/integration-tests/apps/Dockerfile -t ofa/test-app .

# run the tests
# python tests/run_integration_tests.py
