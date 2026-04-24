# Setup-Web.ps1 — Athena AD Lab WEB01 provisioner
# Windows Server 2012 R2 Standard  —  IIS company website, domain member
# Hostname: WEB01  IP: 10.10.10.20  Domain: corp.athena.lab
#
# Usage (as Administrator, after Setup-DC.ps1 has finished on DC01):
#   powershell.exe -ExecutionPolicy Bypass -File .\Setup-Web.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'
$VerbosePreference     = 'Continue'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'common.psm1') -Force

Start-LabTranscript -ScriptName 'Setup-Web'

$DomainName  = 'corp.athena.lab'
$DCAdmin     = 'CORP\Administrator'
$DCAdminPw   = 'DomainAdminPw!2024'         # match the default local admin pw on DC (VMware Easy Install)
$DaPassword  = 'WinterIsComing!2024'         # da_alice — used for service-logon plant

# ============================================================
# Phase A — Baseline: WU off, time sync, network, firewall
# ============================================================
Invoke-Phase 'A-baseline' {
    Disable-WindowsUpdateHard
    Sync-Time -Peer '10.10.10.10'
    Set-LabNetwork -IPAddress '10.10.10.20' -Dns '10.10.10.10'
    New-NetFirewallRule -DisplayName 'Lab-AllowPing' -Protocol ICMPv4 -IcmpType 8 `
        -Action Allow -Direction Inbound -ErrorAction SilentlyContinue | Out-Null
}

# ============================================================
# Phase B — WMF 5.1 (PS 4.0 -> 5.1)
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
# Phase C — Rename + domain join
# ============================================================
Invoke-Phase 'C-domainjoin' {
    $cs = Get-WmiObject Win32_ComputerSystem
    $needsRename = ($cs.Name -ne 'WEB01')
    $needsJoin   = (-not $cs.PartOfDomain) -or ($cs.Domain -ne $DomainName)

    if ($needsRename -or $needsJoin) {
        $cred = New-Object PSCredential($DCAdmin,
            (ConvertTo-SecureString $DCAdminPw -AsPlainText -Force))
        $serversOu = 'OU=Servers,DC=corp,DC=athena,DC=lab'

        if ($needsRename -and $needsJoin) {
            Add-Computer -DomainName $DomainName -NewName 'WEB01' -Credential $cred `
                -OUPath $serversOu -Force -ErrorAction Stop
        } elseif ($needsRename) {
            Rename-Computer -NewName 'WEB01' -Force
        } else {
            Add-Computer -DomainName $DomainName -Credential $cred -OUPath $serversOu -Force
        }

        Register-ResumeTask -ScriptPath $MyInvocation.MyCommand.Path
        Set-Phase 'C-domainjoin'
        Request-Reboot -Reason 'Domain join / rename'
    }
}

# ============================================================
# Phase D — IIS + dummy company site
# ============================================================
Invoke-Phase 'D-iis' {
    Install-WindowsFeature Web-Server, Web-Mgmt-Console, Web-Windows-Auth, Web-Asp-Net45 `
        -IncludeManagementTools | Out-Null

    $siteSource = Join-Path $scriptDir 'site'
    $siteDest   = 'C:\inetpub\wwwroot'
    if (Test-Path $siteSource) {
        Copy-Item -Path (Join-Path $siteSource '*') -Destination $siteDest -Recurse -Force
        Write-Host "  + site content deployed from $siteSource" -ForegroundColor Green
    } else {
        # Bake a minimal placeholder
        $html = @'
<!DOCTYPE html>
<html><head><title>Contoso Accounting Portal</title></head>
<body><h1>Contoso Internal Accounting Portal</h1>
<p>Authorized users only. Please sign in with your domain credentials.</p>
<p><a href="/certsrv">Request a certificate</a></p>
</body></html>
'@
        $html | Set-Content -Path (Join-Path $siteDest 'index.html') -Encoding UTF8
    }
    # Open firewall 80
    New-NetFirewallRule -DisplayName 'IIS HTTP 80' -Direction Inbound -Protocol TCP `
        -LocalPort 80 -Action Allow -ErrorAction SilentlyContinue | Out-Null
}

# ============================================================
# Phase E — Disable SMB signing (relay target)
# ============================================================
Invoke-Phase 'E-smbsigning-off' {
    Set-SmbServerConfiguration -RequireSecuritySignature $false `
        -EnableSecuritySignature $false -Force -Confirm:$false
    # Reg-level belt and suspenders
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'RequireSecuritySignature' 0
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'EnableSecuritySignature'  0
    # Also ensure workstation side doesn't require
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters' 'RequireSecuritySignature' 0
    Write-Host "  + SMB signing disabled" -ForegroundColor Green
}

# ============================================================
# Phase F — LLMNR / NBT-NS on (verify, 2012 R2 default is on)
# ============================================================
Invoke-Phase 'F-llmnr' {
    Set-RegDword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient' 'EnableMulticast' 1
    $nbt = 'HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces'
    Get-ChildItem $nbt -ErrorAction SilentlyContinue | ForEach-Object {
        Set-ItemProperty -Path $_.PSPath -Name 'NetbiosOptions' -Value 0 -ErrorAction SilentlyContinue
    }
    Write-Host "  + LLMNR + NBT-NS enabled" -ForegroundColor Green
}

# ============================================================
# Phase G — Unconstrained delegation on WEB01$ (AD attribute, via DC)
# ============================================================
Invoke-Phase 'G-unconstrained' {
    # Use RSAT locally if available; else invoke on DC
    $rsat = Get-Module -ListAvailable ActiveDirectory
    if ($rsat) {
        Import-Module ActiveDirectory -Force
        Set-ADAccountControl -Identity 'WEB01$' -TrustedForDelegation $true
    } else {
        $cred = New-Object PSCredential($DCAdmin,
            (ConvertTo-SecureString $DCAdminPw -AsPlainText -Force))
        Invoke-Command -ComputerName 'dc01.corp.athena.lab' -Credential $cred -ScriptBlock {
            Import-Module ActiveDirectory
            Set-ADAccountControl -Identity 'WEB01$' -TrustedForDelegation $true
        }
    }
    Write-Host "  + WEB01 TrustedForDelegation = true (unconstrained)" -ForegroundColor Green
}

# ============================================================
# Phase H — WDigest cleartext credential caching
# ============================================================
Invoke-Phase 'H-wdigest' {
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'UseLogonCredential' 1
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'Negotiate'         1
    Write-Host "  + WDigest cleartext caching enabled" -ForegroundColor Green
}

# ============================================================
# Phase I — Plant DA credential in LSASS via persistent service
# ============================================================
Invoke-Phase 'I-plant-da' {
    $svcName = 'LabPlantSvc'
    # Remove any prior instance
    & sc.exe delete $svcName 2>&1 | Out-Null
    Start-Sleep -Seconds 2

    # Use ping -t to create a perpetual foreground process (hidden via service SCM)
    $binPath = 'cmd.exe /c ping -n 86400 127.0.0.1'
    & sc.exe create $svcName binPath= $binPath obj= "CORP\da_alice" password= $DaPassword start= auto DisplayName= "Lab Credential Plant" | Out-Null
    & sc.exe failure $svcName reset= 0 actions= restart/60000/restart/60000/restart/60000 | Out-Null

    # Grant da_alice SeServiceLogonRight (usually auto-granted by sc create, but ensure)
    # Use ntrights-equivalent via Group Policy is overkill — sc.exe create already adds the right.

    Start-Service $svcName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3

    $s = Get-Service $svcName -ErrorAction SilentlyContinue
    if ($s.Status -eq 'Running') {
        Write-Host "  + $svcName running as CORP\da_alice (LSASS will hold DA creds)" -ForegroundColor Green
    } else {
        Write-Host "  ! $svcName not running — check sc.exe query $svcName" -ForegroundColor Yellow
    }
}

# ============================================================
# Phase J — DPAPI credential plant via cmdkey (as da_alice)
# ============================================================
Invoke-Phase 'J-dpapi' {
    # Create a scheduled task running as da_alice that once caches a credential via cmdkey
    $taskName = 'LabDpapiPlant'
    & schtasks.exe /Delete /TN $taskName /F 2>&1 | Out-Null

    $cmdkeyCmd = 'cmd.exe /c cmdkey /add:backup.corp.athena.lab /user:CORP\svc_backup /pass:BackupMe!234 && cmdkey /add:acct-db01.corp.athena.lab /user:CORP\svc_sql /pass:Summer2023'

    & schtasks.exe /Create /TN $taskName /TR $cmdkeyCmd `
        /SC ONSTART /RU 'CORP\da_alice' /RP $DaPassword /RL HIGHEST /F | Out-Null

    # Run it now so the credential is stored even before first reboot
    & schtasks.exe /Run /TN $taskName 2>&1 | Out-Null
    Start-Sleep -Seconds 5
    Write-Host "  + DPAPI credentials planted under da_alice profile" -ForegroundColor Green
}

Write-Host "`n=============================================================" -ForegroundColor Cyan
Write-Host "  WEB01 setup complete. Shutdown and snapshot this VM." -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan

Stop-LabTranscript
