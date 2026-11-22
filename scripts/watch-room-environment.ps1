#requires -Version 7.4
[CmdletBinding(DefaultParameterSetName='NetworkRoom')]
param(
    [Parameter(Mandatory, ParameterSetName='NetworkRoom')][Parameter(Mandatory, ParameterSetName='NetworkVenue')][uri]$ManagementApi,
    [Parameter(Mandatory, ParameterSetName='LocalRoom')][Parameter(Mandatory, ParameterSetName='LocalVenue')][ValidateNotNullOrEmpty()][string]$UnixSocket,
    [Parameter(Mandatory, ParameterSetName='NetworkRoom')][Parameter(Mandatory, ParameterSetName='LocalRoom')][ValidateRange(1,5)][int]$RoomId,
    [Parameter(Mandatory, ParameterSetName='NetworkVenue')][Parameter(Mandatory, ParameterSetName='LocalVenue')][switch]$AllRooms,
    [ValidateRange(1,2147483647)][int]$Samples,
    [switch]$RequireCurrentRead
)

$ErrorActionPreference = 'Stop'
$venueMode = $PSCmdlet.ParameterSetName.EndsWith('Venue')
if ($venueMode -and -not $AllRooms) { throw 'Specify -AllRooms for the venue monitor.' }
$keyName = if ($venueMode) { 'VR_COMMAND_MASTER_KEY' } else { 'VR_COMMAND_ROOM_KEY' }
$key = [Environment]::GetEnvironmentVariable($keyName)
if (-not $key -or $key -cnotmatch '\A[!-~]{1,512}\z') { throw "Set $keyName for the selected monitor." }
$request = @{ Headers = @{ Authorization = "Bearer $key" }; NoProxy = $true; MaximumRedirection = 0
    ConnectionTimeoutSeconds = 3; OperationTimeoutSeconds = 3; Verbose = $false; Debug = $false }
if ($UnixSocket) {
    $request.UnixSocket = $UnixSocket
    $ManagementApi = [uri]'http://127.0.0.1'
}
if (-not $ManagementApi.IsAbsoluteUri -or $ManagementApi.AbsolutePath -ne '/' -or
    $ManagementApi.UserInfo -or $ManagementApi.Query -or $ManagementApi.Fragment -or
    ($ManagementApi.Scheme -ne 'https' -and
        ($ManagementApi.Scheme -ne 'http' -or $ManagementApi.Host -ne '127.0.0.1'))) {
    throw 'Use the HTTPS management origin or HTTP on 127.0.0.1.'
}
$path = if ($venueMode) { '/api/venue/hardware-environment' } else { "/api/rooms/$RoomId/hardware-environment" }
$request.Uri = [uri]::new($ManagementApi, $path)

function Test-PositiveInteger($Value) {
    return ($Value -is [long] -or $Value -is [int]) -and $Value -gt 0
}

function Read-RoomSample($Page, [int]$ExpectedRoom) {
    if ($Page -isnot [pscustomobject] -or -not (Test-PositiveInteger $Page.version) -or $Page.version -ne 1 -or
        -not (Test-PositiveInteger $Page.roomId) -or $Page.roomId -ne $ExpectedRoom -or
        -not $Page.PSObject.Properties['session']) { throw 'Invalid room snapshot.' }
    $session = $Page.session
    if ($null -eq $session) { return }
    $id = [guid]::Empty
    if ($session -isnot [pscustomobject] -or -not (Test-PositiveInteger $session.version) -or $session.version -ne 1 -or
        -not (Test-PositiveInteger $session.roomId) -or $session.roomId -ne $ExpectedRoom -or
        -not [guid]::TryParseExact([string]$session.sessionId,'D',[ref]$id) -or $id -eq [guid]::Empty -or
        $session.state -isnot [string] -or $session.state -cnotin 'Preparing','Running','Paused' -or -not $session.PSObject.Properties['environment']) {
        throw 'Invalid room session.'
    }
    foreach ($seq in $session.throughSequence, $session.phaseSinceSequence, $session.environmentSinceSequence) {
        if (-not (Test-PositiveInteger $seq) -or $seq -gt $session.throughSequence) { throw 'Invalid room sequence.' }
    }
    $climate = $session.environment
    if ($session.state -ceq 'Running') {
        if ($climate -isnot [pscustomobject] -or $climate.mode -isnot [string] -or $climate.mode -cnotin 'VR','MR' -or
            $climate.weather -isnot [string] -or $climate.weather -cnotin 'Clear','Rain','Fog','Storm' -or
            $climate.timeOfDay -isnot [string] -or $climate.timeOfDay -cnotin 'Day','Night' -or $climate.lightning -isnot [bool]) { throw 'Invalid room environment.' }
        $climate = [ordered]@{ mode = $climate.mode; weather = $climate.weather; timeOfDay = $climate.timeOfDay; lightning = $climate.lightning }
    } elseif ($null -ne $climate) { throw 'Inactive room contains an environment.' }
    return [ordered]@{ sessionId = $id.ToString('D'); state = $session.state; throughSequence = $session.throughSequence
        phaseSinceSequence = $session.phaseSinceSequence; environmentSinceSequence = $session.environmentSinceSequence; environment = $climate }
}

function Get-RoomContinuity($Previous, $Current) {
    if (-not $Current -or -not $Previous -or $Current.sessionId -ne $Previous.sessionId) { return $Current }
    if ($Current.throughSequence -lt $Previous.throughSequence) { throw 'Room sequence moved backwards.' }
    foreach ($field in 'phaseSinceSequence','environmentSinceSequence') {
        if ($Current[$field] -ne $Previous[$field] -and $Current[$field] -le $Previous.throughSequence) {
            throw 'Room history disagrees with an accepted sample.'
        }
    }
    if ($Current.phaseSinceSequence -eq $Previous.phaseSinceSequence -and $Current.state -cne $Previous.state) {
        throw 'Room phase changed without a new phase sequence.'
    }
    if ($Previous.environment -and $Current.environmentSinceSequence -eq $Previous.environmentSinceSequence) {
        # Paused output stays empty. Remember the last settings for this revision only in the monitor.
        if (-not $Current.environment) {
            $history = @{} + $Current
            $history.environment = $Previous.environment
            return $history
        }
        foreach ($field in 'mode','weather','timeOfDay','lightning') {
            if ($Current.environment[$field] -cne $Previous.environment[$field]) { throw 'Room environment changed without a new sequence.' }
        }
    }
    return $Current
}

$lastAccepted = @{}
for ($count = 1; ; $count++) {
    $status = 'Unavailable'
    $session = $null
    $reason = 'management-unreachable'
    $rooms = $null
    $checked = $null
    try {
        if ($RequireCurrentRead) {
            $sampleId = [guid]::NewGuid().ToString('D')
            $request.Uri = [uri]::new($ManagementApi, "${path}?sampleId=$sampleId")
        }
        $page = Invoke-RestMethod @request
        if ($RequireCurrentRead -and ($page.sampleId -isnot [string] -or $page.sampleId -cne $sampleId)) {
            $reason = 'sample-id-mismatch'
            throw 'Response does not match the current environment read.'
        }
        $reason = 'invalid-snapshot'
        if ($venueMode) {
            if (-not (Test-PositiveInteger $page.version) -or $page.version -ne 1 -or
                $page.rooms -isnot [array] -or $page.rooms.Count -ne 5) { throw 'Invalid venue snapshot.' }
            $time = $page.checkedAtUtc
            if (($time -is [datetime] -and $time.Kind -eq 'Unspecified') -or
                ($time -isnot [datetimeoffset] -and $time -isnot [datetime] -and
                 ($time -isnot [string] -or $time -cnotmatch '\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,7})?(Z|[+-]\d{2}:\d{2})\z'))) {
                throw 'Invalid venue timestamp.'
            }
            $timestamp = [DateTimeOffset]$time
            $sessions = @{}
            $nextAccepted = @{}
            $rooms = @(foreach ($room in 1..5) {
                $current = Read-RoomSample $page.rooms[$room - 1] $room
                $nextAccepted[$room] = Get-RoomContinuity $lastAccepted[$room] $current
                if ($current) {
                    $signature = ConvertTo-Json $current -Compress -Depth 3
                    if ($sessions.ContainsKey($current.sessionId) -and $sessions[$current.sessionId] -cne $signature) {
                        throw 'Rooms in the same session disagree.'
                    }
                    $sessions[$current.sessionId] = $signature
                }
                [ordered]@{ roomId = $room; status = if ($null -eq $current) { 'Idle' } else { $current.state }; session = $current }
            })
            $checked = $timestamp.ToUniversalTime().ToString('o')
            $lastAccepted = $nextAccepted
            $status = 'Available'
        } else {
            $session = Read-RoomSample $page $RoomId
            $lastAccepted[$RoomId] = Get-RoomContinuity $lastAccepted[$RoomId] $session
            $status = if ($null -eq $session) { 'Idle' } else { $session.state }
        }
        $reason = $null
    } catch {
        $session = $null
        if ($_.Exception.Response.StatusCode -in 401,403) { $reason = 'access-denied' }
    }
    $observed = [DateTimeOffset]::UtcNow.ToString('o')
    if ($venueMode) {
        if ($reason) {
            $rooms = @(foreach ($room in 1..5) { [ordered]@{roomId = $room; status = 'Unavailable'; session = $null} })
        }
        [ordered]@{ version = 1; observedAtUtc = $observed; checkedAtUtc = $checked; status = $status
            reason = $reason; rooms = $rooms } | ConvertTo-Json -Depth 6 -Compress
    } else {
        [ordered]@{ version = 1; observedAtUtc = $observed; roomId = $RoomId
            status = $status; reason = $reason; session = $session } | ConvertTo-Json -Depth 4 -Compress
    }
    if ($reason -eq 'access-denied') { exit 1 }
    if ($Samples -and $count -ge $Samples) { if ($reason) { exit 1 }; break }
    Start-Sleep -Seconds 1
}
