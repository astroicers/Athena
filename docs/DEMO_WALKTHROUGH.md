# Demo Walkthrough — Athena vs Metasploitable 2

## Prerequisites

- Athena running on localhost:8000 with MOCK_METASPLOIT=true (or false for live)
- Metasploitable 2 VM at 192.168.56.101

## Step 1: Create an Operation

```bash
curl -s -X POST http://localhost:8000/api/operations \
  -H "Content-Type: application/json" \
  -d '{"name":"msf2-demo","description":"Metasploitable 2 demo"}' | jq .
```

Example response: `{"id": "op-abc123", "name": "msf2-demo", ...}`

## Step 2: Note on Scope / ROE

Athena respects scope via IP allowlists configured in the target settings. All targets added in Step 3 must be within your authorized scope. Ensure you have written authorization before proceeding.

## Step 3: Add Target

```bash
export TGT_ID=$(curl -s -X POST "http://localhost:8000/api/operations/$OP_ID/targets" \
  -H "Content-Type: application/json" \
  -d '{"ip_address": "192.168.56.101", "hostname": "metasploitable2"}' | jq -r '.id')
echo "Target ID: $TGT_ID"
```

Example response: `{"id": "tgt-xyz456", ...}`

## Step 4: Start OODA Auto Loop (3 iterations)

```bash
curl -s -X POST "http://localhost:8000/api/operations/$OP_ID/ooda/auto-start?interval_sec=10&max_iterations=3" | jq .
```

Expected: `{"status": "started", "interval_sec": 10, "max_iterations": 3}`

## Step 5: Watch Progress

```bash
# Check OODA status
curl -s http://localhost:8000/api/operations/$OP_ID/ooda/auto-status | jq .

# Check facts collected
curl -s http://localhost:8000/api/operations/$OP_ID/facts | jq 'length'

# Check technique executions
curl -s http://localhost:8000/api/operations/$OP_ID/attack-path | jq '.[].status'
```

## Step 6: Stop Loop Manually (if needed)

```bash
curl -s -X DELETE http://localhost:8000/api/operations/$OP_ID/ooda/auto-stop | jq .
```

## Step 7: Generate Report

```bash
curl -s http://localhost:8000/api/operations/$OP_ID/report | jq .
# Or for Markdown:
curl -s http://localhost:8000/api/operations/$OP_ID/report/markdown
```

## What OODA Does Automatically

Each OODA cycle:

1. **Observe**: Collects open ports, services, CVEs via Nmap
2. **Orient**: Uses Claude AI to prioritize next action
3. **Decide**: Selects best technique from Playbook KB
4. **Act**: Executes via DirectSSH / PersistentSSH / Metasploit

For Metasploitable 2, after Nmap detects vsftpd 2.3.4 (CVE-2011-2523), OODA automatically routes to MetasploitRPCEngine.

## Expected Timeline

| Phase | Technique | Expected Time |
|-------|-----------|---------------|
| Nmap scan | T1046 | ~30s |
| CVE lookup | T1595.002 | ~5s |
| vsftpd exploit | T1190 | ~5s (mock) / ~30s (live) |
| Post-exploit facts | T1033 | ~2s |
| Report generation | — | ~1s |
