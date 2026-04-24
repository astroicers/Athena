# common.psm1 -- Shared helpers for Athena AD lab Setup-*.ps1 scripts
# Import with: Import-Module "$PSScriptRoot\common.psm1" -Force

$script:LabRoot = 'C:\LabSetup'

function Initialize-LabRoot {
    if (-not (Test-Path $script:LabRoot)) {
        New-Item -ItemType Directory -Path $script:LabRoot -Force | Out-Null
    }
    $logDir = Join-Path $script:LabRoot 'logs'
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
}

function Start-LabTranscript {
    param([string]$ScriptName)
    Initialize-LabRoot
    $logPath = Join-Path $script:LabRoot "logs\$ScriptName-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
    Start-Transcript -Path $logPath -Append -Force | Out-Null
    Write-Host "=== $ScriptName @ $(Get-Date) ===" -ForegroundColor Cyan
}

function Stop-LabTranscript {
    try { Stop-Transcript | Out-Null } catch { }
}

function Test-Phase {
    param([string]$PhaseId)
    $sentinel = Join-Path $script:LabRoot ".done.$PhaseId"
    return Test-Path $sentinel
}

function Set-Phase {
    param([string]$PhaseId)
    $sentinel = Join-Path $script:LabRoot ".done.$PhaseId"
    "$([DateTime]::UtcNow.ToString('o'))" | Out-File -FilePath $sentinel -Force -Encoding ascii
    Write-Host "[OK] Phase $PhaseId complete." -ForegroundColor Green
}

function Invoke-Phase {
    param(
        [string]$PhaseId,
        [scriptblock]$Action,
        [switch]$Force
    )
    if ((Test-Phase $PhaseId) -and -not $Force) {
        Write-Host "[SKIP] Phase $PhaseId already done." -ForegroundColor Yellow
        return
    }
    Write-Host "`n--- Phase $PhaseId starting ---" -ForegroundColor Cyan
    & $Action
    Set-Phase $PhaseId
}

function Set-RegDword {
    param([string]$Path, [string]$Name, [int]$Value)
    if (-not (Test-Path $Path)) {
        New-Item -Path $Path -Force | Out-Null
    }
    New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType DWord -Force | Out-Null
}

function Set-RegString {
    param([string]$Path, [string]$Name, [string]$Value, [string]$Type = 'String')
    if (-not (Test-Path $Path)) {
        New-Item -Path $Path -Force | Out-Null
    }
    New-ItemProperty -Path $Path -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
}

function Disable-WindowsUpdateHard {
    Write-Host "Disabling Windows Update services..." -ForegroundColor Gray
    foreach ($svc in @('wuauserv', 'UsoSvc', 'WaaSMedicSvc', 'BITS')) {
        try {
            Set-Service -Name $svc -StartupType Disabled -ErrorAction Stop
            Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Host "  (service $svc not found, skipping)" -ForegroundColor DarkGray
        }
    }
    Set-RegDword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' 'NoAutoUpdate' 1
    Set-RegDword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' 'AUOptions'    1
    Set-RegDword 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate'    'DisableWindowsUpdateAccess' 1
}

function Sync-Time {
    param([string]$Peer = 'time.windows.com')
    Write-Host "Syncing time from $Peer..." -ForegroundColor Gray
    try {
        & w32tm /config /manualpeerlist:$Peer /syncfromflags:manual /update | Out-Null
        & net stop w32time 2>$null | Out-Null
        & net start w32time 2>$null | Out-Null
        & w32tm /resync /force | Out-Null
    } catch {
        Write-Host "  (w32tm resync failed, continuing)" -ForegroundColor Yellow
    }
}

function Set-LabNetwork {
    param([string]$IPAddress, [int]$Prefix = 24, [string]$Gateway = '10.10.10.1', [string]$Dns = '10.10.10.10')
    $nic = Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object -First 1
    if (-not $nic) {
        throw "No up network adapter found."
    }

    Write-Host "Configuring $($nic.Name) -> $IPAddress/$Prefix gw=$Gateway dns=$Dns" -ForegroundColor Gray

    # Remove existing IPs on this NIC to avoid conflicts
    Get-NetIPAddress -InterfaceIndex $nic.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -ne $IPAddress } |
        Remove-NetIPAddress -Confirm:$false -ErrorAction SilentlyContinue
    Get-NetRoute -InterfaceIndex $nic.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.DestinationPrefix -eq '0.0.0.0/0' } |
        Remove-NetRoute -Confirm:$false -ErrorAction SilentlyContinue

    $existing = Get-NetIPAddress -InterfaceIndex $nic.ifIndex -IPAddress $IPAddress -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetIPAddress -InterfaceIndex $nic.ifIndex -IPAddress $IPAddress `
            -PrefixLength $Prefix -DefaultGateway $Gateway -ErrorAction SilentlyContinue | Out-Null
    }
    Set-DnsClientServerAddress -InterfaceIndex $nic.ifIndex -ServerAddresses $Dns -ErrorAction Stop
}

function Register-ResumeTask {
    param(
        [string]$ScriptPath,
        [string]$Arguments = '',
        [string]$TaskName  = 'AthenaLabResume'
    )
    # Use the ScheduledTasks cmdlets (PS 4+ on 2012 R2) rather than schtasks.exe
    # — cmdlet API handles quoted arguments robustly.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -EA SilentlyContinue
        $action = New-ScheduledTaskAction -Execute 'powershell.exe' `
            -Argument "-ExecutionPolicy Bypass -NoProfile -File `"$ScriptPath`" $Arguments"
        $trigger = New-ScheduledTaskTrigger -AtStartup
        $principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
            -ExecutionTimeLimit (New-TimeSpan -Hours 3)
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
            -Principal $principal -Settings $settings -Force | Out-Null
        Write-Host "Registered scheduled task '$TaskName' to resume after reboot." -ForegroundColor Gray
    } catch {
        Write-Host "ERROR registering resume task: $_" -ForegroundColor Red
        throw
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Unregister-ResumeTask {
    param([string]$TaskName = 'AthenaLabResume')
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -EA SilentlyContinue
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Request-Reboot {
    param([string]$Reason = 'phase complete')
    Write-Host "`n[REBOOT NEEDED] $Reason. Rebooting in 10 seconds..." -ForegroundColor Yellow
    Stop-LabTranscript
    Start-Sleep -Seconds 10
    Restart-Computer -Force
    exit
}

function Test-PowerShellVersionOK {
    return ($PSVersionTable.PSVersion.Major -ge 5)
}

function Install-Wmf51IfNeeded {
    param([string]$InstallerPath = 'C:\LabSetup\prereq\Win8.1AndW2K12R2-KB3191564-x64.msu')
    if (Test-PowerShellVersionOK) {
        Write-Host "PowerShell $($PSVersionTable.PSVersion) OK, WMF 5.1 not needed." -ForegroundColor Green
        return $false
    }
    if (-not (Test-Path $InstallerPath)) {
        throw "WMF 5.1 installer not found at $InstallerPath. Download KB3191564 first."
    }

    # wusa.exe needs: wuauserv + BITS + TrustedInstaller services running,
    # AND DisableWindowsUpdateAccess registry must NOT be set.
    Write-Host "Temporarily enabling wuauserv / BITS / msiserver for WMF install..." -ForegroundColor Gray
    foreach ($svc in @('wuauserv', 'BITS', 'msiserver', 'TrustedInstaller')) {
        try {
            Set-Service -Name $svc -StartupType Manual -EA SilentlyContinue
            Start-Service -Name $svc -EA SilentlyContinue
        } catch {
            Write-Host "  (service $svc start failed: $_)" -ForegroundColor DarkGray
        }
    }
    # Temporarily clear the WU access block (was set in Disable-WindowsUpdateHard)
    Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate' `
        -Name 'DisableWindowsUpdateAccess' -EA SilentlyContinue
    Remove-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU' `
        -Name 'NoAutoUpdate' -EA SilentlyContinue

    Write-Host "Installing WMF 5.1 from $InstallerPath (will reboot)..." -ForegroundColor Cyan
    $proc = Start-Process -FilePath 'wusa.exe' `
        -ArgumentList @("`"$InstallerPath`"", '/quiet', '/norestart') `
        -Wait -PassThru -NoNewWindow
    $rc = $proc.ExitCode
    Write-Host "wusa.exe exit code: $rc" -ForegroundColor Gray

    # Re-disable wuauserv + BITS so reboot-resume doesn't trigger WU auto-update
    foreach ($svc in @('wuauserv', 'BITS')) {
        try {
            Set-Service -Name $svc -StartupType Disabled -EA SilentlyContinue
            Stop-Service -Name $svc -Force -EA SilentlyContinue
        } catch {}
    }

    # Accept exit codes: 0 = success, 3010 = success/reboot-required,
    # 2359302 = already installed, 1638 = already installed (older wusa)
    $ok = @(0, 3010, 2359302, 1638)
    if ($ok -notcontains $rc) {
        throw "wusa.exe failed with exit code $rc - check C:\Windows\Logs\CBS\CBS.log"
    }
    return $true
}

Export-ModuleMember -Function *
