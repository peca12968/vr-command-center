#requires -Version 7.4
[CmdletBinding(DefaultParameterSetName='Network')]
param(
    [Parameter(Mandatory, ParameterSetName='Network')][uri]$ManagementApi,
    [Parameter(Mandatory, ParameterSetName='Local')][string]$UnixSocket,
    [Parameter(Mandatory)][ValidateRange(1,5)][int]$RoomId,
    [ValidateRange(1,2147483647)][int]$Samples
)

$ErrorActionPreference = 'Stop'
$key = $env:VR_COMMAND_ROOM_KEY
if (-not $key -or $key -cnotmatch '\A[!-~]{1,512}\z') { throw 'Set VR_COMMAND_ROOM_KEY to the room operator key.' }
$request = @{ Headers = @{ Authorization = "Bearer $key" }; NoProxy = $true; MaximumRedirection = 0
    ConnectionTimeoutSeconds = 3; OperationTimeoutSeconds = 3; Verbose = $false; Debug = $false }
if ($PSCmdlet.ParameterSetName -eq 'Local') {
    $request.UnixSocket = $UnixSocket
    $ManagementApi = [uri]'http://127.0.0.1'
}
if (-not $ManagementApi.IsAbsoluteUri -or $ManagementApi.AbsolutePath -ne '/' -or
    $ManagementApi.UserInfo -or $ManagementApi.Query -or $ManagementApi.Fragment -or
    ($ManagementApi.Scheme -ne 'https' -and
        ($ManagementApi.Scheme -ne 'http' -or $ManagementApi.Host -ne '127.0.0.1'))) {
    throw 'Use the HTTPS management origin or HTTP on 127.0.0.1.'
}
$request.Uri = [uri]::new($ManagementApi, "/api/rooms/$RoomId/hardware-environment")

function Test-PositiveInteger($Value) {
    return ($Value -is [long] -or $Value -is [int]) -and $Value -gt 0
}

function Read-RoomSample($Page) {
    if (-not (Test-PositiveInteger $Page.version) -or $Page.version -ne 1 -or
        -not (Test-PositiveInteger $Page.roomId) -or $Page.roomId -ne $RoomId -or
        -not $Page.PSObject.Properties['session']) { throw 'Invalid room snapshot.' }
    $session = $Page.session
    if ($null -eq $session) { return }
    $id = [guid]::Empty
    if (-not (Test-PositiveInteger $session.version) -or $session.version -ne 1 -or
        -not (Test-PositiveInteger $session.roomId) -or $session.roomId -ne $RoomId -or
        -not [guid]::TryParseExact([string]$session.sessionId,'D',[ref]$id) -or $id -eq [guid]::Empty -or
        $session.state -cnotin 'Preparing','Running','Paused' -or -not $session.PSObject.Properties['environment']) {
        throw 'Invalid room session.'
    }
    foreach ($seq in $session.throughSequence, $session.phaseSinceSequence, $session.environmentSinceSequence) {
        if (-not (Test-PositiveInteger $seq) -or $seq -gt $session.throughSequence) { throw 'Invalid room sequence.' }
    }
    $climate = $session.environment
    if ($session.state -ceq 'Running') {
        if ($climate.mode -cnotin 'VR','MR' -or $climate.weather -cnotin 'Clear','Rain','Fog','Storm' -or
            $climate.timeOfDay -cnotin 'Day','Night' -or $climate.lightning -isnot [bool]) { throw 'Invalid room environment.' }
        $climate = [ordered]@{ mode = $climate.mode; weather = $climate.weather; timeOfDay = $climate.timeOfDay; lightning = $climate.lightning }
    } elseif ($null -ne $climate) { throw 'Inactive room contains an environment.' }
    return [ordered]@{ sessionId = $id.ToString('D'); state = $session.state; throughSequence = $session.throughSequence
        phaseSinceSequence = $session.phaseSinceSequence; environmentSinceSequence = $session.environmentSinceSequence; environment = $climate }
}

for ($count = 1; ; $count++) {
    $status = 'Unavailable'
    $session = $null
    $reason = 'management-unreachable'
    try {
        $page = Invoke-RestMethod @request
        $reason = 'invalid-snapshot'
        $session = Read-RoomSample $page
        $status = if ($null -eq $session) { 'Idle' } else { $session.state }
        $reason = $null
    } catch {
        if ($_.Exception.Response.StatusCode -in 401,403) { $reason = 'access-denied' }
    }
    [ordered]@{ version = 1; observedAtUtc = [DateTimeOffset]::UtcNow.ToString('o'); roomId = $RoomId
        status = $status; reason = $reason; session = $session } | ConvertTo-Json -Depth 4 -Compress
    if ($reason -eq 'access-denied') { exit 1 }
    if ($Samples -and $count -ge $Samples) { if ($reason) { exit 1 }; break }
    Start-Sleep -Seconds 1
}
