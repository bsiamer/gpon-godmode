#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"

# Legacy syntax mapping for backward compatibility
if [ "$1" == "port" ]; then
    shift
    exec python -m gpon_godmode.cli ports add "$@"
fi

if [ "$1" == "enable-service" ]; then
    mkdir -p ~/.config/systemd/user
    cp "$SCRIPT_DIR/systemd/gpon.socket" "$SCRIPT_DIR/systemd/gpon.service" ~/.config/systemd/user/
    systemctl --user daemon-reload
    systemctl --user enable --now gpon.socket
    echo "GPON God-Mode on-demand socket activation enabled!"
    echo "Port 8254 is now listening with 0 MB idle RAM. Calls will wake it up automatically."
    exit 0
fi

if [ "$1" == "disable-service" ]; then
    systemctl --user disable --now gpon.socket gpon.service 2>/dev/null || true
    echo "GPON God-Mode socket activation disabled."
    exit 0
fi

if [ "$1" == "service-status" ]; then
    systemctl --user status gpon.socket gpon.service
    exit 0
fi

if [ "$1" == "start" ] || [ "$1" == "daemon" ] || [ "$1" == "api" ]; then
    shift
    exec python -m gpon_godmode.cli daemon "$@"
fi

exec python -m gpon_godmode.cli "$@"
