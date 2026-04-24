# Stage2-DC.ps1 -- DC01 vulnerability injection (after S2 snapshot)
# Adds: users/groups, abusive ACLs, weak password policy, AD CS ESC1+ESC8,
# Spooler, NullSessionPipes, LDAP signing off. No reboots required.

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'
$VerbosePreference     = 'Continue'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $scriptDir 'common.psm1') -Force

Start-LabTranscript -ScriptName 'Stage2-DC'

$DomainName    = 'corp.athena.lab'
$DomainNetBIOS = 'CORP'
$DaPassword    = 'WinterIsComing!2024'

# ============================================================
# Phase S2-E -- OU structure
# ============================================================
Invoke-Phase 'S2-E-ou' {
    Import-Module ActiveDirectory -Force
    $base = (Get-ADDomain).DistinguishedName
    foreach ($ou in @('Tier0','Servers','Workstations')) {
        if (-not (Get-ADOrganizationalUnit -Filter "Name -eq '$ou'" -EA SilentlyContinue)) {
            New-ADOrganizationalUnit -Name $ou -Path $base -ProtectedFromAccidentalDeletion:$false
            Write-Host "  + OU $ou created" -ForegroundColor Green
        }
    }
    # Move WEB01 and ACCT-DB01 to OU=Servers so GPO inheritance block (Phase S2-H) applies
    foreach ($cn in @('WEB01','ACCT-DB01')) {
        $c = Get-ADComputer $cn -EA SilentlyContinue
        if ($c -and $c.DistinguishedName -notmatch 'OU=Servers') {
            Move-ADObject -Identity $c.DistinguishedName -TargetPath "OU=Servers,$base"
            Write-Host "  + moved $cn to OU=Servers" -ForegroundColor Green
        }
    }
}

# ============================================================
# Phase S2-F -- Users + groups + SPNs (BloodHound seeds)
# ============================================================
Invoke-Phase 'S2-F-users' {
    Import-Module ActiveDirectory -Force

    function New-LabUser {
        param([string]$Sam,[string]$Password,[string]$Description,
              [switch]$PreAuthNotRequired,[switch]$PasswordNeverExpires)
        if (Get-ADUser -Filter "SamAccountName -eq '$Sam'" -EA SilentlyContinue) {
            Write-Host "  = $Sam exists, skipping" -ForegroundColor DarkGray; return
        }
        $sec = ConvertTo-SecureString $Password -AsPlainText -Force
        New-ADUser -Name $Sam -SamAccountName $Sam -AccountPassword $sec -Enabled $true `
            -Description $Description -PasswordNeverExpires:$PasswordNeverExpires.IsPresent
        if ($PreAuthNotRequired) { Set-ADAccountControl -Identity $Sam -DoesNotRequirePreAuth $true }
        Write-Host "  + created $Sam" -ForegroundColor Green
    }

    # Weak-password users (rockyou top hits)
    New-LabUser steve      'Summer2024!'       'Help desk tech'
    New-LabUser bob        'Password1!'        'Sales'
    New-LabUser kevin      'Welcome1'          'Intern'
    New-LabUser alice      'P@ssw0rd2024'      'Finance (HelpDeskAdmins)'
    # AS-REP roastable
    New-LabUser legacy_kev 'Qwerty123!'        'AS-REP roastable' -PreAuthNotRequired
    # Kerberoast targets
    New-LabUser svc_sql    'Summer2023'        'MSSQL service account' -PasswordNeverExpires
    New-LabUser svc_backup 'BackupMe!234'      'Backup service account' -PasswordNeverExpires
    # Low-priv with ACL abuse
    New-LabUser low_user   'Changem3!'         'Low-priv helpdesk'
    # Shadow Domain Admin
    New-LabUser da_alice   $DaPassword         'Shadow DA' -PasswordNeverExpires
    if (-not (Get-ADGroupMember 'Domain Admins' | Where-Object SamAccountName -eq 'da_alice')) {
        Add-ADGroupMember 'Domain Admins' -Members da_alice
        Write-Host "  + da_alice -> Domain Admins" -ForegroundColor Green
    }

    # SPN registration
    & setspn.exe -S 'MSSQLSvc/acct-db01.corp.athena.lab:1433' 'CORP\svc_sql'    2>&1 | Out-Null
    & setspn.exe -S 'MSSQLSvc/acct-db01.corp.athena.lab'      'CORP\svc_sql'    2>&1 | Out-Null
    & setspn.exe -S 'HTTP/backup.corp.athena.lab'             'CORP\svc_backup' 2>&1 | Out-Null

    # Groups
    $base = (Get-ADDomain).DistinguishedName
    $tier0Ou = "OU=Tier0,$base"
    if (-not (Get-ADGroup -Filter "Name -eq 'HelpDeskAdmins'" -EA SilentlyContinue)) {
        New-ADGroup -Name 'HelpDeskAdmins' -GroupScope Global -GroupCategory Security -Path $tier0Ou
    }
    if (-not (Get-ADGroupMember 'HelpDeskAdmins' | Where-Object SamAccountName -eq 'alice')) {
        Add-ADGroupMember 'HelpDeskAdmins' -Members alice
    }
}

# ============================================================
# Phase S2-G -- Abusive ACLs
# ============================================================
Invoke-Phase 'S2-G-acls' {
    Import-Module ActiveDirectory -Force
    $base = (Get-ADDomain).DistinguishedName
    $tier0Ou   = "OU=Tier0,$base"
    $serversOu = "OU=Servers,$base"

    # HelpDeskAdmins GenericAll -> Tier0 OU
    $acl = Get-Acl -Path "AD:$tier0Ou"
    $hda = (Get-ADGroup HelpDeskAdmins).SID
    $allSchema = [Guid]::Empty
    $ace = New-Object System.DirectoryServices.ActiveDirectoryAccessRule(
        $hda, 'GenericAll', 'Allow', $allSchema,
        [System.DirectoryServices.ActiveDirectorySecurityInheritance]::All, $allSchema)
    $acl.AddAccessRule($ace)
    Set-Acl -Path "AD:$tier0Ou" -AclObject $acl
    Write-Host "  + HelpDeskAdmins GenericAll -> Tier0" -ForegroundColor Green

    # low_user WriteDacl -> svc_backup
    $svc = Get-ADUser svc_backup
    $acl = Get-Acl -Path "AD:$($svc.DistinguishedName)"
    $lu = (Get-ADUser low_user).SID
    $ace = New-Object System.DirectoryServices.ActiveDirectoryAccessRule($lu, 'WriteDacl', 'Allow')
    $acl.AddAccessRule($ace)
    Set-Acl -Path "AD:$($svc.DistinguishedName)" -AclObject $acl
    Write-Host "  + low_user WriteDacl -> svc_backup" -ForegroundColor Green

    # low_user GenericWrite msDS-AllowedToActOnBehalfOfOtherIdentity on Servers OU (RBCD)
    & dsacls.exe $serversOu /G 'CORP\low_user:WP;msDS-AllowedToActOnBehalfOfOtherIdentity' /I:S | Out-Null
    Write-Host "  + low_user GenericWrite RBCD -> Servers OU" -ForegroundColor Green
}

# ============================================================
# Phase S2-H -- Weak password policy + LDAP signing off + GPO inheritance block
# ============================================================
Invoke-Phase 'S2-H-policy' {
    Import-Module ActiveDirectory -Force
    Set-ADDefaultDomainPasswordPolicy -Identity corp.athena.lab `
        -ComplexityEnabled $true -MinPasswordLength 7 `
        -LockoutThreshold 20 -LockoutDuration (New-TimeSpan -Minutes 5) `
        -LockoutObservationWindow (New-TimeSpan -Minutes 5)

    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\NTDS\Parameters' 'LDAPServerIntegrity' 1
    Set-RegDword 'HKLM:\SYSTEM\CurrentControlSet\Services\NTDS\Parameters' 'LdapEnforceChannelBinding' 0
    Restart-Service NTDS -Force

    # Wait for NTDS + DNS to come back
    Start-Sleep -Seconds 10
    $base = $null
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $base = (Get-ADDomain -Server localhost -EA Stop).DistinguishedName
            break
        } catch {
            Write-Host "  waiting for NTDS... ($i/30)" -ForegroundColor DarkGray
            Start-Sleep -Seconds 5
        }
    }
    if (-not $base) {
        throw "NTDS did not come back within 150s after restart"
    }
    Import-Module GroupPolicy -EA SilentlyContinue
    try {
        Set-GPInheritance -Target "OU=Servers,$base" -IsBlocked Yes -EA SilentlyContinue | Out-Null
        Write-Host "  + GPO inheritance blocked on OU=Servers" -ForegroundColor Green
    } catch {
        Write-Host "  = Set-GPInheritance skipped: $_" -ForegroundColor DarkGray
    }
}

# ============================================================
# Phase S2-I -- Install AD CS Enterprise Root CA + Web Enrollment
# ============================================================
Invoke-Phase 'S2-I-adcs' {
    Install-WindowsFeature ADCS-Cert-Authority, ADCS-Web-Enrollment -IncludeManagementTools -EA Stop | Out-Null

    $caInstalled = $false
    try { Get-CertificationAuthority -EA Stop | Out-Null; $caInstalled = $true } catch { }

    if (-not $caInstalled) {
        Install-AdcsCertificationAuthority -CAType EnterpriseRootCa `
            -CACommonName 'corp-DC01-CA' -HashAlgorithmName SHA256 `
            -KeyLength 2048 -ValidityPeriod Years -ValidityPeriodUnits 10 `
            -Force -Confirm:$false
    }
    try { Install-AdcsWebEnrollment -Force -Confirm:$false } catch {
        Write-Host "  = Web Enrollment: $_" -ForegroundColor DarkGray
    }
    Restart-Service CertSvc -Force
}

# ============================================================
# Phase S2-J -- ESC1 template VulnTemplate1
# ============================================================
Invoke-Phase 'S2-J-esc1' {
    Import-Module ActiveDirectory -Force
    $pkiConfig = 'CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,' + (Get-ADDomain).DistinguishedName
    $existing = Get-ADObject -Filter "Name -eq 'VulnTemplate1'" -SearchBase $pkiConfig -EA SilentlyContinue

    if (-not $existing) {
        $src = Get-ADObject -Identity "CN=User,$pkiConfig" -Properties * -EA Stop
        $attrs = @{}
        foreach ($p in @('flags','pKIDefaultKeySpec','pKIKeyUsage','pKIMaxIssuingDepth','pKICriticalExtensions',
            'pKIExtendedKeyUsage','pKIDefaultCSPs','msPKI-RA-Signature','msPKI-Enrollment-Flag',
            'msPKI-Private-Key-Flag','msPKI-Certificate-Name-Flag','msPKI-Minimal-Key-Size',
            'msPKI-Template-Schema-Version','msPKI-Template-Minor-Revision',
            'msPKI-Certificate-Application-Policy','revision')) {
            if ($null -ne $src.$p) { $attrs[$p] = $src.$p }
        }
        # ESC1 bits
        $attrs['msPKI-Certificate-Name-Flag'] = 1        # ENROLLEE_SUPPLIES_SUBJECT
        $attrs['msPKI-Enrollment-Flag']       = 0        # no manager approval
        $attrs['pKIExtendedKeyUsage']         = @('1.3.6.1.5.5.7.3.2')  # Client Auth
        $attrs['msPKI-Certificate-Application-Policy'] = @('1.3.6.1.5.5.7.3.2')

        New-ADObject -Name 'VulnTemplate1' -Type 'pKICertificateTemplate' `
            -Path $pkiConfig -OtherAttributes $attrs -EA Stop
        Write-Host "  + VulnTemplate1 created" -ForegroundColor Green
    }

    $tmplDn = "CN=VulnTemplate1,$pkiConfig"
    & dsacls.exe $tmplDn /G 'CORP\Domain Users:CA;Enroll' | Out-Null
    & certutil.exe -SetCAtemplates "+VulnTemplate1" | Out-Null
    Restart-Service CertSvc -Force

    $pub = & certutil.exe -CATemplates 2>&1
    if ($pub -match 'VulnTemplate1') {
        Write-Host "  + VulnTemplate1 published on CA" -ForegroundColor Green
    } else {
        Write-Host "  ! VulnTemplate1 not in certutil -CATemplates output" -ForegroundColor Red
    }
}

# ============================================================
# Phase S2-K -- ESC8: weaken Web Enrollment (HTTP + NTLM + no EPA)
# ============================================================
Invoke-Phase 'S2-K-esc8' {
    Import-Module WebAdministration -EA SilentlyContinue
    try {
        Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/access' -name 'sslFlags' -value 'None' -EA SilentlyContinue
        Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/authentication/windowsAuthentication/extendedProtection' `
            -name 'tokenChecking' -value 'None' -EA SilentlyContinue
        Clear-WebConfiguration -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/authentication/windowsAuthentication/providers' -EA SilentlyContinue
        Add-WebConfiguration -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/authentication/windowsAuthentication/providers' -value 'NTLM' -EA SilentlyContinue
        Add-WebConfiguration -pspath 'MACHINE/WEBROOT/APPHOST/Default Web Site/CertSrv' `
            -filter 'system.webServer/security/authentication/windowsAuthentication/providers' -value 'Negotiate' -EA SilentlyContinue
        & iisreset.exe /restart | Out-Null
        Write-Host "  + Web Enrollment weakened (ESC8)" -ForegroundColor Green
    } catch {
        Write-Host "  ! ESC8 weakening partial: $_" -ForegroundColor Yellow
    }
}

# ============================================================
# Phase S2-L -- Spooler ON (PrinterBug)
# ============================================================
Invoke-Phase 'S2-L-spooler' {
    Set-Service -Name Spooler -StartupType Automatic
    Start-Service Spooler -EA SilentlyContinue
    Write-Host "  + Spooler ON" -ForegroundColor Green
}

# ============================================================
# Phase S2-M -- NullSessionPipes (PetitPotam belt-and-suspenders)
# ============================================================
Invoke-Phase 'S2-M-nullpipes' {
    $path = 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters'
    if (-not (Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    $pipes = @('netlogon','samr','lsarpc','efsrpc','spoolss','netdfs')
    New-ItemProperty -Path $path -Name 'NullSessionPipes' -Value $pipes -PropertyType MultiString -Force | Out-Null
    Set-RegDword $path 'RestrictNullSessAccess' 0
    Write-Host "  + NullSessionPipes = $($pipes -join ', ')" -ForegroundColor Green
}

# ============================================================
# Phase S2-N -- Summary
# ============================================================
Invoke-Phase 'S2-N-summary' {
    Write-Host "`n=== DC01 Stage-2 COMPLETE ===" -ForegroundColor Cyan
    Import-Module ActiveDirectory -Force
    Write-Host "[Users]" -ForegroundColor Yellow
    Get-ADUser -Filter * -Properties Description, servicePrincipalName, UserAccountControl |
        Where-Object { $_.SamAccountName -match 'steve|bob|kevin|alice|legacy_kev|svc_|low_user|da_alice' } |
        Select-Object SamAccountName, Description, @{n='SPN';e={$_.servicePrincipalName -join ';'}} |
        Format-Table -AutoSize | Out-String | Write-Host

    Write-Host "[CA Templates]" -ForegroundColor Yellow
    & certutil.exe -CATemplates 2>&1 | Select-Object -First 20 | Out-String | Write-Host
    Write-Host "DC Stage-2 complete. Next run Stage2-Web + Stage2-DB on members." -ForegroundColor Green
}

Unregister-ResumeTask
Stop-LabTranscript
