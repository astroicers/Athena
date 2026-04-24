# Stage1-DC.ps1 -- Athena AD Lab Stage 1 for DC01 (Bridged mode)
# Goal: WMF 5.1 -> rename -> DNS self -> AD DS forest corp.athena.lab. STOP before vulns.
# After this completes, snapshot as 'S2-domain-joined' then run Stage2-DC.ps1.
#
# Existing IP is kept as-is (DHCP-assigned 192.168.0.16). We do NOT change IP
# since the host is on the home LAN Bridged -- only fix DNS to 127.0.0.1 so DC
# becomes its own DNS resolver post-promotion.

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'
$VerbosePreference     = 'Continue'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'common.psm1') -Force

Start-LabTranscript -ScriptName 'Stage1-DC'

$DomainName      = 'corp.athena.lab'
$DomainNetBIOS   = 'CORP'
$SafeModePwPlain = 'SafeMode!2024'

# ============================================================
# Phase A -- Baseline: WU off, time sync, Defender off, firewall
# ============================================================
Invoke-Phase 'A-baseline' {
    Disable-WindowsUpdateHard
    Sync-Time
    foreach ($svc in @('W3SVC')) {
        Set-Service -Name $svc -StartupType Disabled -ErrorAction SilentlyContinue
        Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
    }
    # Allow ICMP inbound for troubleshooting
    New-NetFirewallRule -DisplayName 'Lab-AllowPing' -Protocol ICMPv4 -IcmpType 8 `
        -Action Allow -Direction Inbound -ErrorAction SilentlyContinue | Out-Null

    # Keep Defender (where available) permissive for lab work
    try {
        Set-MpPreference -DisableRealtimeMonitoring $true -EA SilentlyContinue
        Add-MpPreference -ExclusionPath 'C:\' -EA SilentlyContinue
    } catch {}
}

# ============================================================
# Phase B -- WMF 5.1 (PS 4.0 -> 5.1), reboot if installed
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
# Phase C -- Hostname DC01 + DNS = self (keep existing DHCP IP)
# ============================================================
Invoke-Phase 'C-network' {
    # Set DNS to self so AD DS promotion works
    $nic = Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -First 1
    if ($nic) {
        Set-DnsClientServerAddress -InterfaceIndex $nic.ifIndex -ServerAddresses '127.0.0.1'
        Write-Host "DNS set to 127.0.0.1 on $($nic.Name)" -ForegroundColor Green
    }

    if ((Get-WmiObject Win32_ComputerSystem).Name -ne 'DC01') {
        Rename-Computer -NewName 'DC01' -Force
        Register-ResumeTask -ScriptPath $MyInvocation.MyCommand.Path
        Set-Phase 'C-network'
        Request-Reboot -Reason 'Hostname changed to DC01'
    }
}

# ============================================================
# Phase D -- Install AD DS + promote to PDC (creates corp.athena.lab)
# ============================================================
Invoke-Phase 'D-addsforest' {
    Install-WindowsFeature AD-Domain-Services, DNS, RSAT-AD-Tools, RSAT-ADCS, RSAT-DNS-Server `
        -IncludeManagementTools -ErrorAction Stop | Out-Null

    $domainCheck = $null
    try { $domainCheck = Get-ADDomain -Server localhost -ErrorAction Stop } catch { }

    if (-not $domainCheck) {
        Import-Module ADDSDeployment -Force
        $safeModePw = ConvertTo-SecureString $SafeModePwPlain -AsPlainText -Force
        Install-ADDSForest -DomainName $DomainName -DomainNetbiosName $DomainNetBIOS `
            -SafeModeAdministratorPassword $safeModePw -InstallDNS `
            -DomainMode 'Win2012R2' -ForestMode 'Win2012R2' `
            -NoRebootOnCompletion:$false -Force -Confirm:$false

        Register-ResumeTask -ScriptPath $MyInvocation.MyCommand.Path
        Set-Phase 'D-addsforest'
        Request-Reboot -Reason 'Forest promotion - will resume after reboot'
    } else {
        Write-Host "Domain already present: $($domainCheck.DNSRoot)" -ForegroundColor Green
    }
}

# ============================================================
# Phase E -- Verification (light, no user/ACL creation yet)
# ============================================================
Invoke-Phase 'E-verify' {
    Write-Host "`n=== DC01 Stage-1 complete ===" -ForegroundColor Cyan
    $d = Get-ADDomain
    Write-Host "Domain:         $($d.DNSRoot) ($($d.NetBIOSName))" -ForegroundColor Green
    Write-Host "Forest:         $($d.Forest)" -ForegroundColor Green
    Write-Host "DomainMode:     $($d.DomainMode)" -ForegroundColor Green
    Write-Host "PDCEmulator:    $($d.PDCEmulator)" -ForegroundColor Green
    Write-Host "Hostname:       $env:COMPUTERNAME" -ForegroundColor Green
    Write-Host "IP:             $((Get-WmiObject Win32_NetworkAdapterConfiguration | ? IPEnabled).IPAddress -join ',')" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next: SNAPSHOT this VM as 'S2-domain-joined'." -ForegroundColor Yellow
    Write-Host "      Then run Stage1-Web.ps1 on WEB01 + Stage1-DB.ps1 on ACCT-DB01." -ForegroundColor Yellow
}

# Clean up RunOnce so we don't loop
Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce' `
    -Name 'ResumeLabSetup' -ErrorAction SilentlyContinue

Stop-LabTranscript
