# Stage1-DB.ps1 -- Athena AD Lab Stage 1 for ACCT-DB01 (Bridged mode)
# Goal: WMF 5.1 -> rename -> DNS=DC -> domain join corp.athena.lab. STOP before vulns.
#
# Prereq: Stage1-DC.ps1 finished on DC01 (192.168.0.16) with domain up.
# After this completes, snapshot as 'S2-domain-joined' then run Stage2-DB.ps1.

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'
$VerbosePreference     = 'Continue'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'common.psm1') -Force

Start-LabTranscript -ScriptName 'Stage1-DB'

$DomainName = 'corp.athena.lab'
$DCIp       = '192.168.0.16'
$DCAdmin    = 'administrator@corp.athena.lab'   # UPN avoids CORP NetBIOS resolution flakiness
$DCAdminPw  = '1qaz@WSX'

# ============================================================
# Phase A -- Baseline
# ============================================================
Invoke-Phase 'A-baseline' {
    Disable-WindowsUpdateHard
    Sync-Time -Peer $DCIp
    New-NetFirewallRule -DisplayName 'Lab-AllowPing' -Protocol ICMPv4 -IcmpType 8 `
        -Action Allow -Direction Inbound -ErrorAction SilentlyContinue | Out-Null
    try {
        Set-MpPreference -DisableRealtimeMonitoring $true -EA SilentlyContinue
        Add-MpPreference -ExclusionPath 'C:\' -EA SilentlyContinue
    } catch {}
}

# ============================================================
# Phase B -- WMF 5.1
# ============================================================
if (-not (Test-Phase 'B-wmf51')) {
    $needReboot = Install-Wmf51IfNeeded
    Set-Phase 'B-wmf51'
    if ($needReboot) {
        Register-ResumeTask -ScriptPath $MyInvocation.MyCommand.Path
        Request-Reboot -Reason 'WMF 5.1 installed'
    }
}

# ============================================================
# Phase C -- DNS -> DC, rename + domain join
# ============================================================
Invoke-Phase 'C-domainjoin' {
    $nic = Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -First 1
    if ($nic) {
        Set-DnsClientServerAddress -InterfaceIndex $nic.ifIndex -ServerAddresses $DCIp
        Write-Host "DNS set to $DCIp on $($nic.Name)" -ForegroundColor Green
    }

    $maxTries = 30
    for ($i = 0; $i -lt $maxTries; $i++) {
        try {
            Resolve-DnsName -Name $DomainName -Server $DCIp -ErrorAction Stop | Out-Null
            Write-Host "Domain DNS resolution OK" -ForegroundColor Green
            break
        } catch {
            Write-Host "  Waiting for DC DNS... ($i/$maxTries)" -ForegroundColor Gray
            Start-Sleep -Seconds 5
        }
    }

    $cs = Get-WmiObject Win32_ComputerSystem
    $needsRename = ($cs.Name -ne 'ACCT-DB01')
    $needsJoin   = (-not $cs.PartOfDomain) -or ($cs.Domain -ne $DomainName)

    if ($needsRename -or $needsJoin) {
        $cred = New-Object PSCredential($DCAdmin,
            (ConvertTo-SecureString $DCAdminPw -AsPlainText -Force))

        if ($needsJoin) {
            if ($needsRename) {
                Add-Computer -DomainName $DomainName -NewName 'ACCT-DB01' -Credential $cred `
                    -Force -ErrorAction Stop
            } else {
                Add-Computer -DomainName $DomainName -Credential $cred -Force
            }
        } elseif ($needsRename) {
            Rename-Computer -NewName 'ACCT-DB01' -Force
        }

        Register-ResumeTask -ScriptPath $MyInvocation.MyCommand.Path
        Set-Phase 'C-domainjoin'
        Request-Reboot -Reason 'Domain join / rename'
    }
}

# ============================================================
# Phase D -- Verify
# ============================================================
Invoke-Phase 'D-verify' {
    Write-Host "`n=== ACCT-DB01 Stage-1 complete ===" -ForegroundColor Cyan
    $cs = Get-WmiObject Win32_ComputerSystem
    Write-Host "Hostname:     $env:COMPUTERNAME" -ForegroundColor Green
    Write-Host "Domain:       $($cs.Domain)" -ForegroundColor Green
    Write-Host "PartOfDomain: $($cs.PartOfDomain)" -ForegroundColor Green
    Write-Host "IP:           $((Get-WmiObject Win32_NetworkAdapterConfiguration | ? IPEnabled).IPAddress -join ',')" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next: SNAPSHOT this VM as 'S2-domain-joined'." -ForegroundColor Yellow
}

Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce' `
    -Name 'ResumeLabSetup' -ErrorAction SilentlyContinue

Stop-LabTranscript
