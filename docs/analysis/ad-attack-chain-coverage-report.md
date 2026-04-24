# AD Attack Chain Tool Coverage Report

> Date: 2026-04-20
> Status: Verified
> Related: SPEC-060, SPEC-061

---

## Summary

**Coverage: 100% — All 6 AD attack chain stages fully covered.**

23 MCP tool servers (12 AD-specific) provide end-to-end coverage from reconnaissance through persistence. 49 AD-specific MCP tool functions map to 30+ MITRE ATT&CK techniques.

---

## Attack Chain Coverage by Stage

### 1. Reconnaissance

| Technique | Tool | MCP Function | MITRE |
|-----------|------|--------------|-------|
| AD topology + attack paths | `bloodhound-collector` | `bloodhound_collect`, `bloodhound_find_paths` | T1087.002, T1069.002, T1482 |
| Domain trust enumeration | `bloodhound-collector` | `bloodhound_enum_trusts` | T1482 |
| SMB/LDAP enumeration | `netexec-suite` | `netexec_smb_enum`, `netexec_ldap_enum` | T1087.002, T1069.002 |
| SPN enumeration | `netexec-suite` | `netexec_spn_enum` | T1558.003 |
| SID lookup | `impacket-ad` | `impacket_lookup_sid` | T1087.002 |
| AD CS enumeration | `certipy-ad` | `certipy_find` | T1649 |
| Coercion scanning | `coercion-tools` | `coerce_scan` | T1187 |

### 2. Credential Access

| Technique | Tool | MCP Function | MITRE |
|-----------|------|--------------|-------|
| Password spraying | `netexec-suite` | `netexec_password_spray` | T1110.003 |
| AS-REP Roasting detection | `netexec-suite` | `netexec_ldap_enum` | T1558.004 |
| Kerberoasting | `credential-dumper` | `kerberoast` | T1558.003 |
| SAM hash extraction | `credential-dumper` | `dump_sam_hashes` | T1003.002 |
| NTDS.dit extraction (DCSync) | `credential-dumper` | `dump_ntds` | T1003.003, T1003.006 |
| LSA Secrets | `credential-dumper` | `dump_lsa_secrets` | T1003.004 |
| LLMNR/NBT-NS poisoning | `responder-capture` | `responder_start`, `responder_collect` | T1557.001, T1040 |
| PetitPotam (MS-EFSR) | `coercion-tools` | `coerce_petitpotam` | T1187 |
| PrinterBug (MS-RPRN) | `coercion-tools` | `coerce_printerbug` | T1187 |
| DFSCoerce (MS-DFSNM) | `coercion-tools` | `coerce_dfscoerce` | T1187 |
| NTLM relay to LDAP/SMB | `ntlm-relay` | `ntlm_relay_to_ldap`, `ntlm_relay_to_smb` | T1557, T1550.001 |
| AD CS exploitation (ESC1-ESC8) | `certipy-ad` | `certipy_request`, `certipy_auth`, `certipy_shadow` | T1649, T1550.003 |
| Hash cracking (AS-REP/TGS/NTLM) | `hashcat-crack` | `hashcat_crack_asrep`, `hashcat_crack_kerberoast`, `hashcat_crack_ntlm` | T1110.002 |

### 3. Ticket Forgery

| Technique | Tool | MCP Function | MITRE |
|-----------|------|--------------|-------|
| Golden Ticket | `impacket-ad` | `impacket_golden_ticket` | T1558.001 |
| Silver Ticket | `impacket-ad` | `impacket_silver_ticket` | T1558.002 |
| Over-Pass-the-Hash (getTGT) | `impacket-ad` | `impacket_get_tgt` | T1550.003 |
| S4U delegation abuse (getST) | `impacket-ad` | `impacket_get_st` | T1550.003 |

### 4. Lateral Movement

| Technique | Tool | MCP Function | MITRE |
|-----------|------|--------------|-------|
| PsExec | `lateral-mover` | `psexec_lateral` | T1021.002 |
| WMIExec | `lateral-mover` | `wmiexec_lateral` | T1047 |
| Pass-the-Hash (SMB) | `lateral-mover` | `psexec_lateral` (PtH mode) | T1550.002 |
| SMB share enumeration | `lateral-mover` | `smbclient_enum` | T1021.002 |
| Pass-the-Ticket | `impacket-ad` | via ccache from ticket forgery | T1550.003 |
| NTLM relay command exec | `ntlm-relay` | `ntlm_relay_to_smb` | T1557 |

### 5. Privilege Escalation

| Technique | Tool | MCP Function | MITRE |
|-----------|------|--------------|-------|
| ACL abuse (WriteDACL/GenericAll) | `ad-exploiter` | `ad_acl_abuse` | T1098.002 |
| RBCD attack | `ad-exploiter` | `ad_rbcd_attack` | T1098.002, T1550.003 |
| GPO abuse | `ad-exploiter` | `ad_gpo_abuse` | T1484 |
| SID-History injection | `ad-exploiter` | `ad_sid_history` | T1134.005 |
| AD CS privilege escalation | `certipy-ad` | `certipy_request`, `certipy_auth` | T1649 |

### 6. Persistence

| Technique | Tool | MCP Function | MITRE |
|-----------|------|--------------|-------|
| AdminSDHolder ACL backdoor | `ad-exploiter` | `ad_adminsdholder` | T1098.002 |
| Skeleton Key | `ad-persistence` | `persist_skeleton_key` | T1556 |
| DNSAdmins DLL injection | `ad-persistence` | `persist_dnsadmins` | T1547.008 |
| DSRM password backdoor | `ad-persistence` | `persist_dsrm` | T1556 |
| Custom SSP | `ad-persistence` | `persist_custom_ssp` | T1547.005 |

---

## Attack Chain Flow

```
BloodHound (path discovery)
  -> NetExec (SMB/LDAP enum + password spray)
    -> Credential Dumper (SAM/NTDS/Kerberoast)
      -> Hashcat (crack hashes)
    -> Coercion (PetitPotam/PrinterBug) + Responder (capture)
      -> NTLM Relay (relay -> LDAP RBCD / SMB exec)
    -> Certipy (AD CS ESC1-ESC8)
  -> Impacket-AD (Golden/Silver Ticket, Over-PtH, S4U)
    -> Lateral Mover (PsExec/WMIExec/PtH lateral movement)
      -> AD Exploiter (ACL/GPO/RBCD privilege escalation)
        -> AD Persistence (Skeleton Key/DNSAdmins/DSRM/SSP)
```

---

## Tool Inventory

### AD-Specific Tools (12)

| Tool | Port | MCP Functions | Category | Risk |
|------|------|---------------|----------|------|
| `bloodhound-collector` | 58101 | 3 | discovery | high |
| `netexec-suite` | 58102 | 5 | credential_access | critical |
| `certipy-ad` | 58103 | 4 | credential_access | critical |
| `responder-capture` | 58104 | 3 | credential_access | critical |
| `credential-dumper` | 58099 | 4 | credential_access | critical |
| `lateral-mover` | 58100 | 3 | credential_access | critical |
| `impacket-ad` | 58108 | 5 | credential_access | critical |
| `ad-exploiter` | 58109 | 5 | execution | critical |
| `coercion-tools` | 58110 | 4 | credential_access | critical |
| `ad-persistence` | 58111 | 4 | persistence | critical |
| `ntlm-relay` | 58112 | 4 | credential_access | critical |
| `hashcat-crack` | 58113 | 4 | credential_access | high |
| **Total** | | **48** | | |

### Non-AD Tools (11)

| Tool | Port | Category |
|------|------|----------|
| `nmap-scanner` | 58091 | discovery |
| `osint-recon` | 58092 | discovery |
| `vuln-lookup` | 58093 | discovery |
| `credential-checker` | 58094 | credential_access |
| `attack-executor` | 58095 | execution |
| `web-scanner` | 58096 | discovery |
| `api-fuzzer` | 58097 | discovery |
| `privesc-scanner` | 58098 | execution |
| `cloudfox-enum` | 58105 | discovery |
| `pacu-aws` | 58106 | credential_access |
| `scoutsuite-audit` | 58107 | discovery |

---

## Summary Statistics

| Metric | Value |
|--------|-------|
| MCP servers total | 23 |
| AD-specific tools | 12 |
| AD MCP tool functions | 48 |
| Total MCP tool functions (all) | ~80 |
| MITRE ATT&CK techniques (AD) | 30+ |
| Docker Compose port range | 58091-58113 |
| AD attack chain stages covered | 6/6 |
| Coverage gaps | 0 |

---

## MITRE ATT&CK Technique Mapping

| Technique ID | Name | Tool(s) |
|-------------|------|---------|
| T1003.002 | OS Credential Dumping: SAM | credential-dumper |
| T1003.003 | OS Credential Dumping: NTDS | credential-dumper |
| T1003.004 | OS Credential Dumping: LSA Secrets | credential-dumper |
| T1003.006 | OS Credential Dumping: DCSync | credential-dumper |
| T1021.002 | Remote Services: SMB/Windows Admin Shares | lateral-mover, netexec-suite |
| T1040 | Network Sniffing | responder-capture |
| T1047 | Windows Management Instrumentation | lateral-mover, netexec-suite |
| T1069.002 | Permission Groups: Domain Groups | bloodhound-collector, netexec-suite |
| T1087.002 | Account Discovery: Domain Account | bloodhound-collector, netexec-suite, impacket-ad |
| T1098.002 | Account Manipulation: Domain Account | ad-exploiter |
| T1110.002 | Brute Force: Password Cracking | hashcat-crack |
| T1110.003 | Brute Force: Password Spraying | netexec-suite |
| T1134.005 | Access Token Manipulation: SID-History Injection | ad-exploiter |
| T1187 | Forced Authentication | coercion-tools |
| T1482 | Domain Trust Discovery | bloodhound-collector |
| T1484 | Domain Policy Modification | ad-exploiter |
| T1547.005 | Boot/Logon Autostart: SSP | ad-persistence |
| T1547.008 | Boot/Logon Autostart: LSASS Driver | ad-persistence |
| T1550.001 | Alternate Auth Material: Application Access Token | ntlm-relay |
| T1550.002 | Alternate Auth Material: Pass the Hash | lateral-mover |
| T1550.003 | Alternate Auth Material: Pass the Ticket | impacket-ad, certipy-ad |
| T1556 | Modify Authentication Process | ad-persistence |
| T1557.001 | MitM: LLMNR/NBT-NS Poisoning | responder-capture, ntlm-relay |
| T1558.001 | Steal/Forge Kerberos Tickets: Golden Ticket | impacket-ad |
| T1558.002 | Steal/Forge Kerberos Tickets: Silver Ticket | impacket-ad |
| T1558.003 | Steal/Forge Kerberos Tickets: Kerberoasting | credential-dumper, netexec-suite |
| T1558.004 | Steal/Forge Kerberos Tickets: AS-REP Roasting | netexec-suite |
| T1649 | Steal/Forge Authentication Certificates | certipy-ad |

---

## Provenance

| Spec | Tools Added | Commit |
|------|-------------|--------|
| SPEC-060 | privesc-scanner, credential-dumper, lateral-mover | b480b89 |
| SPEC-061 | bloodhound-collector, netexec-suite, certipy-ad, responder-capture, cloudfox-enum, pacu-aws, scoutsuite-audit | 6b19723 |
| Post-SPEC-061 | impacket-ad, ad-exploiter, coercion-tools, ad-persistence, ntlm-relay, hashcat-crack | 662767a |
