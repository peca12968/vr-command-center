param(
    [Parameter(Mandatory)][string]$ClientConfig,
    [string]$Serial,
    [string]$AdbPath = 'F:\Tools\UnityEditors\6000.3.27f1\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe',
    [string]$AlignmentFile
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$apk = Join-Path $projectRoot 'artifacts/quest/VrCommand.apk'
if (-not (Test-Path -LiteralPath $AdbPath)) { throw 'Android platform-tools are not installed.' }
if (-not (Test-Path -LiteralPath $apk)) { throw 'Build the Quest APK before deploying.' }
$config = Get-Content -LiteralPath $ClientConfig -Raw | ConvertFrom-Json
$unknown = @($config.PSObject.Properties.Name | Where-Object { $_ -notin @('role','address','port','joinTicket') })
if ($config.role -ne 'Client' -or -not $config.joinTicket -or $config.gameServerKey -or $unknown.Count -gt 0) {
    throw 'Use a player configuration from prepare-vr-session.py; server credentials must not be deployed to a headset.'
}
if ($AlignmentFile) {
    $AlignmentFile = (Resolve-Path -LiteralPath $AlignmentFile).Path
    $size = (Get-Item -LiteralPath $AlignmentFile).Length
    if ($size -lt 1 -or $size -gt 16384) { throw 'Use a checked room alignment JSON export.' }
    $plan = Get-Content -LiteralPath $AlignmentFile -Raw | ConvertFrom-Json
    if ($plan.version -ne 1 -or $plan.profile -cne 'room-floor-alignment-v1' -or $plan.withinTolerance -isnot [bool] -or -not $plan.withinTolerance) {
        throw 'Use a checked room alignment JSON export.'
    }
    $alignmentHash = (Get-FileHash -LiteralPath $AlignmentFile -Algorithm SHA256).Hash.ToLowerInvariant()
}
if (-not $Serial) {
    $devices = @(& $AdbPath devices | Select-String '^([^\s]+)\s+device$' | ForEach-Object { $_.Matches[0].Groups[1].Value })
    if ($devices.Count -ne 1) { throw 'Connect and authorize one Quest 3, or specify -Serial explicitly.' }
    $Serial = $devices[0]
}
$model = (& $AdbPath -s $Serial shell getprop ro.product.model).Trim()
if ($model -ne 'Quest 3') { throw 'Selected device is not a Meta Quest 3. No app was installed.' }
& $AdbPath -s $Serial install -r $apk
if ($LASTEXITCODE -ne 0) { throw 'APK installation failed.' }
& $AdbPath -s $Serial shell am force-stop com.vrcommand.quest
if ($LASTEXITCODE -ne 0) { throw 'Quest app could not be stopped before copying configuration.' }
$remoteDirectory = '/sdcard/Android/data/com.vrcommand.quest/files'
& $AdbPath -s $Serial shell mkdir -p $remoteDirectory
if ($LASTEXITCODE -ne 0) { throw 'App data directory could not be prepared.' }
$deploymentId = [Guid]::NewGuid().ToString('N')
if ($AlignmentFile) {
    $remoteAlignment = "$remoteDirectory/vr-room-alignment-$deploymentId.tmp"
    & $AdbPath -s $Serial push $AlignmentFile $remoteAlignment | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Room alignment file could not be copied.' }
    & $AdbPath -s $Serial shell mv $remoteAlignment "$remoteDirectory/vr-room-alignment-$alignmentHash.json"
    if ($LASTEXITCODE -ne 0) { throw 'Room alignment file could not be activated.' }
    $config | Add-Member -NotePropertyName 'roomAlignmentSha256' -NotePropertyValue $alignmentHash
}
$stagedConfig = [IO.Path]::GetTempFileName()
try {
    [IO.File]::WriteAllText($stagedConfig, ($config | ConvertTo-Json -Depth 4 -Compress))
    $remoteStage = "$remoteDirectory/vr-connection-$deploymentId.tmp"
    & $AdbPath -s $Serial push $stagedConfig $remoteStage | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Player connection file could not be copied.' }
    & $AdbPath -s $Serial shell mv $remoteStage "$remoteDirectory/vr-connection.json"
    if ($LASTEXITCODE -ne 0) { throw 'Player connection file could not be activated.' }
} finally {
    Remove-Item -LiteralPath $stagedConfig
}
& $AdbPath -s $Serial shell monkey -p com.vrcommand.quest -c android.intent.category.LAUNCHER 1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Quest app launch failed.' }
Write-Host 'Quest client installed and launched. Ticket expiry and server admission still apply.'
