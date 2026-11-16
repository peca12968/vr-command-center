[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Config,
    [string]$Executable = (Join-Path $PSScriptRoot '../artifacts/desktop/VrCommand.exe'),
    [string]$LinkMetrics
)

$ErrorActionPreference = 'Stop'
$program = Get-Item -LiteralPath $Executable
if ($program -isnot [IO.FileInfo] -or $program.Name -ine 'VrCommand.exe') {
    throw 'Select the Windows build of VrCommand.exe.'
}

$previousMode = $env:VR_COMMAND_UNATTENDED
$env:VR_COMMAND_UNATTENDED = '1'
try {
    & (Join-Path $PSScriptRoot 'check-windows-firewall-notifications.ps1') -Executable $program.FullName
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    $connection = Get-Item -LiteralPath $Config
    if ($connection -isnot [IO.FileInfo]) { throw 'Select a connection file.' }
    $gameArguments = @('--vr-config', $connection.FullName)
    if ($LinkMetrics) { $gameArguments += @('--vr-link-metrics', $LinkMetrics) }
    & $program.FullName @gameArguments
    exit $LASTEXITCODE
} finally {
    $env:VR_COMMAND_UNATTENDED = $previousMode
}
