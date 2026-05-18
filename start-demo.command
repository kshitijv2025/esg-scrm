#!/bin/bash
# ESG+SCRM Demo Launcher
# Double-click or: open start-demo.command
# Kills old servers, starts fresh, auto-restarts if crashed.
# Terminal can be closed — servers keep running.

REPO_DIR="/Users/kshitijverma/Desktop/Class Notes/Term 4/Machine Learning For Decision Making/ESG SCRM"
cd "$REPO_DIR"

echo "ESG+SCRM Demo Launcher"
echo "======================"
echo ""
echo "Starting servers..."

# Kill any existing servers
lsof -ti :8001 | xargs kill -9 2>/dev/null
lsof -ti :5173 | xargs kill -9 2>/dev/null
sleep 1

# Copy daemon to /tmp to avoid macOS "Operation not permitted" on paths with spaces
cp "$REPO_DIR/_start-demo-daemon.py" /tmp/esgd.py

# Generate the links HTML
cat > /tmp/esg-links.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>ESG+SCRM Demo Links</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #e6edf3; padding: 40px; }
    h1 { color: #22c55e; margin-bottom: 8px; }
    .subtitle { color: #8b949e; margin-bottom: 32px; }
    .links { display: grid; gap: 16px; max-width: 700px; }
    .link-card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px 24px; text-decoration: none; transition: border-color 0.2s, transform 0.1s; }
    .link-card:hover { border-color: #22c55e; transform: translateY(-1px); }
    .link-title { color: #22c55e; font-size: 16px; font-weight: 600; margin-bottom: 4px; }
    .link-desc { color: #8b949e; font-size: 13px; }
    .link-url { color: #58a6ff; font-size: 12px; margin-top: 6px; font-family: monospace; }
    .badge { display: inline-block; background: #22c55e20; color: #22c55e; font-size: 11px; padding: 2px 8px; border-radius: 999px; margin-left: 8px; }
    .badge-backend { background: #f59e0b20; color: #f59e0b; }
  </style>
</head>
<body>
  <h1>ESG+SCRM Demo</h1>
  <p class="subtitle">Bangladesh Export Textiles Ltd. — Investor Demo</p>
  <div class="links">
    <a class="link-card" href="http://localhost:5173">
      <div class="link-title">Frontend Dashboard <span class="badge">MAIN</span></div>
      <div class="link-desc">Live ESG dashboard with metrics, trend chart, framework comparison</div>
      <div class="link-url">http://localhost:5173</div>
    </a>
    <a class="link-card" href="http://localhost:8001/docs">
      <div class="link-title">API Docs <span class="badge badge-backend">BACKEND</span></div>
      <div class="link-desc">FastAPI interactive docs — try all endpoints here</div>
      <div class="link-url">http://localhost:8001/docs</div>
    </a>
    <a class="link-card" href="http://localhost:8001/api/health">
      <div class="link-title">API Health <span class="badge badge-backend">BACKEND</span></div>
      <div class="link-desc">Backend status check</div>
      <div class="link-url">http://localhost:8001/api/health</div>
    </a>
    <a class="link-card" href="http://localhost:8001/api/org">
      <div class="link-title">Organization <span class="badge badge-backend">BACKEND</span></div>
      <div class="link-desc">Demo org: Bangladesh Export Textiles Ltd., H&M supplier</div>
      <div class="link-url">http://localhost:8001/api/org</div>
    </a>
    <a class="link-card" href="http://localhost:8001/api/dashboard/live">
      <div class="link-title">Live Metrics <span class="badge badge-backend">BACKEND</span></div>
      <div class="link-desc">Energy, Emissions, Water, Scope3 — current values with hash chains</div>
      <div class="link-url">http://localhost:8001/api/dashboard/live</div>
    </a>
  </div>
</body>
</html>
HTMLEOF

# Start the daemon from /tmp (avoids macOS path-with-spaces issues)
python3 /tmp/esgd.py &
DAEMON_PID=$!

# Wait for both servers to come up
READY=0
for i in $(seq 1 30); do
  sleep 2
  BE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/health 2>/dev/null)
  FE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5173 2>/dev/null)
  if [ "$BE" = "200" ] && [ "$FE" = "200" ]; then
    echo "Servers ready!"
    READY=1
    break
  fi
  echo -n "."
done

echo ""
if [ "$READY" = "1" ]; then
  open /tmp/esg-links.html
else
  echo "Servers did not start in time — check /tmp/esg-backend.log"
fi

echo ""
echo "Dashboard:     http://localhost:5173"
echo "API Docs:     http://localhost:8001/docs"
echo "API Health:   http://localhost:8001/api/health"
echo "API Org:      http://localhost:8001/api/org"
echo "Live Metrics: http://localhost:8001/api/dashboard/live"
echo ""
echo "This terminal can be safely closed."
echo "Servers auto-restart if they crash."
echo ""
echo "To stop: lsof -ti :8001 | xargs kill -9 && lsof -ti :5173 | xargs kill -9"
echo ""
