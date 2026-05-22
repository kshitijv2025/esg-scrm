#!/bin/bash
# ESG+SCRM Product Launcher
# Double-click or: open start-product.command
# Kills old servers, starts fresh.
# Terminal can be closed — servers keep running.

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
WEB_DIR="$REPO_DIR/apps/web"
BACKEND_PORT=8001
FRONTEND_PORT=5173

cd "$REPO_DIR"

echo "ESG+SCRM Product Launcher"
echo "========================"
echo ""
echo "Starting servers..."

# Kill any existing servers
lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null
lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null
sleep 1

# Start backend (survives terminal close via nohup)
cd "$REPO_DIR"
nohup .venv/bin/python -m uvicorn src.api.main:app --port $BACKEND_PORT > /tmp/esg-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID $BACKEND_PID)"

# Start frontend (dev server with proxy, survives terminal close via nohup)
cd "$WEB_DIR"
nohup ./node_modules/.bin/vite --port $FRONTEND_PORT > /tmp/esg-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID $FRONTEND_PID)"

# Wait for both servers
READY=0
for i in $(seq 1 30); do
  sleep 2
  BE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$BACKEND_PORT/api/health 2>/dev/null)
  FE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$FRONTEND_PORT 2>/dev/null)
  if [ "$BE" = "200" ] && [ "$FE" = "200" ]; then
    echo "Servers ready!"
    READY=1
    break
  fi
  echo -n "."
done

echo ""
if [ "$READY" = "1" ]; then
  echo "========================="
  echo "All servers READY"
  echo ""
  echo "  Dashboard:  http://localhost:$FRONTEND_PORT"
  echo "  API Docs:  http://localhost:$BACKEND_PORT/docs"
  echo "  Demo HTML: http://localhost:$FRONTEND_PORT/demo.html"
  echo ""
  echo "  Login:     admin@textilebd.com"
  echo "  Password:  admin123"
  echo ""
  echo "This terminal can be safely closed."
  echo "Servers are running in the background."
  echo ""
  echo "To stop: lsof -ti :$BACKEND_PORT | xargs kill -9 && lsof -ti :$FRONTEND_PORT | xargs kill -9"
else
  echo "Servers did not start in time."
  echo "Backend log: /tmp/esg-backend.log"
  echo "Frontend log: /tmp/esg-frontend.log"
fi
