"""Root entry point for GPON God-Mode REST API Daemon.

Forwards to src/gpon_godmode/api.py.
Default port: 8254 (niche port, avoiding 5000/8080).
"""

from gpon_godmode.api import app, run_daemon

if __name__ == "__main__":
    run_daemon()
