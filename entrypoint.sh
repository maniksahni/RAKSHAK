#!/bin/sh
# RAKSHAK bulletproof entrypoint — guarantees $PORT is expanded before gunicorn
PORT="${PORT:-8080}"
echo "=== RAKSHAK running init_db.py ==="
python /app/init_db.py
echo "=== RAKSHAK starting on port ${PORT} ==="
exec gunicorn \
  --worker-class eventlet \
  -w 2 \
  --worker-connections 1000 \
  --bind "0.0.0.0:${PORT}" \
  --timeout 120 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile - \
  wsgi:app
