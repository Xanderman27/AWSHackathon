#!/usr/bin/env bash
# Persist the AWS credentials already exported in THIS shell to ~/.aws, so every process
# picks them up: the API, the pre-flight, and any new terminal. Reads from the environment
# and prints nothing secret.
#
#   source scripts/save_aws_creds.sh      (or just run it)
set -u

if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
  echo "No AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY in this shell."
  echo "Export them here first, then run this again from the same terminal."
  exit 1
fi

mkdir -p ~/.aws && chmod 700 ~/.aws

{
  echo "[default]"
  echo "aws_access_key_id=${AWS_ACCESS_KEY_ID}"
  echo "aws_secret_access_key=${AWS_SECRET_ACCESS_KEY}"
  # Workshop Studio issues temporary keys; long-lived ones have no session token.
  [ -n "${AWS_SESSION_TOKEN:-}" ] && echo "aws_session_token=${AWS_SESSION_TOKEN}"
} > ~/.aws/credentials
chmod 600 ~/.aws/credentials

printf '[default]\nregion=%s\n' "${AWS_REGION:-us-east-1}" > ~/.aws/config
chmod 600 ~/.aws/config

echo "Wrote ~/.aws/credentials ($(wc -c < ~/.aws/credentials | tr -d ' ') bytes)"
echo "Region: ${AWS_REGION:-us-east-1}"
[ -n "${AWS_SESSION_TOKEN:-}" ] && echo "Session token: included (temporary credentials)"
echo
echo "Now tell Claude to re-run the pre-flight."
