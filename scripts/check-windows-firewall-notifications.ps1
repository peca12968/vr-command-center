[CmdletBinding()]
param([Parameter(Mandatory)][string]$Executable)

$ErrorActionPreference = 'Stop'
$file = Get-Item -LiteralPath $Executable
if ($file -isnot [IO.FileInfo] -or $file.Extension -ne '.exe') {
    throw "Expected a Windows executable file: $Executable"
}

$policy = New-Object -ComObject HNetCfg.FwPolicy2
$profiles = [ordered]@{ Domain = 1; Private = 2; Public = 4 }
$active = [int]$policy.CurrentProfileTypes
if ($active -lt 1 -or $active -gt 7) {
    throw 'Could not determine the active Windows Firewall profiles.'
}

# Both an allow rule and a block rule can settle the notification for a program.
# The caller still verifies whether its loopback traffic works.
$rules = @($policy.Rules | Where-Object {
    $_.Enabled -and $_.Direction -eq 1 -and $_.ApplicationName -and
        [Environment]::ExpandEnvironmentVariables($_.ApplicationName) -eq $file.FullName -and
        $_.LocalAddresses -eq '*' -and $_.RemoteAddresses -eq '*' -and
        $_.InterfaceTypes -eq 'All' -and -not $_.Interfaces -and -not $_.ServiceName -and
        ($_.Protocol -eq 256 -or ($_.Protocol -in 6, 17 -and $_.LocalPorts -eq '*' -and $_.RemotePorts -eq '*'))
})

foreach ($profile in $profiles.GetEnumerator()) {
    $mask = $profile.Value
    if (($active -band $mask) -eq 0) { continue }
    if (-not $policy.FirewallEnabled($mask) -or $policy.NotificationsDisabled($mask)) { continue }

    $protocols = @($rules | Where-Object { ($_.Profiles -band $mask) -ne 0 } | ForEach-Object Protocol)
    if (256 -notin $protocols -and (6 -notin $protocols -or 17 -notin $protocols)) {
        [Console]::Error.WriteLine("Windows Firewall may prompt on the $($profile.Key) profile. No matching inbound TCP and UDP rules found for $($file.FullName).")
        exit 2
    }
}
exit 0
