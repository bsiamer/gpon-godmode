#!/bin/bash

API_URL="http://127.0.0.1:5000"

function show_help() {
    echo "========================================="
    echo "       GPON GOD-MODE CLI WRAPPER         "
    echo "========================================="
    echo "Usage: ./gpon.sh [command] [args...]"
    echo ""
    echo "Commands:"
    echo "  start                       Start the background API server"
    echo "  stop                        Stop the background API server"
    echo "  dns <primary> <secondary>     Force-set LAN DNS servers"
echo "  ipv6-dns <pri> <sec>          Force-set IPv6 DNS servers"
echo "  block <mac_address>           Block a device from the Wi-Fi"
echo "  wifi-pass <new_password>      Change the Wi-Fi password"
    echo "  port <ext> <int> <ip>       Force open a port forward"
    echo "  reboot                      Reboot the GPON gateway"
    echo "========================================="
}

if [ "$1" == "start" ]; then
    echo "Starting API server..."
    source venv/bin/activate
    nohup python api.py > api.log 2>&1 &
    echo $! > api.pid
    echo "API Server started! Ready to accept commands."
    exit 0
fi

if [ "$1" == "stop" ]; then
    if [ -f api.pid ]; then
        kill $(cat api.pid) || true
        rm api.pid
        echo "API Server stopped."
    else
        echo "API Server is not running (api.pid not found)."
    fi
    exit 0
fi

if [ "$1" == "dns" ]; then
    if [ -z "$2" ] || [ -z "$3" ]; then
        echo "Usage: ./gpon.sh dns <primary_dns> <secondary_dns>"
        exit 1
    fi
    PAYLOAD=$(python -c "import json, sys; print(json.dumps({
      'main_menu': 'Network',
      'sub_menu': 'LAN',
      'settings': { 'firstDns': sys.argv[1], 'secondDns': sys.argv[2] },
      'submit_button': 'save2'
    }))" "$2" "$3")
    curl -N -X POST $API_URL/forceset -H "Content-Type: application/json" -d "$PAYLOAD"
    echo ""
    exit 0
fi

if [ "$1" == "ipv6-dns" ]; then
    if [ -z "$2" ] || [ -z "$3" ]; then
        echo "Usage: ./gpon.sh ipv6-dns <primary_dns> <secondary_dns>"
        exit 1
    fi
    PAYLOAD=$(python -c "import json, sys; print(json.dumps({
      'main_menu': 'Network',
      'sub_menu': 'LAN_IPv6',
      'settings': { 'LanDNS_select': 'Static', 'LanPri_DNS_text': sys.argv[1], 'LanSec_DNS_text': sys.argv[2] },
      'submit_button': 'Apply_button'
    }))" "$2" "$3")
    curl -N -X POST $API_URL/forceset -H "Content-Type: application/json" -d "$PAYLOAD"
    echo ""
    exit 0
fi

if [ "$1" == "port" ]; then
    if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
        echo "Usage: ./gpon.sh port <external_port> <internal_port> <server_ip>"
        exit 1
    fi
    PAYLOAD=$(python -c "import json, sys; print(json.dumps({
      'external_port': int(sys.argv[1]),
      'internal_port': int(sys.argv[2]),
      'server_ip': sys.argv[3]
    }))" "$2" "$3" "$4")
    curl -N -X POST $API_URL/portforward -H "Content-Type: application/json" -d "$PAYLOAD"
    echo ""
    exit 0
fi

if [ "$1" == "block" ]; then
    if [ -z "$2" ]; then
        echo "Usage: ./gpon.sh block <mac_address>"
        exit 1
    fi
    PAYLOAD=$(python -c "import json, sys; print(json.dumps({
      'main_menu': 'Security',
      'sub_menu': 'MAC Filter',
      'settings': { 'wlan_mac_exclude_mod': 'Blocked', 'wlan_mac_address': sys.argv[1] },
      'submit_button': 'submit'
    }))" "$2")
    curl -N -X POST $API_URL/forceset -H "Content-Type: application/json" -d "$PAYLOAD"
    echo ""
    exit 0
fi

if [ "$1" == "wifi-pass" ]; then
    if [ -z "$2" ]; then
        echo "Usage: ./gpon.sh wifi-pass <new_password>"
        exit 1
    fi
    PAYLOAD=$(python -c "import json, sys; print(json.dumps({
      'main_menu': 'Network',
      'sub_menu': 'Wireless (2.4GHz)',
      'settings': { 'wpaKey': sys.argv[1] },
      'submit_button': 'btnApply'
    }))" "$2")
    curl -N -X POST $API_URL/forceset -H "Content-Type: application/json" -d "$PAYLOAD"
    echo ""
    exit 0
fi

if [ "$1" == "reboot" ]; then
    curl -N -X POST $API_URL/reboot
    echo ""
    exit 0
fi

show_help
