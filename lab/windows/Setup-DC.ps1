# Setup-DC.ps1 — Athena AD Lab DC01 provisioner
# Windows Server 2012 R2 Standard
# Hostname: DC01  IP: 10.10.10.10  Domain: corp.athena.lab  (NetBIOS: CORP)
#
# Usage (as Administrator, from C:\LabSetup\):
#   powershell.exe -ExecutionPolicy Bypass -File .\Setup-DC.ps1
# Script is idempotent and reboot-safe (uses RunOnce to resume).

#Requires -RunAsAdministrator

$ErrorActionPreference = 'Stop'
$VerbosePreference     = 'Continue'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'common.psm1') -Force

Start-LabTranscript -ScriptName 'Setup-DC'

$DomainName       = 'corp.athena.lab'
$DomainNetBIOS    = 'CORP'
$SafeModePwPlain  = 'SafeMode!2024'
$DaPassword       = 'WinterIsComing!2024'   # da_alice — used by Web/DB service-logon plant

# ============================================================
# Phase A — Windows Update disable + time sync + baseline
# ============================================================
Invoke-Phase 'A-baseline' {
    Disable-WindowsUpdateHard
    Sync-Time
    # Disable other services that may conflict
    foreach ($svc in @('W3SVC')) {
        Set-Service -Name $svc -StartupType Disabled -ErrorAction SilentlyContinue
        Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
    }
    # Allow all ICMP (ping) inbound — makes troubleshooting easier
    New-NetFirewallRule -DisplayName 'Lab-AllowPing' -Protocol ICMPv4 -IcmpType 8 `
        -Action Allow -Direction Inbound -ErrorAction SilentlyContinue | Out-Null
}

# ============================================================
# Phase B — Install WMF 5.1 if PS < 5 (Server 2012 R2 ships with 4.0)
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
# Phase C — Hostname + static IP + DNS = self
# ============================================================
Invoke-Phase 'C-network' {
    Set-LabNetwork -IPAddress '10.10.10.10' -Dns '127.0.0.1'
    if ((Get-WmiObject Win32_ComputerSystem).Name -ne 'DC01') {
        Rename-Computer -NewName 'DC01' -Force
        Register-ResumeTask -ScriptPath $MyInvocation.MyCommand.Path
        Set-Phase 'C-network'
        Request-Reboot -Reason 'Hostname changed to DC01'
    }
}

# ============================================================
# Phase D — Install AD DS + promote to PDC (creates corp.athena.lab)
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
            -DomainMode 'WinThreshold' -ForestMode 'WinThreshold' `
            -NoRebootOnCompletion:$false -Force -Confirm:$false

        Register-ResumeTask -ScriptPath $MyInvocation.MyCommand.Path
        Set-Phase 'D-addsforest'
        Request-Reboot -Reason 'Forest promotion — will resume after reboot'
    }
    else {
        Write-Host "Domain already present: $($domainCheck.DNSRoot)" -ForegroundColor Green
    }
}

# ============================================================
# Phase E — OU structure
# ============================================================
Invoke-Phase 'E-ou' {
    Import-Module ActiveDirectory -Force
    $base = (Get-ADDomain).DistinguishedName
    foreach ($ou in @('Tier0', 'Servers', 'Workstations')) {
        if (-not (Get-ADOrganizationalUnit -Filter "Name -eq '$ou'" -ErrorAction SilentlyContinue)) {
            New-ADOrganizationalUnit -Name $ou -Path $base -ProtectedFromAccidentalDeletion:$false
            Write-Host "Created OU: $ou" -ForegroundColor Green
        }
    }
}

# ============================================================
# Phase F — Users and groups (BloodHound attack path seeds)
# ============================================================
Invoke-Phase 'F-users' {
    Import-Module ActiveDirectory -Force

    function New-LabUser {
        param(
            [string]$Sam,
            [string]$Password,
            [string]$Description,
            [switch]$PreAuthNotRequired,
            [switch]$PasswordNeverExpires
        )
        if (Get-ADUser -Filter "SamAccountName -eq '$Sam'" -ErrorAction SilentlyContinue) {
            Write-Host "  user $Sam exists, skipping" -ForegroundColor DarkGray
            return
        }
        $sec = ConvertTo-SecureString $Password -AsPlainText -Force
        New-ADUser -Name $Sam -SamAccountName $Sam -AccountPassword $sec `
            -Enabled $true -Description $Description `
            -PasswordNeverExpires:$PasswordNeverExpires.IsPresent
        if ($PreAuthNotRequired) {
            Set-ADAccountControl -Identity $Sam -DoesNotRequirePreAuth $true
        }
        Write-Host "  + created $Sam" -ForegroundColor Green
    }

    # Standard users — weak passwords (top rockyou hits)
    New-LabUser -Sam 'steve'      -Password 'Summer2024!'       -Description 'Help desk tech'
    New-LabUser -Sam 'bob'        -Password 'Password1!'        -Description 'Sales'
    New-LabUser -Sam 'kevin'      -Password 'Welcome1'          -Description 'Intern'
    New-LabUser -Sam 'alice'      -Password 'P@ssw0rd2024'      -Description 'Finance (HelpDeskAdmins)'

    # AS-REP roastable
    New-LabUser -Sam 'legacy_kev' -Password 'Qwerty123!'        -Description 'AS-REP roastable' -PreAuthNotRequired

    # Service accounts with SPNs (Kerberoast)
    New-LabUser -Sam 'svc_sql'    -Password 'Summer2023'        -Description 'MSSQL service account' -PasswordNeverExpires
    New-LabUser -Sam 'svc_backup' -Password 'BackupMe!234'      -Description 'Backup service account' -PasswordNeverExpires

    # Low-priv with ACL abuse potential
    New-LabUser -Sam 'low_user'   -Password 'Changem3!'         -Description 'Low-priv helpdesk'

    # Domain Admin plant (replays on WEB01/ACCT-DB01)
    New-LabUser -Sam 'da_alice'   -Password $DaPassword         -Description 'Shadow DA' -PasswordNeverExpires
    if (-not (Get-ADGroupMember 'Domain Admins' | Where-Object SamAccountName -eq 'da_alice')) {
        Add-ADGroupMember -Identity 'Domain Admins' -Members da_alice
        Write-Host "  + da_alice added to Domain Admins" -ForegroundColor Green
    }

    # Register SPNs (Kerberoast)
    & setspn.exe -S 'MSSQLSvc/acct-db01.corp.athena.lab:1433' 'CORP\svc_sql'    2>&1 | Out-Null
    & setspn.exe -S 'MSSQLSvc/acct-db01.corp.athena.lab'      'CORP\svc_sql'    2>&1 | Out-Null
    & setspn.exe -S 'HTTP/backup.corp.athena.lab'             'CORP\svc_backup' 2>&1 | Out-Null

    # Groups
    $base = (Get-ADDomain).DistinguishedName
    $tier0Ou = "OU=Tier0,$base"
    if (-not (Get-ADGroup -Filter "Name -eq 'HelpDeskAdmins'" -ErrorAction SilentlyContinue)) {
        New-ADGroup -Name 'HelpDeskAdmins' -GroupScope Global -GroupCategory Security -Path $tier0Ou
    }
    if (-not (Get-ADGroupMember 'HelpDeskAdmins' | Where-Object SamAccountName -eq 'alice')) {
        Add-ADGroupMember -Identity 'HelpDeskAdmins' -Members alice
    }
}

# ============================================================
# Phase G — Over-permissive ACLs (BloodHound GenericAll / WriteDacl paths)
# ============================================================
Invoke-Phase 'G-acls' {
    Import-Module ActiveDirectory -Force
    $base    = (Get-ADDomain).DistinguishedName
    $tier0Ou = "OU=Tier0,$base"
    $serversOu = "OU=Servers,$base"

    # ACL 1: HelpDeskAdmins has GenericAll over Tier0 OU
    $acl = Get-Acl -Path "AD:$tier0Ou"
    $hdaSid = (Get-ADGroup HelpDeskAdmins).SID
    $allSchema = [Guid]::Empty
    $ace = New-Object System.DirectoryServices.ActiveDirectoryAccessRule(
        $hdaSid, 'GenericAll', 'Allow', $allSchema,
        [System.DirectoryServices.ActiveDirectorySecurityInheritance]::All, $allSchema
    )
    $acl.AddAccessRule($ace)
    Set-Acl -Path "AD:$tier0Ou" -AclObject $acl
    Write-Host "  + HelpDeskAdmins GenericAll -> Tier0 OU" -ForegroundColor Green

    # ACL 2: low_user has WriteDacl over svc_backup (shadow-creds path)
    $svc = Get-ADUser svc_backup
    $acl = Get-Acl -Path "AD:$($svc.DistinguishedName)"
    $luSid = (Get-ADUser low_user).SID
    $ace = New-Object System.DirectoryServices.ActiveDirectoryAccessRule(
        $luSid, 'WriteDacl', 'Allow'
    )
    $acl.AddAccessRule($ace)
    Set-Acl -Path "AD:$($svc.DistinguishedName)" -AclObject $acl
    Write-Host "  + low_user WriteDacl -> svc_backup" -ForegroundColor Green

    # ACL 3: low_user has GenericWrite over Servers OU (RBCD on any member)
    & dsacls.exe $serversOu /G 'CORP\low_user:WP;msDS-AllowedToActOnBehalfOfOtherIdentity' /I:S | Out-Null
    Write-Host "  + low_user GenericWrite msDS-AllowedToActOnBehalfOfOtherIdentity -> Servers OU" -ForegroundColor Green
}

# ============================================================
# Phase H — Weak password policy + LDAP signing not required
# ============================================================
Invoke-Phase 'H-policy' {
    Import-Module ActiveDirectory -Force
    Set-ADDefaultDomainPasswordPolicy -Identity corp.athena.lab `
        -ComplexityEnabled $true -MinPasswordLength 7 `
        -LockoutThreshold 20 -LockoutDuration (New-TimeSpan -Minutes 5) `
        -LockoutObservationWindow (New-TimeSpan -Minutes 5)

    # LDAP signing / channel binding — pin to NOT required
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\NTDS\Parameters' 'LDAPServerIntegrity' 1
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\NTDS\Parameters' 'LdapEnforceChannelBinding' 0
    Restart-Service NTDS -Force

    # Block GPO inheritance on Servers OU so SMB/LLMNR policies don't stomp our vulns later
    $base = (Get-ADDomain).DistinguishedName
    Import-Module GroupPolicy -ErrorAction SilentlyContinue
    Set-GPInheritance -Target "OU=Servers,$base" -IsBlocked Yes -ErrorAction SilentlyContinue | Out-Null
}

# ============================================================
# Phase I — Install AD CS (Enterprise Root CA) + Web Enrollment
# ============================================================
Invoke-Phase 'I-adcs' {
    Install-WindowsFeature ADCS-Cert-Authority, ADCS-Web-Enrollment -IncludeManagementTools -ErrorAction Stop | Out-Null

    $caInstalled = $false
    try { Get-CertificationAuthority -ErrorAction Stop | Out-Null; $caInstalled = $true } catch { }

    if (-not $caInstalled) {
        Install-AdcsCertificationAuthority -CAType EnterpriseRootCa `
            -CACommonName 'corp-DC01-CA' -HashAlgorithmName SHA256 `
            -KeyLength 2048 -ValidityPeriod Years -ValidityPeriodUnits 10 `
            -Force -Confirm:$false
    }

    try { Install-AdcsWebEnrollment -Force -Confirm:$false } catch {
        Write-Host "  Web Enrollment already installed or warning: $_" -ForegroundColor Yellow
    }
    Restart-Service CertSvc -Force
}

# ============================================================
# Phase J — ESC1 template VulnTemplate1
# ============================================================
Invoke-Phase 'J-esc1' {
    Import-Module ActiveDirectory -Force
    $pkiConfig = 'CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,' + (Get-ADDomain).DistinguishedName
    $existing = Get-ADObject -Filter "Name -eq 'VulnTemplate1'" -SearchBase $pkiConfig -ErrorAction SilentlyContinue

    if (-not $existing) {
        # Clone the built-in 'User' template attributes
        $src = Get-ADObject -Identity "CN=User,$pkiConfig" -Properties * -ErrorAction Stop
        $attrs = @{}
        foreach ($p in @(
            'flags','pKIDefaultKeySpec','pKIKeyUsage','pKIMaxIssuingDepth','pKICriticalExtensions',
            'pKIExtendedKeyUsage','pKIDefaultCSPs','msPKI-RA-Signature',
            'msPKI-Enrollment-Flag','msPKI-Private-Key-Flag','msPKI-Certificate-Name-Flag',
            'msPKI-Minimal-Key-Size','msPKI-Template-Schema-Version','msPKI-Template-Minor-Revision',
            'msPKI-Certificate-Application-Policy','revision'
        )) {
            if ($null -ne $src.$p) { $attrs[$p] = $src.$p }
        }
        # ESC1 bits
        $attrs['msPKI-Certificate-Name-Flag'] = 1        # CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT
        $attrs['msPKI-Enrollment-Flag']       = 0        # no manager approval
        $attrs['pKIExtendedKeyUsage']         = @('1.3.6.1.5.5.7.3.2')  # Client Auth
        $attrs['msPKI-Certificate-Application-Policy'] = @('1.3.6.1.5.5.7.3.2')

        New-ADObject -Name 'VulnTemplate1' -Type 'pKICertificateTemplate' `
            -Path $pkiConfig -OtherAttributes $attrs -ErrorAction Stop
        Write-Host "  + VulnTemplate1 created" -ForegroundColor Green
    }

    # Grant Domain Users Enroll right
    $tmplDn = "CN=VulnTemplate1,$pkiConfig"
    & dsacls.exe $tmplDn /G 'CORP\Domain Users:CA;Enroll' | Out-Null

    # Publish to CA
    & certutil.exe -SetCAtemplates "+VulnTemplate1" | Out-Null
    Restart-Service CertSvc -Force

    # Verify
    $pub = & certutil.exe -CATemplates 2>&1
    if ($pub -match 'VulnTemplate1') {
        Write-Host "  + VulnTemplate1 published on CA" -ForegroundColor Green
    } else {
        Write-Host "  ! WARNING: VulnTemplate1 not showing in certutil -CATemplates output" -ForegroundColor Red
    }
}

# ============================================================
# Phase K — ESC8: weaken Web Enrollment (HTTP + NTLM + no EPA)
# ============================================================
Invoke-Phase 'K-esc8' {
    Import-Module WebAdministration -ErrorAction SilentlyContinue
    try {
        # Remove SSL requirement
        Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/access' -name 'sslFlags' -value 'None' -ErrorAction SilentlyContinue
        # Disable Extended Protection
        Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/authentication/windowsAuthentication/extendedProtection' `
            -name 'tokenChecking' -value 'None' -ErrorAction SilentlyContinue
        # Enable NTLM fallback
        Clear-WebConfiguration -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/authentication/windowsAuthentication/providers' -ErrorAction SilentlyContinue
        Add-WebConfiguration -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/authentication/windowsAuthentication/providers' -value 'NTLM' -ErrorAction SilentlyContinue
        Add-WebConfiguration -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/authentication/windowsAuthentication/providers' -value 'Negotiate' -ErrorAction SilentlyContinue
        & iisreset.exe /restart | Out-Null
        Write-Host "  + Web Enrollment weakened (ESC8)" -ForegroundColor Green
    } catch {
        Write-Host "  ! ESC8 weakening partially failed: $_" -ForegroundColor Yellow
    }
}

# ============================================================
# Phase L — Ensure Spooler service is on (PrinterBug)
# ============================================================
Invoke-Phase 'L-spooler' {
    Set-Service -Name Spooler -StartupType Automatic
    Start-Service Spooler -ErrorAction SilentlyContinue
    Write-Host "  + Spooler ON" -ForegroundColor Green
}

# ============================================================
# Phase M — NullSessionPipes belt-and-suspenders (PetitPotam)
# ============================================================
Invoke-Phase 'M-nullpipes' {
    $path = 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters'
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    Set-RegDword $path 'NullSessionPipes_dummy' 0  # ensure key exists
    Remove-ItemProperty -Path $path -Name 'NullSessionPipes_dummy' -ErrorAction SilentlyContinue

    $pipes = @('netlogon','samr','lsarpc','efsrpc','spoolss','netdfs')
    New-ItemProperty -Path $path -Name 'NullSessionPipes' -Value $pipes `
        -PropertyType MultiString -Force | Out-Null
    Set-RegDword $path 'RestrictNullSessAccess' 0
    Write-Host "  + NullSessionPipes = $($pipes -join ', ')" -ForegroundColor Green
}

# ============================================================
# Phase N — DHCP scope for lab (10.10.10.100-200)
# ============================================================
Invoke-Phase 'N-dhcp' {
    try {
        Install-WindowsFeature DHCP -IncludeManagementTools -ErrorAction Stop | Out-Null
        Add-DhcpServerInDC -DnsName 'dc01.corp.athena.lab' -IPAddress 10.10.10.10 -ErrorAction SilentlyContinue
        # Mark DHCP as configured in registry
        Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\ServerManager\Roles\12' -Name 'ConfigurationState' -Value 2 -ErrorAction SilentlyContinue

        if (-not (Get-DhcpServerv4Scope -ScopeId 10.10.10.0 -ErrorAction SilentlyContinue)) {
            Add-DhcpServerv4Scope -Name 'AthenaLab' -StartRange 10.10.10.100 -EndRange 10.10.10.200 `
                -SubnetMask 255.255.255.0 -State Active
            Set-DhcpServerv4OptionValue -ScopeId 10.10.10.0 -DnsServer 10.10.10.10 `
                -Router 10.10.10.1 -DnsDomain 'corp.athena.lab'
        }
        Restart-Service DHCPServer -Force
        Write-Host "  + DHCP scope 10.10.10.100-200 active" -ForegroundColor Green
    } catch {
        Write-Host "  ! DHCP setup failed (non-fatal): $_" -ForegroundColor Yellow
    }
}

# ============================================================
# Phase O — Verification summary
# ============================================================
Invoke-Phase 'O-verify' {
    Write-Host "`n=============================================================" -ForegroundColor Cyan
    Write-Host "  DC01 VERIFICATION SUMMARY" -ForegroundColor Cyan
    Write-Host "=============================================================" -ForegroundColor Cyan

    Import-Module ActiveDirectory -Force
    Write-Host "`n[Users]" -ForegroundColor Yellow
    Get-ADUser -Filter * -Properties Description, servicePrincipalName, UserAccountControl |
        Where-Object { $_.SamAccountName -match 'steve|bob|kevin|alice|legacy_kev|svc_|low_user|da_alice' } |
        Select-Object SamAccountName, Description, @{n='SPN';e={$_.servicePrincipalName -join ';'}}, @{n='UAC_flags';e={'{0:X}' -f $_.UserAccountControl}} |
        Format-Table -AutoSize | Out-String | Write-Host

    Write-Host "`n[Domain Admins]" -ForegroundColor Yellow
    Get-ADGroupMember 'Domain Admins' | Select-Object SamAccountName | Format-Table -AutoSize | Out-String | Write-Host

    Write-Host "`n[CA Templates]" -ForegroundColor Yellow
    & certutil.exe -CATemplates 2>&1 | Out-String | Write-Host

    Write-Host "`n[Spooler]" -ForegroundColor Yellow
    Get-Service Spooler | Format-Table -AutoSize | Out-String | Write-Host

    Write-Host "`n[LDAP Integrity Registry]" -ForegroundColor Yellow
    Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\NTDS\Parameters' -Name LDAPServerIntegrity, LdapEnforceChannelBinding -ErrorAction SilentlyContinue |
        Format-List | Out-String | Write-Host

    Write-Host "`n[Null Session Pipes]" -ForegroundColor Yellow
    (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters').NullSessionPipes | Out-String | Write-Host

    Write-Host "`n[Recently applied hotfixes (should be EMPTY for clean 2012 R2)]" -ForegroundColor Yellow
    Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 | Format-Table -AutoSize | Out-String | Write-Host

    Write-Host "`n*** DC01 setup complete. Shutdown and snapshot as 'clean-vulnerable'. ***" -ForegroundColor Green
    Write-Host "*** Next steps on DC: run Setup-Web.ps1 on WEB01, Setup-DB.ps1 on ACCT-DB01 ***" -ForegroundColor Green
}

Stop-LabTranscript
