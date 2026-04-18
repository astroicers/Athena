# SPEC-061: AD/Cloud Attack Chain MCP Tools

> Seven MCP tool servers covering Active Directory and Cloud attack chains for end-to-end penetration testing.

| Field | Value |
|-------|-------|
| **Spec ID** | SPEC-061 |
| **Related ADR** | N/A |
| **Estimated Complexity** | High |
| **HITL Level** | minimal |

---

## Goal

Close the AD and Cloud coverage gaps in Athena's MCP tool ecosystem. Before this spec, AD attack chain had only 3 playbook commands with tools, and Cloud attack chain had zero coverage. After implementation, both attack chains have end-to-end tool coverage.

---

## Scope

### AD Attack Chain Tools (4)

| Tool ID | Name | Category | Risk | Port | MITRE Techniques |
|---------|------|----------|------|------|-----------------|
| `bloodhound-collector` | BloodHound Collector | discovery | high | 58101 | T1087.002, T1069.002, T1482 |
| `netexec-suite` | NetExec Suite | credential_access | critical | 58102 | T1110.003, T1087.002, T1069.002, T1021.002, T1003.006 |
| `certipy-ad` | Certipy AD CS | credential_access | critical | 58103 | T1649, T1558.004, T1550.003 |
| `responder-capture` | Responder Capture | credential_access | critical | 58104 | T1557.001, T1040 |

### Cloud Attack Chain Tools (3)

| Tool ID | Name | Category | Risk | Port | MITRE Techniques |
|---------|------|----------|------|------|-----------------|
| `cloudfox-enum` | CloudFox Enumerator | discovery | high | 58105 | T1580, T1087.004, T1069.003 |
| `pacu-aws` | Pacu AWS | credential_access | critical | 58106 | T1078.004, T1530, T1525 |
| `scoutsuite-audit` | ScoutSuite Auditor | discovery | medium | 58107 | T1580, T1526 |

---

## Tool Details

### bloodhound-collector (Port 58101)

**GitHub Project:** SpecterOps/BloodHound (Python ingestor)

**MCP Tools (3):**
- `bloodhound_collect` — AD environment graph collection (Users/Groups/Sessions/ACLs/Trusts)
- `bloodhound_find_paths` — Attack path analysis to Domain Admin
- `bloodhound_enum_trusts` — Domain Trust relationship enumeration

**Output Traits:** `ad.bloodhound_data`, `ad.domain_users_count`, `ad.attack_path`, `ad.high_value_target`, `ad.domain_trust`, `ad.trust_direction`

**Dependencies:** `bloodhound>=1.7.1`, `neo4j>=5.0.0`

### netexec-suite (Port 58102)

**GitHub Project:** Pennyw0rth/NetExec (CrackMapExec successor)

**MCP Tools (5):**
- `netexec_smb_enum` — SMB enumeration: OS version, shares, logged-in users, GPP passwords
- `netexec_password_spray` — Password spraying (SMB/LDAP/WinRM)
- `netexec_ldap_enum` — LDAP deep enumeration: AS-REP Roastable, Kerberoastable, LAPS
- `netexec_exec` — Remote execution via SMBExec/WMIExec/PSExec
- `netexec_spn_enum` — SPN enumeration + service account detection

**Output Traits:** `ad.smb_host`, `ad.smb_share`, `ad.smb_user`, `ad.gpp_password`, `credential.valid_pair`, `ad.sprayed_account`, `ad.asreproast_user`, `ad.kerberoastable_user`, `ad.laps_password`, `lateral.session`, `credential.shell`, `ad.spn_account`

**Dependencies:** `netexec>=1.2.0`

### certipy-ad (Port 58103)

**GitHub Project:** ly4k/Certipy

**MCP Tools (4):**
- `certipy_find` — Scan AD CS for vulnerable certificate templates (ESC1-ESC8)
- `certipy_request` — Request malicious certificates (ESC1/ESC2 exploitation)
- `certipy_auth` — Kerberos authentication with malicious certificate (TGT + NT hash)
- `certipy_shadow` — Shadow Credentials attack (Key Trust abuse)

**Output Traits:** `ad.vulnerable_template`, `ad.esc_type`, `ad.ca_name`, `ad.certificate_pfx`, `ad.impersonated_user`, `credential.hash`, `credential.certificate_auth`, `credential.shadow_credential`

**Dependencies:** `certipy-ad>=4.8.0`

### responder-capture (Port 58104)

**GitHub Project:** lgandx/Responder

**MCP Tools (3) — Three-phase listener design:**
- `responder_start` — Start LLMNR/NBT-NS/mDNS poisoning (default: analyze-only mode)
- `responder_collect` — Collect captured NTLMv2 hashes from Responder logs
- `responder_stop` — Stop Responder process

**Output Traits:** `credential.ntlmv2_hash`, `ad.responder_victim`, `ad.responder_session`

**Dependencies:** `netifaces>=0.11.0` (Responder cloned into container)

### cloudfox-enum (Port 58105)

**GitHub Project:** BishopFox/cloudfox

**MCP Tools (3):**
- `cloudfox_iam_enum` — IAM permission enumeration + privilege escalation path analysis
- `cloudfox_all_checks` — Run all CloudFox security checks
- `cloudfox_find_secrets` — Search cloud environment for sensitive info (env vars, SSM, Secrets Manager)

**Output Traits:** `cloud.iam_role`, `cloud.privesc_path`, `cloud.overprivileged_user`, `cloud.public_resource`, `cloud.secret_found`, `cloud.misconfiguration`, `cloud.env_variable`, `cloud.ssm_parameter`

**Dependencies:** CloudFox Go binary (downloaded in Dockerfile)

### pacu-aws (Port 58106)

**GitHub Project:** RhinoSecurityLabs/pacu

**MCP Tools (4):**
- `pacu_iam_privesc_scan` — IAM privilege escalation path scan
- `pacu_s3_enum` — S3 bucket access enumeration + sensitive files
- `pacu_lambda_backdoor` — Lambda function backdoor analysis
- `pacu_ec2_enum` — EC2 instance enumeration + security group analysis

**Output Traits:** `cloud.iam_privesc`, `cloud.exploitable_policy`, `cloud.s3_bucket`, `cloud.s3_public_bucket`, `cloud.s3_sensitive_file`, `cloud.lambda_function`, `cloud.lambda_backdoor_opportunity`, `cloud.ec2_instance`, `cloud.security_group_open`, `cloud.ec2_public_ip`

**Dependencies:** `pacu`, `boto3>=1.28.0`

### scoutsuite-audit (Port 58107)

**GitHub Project:** nccgroup/ScoutSuite

**MCP Tools (2):**
- `scoutsuite_audit` — Full security audit (HTML report + JSON structured data)
- `scoutsuite_service_check` — Single service deep security check

**Output Traits:** `cloud.audit_finding`, `cloud.critical_count`, `cloud.high_count`, `cloud.service_finding`, `cloud.misconfiguration`

**Dependencies:** `scoutsuite>=5.14.0`

---

## Seed Data

### TOOL_REGISTRY_SEEDS (+7 entries)

All 7 tools registered with proper name, mcp_server, category, description, risk_level, mitre_techniques, and supported_platforms.

### TECHNIQUE_SEEDS (+9 new MITRE techniques)

| Technique ID | Name | Tactic |
|-------------|------|--------|
| T1087.002 | Account Discovery: Domain Account | discovery |
| T1069.002 | Permission Groups Discovery: Domain Groups | discovery |
| T1482 | Domain Trust Discovery | discovery |
| T1110.003 | Brute Force: Password Spraying | credential_access |
| T1557.001 | LLMNR/NBT-NS Poisoning | credential_access |
| T1649 | Steal or Forge Authentication Certificates | credential_access |
| T1087.004 | Account Discovery: Cloud Account | discovery |
| T1069.003 | Permission Groups Discovery: Cloud Groups | discovery |
| T1530 | Data from Cloud Storage | collection |

### MCP_DISCOVERED_MITRE (+25 mappings)

Each MCP tool function mapped to corresponding MITRE technique IDs for Orient engine auto-recommendation.

---

## Implementation Details

- Standard Athena MCP pattern: FastMCP + `_run_command()` + fact pipeline
- Docker Compose ports: 58101-58107 on `athena-net`
- Base image: `athena-mcp-base:latest`

---

## Verification

```bash
# Syntax validation
for tool in bloodhound-collector netexec-suite certipy-ad responder-capture cloudfox-enum pacu-aws scoutsuite-audit; do
  python3 -c "import ast; ast.parse(open('tools/$tool/server.py').read()); print(f'$tool: OK')"
done

# seed.py validation
python3 -c "import ast; ast.parse(open('backend/app/database/seed.py').read()); print('seed.py: OK')"
```

---

## Impact

| Metric | Before | After |
|--------|--------|-------|
| AD tool coverage | 3 playbook commands | Full coverage |
| Cloud tool coverage | 0 | AWS/Azure/GCP basic coverage |
| MCP tool total | 13 | 20 |
| Executable MITRE techniques | ~35 | ~50+ |
| Attack chain completeness | privesc→cred→lateral | + AD chain + Cloud chain |

---

## Status

Implemented and merged.
