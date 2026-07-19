#!/bin/bash
set -e

echo "Starting Cloudflare SQL tunnel..."

cloudflared access tcp \
  --hostname ${CF_TUNNEL_HOSTNAME} \
  --url localhost:15433 \
  --loglevel debug &
CF_PID=$!

sleep 5

echo "Checking local port..."
nc -vz 127.0.0.1 15433 || true

echo "Starting FastAPI..."
python main.py
