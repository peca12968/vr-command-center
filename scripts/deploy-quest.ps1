[CmdletBinding(DefaultParameterSetName='Player')]
param(
    [Parameter(Mandatory, ParameterSetName='Player')][string]$ClientConfig,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][string]$Serial,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][string]$AdbPath = 'F:\Tools\UnityEditors\6000.3.27f1\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe',
    [Parameter(ParameterSetName='Player')][string]$AlignmentFile,
    [Parameter(ParameterSetName='Player')][switch]$Passthrough,
    [Parameter(ParameterSetName='Player')][switch]$MixedReality,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][switch]$CheckOnly,
    [Parameter(Mandatory, ParameterSetName='Venue')][string]$VenueManifest,
    [Parameter(Mandatory, ParameterSetName='Bundle')][string]$VenueBundle,
    [Parameter(ParameterSetName='Bundle')][ValidateRange(1,5)][int]$RoomId,
    [Parameter(ParameterSetName='Bundle')][ValidateRange(1,5)][int]$Seat,
    [Parameter(ParameterSetName='Venue')][Parameter(ParameterSetName='Bundle')][ValidateNotNullOrEmpty()][string]$ManagementApi
)
$ErrorActionPreference = 'Stop'
# Handle ADB exit codes here so both Windows PowerShell and PowerShell report the failing step.
$PSNativeCommandUseErrorActionPreference = $false

function Read-DeploymentBytes([IO.Stream]$Stream, [long]$Size, [int]$Limit) {
    if ($Size -lt 1 -or $Size -gt $Limit) { throw 'Invalid file size.' }
    $reader = [IO.BinaryReader]::new($Stream, [Text.Encoding]::UTF8, $true)
    try {
        $bytes = $reader.ReadBytes([int]$Size)
        if ($bytes.Length -ne $Size -or $Stream.ReadByte() -ne -1) { throw 'Unexpected file length.' }
    } finally { $reader.Dispose() }
    return ,$bytes
}

function Read-DeploymentStream([IO.Stream]$Stream, [long]$Size, [int]$Limit) {
    $bytes = Read-DeploymentBytes $Stream $Size $Limit
    $json = [Text.UTF8Encoding]::new($false, $true).GetString($bytes).TrimStart([char]0xFEFF)
    if (-not $json.TrimStart().StartsWith('{')) { throw 'Expected a JSON object.' }
    return @{ Bytes = $bytes; Document = ConvertFrom-Json -InputObject $json }
}

function Read-DeploymentJson([string]$Path, [int]$Limit, [string]$Description) {
    try {
        $file = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).ProviderPath)
        try { return Read-DeploymentStream $file $file.Length $Limit }
        finally { $file.Dispose() }
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
    return @{
        RoomId = $room; Seat = $seat; ExpiresAtUtc = [DateTimeOffset]::FromUnixTimeSeconds($expiry)
        SessionId = [Guid]::new([byte[]]$payload[1..16])
        PlayerId = [Guid]::new([byte[]]$payload[17..32])
        AdmissionId = [Guid]::new([byte[]]$payload[33..48])
    }
}

function Test-FloorPoint($Point, [double]$Limit) {
    foreach ($value in @($Point.x, $Point.z)) {
        if (($value -isnot [int] -and $value -isnot [long] -and $value -isnot [double] -and $value -isnot [decimal]) -or
            -not ([Math]::Abs([double]$value) -le $Limit)) { return $false }
    }
    return $true
}

function Test-JsonInteger($Value) { return $Value -is [int] -or $Value -is [long] }

function Read-PlayerConfig($Config) {
    $unknown = @($Config.PSObject.Properties.Name | Where-Object { $_ -cnotin @('role','address','port','joinTicket','roomAlignmentSha256') })
    if ($Config.role -isnot [string] -or $Config.role -cne 'Client' -or $Config.joinTicket -isnot [string] -or
        $Config.address -isnot [string] -or $Config.address -notmatch '\A[^\s]+\z' -or
        -not (Test-JsonInteger $Config.port) -or $Config.port -lt 1 -or $Config.port -gt 65535 -or $unknown.Count -gt 0) {
        throw 'Use a player-only connection file from the management console or prepare-vr-session.py.'
    }
    $ticket = Get-PlayerTicketDetails $Config.joinTicket
    if ($null -ne $Config.PSObject.Properties['roomAlignmentSha256']) {
        $hash = $Config.roomAlignmentSha256
        if ($hash -isnot [string] -or $hash -cnotmatch '\A[a-f0-9]{64}\z') { throw 'Use a valid locked MR alignment SHA-256 in the player connection file.' }
        $ticket.AlignmentHash = $hash
    }
    return $ticket
}

function Confirm-RoomAlignment($Alignment, [int]$RoomId) {
    $plan = $alignment.Document
    if (-not (Test-JsonInteger $plan.version) -or $plan.version -ne 1 -or
        $plan.profile -isnot [string] -or $plan.profile -cne 'room-floor-alignment-v1' -or
        $plan.withinTolerance -isnot [bool] -or -not $plan.withinTolerance -or
        -not (Test-JsonInteger $plan.roomId) -or $plan.roomId -notin 1..5 -or $plan.markers -isnot [array] -or $plan.markers.Count -ne 3 -or
        -not (Test-FloorPoint $plan.roomOrigin 28) -or $plan.roomOrigin.x -ne (($plan.roomId - 3) * 14) -or $plan.roomOrigin.z -ne 0) {
        throw 'Use a checked room alignment JSON export.'
    }
    if ($plan.roomId -ne $RoomId) {
        throw "The player ticket is for room $RoomId; the alignment export is for room $($plan.roomId)."
    }
    for ($i = 0; $i -lt 3; $i++) {
        $marker = $plan.markers[$i]
        if ($marker.name -isnot [string] -or $marker.name -cne 'ABC'[$i].ToString() -or
            -not (Test-FloorPoint $marker.room 6) -or -not (Test-FloorPoint $marker.tracking 100)) {
            throw 'Use the original A, B and C room alignment measurements.'
        }
    }
    $sha = [Security.Cryptography.SHA256]::Create()
    try { $alignment.Hash = [BitConverter]::ToString($sha.ComputeHash($alignment.Bytes)).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
    return $alignment
}

function Read-RoomAlignment([string]$Path, [int]$RoomId) {
    Confirm-RoomAlignment (Read-DeploymentJson $Path 16384 'checked room alignment') $RoomId
}

function Get-VenueInputPath([string]$Directory, [string]$Path) {
    if ([IO.Path]::IsPathRooted($Path)) { return $Path }
    return [IO.Path]::Combine($Directory, $Path)
}

function Read-VenueRoomTickets([string]$Path, [int]$RoomId, [Guid]$SessionId) {
    try { $file = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).ProviderPath) }
    catch { throw "Room $RoomId needs a readable room connection ZIP." }
    try {
        if ($file.Length -lt 1 -or $file.Length -gt 65536) { throw "Room $RoomId connection ZIP has an invalid size." }
        Read-VenueTicketStream $file $RoomId $SessionId
    } finally { $file.Dispose() }
}

function Read-VenueTicketStream([IO.Stream]$InputStream, [int]$RoomId, [Guid]$SessionId, [switch]$ForBundle) {
    try { $archive = [IO.Compression.ZipArchive]::new($InputStream, [IO.Compression.ZipArchiveMode]::Read, $true) }
    catch { throw "Room $RoomId needs a valid room connection ZIP." }
    try {
        if ($archive.Entries.Count -ne 5) { throw "Room $RoomId must contain exactly five seat connection files." }
        foreach ($seat in 1..5) {
            $entry = $archive.GetEntry(('room-{0:00}-seat-{1:00}.json' -f $RoomId, $seat))
            if ($null -eq $entry) { throw "Room $RoomId is missing the expected seat $seat connection file." }
            try {
                $stream = $entry.Open()
                try { $fileContent = Read-DeploymentStream $stream $entry.Length 4096 }
                finally { $stream.Dispose() }
            } catch { throw "Room $RoomId seat $seat contains an invalid connection JSON file." }
            $config = $fileContent.Document
            try { $ticket = Read-PlayerConfig $config }
            catch { throw ('Room {0} seat {1}: {2}' -f $RoomId, $seat, $_.Exception.Message) }
            if ($ticket.SessionId -ne $SessionId -or $ticket.RoomId -ne $RoomId -or $ticket.Seat -ne ($seat - 1) -or
                $ticket.PlayerId -eq [Guid]::Empty -or $ticket.AdmissionId -eq [Guid]::Empty) {
                throw "Room $RoomId seat $seat ticket does not match the expected session or seat."
            }
            $address = $null
            if (-not [Net.IPAddress]::TryParse($config.address, [ref]$address) -or
                $address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or
                $address.ToString() -cne $config.address -or $address.GetAddressBytes()[0] -eq 0 -or
                $address.GetAddressBytes()[0] -ge 224 -or $config.port -lt 1024) {
                throw "Room $RoomId seat $seat needs a canonical unicast IPv4 address and UDP port 1024–65535."
            }
            if ($ForBundle -and [Net.IPAddress]::IsLoopback($address)) {
                throw "Room $RoomId seat $seat needs a venue endpoint usable outside the server computer."
            }
            $ticket.Endpoint = [string]$config.address + ':' + $config.port
            $ticket.Bytes = $fileContent.Bytes
            $ticket.Config = $config
            $ticket
        }
    } finally { $archive.Dispose() }
}

function Confirm-VenueWithManagement([string]$Address, [string]$Topology, [object[]]$Rooms, $PublishedEndpoints) {
    $uri = $null
    if (-not [Uri]::TryCreate($Address, [UriKind]::Absolute, [ref]$uri) -or
        ($uri.Scheme -ne 'https' -and -not ($uri.Scheme -eq 'http' -and $uri.IsLoopback)) -or
        $uri.AbsolutePath -ne '/' -or $uri.UserInfo -or $uri.Query -or $uri.Fragment) {
        throw 'ManagementApi must be an HTTPS origin or a local loopback HTTP origin, without credentials, path, query or fragment.'
    }
    $masterKey = [Environment]::GetEnvironmentVariable('VR_COMMAND_MASTER_KEY')
    if ([string]::IsNullOrWhiteSpace($masterKey)) { throw 'Set VR_COMMAND_MASTER_KEY for the live venue check.' }
    $endpoint = [Uri]::new($uri, '/api/mr-deployment/venue-check')
    $body = @{ topology = $Topology; rooms = $Rooms } | ConvertTo-Json -Compress -Depth 6
    try {
        $response = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' `
            -Headers @{ Authorization = 'Bearer ' + $masterKey } -Body $body -NoProxy -MaximumRedirection 0 -TimeoutSec 10 -SkipHttpErrorCheck
    } catch { throw 'The live venue check could not reach the management service.' }
    if ($response.StatusCode -in 401,403) { throw 'The management service requires the current Master key for the live venue check.' }
    if ($response.StatusCode -ne 200) { throw 'The management service did not accept the live venue check. Verify the management version and service status.' }
    try { $result = ConvertFrom-Json -InputObject $response.Content }
    catch { throw 'The management service returned an invalid venue check receipt.' }
    if ($result.topology -cne $Topology -or $result.allMatched -isnot [bool] -or $result.seats -isnot [array] -or $result.seats.Count -ne 25) {
        throw 'The management service returned an invalid venue check receipt.'
    }
    $failures = for ($i = 0; $i -lt 25; $i++) {
        $room = [int][Math]::Floor($i / 5) + 1
        $seat = $i % 5
        $row = $result.seats[$i]
        if (-not (Test-JsonInteger $row.roomId) -or -not (Test-JsonInteger $row.seat) -or
            $row.roomId -ne $room -or $row.seat -ne $seat -or $row.status -cnotin @('matched', 'session-unavailable',
            'alignment-not-locked', 'seat-unavailable', 'connection-invalid', 'ticket-invalid', 'wrong-seat',
            'admission-changed', 'connection-hash-mismatch', 'alignment-invalid', 'alignment-wrong-room', 'alignment-hash-mismatch')) {
            throw 'The management service returned an invalid venue check receipt.'
        }
        if ($row.status -cne 'matched') { 'Room {0} seat {1}: {2}' -f $room, ($seat + 1), $row.status }
    }
    if ($result.allMatched -ne (-not $failures)) { throw 'The management service returned an inconsistent venue check receipt.' }
    if ($failures) { throw ('Live venue check failed. ' + ($failures -join '; ')) }
    foreach ($sessionId in $PublishedEndpoints.Keys) {
        $source = [Uri]::new($uri, "/api/sessions/$sessionId/connection-endpoint")
        try {
            $metadata = Invoke-WebRequest -Uri $source -Method Get -Headers @{ Authorization = 'Bearer ' + $masterKey } `
                -NoProxy -MaximumRedirection 0 -TimeoutSec 10 -SkipHttpErrorCheck
            if ($metadata.StatusCode -ne 200) { throw 'Published endpoint unavailable.' }
            $published = ConvertFrom-Json -InputObject $metadata.Content
        } catch { throw 'The live bundle check could not read the current published game endpoint.' }
        if (-not (Test-JsonInteger $published.version) -or $published.version -ne 1 -or
            $published.sessionId -cne $sessionId -or $published.sessionEnded -isnot [bool] -or $published.sessionEnded -or
            $published.address -isnot [string] -or -not (Test-JsonInteger $published.port) -or
            ($published.address + ':' + $published.port) -cne $PublishedEndpoints[$sessionId]) {
            throw 'The bundle connection endpoint does not match the current published game endpoint.'
        }
    }
}

function Read-VenueJsonEntry($Entry, [string]$Description) {
    try {
        $stream = $Entry.Open()
        try { Read-DeploymentStream $stream $Entry.Length 16384 }
        finally { $stream.Dispose() }
    } catch { throw "Use a valid $Description JSON in the deployment ZIP." }
}

function Read-VenueBundle([string]$Path, [int]$SelectedRoom, [int]$SelectedSeat) {
    try { $file = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).ProviderPath) }
    catch { throw 'Use a readable five-room MR deployment ZIP from the management console.' }
    try {
        if ($file.Length -lt 1 -or $file.Length -gt 512KB) { throw 'The five-room MR deployment ZIP has an invalid size.' }
        try { $archive = [IO.Compression.ZipArchive]::new($file, [IO.Compression.ZipArchiveMode]::Read, $true) }
        catch { throw 'Use a valid five-room MR deployment ZIP from the management console.' }
        try {
            if ($archive.Entries.Count -ne 11) { throw 'The deployment ZIP must contain exactly one manifest and ten room files.' }
            $entries = [Collections.Generic.Dictionary[string,IO.Compression.ZipArchiveEntry]]::new([StringComparer]::Ordinal)
            foreach ($entry in $archive.Entries) {
                if ($entries.ContainsKey($entry.FullName)) { throw 'The deployment ZIP contains a duplicate entry.' }
                $entries.Add($entry.FullName, $entry)
            }
            $manifest = (Read-VenueJsonEntry $entries['venue.json'] 'venue manifest').Document
            Read-Venue $manifest '' $entries $SelectedRoom $SelectedSeat
        } finally { $archive.Dispose() }
    } finally { $file.Dispose() }
}

function Read-Venue($Manifest, [string]$Directory, $BundleEntries, [int]$SelectedRoom, [int]$SelectedSeat) {
    if (-not (Test-JsonInteger $manifest.version) -or $manifest.version -ne 1 -or
        $manifest.topology -isnot [string] -or $manifest.topology -cnotin @('Linked','Independent') -or
        $manifest.rooms -isnot [array] -or $manifest.rooms.Count -ne 5 -or
        @($manifest.PSObject.Properties.Name | Where-Object { $_ -cnotin @('version','topology','rooms') }).Count -gt 0) {
        throw 'Use a version 1 venue manifest with Linked or Independent topology and five rooms.'
    }
    $seenRooms = [Collections.Generic.HashSet[int]]::new()
    $players = [Collections.Generic.HashSet[Guid]]::new()
    $admissions = [Collections.Generic.HashSet[Guid]]::new()
    $sessions = [Collections.Generic.HashSet[Guid]]::new()
    $endpoints = [Collections.Generic.HashSet[string]]::new()
    $earliest = [DateTimeOffset]::MaxValue
    $usesPins = $null
    $selected = $null
    $liveRooms = [Collections.Generic.List[object]]::new()
    $publishedEndpoints = @{}
    $rooms = foreach ($room in $manifest.rooms) {
        $session = [Guid]::Empty
        if (-not (Test-JsonInteger $room.roomId) -or $room.roomId -notin 1..5 -or -not $seenRooms.Add($room.roomId) -or
            $room.sessionId -isnot [string] -or -not [Guid]::TryParseExact($room.sessionId, 'D', [ref]$session) -or $session -eq [Guid]::Empty -or
            $room.ticketsZip -isnot [string] -or [string]::IsNullOrWhiteSpace($room.ticketsZip) -or
            $room.alignmentFile -isnot [string] -or [string]::IsNullOrWhiteSpace($room.alignmentFile) -or
            @($room.PSObject.Properties.Name | Where-Object { $_ -cnotin @('roomId','sessionId','ticketsZip','alignmentFile') }).Count -gt 0) {
            throw 'Provide one entry per room with roomId, sessionId, ticketsZip and alignmentFile.'
        }
        $id = $room.roomId
        if ($BundleEntries) {
            $expectedZip = 'room-{0:00}-connections.zip' -f $id
            $expectedAlignment = 'room-{0:00}-alignment.json' -f $id
            if ($room.ticketsZip -cne $expectedZip -or $room.alignmentFile -cne $expectedAlignment -or
                -not $BundleEntries.ContainsKey($expectedZip) -or -not $BundleEntries.ContainsKey($expectedAlignment)) {
                throw "Room $id must use the original room filenames inside the deployment ZIP."
            }
            $alignment = Confirm-RoomAlignment (Read-VenueJsonEntry $BundleEntries[$expectedAlignment] "room $id alignment") $id
            $entry = $BundleEntries[$expectedZip]
            $stream = $entry.Open()
            try { $bytes = Read-DeploymentBytes $stream $entry.Length 65536 }
            catch { throw "Room $id connection ZIP has an invalid size or length." }
            finally { $stream.Dispose() }
            $inner = [IO.MemoryStream]::new($bytes, $false)
            try { $tickets = @(Read-VenueTicketStream $inner $id $session -ForBundle) }
            finally { $inner.Dispose() }
        } else {
            $alignment = Read-RoomAlignment (Get-VenueInputPath $directory $room.alignmentFile) $id
            $tickets = @(Read-VenueRoomTickets (Get-VenueInputPath $directory $room.ticketsZip) $id $session)
        }
        $endpoint = $tickets[0].Endpoint
        foreach ($ticket in $tickets) {
            $hasPin = $null -ne $ticket.AlignmentHash
            if ($BundleEntries -and -not $hasPin) { throw "Room $id seat $($ticket.Seat + 1) needs a locked MR connection file." }
            if ($null -eq $usesPins) { $usesPins = $hasPin }
            if ($usesPins -ne $hasPin) { throw 'Do not mix locked MR and legacy connection files in the same venue preflight.' }
            if ($hasPin -and $ticket.AlignmentHash -cne $alignment.Hash) {
                throw "Room $id seat $($ticket.Seat + 1) does not match the locked MR alignment file."
            }
            if ($ticket.Endpoint -cne $endpoint) { throw "Room $id contains different game-server endpoints." }
            if (-not $players.Add($ticket.PlayerId) -or -not $admissions.Add($ticket.AdmissionId)) {
                throw "Room $id seat $($ticket.Seat + 1) repeats a player or admission."
            }
            if ($ticket.ExpiresAtUtc -lt $earliest) { $earliest = $ticket.ExpiresAtUtc }
            if ($id -eq $SelectedRoom -and $ticket.Seat -eq ($SelectedSeat - 1)) {
                $selected = @{ Alignment = $alignment; Ticket = $ticket }
            }
        }
        $null = $sessions.Add($session)
        $null = $endpoints.Add($endpoint)
        if ($ManagementApi) {
            if ($tickets | Where-Object { $_.Bytes.Length -gt 2048 }) { throw "Room $id connection JSON exceeds the live check's 2 KiB per-seat limit." }
            $liveRooms.Add(@{ roomId = $id; sessionId = $session; alignmentFile = [Convert]::ToBase64String($alignment.Bytes)
                connectionFiles = @($tickets | ForEach-Object { [Convert]::ToBase64String($_.Bytes) }) })
            if ($BundleEntries) { $publishedEndpoints[$session.ToString('D')] = $endpoint }
        }
        [pscustomobject]@{ roomId = $id; seats = $tickets.Count; endpoint = $endpoint; alignmentSha256 = $alignment.Hash }
    }
    $expected = if ($manifest.topology -ceq 'Linked') { 1 } else { 5 }
    if ($sessions.Count -ne $expected -or $endpoints.Count -ne $expected) {
        throw "$($manifest.topology) requires $expected distinct session(s) and $expected distinct game-server endpoint(s)."
    }
    if ($ManagementApi) {
        if (-not $usesPins) { throw 'The live venue check requires all 25 connection files to carry locked MR alignment hashes.' }
        Confirm-VenueWithManagement $ManagementApi $manifest.topology $liveRooms.ToArray() $publishedEndpoints
    }
    if ($earliest -le [DateTimeOffset]::UtcNow) { throw 'A player ticket expired during venue preflight. Download fresh room connection ZIPs.' }
    $report = [ordered]@{
        topology = $manifest.topology
        seats = $players.Count
        earliestExpiryUtc = $earliest.ToString('o')
        rooms = @($rooms | Sort-Object roomId)
    }
    if ($usesPins) { $report.alignmentPinsVerified = $true }
    if ($ManagementApi) { $report.managementVerified = $true }
    return @{ Report = $report; Selected = $selected }
}

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

if ($PSCmdlet.ParameterSetName -eq 'Venue') {
    $manifest = (Read-DeploymentJson $VenueManifest 16384 'venue manifest').Document
    $directory = [IO.Path]::GetDirectoryName((Resolve-Path -LiteralPath $VenueManifest).ProviderPath)
    (Read-Venue $manifest $directory).Report | ConvertTo-Json -Depth 4 -Compress
    return
}

$alignment = $null
$alignmentHash = $null
if ($PSCmdlet.ParameterSetName -eq 'Bundle') {
    if ([bool]$RoomId -ne [bool]$Seat) { throw 'Specify both -RoomId and -Seat, or omit both for five-room preflight.' }
    if (-not $RoomId -and $Serial) { throw 'Specify -RoomId and -Seat when targeting a Quest device.' }
    if ($RoomId -and -not $CheckOnly -and [string]::IsNullOrWhiteSpace($Serial)) { throw 'Specify -Serial to deploy a bundle seat to a Quest 3.' }
    $venue = Read-VenueBundle $VenueBundle $RoomId $Seat
    if (-not $RoomId) {
        $venue.Report | ConvertTo-Json -Depth 4 -Compress
        return
    }
    $ticket = $venue.Selected.Ticket
    $config = $ticket.Config
    $alignment = $venue.Selected.Alignment
    $alignmentHash = $alignment.Hash
    $isMixedReality = $true
} else {
    $config = (Read-DeploymentJson $ClientConfig 4096 'player connection').Document
    $ticket = Read-PlayerConfig $config
    $isMixedReality = $MixedReality -or $null -ne $ticket.AlignmentHash
    if (($Passthrough -or $isMixedReality) -and -not $AlignmentFile) { throw 'Quest passthrough requires a checked room alignment JSON export.' }
    if ($AlignmentFile) {
        $alignment = Read-RoomAlignment $AlignmentFile $ticket.RoomId
        $alignmentHash = $alignment.Hash
        if ($ticket.AlignmentHash -and $ticket.AlignmentHash -cne $alignmentHash) {
            throw "The supplied file does not match the locked MR alignment for room $($ticket.RoomId)."
        }
    }
}
if ($CheckOnly) {
    $report = [ordered]@{
        roomId = $ticket.RoomId
        seat = $ticket.Seat + 1
        expiresAtUtc = $ticket.ExpiresAtUtc.ToString('o')
        mode = if ($isMixedReality) { 'MR' } elseif ($Passthrough) { 'VR with passthrough' } else { 'VR' }
        alignmentSha256 = $alignmentHash
    }
    if ($ticket.AlignmentHash) { $report.alignmentPinsVerified = $true }
    if ($ManagementApi) { $report.managementVerified = $true }
    $report | ConvertTo-Json -Compress
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
if ($alignment) {
    $stagedAlignment = [IO.Path]::GetTempFileName()
    try {
        [IO.File]::WriteAllBytes($stagedAlignment, $alignment.Bytes)
        Publish-QuestFile $stagedAlignment "$remoteDirectory/vr-room-alignment-$deploymentId.tmp" `
            "$remoteDirectory/vr-room-alignment-$alignmentHash.json" 'Room alignment file'
    } finally {
        Remove-Item -LiteralPath $stagedAlignment
    }
    if (-not $ticket.AlignmentHash) { $config | Add-Member -NotePropertyName 'roomAlignmentSha256' -NotePropertyValue $alignmentHash }
}
if ($Passthrough -or $isMixedReality) { $config | Add-Member -NotePropertyName 'questPassthrough' -NotePropertyValue $true }
if ($isMixedReality) { $config | Add-Member -NotePropertyName 'requestMixedReality' -NotePropertyValue $true }
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
