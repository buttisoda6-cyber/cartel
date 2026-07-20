#!/bin/bash
set -e

echo "Starting Cloudflare SQL tunnel..."

cloudflared access tcp \
  --hostname ${CF_TUNNEL_HOSTNAME} \
  --url localhost:15433 \
  --loglevel debug &
CF_PID=$!

sleep 5

echo "Testing TCP..."

python - <<'EOF'
import socket

try:
    s = socket.create_connection(("127.0.0.1",15433), timeout=10)
    print("✅ TCP CONNECTED")
    s.close()
except Exception as e:
    print("❌ TCP FAILED:", e)
EOF

python main.py

echo "Starting FastAPI..."
python main.py
