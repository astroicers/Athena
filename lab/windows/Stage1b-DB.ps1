# Stage1b-DB.ps1 -- Offline domain join via djoin blob

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$VerbosePreference     = 'Continue'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'common.psm1') -Force

Start-LabTranscript -ScriptName 'Stage1b-DB'

$DomainName = 'corp.athena.lab'
$DCIp       = '192.168.0.16'
$BlobPath   = Join-Path $scriptDir 'acctdb01-djoin.blob'

Invoke-Phase 'C-domainjoin-offline' {
    $nic = Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -First 1
    if ($nic) {
        Set-DnsClientServerAddress -InterfaceIndex $nic.ifIndex -ServerAddresses $DCIp
    }
    if (-not (Test-Path $BlobPath)) {
        throw "djoin blob not found at $BlobPath"
    }
    & djoin.exe /REQUESTODJ /LOADFILE $BlobPath /WINDOWSPATH C:\Windows /LOCALOS
    if ($LASTEXITCODE -ne 0) {
        throw "djoin /REQUESTODJ failed: exit $LASTEXITCODE"
    }
    Register-ResumeTask -ScriptPath $MyInvocation.MyCommand.Path
    Set-Phase 'C-domainjoin-offline'
    Request-Reboot -Reason 'Offline domain join applied -- reboot to activate'
}

Invoke-Phase 'D-verify' {
    Write-Host "`n=== ACCT-DB01 Stage-1 complete ===" -ForegroundColor Cyan
    $cs = Get-WmiObject Win32_ComputerSystem
    Write-Host "Hostname:     $env:COMPUTERNAME" -ForegroundColor Green
    Write-Host "Domain:       $($cs.Domain)"  -ForegroundColor Green
    Write-Host "PartOfDomain: $($cs.PartOfDomain)" -ForegroundColor Green
    Write-Host "IP:           $((Get-WmiObject Win32_NetworkAdapterConfiguration|?IPEnabled).IPAddress -join ',')" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next: SNAPSHOT this VM as 'S2-domain-joined'." -ForegroundColor Yellow
}

Unregister-ResumeTask
Stop-LabTranscript
