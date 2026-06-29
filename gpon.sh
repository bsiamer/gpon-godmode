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
    echo "  dns <pri_ip> <sec_ip>       Force set the LAN IPv4 DNS servers"
    echo "  ipv6-dns <pri> <sec>        Force set the LAN IPv6 DNS servers"
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
    curl -N -X POST $API_URL/forceset -H "Content-Type: application/json" -d '{
      "main_menu": "Network",
      "sub_menu": "LAN",
      "settings": { "firstDns": "'$2'", "secondDns": "'$3'" },
      "submit_button": "save2"
    }'
    echo ""
    exit 0
fi

if [ "$1" == "ipv6-dns" ]; then
    if [ -z "$2" ] || [ -z "$3" ]; then
        echo "Usage: ./gpon.sh ipv6-dns <primary_dns> <secondary_dns>"
        exit 1
    fi
    curl -N -X POST $API_URL/forceset -H "Content-Type: application/json" -d '{
      "main_menu": "Network",
      "sub_menu": "LAN_IPv6",
      "settings": { "LanDNS_select": "Static", "LanPri_DNS_text": "'$2'", "LanSec_DNS_text": "'$3'" },
      "submit_button": "Apply_button"
    }'
    echo ""
    exit 0
fi

if [ "$1" == "port" ]; then
    if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
        echo "Usage: ./gpon.sh port <external_port> <internal_port> <server_ip>"
        exit 1
    fi
    curl -N -X POST $API_URL/portforward -H "Content-Type: application/json" -d '{
      "external_port": '$2',
      "internal_port": '$3',
      "server_ip": "'$4'"
    }'
    echo ""
    exit 0
fi

if [ "$1" == "reboot" ]; then
    curl -N -X POST $API_URL/reboot
    echo ""
    exit 0
fi

show_help
