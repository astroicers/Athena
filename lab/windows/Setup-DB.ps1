# Setup-DB.ps1 — Athena AD Lab ACCT-DB01 provisioner
# Windows Server 2012 R2 Standard  —  MSSQL 2019 Express, domain member
# Hostname: ACCT-DB01  IP: 10.10.10.30  Domain: corp.athena.lab
#
# Prerequisites in C:\LabSetup\:
#   - sql\ConfigurationFile.ini        (provided)
#   - sql\setup.exe (and full MSSQL 2019 Express media)
#     Download: https://www.microsoft.com/en-us/download/details.aspx?id=101064
#     Extract the full media (Media Download ~ 660MB), place setup.exe + all files under sql\
#
# Usage (as Administrator, after Setup-DC.ps1 has finished on DC01):
#   powershell.exe -ExecutionPolicy Bypass -File .\Setup-DB.ps1

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'
$VerbosePreference     = 'Continue'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'common.psm1') -Force

Start-LabTranscript -ScriptName 'Setup-DB'

$DomainName  = 'corp.athena.lab'
$DCAdmin     = 'CORP\Administrator'
$DCAdminPw   = 'DomainAdminPw!2024'
$DaPassword  = 'WinterIsComing!2024'

# ============================================================
# Phase A — Baseline
# ============================================================
Invoke-Phase 'A-baseline' {
    Disable-WindowsUpdateHard
    Sync-Time -Peer '10.10.10.10'
    Set-LabNetwork -IPAddress '10.10.10.30' -Dns '10.10.10.10'
    New-NetFirewallRule -DisplayName 'Lab-AllowPing' -Protocol ICMPv4 -IcmpType 8 `
        -Action Allow -Direction Inbound -ErrorAction SilentlyContinue | Out-Null
}

# ============================================================
# Phase B — WMF 5.1
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
    $needsRename = ($cs.Name -ne 'ACCT-DB01')
    $needsJoin   = (-not $cs.PartOfDomain) -or ($cs.Domain -ne $DomainName)

    if ($needsRename -or $needsJoin) {
        $cred = New-Object PSCredential($DCAdmin,
            (ConvertTo-SecureString $DCAdminPw -AsPlainText -Force))
        $serversOu = 'OU=Servers,DC=corp,DC=athena,DC=lab'

        if ($needsRename -and $needsJoin) {
            Add-Computer -DomainName $DomainName -NewName 'ACCT-DB01' -Credential $cred `
                -OUPath $serversOu -Force -ErrorAction Stop
        } elseif ($needsRename) {
            Rename-Computer -NewName 'ACCT-DB01' -Force
        } else {
            Add-Computer -DomainName $DomainName -Credential $cred -OUPath $serversOu -Force
        }

        Register-ResumeTask -ScriptPath $MyInvocation.MyCommand.Path
        Set-Phase 'C-domainjoin'
        Request-Reboot -Reason 'Domain join / rename'
    }
}

# ============================================================
# Phase D — Disable SMB signing (relay target)
# ============================================================
Invoke-Phase 'D-smbsigning-off' {
    Set-SmbServerConfiguration -RequireSecuritySignature $false `
        -EnableSecuritySignature $false -Force -Confirm:$false
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'RequireSecuritySignature' 0
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'EnableSecuritySignature'  0
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters' 'RequireSecuritySignature' 0
}

# ============================================================
# Phase E — WDigest + DA plant service + DPAPI cmdkey
# ============================================================
Invoke-Phase 'E-plant-da' {
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'UseLogonCredential' 1
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'Negotiate' 1

    $svcName = 'LabPlantSvc'
    & sc.exe delete $svcName 2>&1 | Out-Null
    Start-Sleep -Seconds 2
    $binPath = 'cmd.exe /c ping -n 86400 127.0.0.1'
    & sc.exe create $svcName binPath= $binPath obj= "CORP\da_alice" password= $DaPassword start= auto DisplayName= "Lab Credential Plant" | Out-Null
    & sc.exe failure $svcName reset= 0 actions= restart/60000/restart/60000/restart/60000 | Out-Null
    Start-Service $svcName -ErrorAction SilentlyContinue

    $taskName = 'LabDpapiPlant'
    & schtasks.exe /Delete /TN $taskName /F 2>&1 | Out-Null
    $cmdkeyCmd = 'cmd.exe /c cmdkey /add:backup.corp.athena.lab /user:CORP\svc_backup /pass:BackupMe!234 && cmdkey /add:web01.corp.athena.lab /user:CORP\alice /pass:P@ssw0rd2024'
    & schtasks.exe /Create /TN $taskName /TR $cmdkeyCmd `
        /SC ONSTART /RU 'CORP\da_alice' /RP $DaPassword /RL HIGHEST /F | Out-Null
    & schtasks.exe /Run /TN $taskName 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    Write-Host "  + DA + DPAPI plants installed" -ForegroundColor Green
}

# ============================================================
# Phase F — Install MSSQL 2019 Express silently
# ============================================================
Invoke-Phase 'F-mssql' {
    $setupExe = Join-Path $scriptDir 'sql\setup.exe'
    $iniPath  = Join-Path $scriptDir 'sql\ConfigurationFile.ini'

    if (-not (Test-Path $setupExe)) {
        throw "MSSQL 2019 Express media not found at $setupExe — download full media and extract to $scriptDir\sql\"
    }
    if (-not (Test-Path $iniPath)) {
        throw "ConfigurationFile.ini not found at $iniPath"
    }

    # Skip if already installed
    $sqlInstalled = Get-Service -Name 'MSSQLSERVER' -ErrorAction SilentlyContinue
    if ($sqlInstalled) {
        Write-Host "  MSSQL already installed, skipping" -ForegroundColor Yellow
        return
    }

    Write-Host "  Installing MSSQL 2019 Express (this takes ~10 min)..." -ForegroundColor Gray
    $proc = Start-Process -FilePath $setupExe -ArgumentList @(
        "/ConfigurationFile=`"$iniPath`""
        "/Q"
        "/IACCEPTSQLSERVERLICENSETERMS"
    ) -Wait -PassThru -NoNewWindow
    if ($proc.ExitCode -ne 0) {
        throw "MSSQL install failed with exit code $($proc.ExitCode). Check C:\Program Files\Microsoft SQL Server\*\Setup Bootstrap\Log\Summary.txt"
    }
    Write-Host "  + MSSQL 2019 Express installed" -ForegroundColor Green
}

# ============================================================
# Phase G — Post-install MSSQL config: xp_cmdshell + fake Accounting DB
# ============================================================
Invoke-Phase 'G-mssql-config' {
    # Ensure sqlcmd exists (shipped with MSSQL setup)
    $sqlcmd = Get-Command sqlcmd.exe -ErrorAction SilentlyContinue
    if (-not $sqlcmd) {
        throw "sqlcmd.exe not on PATH. Log off and back on to pick up updated PATH, or rerun with PATH including MSSQL tools."
    }

    $bootstrap = @'
-- Enable xp_cmdshell (intentional - post-exploit proof)
EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;

-- Create a fake accounting database with some data
IF DB_ID('Accounting') IS NULL
    CREATE DATABASE Accounting;
GO
USE Accounting;
IF OBJECT_ID('Payroll') IS NULL
BEGIN
    CREATE TABLE Payroll (
        EmpId INT PRIMARY KEY,
        Name NVARCHAR(100),
        Salary DECIMAL(10,2),
        SSN VARCHAR(11)
    );
    INSERT INTO Payroll VALUES
        (1, 'Steve Stevenson',  72000.00, '123-45-6789'),
        (2, 'Alice Allenson',  145000.00, '234-56-7890'),
        (3, 'Kevin Keverson',   42000.00, '345-67-8901'),
        (4, 'Bob Bobberson',    61000.00, '456-78-9012');
END;
IF OBJECT_ID('Vendors') IS NULL
BEGIN
    CREATE TABLE Vendors (
        VendorId INT PRIMARY KEY,
        Name NVARCHAR(200),
        AccountNumber VARCHAR(50)
    );
    INSERT INTO Vendors VALUES
        (1, 'Acme Supplies',      'ACC-0001-ACME'),
        (2, 'Globex Imports',     'ACC-0002-GLBX'),
        (3, 'Initech Contractors','ACC-0003-INIT');
END;
'@ -replace "`r`n", "`n"

    $bootstrap | & sqlcmd -S 'localhost' -E -b
    if ($LASTEXITCODE -ne 0) {
        throw "sqlcmd bootstrap failed with exit $LASTEXITCODE"
    }
    Write-Host "  + xp_cmdshell enabled + Accounting DB seeded" -ForegroundColor Green
}

# ============================================================
# Phase H — Firewall: allow MSSQL 1433 inbound
# ============================================================
Invoke-Phase 'H-firewall' {
    New-NetFirewallRule -DisplayName 'MSSQL 1433' -Direction Inbound -Protocol TCP `
        -LocalPort 1433 -Action Allow -ErrorAction SilentlyContinue | Out-Null
    New-NetFirewallRule -DisplayName 'MSSQL Browser' -Direction Inbound -Protocol UDP `
        -LocalPort 1434 -Action Allow -ErrorAction SilentlyContinue | Out-Null
    Write-Host "  + Firewall allows 1433/tcp + 1434/udp" -ForegroundColor Green
}

# ============================================================
# Phase I — Verify SPN registered on DC (should be done by Setup-DC.ps1)
# ============================================================
Invoke-Phase 'I-verify' {
    $spn = & setspn.exe -L 'CORP\svc_sql' 2>&1 | Out-String
    if ($spn -match 'MSSQLSvc/acct-db01') {
        Write-Host "  + SPN registered: MSSQLSvc/acct-db01.corp.athena.lab" -ForegroundColor Green
    } else {
        Write-Host "  ! WARNING: SPN not registered on svc_sql — run on DC:" -ForegroundColor Red
        Write-Host "    setspn -S MSSQLSvc/acct-db01.corp.athena.lab:1433 CORP\svc_sql" -ForegroundColor Red
    }
}

Write-Host "`n=============================================================" -ForegroundColor Cyan
Write-Host "  ACCT-DB01 setup complete. Shutdown and snapshot this VM." -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan

Stop-LabTranscript
