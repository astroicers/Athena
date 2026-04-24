# Stage2-DB.ps1 -- ACCT-DB01 vuln injection (after S2-domain-joined snapshot)
# Adds: SMB signing off, WDigest, da_alice plant, DPAPI cmdkey plant,
# MSSQL 2019 Express, xp_cmdshell, fake Accounting DB

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$VerbosePreference     = 'Continue'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'common.psm1') -Force

Start-LabTranscript -ScriptName 'Stage2-DB'

$DomainName = 'corp.athena.lab'
$DaPassword = 'WinterIsComing!2024'

# ============================================================
# Phase S2-D -- Disable SMB signing
# ============================================================
Invoke-Phase 'S2-D-smbsigning-off' {
    Set-SmbServerConfiguration -RequireSecuritySignature $false `
        -EnableSecuritySignature $false -Force -Confirm:$false
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'RequireSecuritySignature' 0
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters' 'EnableSecuritySignature'  0
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters' 'RequireSecuritySignature' 0
    Write-Host "  + SMB signing disabled" -ForegroundColor Green
}

# ============================================================
# Phase S2-E -- WDigest + DA plant + DPAPI
# ============================================================
Invoke-Phase 'S2-E-plant-da' {
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'UseLogonCredential' 1
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\WDigest' 'Negotiate' 1

    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $svcName = 'LabPlantSvc'
        cmd.exe /c "sc.exe delete $svcName >nul 2>&1" | Out-Null
        Start-Sleep -Seconds 2
        $binPath = 'cmd.exe /c ping -n 86400 127.0.0.1'
        & sc.exe create $svcName binPath= $binPath obj= "CORP\da_alice" password= $DaPassword start= auto DisplayName= "Lab Credential Plant" | Out-Null
        & sc.exe failure $svcName reset= 0 actions= restart/60000/restart/60000/restart/60000 | Out-Null
        Start-Service $svcName -EA SilentlyContinue

        $taskName = 'LabDpapiPlant'
        cmd.exe /c "schtasks /Delete /TN `"$taskName`" /F >nul 2>&1" | Out-Null
        $cmdkeyCmd = 'cmd.exe /c cmdkey /add:backup.corp.athena.lab /user:CORP\svc_backup /pass:BackupMe!234 && cmdkey /add:web01.corp.athena.lab /user:CORP\alice /pass:P@ssw0rd2024'
        cmd.exe /c "schtasks /Create /TN `"$taskName`" /TR `"$cmdkeyCmd`" /SC ONSTART /RU `"CORP\da_alice`" /RP `"$DaPassword`" /RL HIGHEST /F >nul 2>&1" | Out-Null
        cmd.exe /c "schtasks /Run /TN `"$taskName`" >nul 2>&1" | Out-Null
    } finally {
        $ErrorActionPreference = $prev
    }
    Start-Sleep -Seconds 3
    Write-Host "  + WDigest + DA + DPAPI plants installed" -ForegroundColor Green
}

# ============================================================
# Phase S2-F -- Install MSSQL 2019 Express silently
# ============================================================
Invoke-Phase 'S2-F-mssql' {
    $sfx      = Join-Path $scriptDir 'sql\SQLEXPR_x64_ENU.exe'
    $iniPath  = Join-Path $scriptDir 'sql\ConfigurationFile.ini'
    $extractDir = 'C:\LabSetup\sql\extracted'

    $sqlInstalled = Get-Service -Name 'MSSQLSERVER' -EA SilentlyContinue
    if ($sqlInstalled) {
        Write-Host "  = MSSQL already installed, skipping" -ForegroundColor DarkGray
        return
    }

    if (-not (Test-Path $sfx)) {
        throw "SQLEXPR_x64_ENU.exe not found at $sfx - upload full media first"
    }
    if (-not (Test-Path $iniPath)) {
        throw "ConfigurationFile.ini not found at $iniPath"
    }

    # Step 1: extract the self-extracting CAB to extractDir (skip if done)
    $setupExe = Join-Path $extractDir 'setup.exe'
    if (-not (Test-Path $setupExe)) {
        New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
        Write-Host "  Extracting SQLEXPR_x64_ENU.exe to $extractDir ..." -ForegroundColor Gray
        $proc = Start-Process -FilePath $sfx -ArgumentList @("/q", "/x:`"$extractDir`"") -Wait -PassThru -NoNewWindow
        if ($proc.ExitCode -ne 0) {
            throw "SQLEXPR self-extract failed exit=$($proc.ExitCode)"
        }
        Write-Host "  + extraction complete" -ForegroundColor Green
    }
    if (-not (Test-Path $setupExe)) {
        throw "setup.exe not found at $setupExe after extract"
    }

    # Step 2: silent install with our ConfigurationFile.ini
    Write-Host "  Installing MSSQL 2019 Express (~10 min)..." -ForegroundColor Gray
    $proc = Start-Process -FilePath $setupExe -ArgumentList @(
        "/ConfigurationFile=`"$iniPath`"", "/Q", "/IACCEPTSQLSERVERLICENSETERMS"
    ) -Wait -PassThru -NoNewWindow
    if ($proc.ExitCode -ne 0) {
        throw "MSSQL install failed exit=$($proc.ExitCode). See C:\Program Files\Microsoft SQL Server\*\Setup Bootstrap\Log\Summary.txt"
    }
    Write-Host "  + MSSQL 2019 Express installed" -ForegroundColor Green
}

# ============================================================
# Phase S2-G -- Post-install MSSQL config (xp_cmdshell + Accounting DB)
# ============================================================
Invoke-Phase 'S2-G-mssql-config' {
    $sqlcmd = Get-Command sqlcmd.exe -EA SilentlyContinue
    if (-not $sqlcmd) {
        # SQL tools may be in path after reboot; try well-known paths
        $known = @(
            "${env:ProgramFiles}\Microsoft SQL Server\Client SDK\ODBC\170\Tools\Binn\sqlcmd.exe",
            "${env:ProgramFiles}\Microsoft SQL Server\Client SDK\ODBC\130\Tools\Binn\sqlcmd.exe",
            "${env:ProgramFiles(x86)}\Microsoft SQL Server\Client SDK\ODBC\170\Tools\Binn\sqlcmd.exe"
        )
        foreach ($p in $known) { if (Test-Path $p) { $sqlcmd = $p; break } }
        if (-not $sqlcmd) { throw "sqlcmd.exe not found - reboot and retry" }
        $env:Path += ";$(Split-Path $sqlcmd -Parent)"
    }

    $bootstrap = @'
EXEC sp_configure 'show advanced options', 1; RECONFIGURE;
EXEC sp_configure 'xp_cmdshell', 1; RECONFIGURE;
GO
IF DB_ID('Accounting') IS NULL CREATE DATABASE Accounting;
GO
USE Accounting;
IF OBJECT_ID('Payroll') IS NULL
BEGIN
    CREATE TABLE Payroll (EmpId INT PRIMARY KEY, Name NVARCHAR(100), Salary DECIMAL(10,2), SSN VARCHAR(11));
    INSERT INTO Payroll VALUES
        (1,'Steve Stevenson',72000.00,'123-45-6789'),
        (2,'Alice Allenson',145000.00,'234-56-7890'),
        (3,'Kevin Keverson',42000.00,'345-67-8901'),
        (4,'Bob Bobberson',61000.00,'456-78-9012');
END;
IF OBJECT_ID('Vendors') IS NULL
BEGIN
    CREATE TABLE Vendors (VendorId INT PRIMARY KEY, Name NVARCHAR(200), AccountNumber VARCHAR(50));
    INSERT INTO Vendors VALUES
        (1,'Acme Supplies','ACC-0001-ACME'),
        (2,'Globex Imports','ACC-0002-GLBX'),
        (3,'Initech Contractors','ACC-0003-INIT');
END;
GO
'@
    $tmpSql = Join-Path $env:TEMP 'labsetup-boot.sql'
    $bootstrap | Set-Content -Path $tmpSql -Encoding ASCII

    & sqlcmd -S 'localhost' -E -b -i $tmpSql
    if ($LASTEXITCODE -ne 0) {
        throw "sqlcmd bootstrap failed exit=$LASTEXITCODE"
    }
    Remove-Item $tmpSql -EA SilentlyContinue
    Write-Host "  + xp_cmdshell enabled + Accounting DB seeded" -ForegroundColor Green
}

# ============================================================
# Phase S2-H -- Firewall: MSSQL 1433 + 1434 inbound
# ============================================================
Invoke-Phase 'S2-H-firewall' {
    New-NetFirewallRule -DisplayName 'MSSQL 1433' -Direction Inbound -Protocol TCP `
        -LocalPort 1433 -Action Allow -EA SilentlyContinue | Out-Null
    New-NetFirewallRule -DisplayName 'MSSQL Browser' -Direction Inbound -Protocol UDP `
        -LocalPort 1434 -Action Allow -EA SilentlyContinue | Out-Null
    Write-Host "  + Firewall allows 1433/tcp + 1434/udp" -ForegroundColor Green
}

# ============================================================
# Phase S2-I -- Verify SPN
# ============================================================
Invoke-Phase 'S2-I-verify' {
    $spn = & setspn.exe -L 'CORP\svc_sql' 2>&1 | Out-String
    if ($spn -match 'MSSQLSvc/acct-db01') {
        Write-Host "  + SPN MSSQLSvc/acct-db01 registered" -ForegroundColor Green
    } else {
        Write-Host "  ! SPN missing - run on DC: setspn -S MSSQLSvc/acct-db01.corp.athena.lab:1433 CORP\svc_sql" -ForegroundColor Red
    }
}

Write-Host "`n=== ACCT-DB01 Stage-2 COMPLETE ===" -ForegroundColor Cyan
Unregister-ResumeTask
Stop-LabTranscript
