param(
    [Parameter(Mandatory)][string]$ClientConfig,
    [string]$Serial,
    [string]$AdbPath = 'F:\Tools\UnityEditors\6000.3.27f1\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe',
    [string]$AlignmentFile,
    [switch]$Passthrough,
    [switch]$MixedReality,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
# Handle ADB exit codes here so both Windows PowerShell and PowerShell report the failing step.
$PSNativeCommandUseErrorActionPreference = $false

function Read-DeploymentJson([string]$Path, [int]$Limit, [string]$Description) {
    try {
        $reader = [IO.BinaryReader]::new([IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).ProviderPath))
        try {
            $size = $reader.BaseStream.Length
            if ($size -lt 1 -or $size -gt $Limit) { throw 'Invalid file size.' }
            $bytes = $reader.ReadBytes([int]$size)
        } finally {
            $reader.Dispose()
        }
        $json = [Text.UTF8Encoding]::new($false, $true).GetString($bytes).TrimStart([char]0xFEFF)
        if (-not $json.TrimStart().StartsWith('{')) { throw 'Expected a JSON object.' }
        return @{ Bytes = $bytes; Document = ConvertFrom-Json -InputObject $json }
    } catch {
        throw "Use a valid $Description JSON file."
    }
}

function Get-PlayerTicketDetails([string]$Ticket) {
    if ($Ticket -cnotmatch '\Av2\.([A-Za-z0-9_-]{100})\.[A-Za-z0-9_-]{43}\z') {
        throw 'Use a current v2 player ticket from the management service.'
    }
    # This reads public v2 fields for offline preflight. The server verifies the signature and admission.
    $payload = [Convert]::FromBase64String($Matches[1].Replace('-', '+').Replace('_', '/'))
    $room = [int]$payload[49]
    $seat = [int]$payload[50]
    $expiryBytes = [byte[]]$payload[51..58]
    if ([BitConverter]::IsLittleEndian) { [Array]::Reverse($expiryBytes) }
    $expiry = [BitConverter]::ToInt64($expiryBytes, 0)
    if ($payload[0] -ne 2 -or $room -notin 1..5 -or $seat -notin 0..4 -or $expiry -gt 253402300799L) {
        throw 'Use a current v2 player ticket from the management service.'
    }
    if ($expiry -le [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) {
        throw 'Player ticket has expired. Download a fresh connection file.'
    }
    return @{ RoomId = $room; Seat = $seat; ExpiresAtUtc = [DateTimeOffset]::FromUnixTimeSeconds($expiry) }
}

function Test-FloorPoint($Point, [double]$Limit) {
    foreach ($value in @($Point.x, $Point.z)) {
        if (($value -isnot [int] -and $value -isnot [long] -and $value -isnot [double] -and $value -isnot [decimal]) -or
            -not ([Math]::Abs([double]$value) -le $Limit)) { return $false }
    }
    return $true
}

function Test-JsonInteger($Value) { return $Value -is [int] -or $Value -is [long] }

function Publish-QuestFile([string]$Local, [string]$Staging, [string]$Destination, [string]$Description) {
    try {
        & $AdbPath -s $Serial push $Local $Staging | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "$Description could not be copied." }
        & $AdbPath -s $Serial shell mv $Staging $Destination
        if ($LASTEXITCODE -ne 0) { throw "$Description could not be activated." }
    } catch {
        $publishError = $_
        try {
            & $AdbPath -s $Serial shell rm -f $Staging *> $null
            if ($LASTEXITCODE -ne 0) { throw 'ADB cleanup failed.' }
        } catch {
            Write-Warning 'Could not remove the temporary deployment file from the selected device.'
        }
        throw $publishError
    }
}

$config = (Read-DeploymentJson $ClientConfig 4096 'player connection').Document
$unknown = @($config.PSObject.Properties.Name | Where-Object { $_ -cnotin @('role','address','port','joinTicket') })
if ($config.role -isnot [string] -or $config.role -cne 'Client' -or $config.joinTicket -isnot [string] -or
    $config.address -isnot [string] -or $config.address -notmatch '\A[^\s]+\z' -or
    -not (Test-JsonInteger $config.port) -or $config.port -lt 1 -or $config.port -gt 65535 -or
    $unknown.Count -gt 0) {
    throw 'Use a player-only connection file from the management console or prepare-vr-session.py.'
}
$ticket = Get-PlayerTicketDetails $config.joinTicket
if (($Passthrough -or $MixedReality) -and -not $AlignmentFile) { throw 'Quest passthrough requires a checked room alignment JSON export.' }
$alignmentHash = $null
if ($AlignmentFile) {
    $alignment = Read-DeploymentJson $AlignmentFile 16384 'checked room alignment'
    $plan = $alignment.Document
    if (-not (Test-JsonInteger $plan.version) -or $plan.version -ne 1 -or
        $plan.profile -isnot [string] -or $plan.profile -cne 'room-floor-alignment-v1' -or
        $plan.withinTolerance -isnot [bool] -or -not $plan.withinTolerance -or
        -not (Test-JsonInteger $plan.roomId) -or $plan.roomId -notin 1..5 -or $plan.markers -isnot [array] -or $plan.markers.Count -ne 3 -or
        -not (Test-FloorPoint $plan.roomOrigin 28) -or $plan.roomOrigin.x -ne (($plan.roomId - 3) * 14) -or $plan.roomOrigin.z -ne 0) {
        throw 'Use a checked room alignment JSON export.'
    }
    if ($plan.roomId -ne $ticket.RoomId) {
        throw "The player ticket is for room $($ticket.RoomId); the alignment export is for room $($plan.roomId)."
    }
    for ($i = 0; $i -lt 3; $i++) {
        $marker = $plan.markers[$i]
        if ($marker.name -isnot [string] -or $marker.name -cne 'ABC'[$i].ToString() -or
            -not (Test-FloorPoint $marker.room 6) -or -not (Test-FloorPoint $marker.tracking 100)) {
            throw 'Use the original A, B and C room alignment measurements.'
        }
    }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $alignmentHash = [BitConverter]::ToString($sha.ComputeHash($alignment.Bytes)).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}
if ($CheckOnly) {
    [pscustomobject]@{
        roomId = $ticket.RoomId
        seat = $ticket.Seat + 1
        expiresAtUtc = $ticket.ExpiresAtUtc.ToString('o')
        mode = if ($MixedReality) { 'MR' } elseif ($Passthrough) { 'VR with passthrough' } else { 'VR' }
        alignmentSha256 = $alignmentHash
    } | ConvertTo-Json -Compress
    return
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$apk = Join-Path $projectRoot 'artifacts/quest/VrCommand.apk'
if (-not (Test-Path -LiteralPath $AdbPath -PathType Leaf)) { throw 'Android platform-tools are not installed.' }
if (-not (Test-Path -LiteralPath $apk -PathType Leaf)) { throw 'Build the Quest APK before deploying.' }
if (-not $Serial) {
    $devices = @(& $AdbPath devices | Select-String '^([^\s]+)\s+device$' | ForEach-Object { $_.Matches[0].Groups[1].Value })
    if ($LASTEXITCODE -ne 0) { throw 'Could not list authorized Android devices.' }
    if ($devices.Count -ne 1) { throw 'Connect and authorize one Quest 3, or specify -Serial explicitly.' }
    $Serial = $devices[0]
}
$model = & $AdbPath -s $Serial shell getprop ro.product.model
if ($LASTEXITCODE -ne 0) { throw 'Could not identify the selected Android device.' }
$model = ([string]$model).Trim()
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
    $stagedAlignment = [IO.Path]::GetTempFileName()
    try {
        [IO.File]::WriteAllBytes($stagedAlignment, $alignment.Bytes)
        Publish-QuestFile $stagedAlignment "$remoteDirectory/vr-room-alignment-$deploymentId.tmp" `
            "$remoteDirectory/vr-room-alignment-$alignmentHash.json" 'Room alignment file'
    } finally {
        Remove-Item -LiteralPath $stagedAlignment
    }
    $config | Add-Member -NotePropertyName 'roomAlignmentSha256' -NotePropertyValue $alignmentHash
}
if ($Passthrough -or $MixedReality) { $config | Add-Member -NotePropertyName 'questPassthrough' -NotePropertyValue $true }
if ($MixedReality) { $config | Add-Member -NotePropertyName 'requestMixedReality' -NotePropertyValue $true }
$stagedConfig = [IO.Path]::GetTempFileName()
try {
    if ($ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) { throw 'Player ticket expired during deployment. Download a fresh connection file.' }
    [IO.File]::WriteAllText($stagedConfig, ($config | ConvertTo-Json -Depth 4 -Compress))
    Publish-QuestFile $stagedConfig "$remoteDirectory/vr-connection-$deploymentId.tmp" "$remoteDirectory/vr-connection.json" 'Player connection file'
} finally {
    Remove-Item -LiteralPath $stagedConfig
}
& $AdbPath -s $Serial shell monkey -p com.vrcommand.quest -c android.intent.category.LAUNCHER 1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Quest app launch failed.' }
Write-Host 'Quest client installed and launched. Ticket expiry and server admission still apply.'
