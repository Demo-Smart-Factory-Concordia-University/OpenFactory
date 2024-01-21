#!/bin/bash
for script in ${KSQL_START_SCRIPTS//:/ }; do
    ksql http://ksqldb-server:8088 --file scripts/$script
done
