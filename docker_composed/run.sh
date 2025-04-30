#!/bin/bash
# Custom startup script for Spark container.
echo "Starting Spark container with custom script..."

if [ "$#" -eq 0 ]; then
  exec /opt/bitnami/scripts/spark/entrypoint.sh /run.sh
else
  exec /opt/bitnami/scripts/spark/entrypoint.sh "$@"
fi
