#!/bin/bash
set -e

echo "Starting Cloudflare SQL tunnel..."

cloudflared access tcp \
  --hostname ${CF_TUNNEL_HOSTNAME} \
  --url localhost:15433 \
  --loglevel debug &
CF_PID=$!

sleep 5

echo "Starting FastAPI..."
python main.py
