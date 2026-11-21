[CmdletBinding()]
# Keep -Unattended for callers from existing packages and scripts.
param([Parameter(Mandatory)][string]$Executable, [switch]$Unattended)

$ErrorActionPreference = 'Stop'
trap {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
}
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

# Include inactive profiles because Windows can switch networks while the game is running.
$notifyingProfiles = @(foreach ($profile in $profiles.GetEnumerator()) {
    $enabled = $policy.FirewallEnabled($profile.Value)
    $disabled = $policy.NotificationsDisabled($profile.Value)
    if ($enabled -isnot [bool] -or $disabled -isnot [bool]) {
        throw "Startup skipped for $($file.FullName). Could not read the Windows Firewall state for $($profile.Key)."
    }
    if ($enabled -and -not $disabled) { $profile.Key }
})
if ($notifyingProfiles.Count) {
    [Console]::Error.WriteLine("Startup skipped for $($file.FullName). Windows Firewall inbound notifications are enabled on: $($notifyingProfiles -join ', ').")
    exit 2
}
exit 0
