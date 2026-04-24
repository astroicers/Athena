#!/usr/bin/env python3
"""Deploy Athena AD lab scripts to 3 Windows Server 2012 R2 VMs via WinRM.

Usage:
  OPENSSL_CONF=/tmp/openssl-legacy.cnf python3 deploy_lab.py upload
  OPENSSL_CONF=/tmp/openssl-legacy.cnf python3 deploy_lab.py run-stage1 dc
  OPENSSL_CONF=/tmp/openssl-legacy.cnf python3 deploy_lab.py run-stage1 web
  OPENSSL_CONF=/tmp/openssl-legacy.cnf python3 deploy_lab.py run-stage1 db
  OPENSSL_CONF=/tmp/openssl-legacy.cnf python3 deploy_lab.py wait <ip>
"""
import base64
import os
import subprocess
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import winrm  # type: ignore
from winrm.exceptions import WinRMError  # type: ignore

HOSTS = {
    "dc":   ("DC01",      "192.168.0.16"),
    "web":  ("WEB01",     "192.168.0.20"),
    "db":   ("ACCT-DB01", "192.168.0.23"),
    "webb": ("WEB01",     "192.168.0.20"),
    "dbb":  ("ACCT-DB01", "192.168.0.23"),
    "dc2":  ("DC01",      "192.168.0.16"),
    "web2": ("WEB01",     "192.168.0.20"),
    "db2":  ("ACCT-DB01", "192.168.0.23"),
}
USER = "administrator"
PW   = "1qaz@WSX"

LAB_DIR    = Path(__file__).parent / "windows"
REMOTE_DIR = r"C:\LabSetup"

# WSL's IP on the home LAN (from `ip -br addr | grep 192.168`)
WSL_LAN_IP = "192.168.0.18"
HTTP_PORT  = 8888


def session(ip: str) -> winrm.Session:
    return winrm.Session(
        f"http://{ip}:5985/wsman",
        auth=(USER, PW),
        transport="ntlm",
        read_timeout_sec=600,
        operation_timeout_sec=590,
    )


def ps(s: winrm.Session, script: str, label: str = "") -> tuple[int, str, str]:
    r = s.run_ps(script)
    rc = r.status_code
    out = r.std_out.decode(errors="replace")
    err = r.std_err.decode(errors="replace")
    if label:
        print(f"  [{label}] rc={rc}")
    return rc, out, err


def upload_file(s: winrm.Session, local: Path, remote: str, http_relpath: str) -> None:
    """Upload a file by telling the VM to pull it from our HTTP server.

    Assumes a python3 -m http.server running on WSL_LAN_IP:HTTP_PORT serving
    the lab/windows/ directory. Fast even for 20MB MSU.
    """
    size = local.stat().st_size
    parent = remote.rsplit("\\", 1)[0]
    ps(s, f'New-Item -ItemType Directory -Path "{parent}" -Force | Out-Null', "")

    url = f"http://{WSL_LAN_IP}:{HTTP_PORT}/{http_relpath.replace(chr(92), '/')}"
    print(f"  pulling {local.name} ({size/1024:.1f} KB) from {url}")

    # IMPORTANT: Invoke-WebRequest's -OutFile is slow due to progress indicator;
    # use WebClient for speed and force TLS12 just in case.
    script = f'''
$url = "{url}"
$dst = "{remote}"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.ServicePointManager]::SecurityProtocol
$ProgressPreference = 'SilentlyContinue'
try {{
    (New-Object System.Net.WebClient).DownloadFile($url, $dst)
    $sz = (Get-Item $dst).Length
    "OK size=$sz"
}} catch {{
    "FAIL: " + $_.Exception.Message
    exit 1
}}
'''
    rc, out, err = ps(s, script)
    if rc != 0 or "FAIL" in out:
        print(f"  ERROR: {out} {err[:300]}")
        sys.exit(1)
    print(f"  {out.strip()} (expected {size})")


_httpd_proc: subprocess.Popen | None = None


def start_httpd() -> None:
    """Start a python http.server serving LAB_DIR on HTTP_PORT."""
    global _httpd_proc
    if _httpd_proc is not None:
        return
    _httpd_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(HTTP_PORT)],
        cwd=str(LAB_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1)
    print(f"[httpd] serving {LAB_DIR} on 0.0.0.0:{HTTP_PORT} (pid={_httpd_proc.pid})")


def stop_httpd() -> None:
    global _httpd_proc
    if _httpd_proc is not None:
        _httpd_proc.terminate()
        try:
            _httpd_proc.wait(timeout=5)
        except Exception:
            _httpd_proc.kill()
        _httpd_proc = None
        print("[httpd] stopped")


def upload_lab(ip: str, stage2: bool = False) -> None:
    """Upload all LabSetup files to a single VM.
    stage2=True additionally uploads Stage2-*.ps1 + site/ + sql/ + needed blobs."""
    s = session(ip)
    print(f"[{ip}] connecting...")
    rc, out, _ = ps(s, "$env:COMPUTERNAME")
    print(f"[{ip}] hostname={out.strip()}")

    ps(s, f'New-Item -ItemType Directory -Path "{REMOTE_DIR}" -Force | Out-Null', "mkdir")
    ps(s, f'New-Item -ItemType Directory -Path "{REMOTE_DIR}\\prereq" -Force | Out-Null', "mkdir prereq")
    if stage2:
        ps(s, f'New-Item -ItemType Directory -Path "{REMOTE_DIR}\\sql" -Force | Out-Null', "mkdir sql")
        ps(s, f'New-Item -ItemType Directory -Path "{REMOTE_DIR}\\site" -Force | Out-Null', "mkdir site")

    files = [
        "common.psm1",
        "Stage1-DC.ps1",
        "Stage1-Web.ps1",
        "Stage1-DB.ps1",
        "Stage1b-Web.ps1",
        "Stage1b-DB.ps1",
        "web01-djoin.blob",
        "acctdb01-djoin.blob",
        "prereq/Win8.1AndW2K12R2-KB3191564-x64.msu",
    ]
    if stage2:
        files.extend([
            "Stage2-DC.ps1",
            "Stage2-Web.ps1",
            "Stage2-DB.ps1",
            "site/index.html",
            "sql/ConfigurationFile.ini",
            "sql/SQLEXPR_x64_ENU.exe",
        ])

    for f in files:
        local = LAB_DIR / f
        if not local.exists():
            print(f"  SKIP: {local} not found locally")
            continue
        remote_path = f"{REMOTE_DIR}\\{f.replace('/', chr(92))}"
        upload_file(s, local, remote_path, f)

    print(f"[{ip}] upload complete")


def run_stage1(role: str) -> None:
    name, ip = HOSTS[role]
    script_name = {
        "dc":   "Stage1-DC.ps1",
        "web":  "Stage1-Web.ps1",
        "db":   "Stage1-DB.ps1",
        "webb": "Stage1b-Web.ps1",
        "dbb":  "Stage1b-DB.ps1",
        "dc2":  "Stage2-DC.ps1",
        "web2": "Stage2-Web.ps1",
        "db2":  "Stage2-DB.ps1",
    }[role]
    s = session(ip)
    print(f"[{name} @ {ip}] running {script_name}...")
    # Use schtasks to run as SYSTEM — WinRM's process context cannot survive reboots
    # and has no desktop; SYSTEM has full privileges and the task persists.
    task_name = f"AthenaLab-{role}"
    script_path = f"{REMOTE_DIR}\\{script_name}"
    tr = f'powershell.exe -ExecutionPolicy Bypass -NoProfile -File "{script_path}"'
    ps_script = f'''
schtasks /Delete /TN "{task_name}" /F 2>$null | Out-Null
schtasks /Create /TN "{task_name}" /SC ONCE /ST 23:59 /RL HIGHEST /RU SYSTEM /TR '{tr}' /F | Out-Null
schtasks /Run /TN "{task_name}" | Out-Null
"launched"
'''
    rc, out, err = ps(s, ps_script, "launch")
    print("stdout:", out[:500])
    if err:
        print("stderr:", err[:500])


def wait_for(ip: str, timeout: int = 600) -> bool:
    """Poll WinRM until host responds (survives reboots)."""
    print(f"[{ip}] waiting for WinRM (timeout={timeout}s)...")
    start = time.time()
    last_err = None
    while time.time() - start < timeout:
        try:
            s = session(ip)
            r = s.run_cmd("hostname")
            if r.status_code == 0:
                print(f"[{ip}] up: hostname={r.std_out.decode().strip()}")
                return True
        except Exception as e:
            last_err = type(e).__name__
        time.sleep(5)
        print(".", end="", flush=True)
    print(f"\n[{ip}] TIMEOUT (last error: {last_err})")
    return False


def tail_log(ip: str, log_prefix: str = "Stage1") -> None:
    """Print the latest LabSetup transcript log."""
    s = session(ip)
    script = (
        f'Get-ChildItem "{REMOTE_DIR}\\logs\\{log_prefix}*.log" '
        f'-ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | '
        f'Select-Object -First 1 | Get-Content -Tail 50'
    )
    rc, out, err = ps(s, script)
    print(out)


def check_phase(ip: str) -> None:
    """Show sentinel files to know where the script is."""
    s = session(ip)
    rc, out, err = ps(s,
        f'Get-ChildItem "{REMOTE_DIR}\\.done.*" -Force -ErrorAction SilentlyContinue | '
        f'Select-Object -ExpandProperty Name'
    )
    print(f"[{ip}] phases done:")
    print(out or "  (none)")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]

    if cmd == "upload":
        args = sys.argv[2:] if len(sys.argv) > 2 else list(HOSTS.keys())
        stage2 = False
        targets = []
        for a in args:
            if a == "--stage2":
                stage2 = True
            else:
                targets.append(a)
        if not targets:
            targets = ["dc", "web", "db"]
        start_httpd()
        try:
            for role in targets:
                _, ip = HOSTS[role]
                upload_lab(ip, stage2=stage2)
        finally:
            stop_httpd()

    elif cmd == "run-stage1":
        role = sys.argv[2]
        run_stage1(role)

    elif cmd == "wait":
        ip = sys.argv[2]
        wait_for(ip, timeout=int(sys.argv[3]) if len(sys.argv) > 3 else 600)

    elif cmd == "tail":
        ip = sys.argv[2]
        tail_log(ip, sys.argv[3] if len(sys.argv) > 3 else "Stage1")

    elif cmd == "phases":
        ip = sys.argv[2] if len(sys.argv) > 2 else None
        if ip:
            check_phase(ip)
        else:
            for role, (name, ip) in HOSTS.items():
                check_phase(ip)

    elif cmd == "ps":
        # OPENSSL_CONF=/tmp/openssl-legacy.cnf python3 deploy_lab.py ps <ip> "<script>"
        ip = sys.argv[2]
        script = sys.argv[3]
        s = session(ip)
        rc, out, err = ps(s, script)
        print(f"rc={rc}")
        print(out)
        if err:
            print("STDERR:", err)

    else:
        print(f"unknown command: {cmd}")
        print(__doc__)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
