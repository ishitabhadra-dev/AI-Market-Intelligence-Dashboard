#!/bin/sh
set -e
mkdir -p /app/data
# Unset empty AWS_PROFILE (breaks boto3 in containers)
if [ -z "${AWS_PROFILE:-}" ]; then
  unset AWS_PROFILE
fi
exec "$@"
