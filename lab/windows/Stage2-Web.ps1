# Stage2-Web.ps1 -- WEB01 vuln injection (after S2-domain-joined snapshot)
# Adds: IIS + site, SMB signing off, LLMNR verify, unconstrained delegation on WEB01$,
# WDigest cleartext, da_alice service-logon plant, DPAPI cmdkey plant

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$VerbosePreference     = 'Continue'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'common.psm1') -Force

Start-LabTranscript -ScriptName 'Stage2-Web'

$DomainName = 'corp.athena.lab'
$DCAdmin    = 'administrator@corp.athena.lab'
$DCAdminPw  = '1qaz@WSX'
$DaPassword = 'WinterIsComing!2024'

# ============================================================
# Phase S2-D -- IIS + dummy site
# ============================================================
Invoke-Phase 'S2-D-iis' {
    Install-WindowsFeature Web-Server, Web-Mgmt-Console, Web-Windows-Auth -IncludeManagementTools | Out-Null

    $siteDst = 'C:\inetpub\wwwroot'
    $siteSrc = Join-Path $scriptDir 'site'
    if (Test-Path $siteSrc) {
        Copy-Item -Path (Join-Path $siteSrc '*') -Destination $siteDst -Recurse -Force
        Write-Host "  + site deployed from $siteSrc" -ForegroundColor Green
    } else {
        $html = '<!DOCTYPE html><html><head><title>Contoso Accounting Portal</title></head><body><h1>Contoso Internal Accounting Portal</h1><p>Authorized users only.</p></body></html>'
        $html | Set-Content -Path (Join-Path $siteDst 'index.html') -Encoding UTF8
        Write-Host "  + minimal index.html written" -ForegroundColor Green
    }
    New-NetFirewallRule -DisplayName 'IIS HTTP 80' -Direction Inbound -Protocol TCP `
        -LocalPort 80 -Action Allow -EA SilentlyContinue | Out-Null
}

# ============================================================
# Phase S2-E -- Disable SMB signing (relay target)
# ============================================================
Invoke-Phase 'S2-E-smbsigning-off' {
    Set-SmbServerConfiguration -RequireSecuritySignature $false `
        -EnableSecuritySignature $false -Force -Confirm:$false
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'RequireSecuritySignature' 0
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'EnableSecuritySignature'  0
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters' 'RequireSecuritySignature' 0
    Write-Host "  + SMB signing disabled" -ForegroundColor Green
}

# ============================================================
# Phase S2-F -- LLMNR / NBT-NS enabled
# ============================================================
Invoke-Phase 'S2-F-llmnr' {
    Set-RegDword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\DNSClient' 'EnableMulticast' 1
    $nbt = 'HKLM:\SYSTEM\CurrentControlSet\Services\NetBT\Parameters\Interfaces'
    Get-ChildItem $nbt -EA SilentlyContinue | ForEach-Object {
        Set-ItemProperty -Path $_.PSPath -Name 'NetbiosOptions' -Value 0 -EA SilentlyContinue
    }
    Write-Host "  + LLMNR + NBT-NS enabled" -ForegroundColor Green
}

# ============================================================
# Phase S2-G -- Unconstrained delegation on WEB01$ (via DC RSAT)
# ============================================================
Invoke-Phase 'S2-G-unconstrained' {
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
    Write-Host "  + WEB01 TrustedForDelegation=True" -ForegroundColor Green
}

# ============================================================
# Phase S2-H -- WDigest cleartext caching
# ============================================================
Invoke-Phase 'S2-H-wdigest' {
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'UseLogonCredential' 1
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'Negotiate' 1
    Write-Host "  + WDigest cleartext enabled" -ForegroundColor Green
}

# ============================================================
# Phase S2-I -- Plant DA credential in LSASS via persistent service
# ============================================================
Invoke-Phase 'S2-I-plant-da' {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $svcName = 'LabPlantSvc'
        cmd.exe /c "sc.exe delete $svcName >nul 2>&1" | Out-Null
        Start-Sleep -Seconds 2

        $binPath = 'cmd.exe /c ping -n 86400 127.0.0.1'
        & sc.exe create $svcName binPath= $binPath obj= "CORP\da_alice" password= $DaPassword `
            start= auto DisplayName= "Lab Credential Plant" | Out-Null
        & sc.exe failure $svcName reset= 0 actions= restart/60000/restart/60000/restart/60000 | Out-Null

        Start-Service $svcName -EA SilentlyContinue
        Start-Sleep -Seconds 3
        $s = Get-Service $svcName -EA SilentlyContinue
        if ($s.Status -eq 'Running') {
            Write-Host "  + $svcName running as CORP\da_alice" -ForegroundColor Green
        } else {
            Write-Host "  ! $svcName not running: $($s.Status)" -ForegroundColor Yellow
        }
    } finally {
        $ErrorActionPreference = $prev
    }
}

# ============================================================
# Phase S2-J -- DPAPI cmdkey plant (as da_alice via scheduled task)
# ============================================================
Invoke-Phase 'S2-J-dpapi' {
    $taskName = 'LabDpapiPlant'
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        cmd.exe /c "schtasks /Delete /TN `"$taskName`" /F >nul 2>&1" | Out-Null
        $cmdkeyCmd = 'cmd.exe /c cmdkey /add:backup.corp.athena.lab /user:CORP\svc_backup /pass:BackupMe!234 && cmdkey /add:acct-db01.corp.athena.lab /user:CORP\svc_sql /pass:Summer2023'
        cmd.exe /c "schtasks /Create /TN `"$taskName`" /TR `"$cmdkeyCmd`" /SC ONSTART /RU `"CORP\da_alice`" /RP `"$DaPassword`" /RL HIGHEST /F >nul 2>&1" | Out-Null
        cmd.exe /c "schtasks /Run /TN `"$taskName`" >nul 2>&1" | Out-Null
    } finally {
        $ErrorActionPreference = $prev
    }
    Start-Sleep -Seconds 5
    Write-Host "  + DPAPI plants installed" -ForegroundColor Green
}

Write-Host "`n=== WEB01 Stage-2 COMPLETE ===" -ForegroundColor Cyan
Unregister-ResumeTask
Stop-LabTranscript
