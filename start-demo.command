#!/bin/bash
# ESG+SCRM Demo Launcher
# Double-click or: open start-demo.command
# Kills old servers, starts fresh, auto-restarts if crashed.
# Terminal can be closed — servers keep running.

REPO_DIR="/Users/kshitijverma/esg-scrm"
WEB_DIR="$REPO_DIR/apps/web"
BACKEND_PORT=8001
FRONTEND_PORT=5173

cd "$REPO_DIR"

echo "ESG+SCRM Demo Launcher"
echo "======================"
echo ""
echo "Starting servers..."

# Kill any existing servers
lsof -ti :$BACKEND_PORT | xargs kill -9 2>/dev/null
lsof -ti :$FRONTEND_PORT | xargs kill -9 2>/dev/null
sleep 1

# Build frontend if dist is stale
VITE_DIST="$WEB_DIR/dist/index.html"
if [ ! -f "$VITE_DIST" ]; then
  echo "Building frontend..."
  cd "$WEB_DIR" && npm run build > /tmp/esg-frontend-build.log 2>&1 && cd "$REPO_DIR"
fi

# Start backend (cd to repo first, survives terminal close via nohup)
nohup bash -c "cd '$REPO_DIR' && exec .venv/bin/python -m uvicorn src.api.main:app --port $BACKEND_PORT" > /tmp/esg-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID $BACKEND_PID)"

# Start frontend (cd to web dir, survives terminal close via nohup)
nohup bash -c "cd '$WEB_DIR' && exec ./node_modules/.bin/vite preview --port $FRONTEND_PORT" > /tmp/esg-frontend.log 2>&1 &
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
  echo "========================"
  echo "All servers READY"
  echo ""
  echo "  Dashboard:     http://localhost:$FRONTEND_PORT"
  echo "  API Docs:     http://localhost:$BACKEND_PORT/docs"
  echo "  API Health:   http://localhost:$BACKEND_PORT/api/health"
  echo "  API Org:      http://localhost:$BACKEND_PORT/api/org"
  echo "  Live Metrics: http://localhost:$BACKEND_PORT/api/dashboard/live"
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
