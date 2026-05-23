#!/usr/bin/env python3
"""
ESG+SCRM Demo Daemon Launcher
Fully daemonizes so servers survive terminal close.
Auto-restarts servers if they crash.
"""
import os
import sys
import time
import signal
import subprocess
import urllib.request
import urllib.error

# Auto-detect repo directory from daemon script location
# The daemon is copied to /tmp/esgd.py, so use __file__ to find original location
_DAEMON_ORIGINAL = os.path.join(os.path.dirname(__file__))  # Path where daemon was originally located
# When run from /tmp/esgd.py, __file__ is /tmp/esgd.py
# We need REPO_DIR — the daemon was copied from repo root
# Use the fact that the daemon IS the original _start-demo-daemon.py in the repo root
_REPO_DIR = os.path.dirname(os.path.abspath(__file__))
# If __file__ is /tmp/esgd.py, we need to find repo root differently
# The daemon was originally at $REPO_DIR/_start-demo-daemon.py
# Since it's now at /tmp/esgd.py, we use a heuristic:
# Look for the marker file that tells us where we are
if os.path.exists("/tmp/esgd.py"):
    # We're running from /tmp — find the real repo by looking for the marker
    # The repo always has src/api/main.py
    import glob
    possible_repos = glob.glob("/Users/kshitijverma/Downloads/esg-scrm-*/")
    for candidate in possible_repos:
        if os.path.exists(os.path.join(candidate, "src", "api", "main.py")):
            REPO_DIR = candidate.rstrip("/")
            break
    else:
        # Fallback: try the most recent download dir
        REPO_DIR = "/Users/kshitijverma/Downloads/esg-scrm-f8452b89453fd60b9b5c00020f783c9759d24c32"
else:
    # Running from repo dir directly
    REPO_DIR = os.path.dirname(os.path.abspath(__file__))

WEB_DIR = os.path.join(REPO_DIR, "apps", "web")
BACKEND_PORT = 8001
FRONTEND_PORT = 5173
LOG_DIR = "/tmp"

def log(msg, end="\n", flush=True):
    print(msg, end=end, flush=flush)

def check(url, timeout=3):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.getcode() == 200
    except (urllib.error.URLError, OSError):
        return False

def wait_for_build():
    """Wait for npm build to complete by watching the dist folder."""
    dist = os.path.join(WEB_DIR, "dist")
    marker = os.path.join(dist, "index.html")
    log("Building frontend... (this takes ~10-30s)")
    start = time.time()
    while time.time() - start < 120:
        if os.path.exists(marker):
            return True
        time.sleep(2)
    return False

def main():
    log("ESG+SCRM Demo Launcher")
    log("========================")
    log(f"Repo: {REPO_DIR}")
    log("")

    # Kill existing servers
    for port in [BACKEND_PORT, FRONTEND_PORT]:
        try:
            out = subprocess.check_output(
                ["lsof", "-ti", f":{port}"], text=True
            ).strip()
            if out:
                subprocess.run(["kill", "-9", out], capture_output=True)
                log(f"Killed existing server on {port}")
        except subprocess.CalledProcessError:
            pass
    time.sleep(1)

    # Build frontend
    log("")
    if not wait_for_build():
        log("ERROR: Frontend build failed")
        sys.exit(1)

    # Start backend
    backend_log = open(f"{LOG_DIR}/esg-backend.log", "a")
    venv_python = os.path.join(REPO_DIR, ".venv", "bin", "python")
    backend_proc = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "src.api.main:app",
         "--port", str(BACKEND_PORT)],
        cwd=REPO_DIR,
        stdout=backend_log,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid  # new session — survives terminal close
    )
    log(f"Backend started (PID {backend_proc.pid})")

    # Start frontend
    frontend_log = open(f"{LOG_DIR}/esg-frontend.log", "a")
    frontend_proc = subprocess.Popen(
        [os.path.join(WEB_DIR, "node_modules", ".bin", "vite"), "preview",
         "--port", str(FRONTEND_PORT)],
        cwd=WEB_DIR,  # cd to web dir so vite finds the dist/ correctly
        stdout=frontend_log,
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid  # new session — survives terminal close
    )
    log(f"Frontend started (PID {frontend_proc.pid})")

    log("")
    log("Waiting for servers to come up...")

    # Wait for both servers
    backend_ready = False
    frontend_ready = False
    for i in range(30):  # 60 seconds max
        time.sleep(2)
        if not backend_ready and check(f"http://localhost:{BACKEND_PORT}/api/health"):
            backend_ready = True
            log(f"Backend (:{BACKEND_PORT}): READY")
        if not frontend_ready and check(f"http://localhost:{FRONTEND_PORT}"):
            frontend_ready = True
            log(f"Frontend (:{FRONTEND_PORT}): READY")
        if backend_ready and frontend_ready:
            break
        log(".", end="", flush=True)

    log("")
    if backend_ready and frontend_ready:
        log("========================")
        log("All servers READY")
        log("")
        log("  Dashboard:     http://localhost:5173")
        log("  API Docs:     http://localhost:8001/docs")
        log("  API Health:   http://localhost:8001/api/health")
        log("  API Org:      http://localhost:8001/api/org")
        log("  Live Metrics: http://localhost:8001/api/dashboard/live")
        log("")
        # Open browser from the daemon process (not a background subshell)
        subprocess.call(["open", "/tmp/esg-links.html"])
        log("Browser opened.")
        log("")
        log("Ctrl+C to stop all servers")
    else:
        log("ERROR: Some servers failed to start")
        if not backend_ready:
            log("  Backend failed — check /tmp/esg-backend.log")
        if not frontend_ready:
            log("  Frontend failed — check /tmp/esg-frontend.log")

    log("")
    log("Auto-restarting if servers crash...")

    # Monitor loop — restart dead servers
    while True:
        time.sleep(5)

        # Check and restart backend
        venv_python = os.path.join(REPO_DIR, ".venv", "bin", "python")
        if backend_proc.poll() is not None:  # process died
            log("Backend died! Restarting...")
            backend_log = open(f"{LOG_DIR}/esg-backend.log", "a")
            backend_proc = subprocess.Popen(
                [venv_python, "-m", "uvicorn", "src.api.main:app",
                 "--port", str(BACKEND_PORT)],
                cwd=REPO_DIR,
                stdout=backend_log,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            log(f"Backend restarted (PID {backend_proc.pid})")

        # Check and restart frontend
        if frontend_proc.poll() is not None:  # process died
            log("Frontend died! Restarting...")
            frontend_log = open(f"{LOG_DIR}/esg-frontend.log", "a")
            frontend_proc = subprocess.Popen(
                [os.path.join(WEB_DIR, "node_modules", ".bin", "vite"), "preview",
                 "--port", str(FRONTEND_PORT)],
                cwd=WEB_DIR,
                stdout=frontend_log,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            log(f"Frontend restarted (PID {frontend_proc.pid})")

        # Also verify they're responding (not just running)
        if backend_proc.poll() is None and not check(f"http://localhost:{BACKEND_PORT}/api/health"):
            log("Backend not responding! Restarting...")
            backend_proc.terminate()
            backend_log = open(f"{LOG_DIR}/esg-backend.log", "a")
            backend_proc = subprocess.Popen(
                [venv_python, "-m", "uvicorn", "src.api.main:app",
                 "--port", str(BACKEND_PORT)],
                cwd=REPO_DIR,
                stdout=backend_log,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            log(f"Backend restarted (PID {backend_proc.pid})")

        if frontend_proc.poll() is None and not check(f"http://localhost:{FRONTEND_PORT}"):
            log("Frontend not responding! Restarting...")
            frontend_proc.terminate()
            frontend_log = open(f"{LOG_DIR}/esg-frontend.log", "a")
            frontend_proc = subprocess.Popen(
                [os.path.join(WEB_DIR, "node_modules", ".bin", "vite"), "preview",
                 "--port", str(FRONTEND_PORT)],
                cwd=WEB_DIR,
                stdout=frontend_log,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid
            )
            log(f"Frontend restarted (PID {frontend_proc.pid})")


if __name__ == "__main__":
    # Fork 1: child runs the daemon, parent exits
    pid = os.fork()
    if pid > 0:
        print("ESG+SCRM Demo starting in background...", flush=True)
        print("This window can be closed — servers keep running.", flush=True)
        print("", flush=True)
        sys.exit(0)

    # Child: become session leader (survives terminal close)
    os.setsid()

    # Fork 2: prevent any future fork from being attached to terminal
    pid2 = os.fork()
    if pid2 > 0:
        sys.exit(0)

    # Grandchild: the actual daemon
    os.chdir(REPO_DIR)
    os.umask(0)
    # Detach stdin from terminal (survives terminal close)
    fd = os.open(os.devnull, os.O_RDWR)
    os.dup2(fd, 0)   # stdin -> /dev/null
    os.close(fd)
    # stdout/stderr stay connected so main() can log

    main()
