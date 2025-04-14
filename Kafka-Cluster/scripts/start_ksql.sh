#!/bin/bash
for script in ${KSQL_START_SCRIPTS//:/ }; do
    echo "Running script "$script
    ksql ${KSQL_URL} --file scripts/$script
done
