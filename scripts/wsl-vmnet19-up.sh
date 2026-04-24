#!/usr/bin/env bash
# wsl-vmnet19-up.sh — 把 WSL mirrored 的 VMnet19 鏡射介面 bring up 並配 10.10.10.2/24
#
# 為什麼需要：WSL 2.4 mirrored 模式對 VMware NIC (OUI 00:50:56) 只創介面不給 IP，
# 且預設 state=DOWN。此腳本補齊這段。
#
# 使用：
#   sudo ./scripts/wsl-vmnet19-up.sh
#
# 永久化（systemd unit，啟動時自動跑）：
#   sudo ./scripts/wsl-vmnet19-up.sh --install
#
# 還原：
#   sudo ./scripts/wsl-vmnet19-up.sh --uninstall

set -euo pipefail

WSL_IP="${WSL_IP:-10.10.10.2}"
PREFIX="${PREFIX:-24}"
TARGET_MAC="00:50:56:c0:00:13"  # VMnet19 OUI + fixed suffix (VMware 預設)
SERVICE_NAME="wsl-vmnet19-up"

find_eth() {
    # 透過 MAC 找到鏡射介面（每次 WSL 啟動介面名可能變）
    for nic in /sys/class/net/eth*; do
        [[ -e "$nic" ]] || continue
        mac=$(cat "$nic/address" 2>/dev/null || true)
        if [[ "$mac" == "$TARGET_MAC" ]]; then
            basename "$nic"
            return 0
        fi
    done
    return 1
}

configure() {
    local eth
    eth=$(find_eth) || {
        echo "ERROR: 找不到 MAC $TARGET_MAC 的介面。" >&2
        echo "  確認 1) .wslconfig 的 networkingMode=mirrored 已啟用" >&2
        echo "  確認 2) VMware VMnet19 在 Windows 端存在且 UP" >&2
        echo "  確認 3) Windows 端 VMware Network Adapter VMnet19 有指派 10.10.10.1" >&2
        exit 1
    }
    echo "Found VMnet19 mirror interface: $eth"

    # Up + 設 IP (idempotent)
    ip link set "$eth" up
    if ! ip addr show dev "$eth" | grep -q "$WSL_IP"; then
        ip addr add "$WSL_IP/$PREFIX" dev "$eth"
    fi

    # 路由（mirrored 可能沒自動加）
    if ! ip route show | grep -q "10.10.10.0/$PREFIX.*dev $eth"; then
        ip route add "10.10.10.0/$PREFIX" dev "$eth" metric 100 || true
    fi

    echo "---"
    ip -br addr show "$eth"
    ip route | grep 10.10.10 || true
    echo "---"
    echo "Ping 10.10.10.1 (Windows host VMnet19 adapter):"
    ping -c2 -W2 10.10.10.1 || echo "  (ping 失敗：打開 Hyper-V firewall — 見 plan 2.4a #3)"
}

install_service() {
    local script_path
    script_path="$(readlink -f "$0")"
    local unit="/etc/systemd/system/${SERVICE_NAME}.service"

    cat > "$unit" <<EOF
[Unit]
Description=Bring up WSL mirrored VMnet19 interface and configure lab IP
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=$script_path
RemainAfterExit=yes
# 失敗時重試（WSL 啟動時機可能 race）
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    systemctl start  "$SERVICE_NAME"
    echo "Installed: $unit"
    systemctl status "$SERVICE_NAME" --no-pager -l | head -20
}

uninstall_service() {
    systemctl disable --now "$SERVICE_NAME" 2>/dev/null || true
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    systemctl daemon-reload
    echo "Uninstalled."
}

case "${1:-run}" in
    run)          configure ;;
    --install)    configure && install_service ;;
    --uninstall)  uninstall_service ;;
    *)
        echo "Usage: sudo $0 [--install | --uninstall]"
        exit 2
        ;;
esac
