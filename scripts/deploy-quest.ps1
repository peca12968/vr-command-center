[CmdletBinding(DefaultParameterSetName='Player')]
param(
    [Parameter(Mandatory, ParameterSetName='Player')][Parameter(Mandatory, ParameterSetName='Refresh')][string]$ClientConfig,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][Parameter(Mandatory, ParameterSetName='Refresh')][string]$Serial,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][Parameter(ParameterSetName='Refresh')][string]$AdbPath = 'F:\Tools\UnityEditors\6000.3.27f1\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe',
    [Parameter(Mandatory, ParameterSetName='Refresh')][switch]$RefreshPlayerTicket,
    [Parameter(ParameterSetName='Player')][string]$AlignmentFile,
    [Parameter(ParameterSetName='Player')][switch]$Passthrough,
    [Parameter(ParameterSetName='Player')][switch]$MixedReality,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][switch]$CheckOnly,
    [Parameter(Mandatory, ParameterSetName='Venue')][string]$VenueManifest,
    [Parameter(Mandatory, ParameterSetName='Bundle')][Parameter(Mandatory, ParameterSetName='CapturePlan')][string]$VenueBundle,
    [Parameter(ParameterSetName='Bundle')][ValidateRange(1,5)][int]$RoomId,
    [Parameter(ParameterSetName='Bundle')][ValidateRange(1,5)][int]$Seat,
    [Parameter(ParameterSetName='Bundle')][Parameter(Mandatory, ParameterSetName='CapturePlan')][ValidateNotNullOrEmpty()][string]$DeviceMap,
    [Parameter(ParameterSetName='Bundle')][Parameter(ParameterSetName='CapturePlan')][switch]$AllowPartialMap,
    [Parameter(Mandatory, ParameterSetName='CapturePlan')][switch]$ReadCapturePlan,
    [Parameter(ParameterSetName='Bundle')][ValidateRange(1,2147483647)][int]$ExpectedVersionCode,
    [Parameter(ParameterSetName='Bundle')][switch]$DeployMappedSeats,
    [Parameter(ParameterSetName='Bundle')][switch]$VerifyTrackedSeats,
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

function Get-PlayerTicketDetails([string]$Ticket, [switch]$AllowExpired) {
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
    if ($payload[0] -ne 2 -or $room -notin 1..5 -or $seat -notin 0..4 -or $expiry -le 0 -or $expiry -gt 253402300799L) {
        throw 'Use a current v2 player ticket from the management service.'
    }
    if (-not $AllowExpired -and $expiry -le [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) {
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

function Read-PlayerConfig($Config, [switch]$Installed) {
    $fields = @('role','address','port','joinTicket','roomAlignmentSha256')
    if ($Installed) { $fields += 'questPassthrough','requestMixedReality' }
    $unknown = @($Config.PSObject.Properties.Name | Where-Object { $_ -cnotin $fields })
    if ($Config.role -isnot [string] -or $Config.role -cne 'Client' -or $Config.joinTicket -isnot [string] -or
        $Config.address -isnot [string] -or $Config.address -notmatch '\A[^\s]+\z' -or
        -not (Test-JsonInteger $Config.port) -or $Config.port -lt 1 -or $Config.port -gt 65535 -or $unknown.Count -gt 0) {
        throw 'Use a player-only connection file from the management console or prepare-vr-session.py.'
    }
    $ticket = Get-PlayerTicketDetails $Config.joinTicket -AllowExpired:($ReadCapturePlan -or $Installed)
    if ($null -ne $Config.PSObject.Properties['roomAlignmentSha256']) {
        $hash = $Config.roomAlignmentSha256
        if ($hash -isnot [string] -or $hash -cnotmatch '\A[a-f0-9]{64}\z') { throw 'Use a valid locked MR alignment SHA-256 in the player connection file.' }
        $ticket.AlignmentHash = $hash
    }
    if ($Installed) {
        foreach ($flag in 'questPassthrough','requestMixedReality') {
            if ($null -ne $Config.PSObject.Properties[$flag] -and $Config.$flag -isnot [bool]) {
                throw 'Installed Quest flags must be boolean.'
            }
        }
        if (($Config.questPassthrough -and -not $ticket.AlignmentHash) -or
            ($Config.requestMixedReality -and -not $Config.questPassthrough)) {
            throw 'Installed Quest profile requires its original alignment and passthrough settings.'
        }
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

function Get-ManagementTarget([string]$Address) {
    $uri = $null
    if (-not [Uri]::TryCreate($Address, [UriKind]::Absolute, [ref]$uri) -or
        ($uri.Scheme -ne 'https' -and -not ($uri.Scheme -eq 'http' -and $uri.IsLoopback)) -or
        $uri.AbsolutePath -ne '/' -or $uri.UserInfo -or $uri.Query -or $uri.Fragment) {
        throw 'ManagementApi must be an HTTPS origin or a local loopback HTTP origin, without credentials, path, query or fragment.'
    }
    $masterKey = [Environment]::GetEnvironmentVariable('VR_COMMAND_MASTER_KEY')
    if ([string]::IsNullOrWhiteSpace($masterKey)) { throw 'Set VR_COMMAND_MASTER_KEY for the live venue check.' }
    return @{ Origin = $uri; Headers = @{ Authorization = 'Bearer ' + $masterKey } }
}

function Confirm-VenueWithManagement([string]$Address, [string]$Topology, [object[]]$Rooms, $PublishedEndpoints, [string]$Mode = 'MR') {
    $target = Get-ManagementTarget $Address
    $endpoint = [Uri]::new($target.Origin, "/api/$($Mode.ToLowerInvariant())-deployment/venue-check")
    $checksHeadset = $Mode -cin @('VR','Mixed')
    $body = @{ topology = $Topology; rooms = $Rooms } | ConvertTo-Json -Compress -Depth 6
    try {
        $response = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' `
            -Headers $target.Headers -Body $body -NoProxy -MaximumRedirection 0 -TimeoutSec 10 -SkipHttpErrorCheck
    } catch { throw 'The live venue check could not reach the management service.' }
    if ($response.StatusCode -in 401,403) { throw 'The management service requires the current Master key for the live venue check.' }
    if ($response.StatusCode -ne 200) { throw 'The management service did not accept the live venue check. Verify the management version and service status.' }
    try { $result = ConvertFrom-Json -InputObject $response.Content }
    catch { throw 'The management service returned an invalid venue check receipt.' }
    if ($result.topology -cne $Topology -or $result.allMatched -isnot [bool] -or $result.seats -isnot [array] -or $result.seats.Count -ne 25) {
        throw 'The management service returned an invalid venue check receipt.'
    }
    $validStatuses = @('matched', 'session-unavailable', 'seat-unavailable', 'connection-invalid', 'ticket-invalid', 'wrong-seat', 'admission-changed')
    if ($checksHeadset) { $validStatuses += @('endpoint-mismatch', 'venue-unavailable') }
    if ($Mode -cne 'VR') { $validStatuses += @('alignment-not-locked', 'connection-hash-mismatch', 'alignment-invalid', 'alignment-wrong-room', 'alignment-hash-mismatch') }
    $failures = for ($i = 0; $i -lt 25; $i++) {
        $room = [int][Math]::Floor($i / 5) + 1
        $seat = $i % 5
        $row = $result.seats[$i]
        if (-not (Test-JsonInteger $row.roomId) -or -not (Test-JsonInteger $row.seat) -or
            $row.roomId -ne $room -or $row.seat -ne $seat -or $row.status -cnotin $validStatuses -or
            ($checksHeadset -and $row.status -ceq 'matched' -and $row.headset -cnotin @('Quest3', 'ViveXr'))) {
            throw 'The management service returned an invalid venue check receipt.'
        }
        if ($row.status -cne 'matched') { 'Room {0} seat {1}: {2}' -f $room, ($seat + 1), $row.status }
    }
    if ($result.allMatched -ne (-not $failures)) { throw 'The management service returned an inconsistent venue check receipt.' }
    if ($failures) { throw ('Live venue check failed. ' + ($failures -join '; ')) }
    if ($checksHeadset) { return $result.seats }
    foreach ($sessionId in $PublishedEndpoints.Keys) {
        $source = [Uri]::new($target.Origin, "/api/sessions/$sessionId/connection-endpoint")
        try {
            $metadata = Invoke-WebRequest -Uri $source -Method Get -Headers $target.Headers `
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
    catch { throw 'Use a readable five-room deployment ZIP from the management console.' }
    try {
        if ($file.Length -lt 1 -or $file.Length -gt 512KB) { throw 'The five-room deployment ZIP has an invalid size.' }
        try { $archive = [IO.Compression.ZipArchive]::new($file, [IO.Compression.ZipArchiveMode]::Read, $true) }
        catch { throw 'Use a valid five-room deployment ZIP from the management console.' }
        try {
            if ($archive.Entries.Count -lt 6 -or $archive.Entries.Count -gt 11) { throw 'The deployment ZIP must contain exactly one manifest and ten room files for MR, five room files for VR, or the mixed room files.' }
            $entries = [Collections.Generic.Dictionary[string,IO.Compression.ZipArchiveEntry]]::new([StringComparer]::Ordinal)
            foreach ($entry in $archive.Entries) {
                if ($entries.ContainsKey($entry.FullName)) { throw 'The deployment ZIP contains a duplicate entry.' }
                $entries.Add($entry.FullName, $entry)
            }
            $manifest = (Read-VenueJsonEntry $entries['venue.json'] 'venue manifest').Document
            if ($manifest.mode -ceq 'VR') {
                if ($entries.Count -ne 6) { throw 'The VR ZIP must contain exactly one manifest and five room files.' }
            } elseif ($manifest.mode -ceq 'Mixed') {
                $mrCount = @($manifest.rooms | Where-Object mode -CEQ 'MR').Count
                if ($mrCount -notin 1..4 -or $entries.Count -ne (6 + $mrCount)) { throw 'The mixed ZIP needs five room bundles and exactly one alignment file per MR room.' }
            } elseif ($entries.Count -ne 11) { throw 'The deployment ZIP must contain exactly one manifest and ten room files for MR.' }
            Read-Venue $manifest '' $entries $SelectedRoom $SelectedSeat
        } finally { $archive.Dispose() }
    } finally { $file.Dispose() }
}

function Read-Venue($Manifest, [string]$Directory, $BundleEntries, [int]$SelectedRoom, [int]$SelectedSeat) {
    $isVr = $BundleEntries -and $manifest.mode -ceq 'VR'
    $isMixed = $BundleEntries -and $manifest.mode -ceq 'Mixed'
    $manifestFields = @('version','topology','rooms')
    if ($isVr -or $isMixed) { $manifestFields += 'mode' }
    $version = if ($isMixed) { 2 } else { 1 }
    if (-not (Test-JsonInteger $manifest.version) -or $manifest.version -ne $version -or
        ($isMixed -and $manifest.topology -cne 'Independent') -or
        $manifest.topology -isnot [string] -or $manifest.topology -cnotin @('Linked','Independent') -or
        $manifest.rooms -isnot [array] -or $manifest.rooms.Count -ne 5 -or
        @($manifest.PSObject.Properties.Name | Where-Object { $_ -cnotin $manifestFields }).Count -gt 0) {
        throw 'Use a supported venue manifest with five rooms and its original topology.'
    }
    $seenRooms = [Collections.Generic.HashSet[int]]::new()
    $players = [Collections.Generic.HashSet[Guid]]::new()
    $admissions = [Collections.Generic.HashSet[Guid]]::new()
    $sessions = [Collections.Generic.HashSet[Guid]]::new()
    $endpoints = [Collections.Generic.HashSet[string]]::new()
    $earliest = [DateTimeOffset]::MaxValue
    $usesPins = $null
    $connections = @{}
    $liveRooms = [Collections.Generic.List[object]]::new()
    $publishedEndpoints = @{}
    $rooms = foreach ($room in $manifest.rooms) {
        $session = [Guid]::Empty
        if (-not (Test-JsonInteger $room.roomId) -or $room.roomId -notin 1..5 -or -not $seenRooms.Add($room.roomId) -or
            $room.sessionId -isnot [string] -or -not [Guid]::TryParseExact($room.sessionId, 'D', [ref]$session) -or $session -eq [Guid]::Empty -or
            $room.ticketsZip -isnot [string] -or [string]::IsNullOrWhiteSpace($room.ticketsZip)) {
            throw 'Provide one entry per room with roomId, sessionId and ticketsZip.'
        }
        $roomVr = $isVr -or ($isMixed -and $room.mode -ceq 'VR')
        if ($isMixed) {
            $fields = @('roomId','sessionId','mode','address','port','ticketsZip')
            if (-not $roomVr) { $fields += 'alignmentFile' }
            if ($room.mode -isnot [string] -or $room.mode -cnotin @('VR','MR') -or $room.address -isnot [string] -or -not (Test-JsonInteger $room.port) -or
                @($room.PSObject.Properties.Name | Where-Object { $_ -cnotin $fields }).Count -gt 0) {
                throw "Room $($room.roomId) needs its original mode and endpoint."
            }
        } elseif ($isVr) {
            if ($room.address -isnot [string] -or -not (Test-JsonInteger $room.port) -or
                $room.seats -isnot [array] -or $room.seats.Count -ne 5 -or
                @($room.PSObject.Properties.Name | Where-Object { $_ -cnotin @('roomId','sessionId','ticketsZip','address','port','seats') }).Count -gt 0) {
                throw 'Provide the original VR venue room endpoints and seats.'
            }
            for ($i = 0; $i -lt 5; $i++) {
                $listed = $room.seats[$i]
                if (-not (Test-JsonInteger $listed.seat) -or $listed.seat -ne ($i + 1) -or
                    $listed.name -isnot [string] -or [string]::IsNullOrWhiteSpace($listed.name) -or
                    @($listed.PSObject.Properties.Name | Where-Object { $_ -cnotin @('seat','name') }).Count -gt 0) {
                    throw "Room $($room.roomId) needs the original five named VR seats."
                }
            }
        } elseif ($room.alignmentFile -isnot [string] -or [string]::IsNullOrWhiteSpace($room.alignmentFile) -or
            @($room.PSObject.Properties.Name | Where-Object { $_ -cnotin @('roomId','sessionId','ticketsZip','alignmentFile') }).Count -gt 0) {
            throw 'Provide one entry per room with roomId, sessionId, ticketsZip and alignmentFile.'
        }
        $id = $room.roomId
        $alignment = $null
        if ($BundleEntries) {
            $expectedZip = 'room-{0:00}-connections.zip' -f $id
            $expectedAlignment = 'room-{0:00}-alignment.json' -f $id
            if ($room.ticketsZip -cne $expectedZip -or -not $BundleEntries.ContainsKey($expectedZip) -or
                (-not $roomVr -and ($room.alignmentFile -cne $expectedAlignment -or -not $BundleEntries.ContainsKey($expectedAlignment)))) {
                throw "Room $id must use the original room filenames inside the deployment ZIP."
            }
            if (-not $roomVr) { $alignment = Confirm-RoomAlignment (Read-VenueJsonEntry $BundleEntries[$expectedAlignment] "room $id alignment") $id }
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
        if (($isVr -or $isMixed) -and ($room.address + ':' + $room.port) -cne $endpoint) {
            throw "Room $id connection files do not match the $($manifest.mode) manifest endpoint."
        }
        foreach ($ticket in $tickets) {
            $hasPin = $null -ne $ticket.AlignmentHash
            if ($roomVr -and $hasPin) { throw "Room $id seat $($ticket.Seat + 1) needs a VR connection file." }
            if ($BundleEntries -and -not $roomVr -and -not $hasPin) { throw "Room $id seat $($ticket.Seat + 1) needs a locked MR connection file." }
            if ($null -eq $usesPins) { $usesPins = $hasPin }
            if (-not $isMixed -and $usesPins -ne $hasPin) { throw 'Do not mix locked MR and legacy connection files in the same venue preflight.' }
            if ($hasPin -and $ticket.AlignmentHash -cne $alignment.Hash) {
                throw "Room $id seat $($ticket.Seat + 1) does not match the locked MR alignment file."
            }
            if ($ticket.Endpoint -cne $endpoint) { throw "Room $id contains different game-server endpoints." }
            if (-not $players.Add($ticket.PlayerId) -or -not $admissions.Add($ticket.AdmissionId)) {
                throw "Room $id seat $($ticket.Seat + 1) repeats a player or admission."
            }
            if ($ticket.ExpiresAtUtc -lt $earliest) { $earliest = $ticket.ExpiresAtUtc }
            if ($BundleEntries) {
                $connections["$id/$($ticket.Seat + 1)"] = @{ Alignment = $alignment; Ticket = $ticket }
            }
        }
        $null = $sessions.Add($session)
        $null = $endpoints.Add($endpoint)
        if ($ManagementApi) {
            if ($tickets | Where-Object { $_.Bytes.Length -gt 2048 }) { throw "Room $id connection JSON exceeds the live check's 2 KiB per-seat limit." }
            $live = @{ roomId = $id; sessionId = $session
                connectionFiles = @($tickets | ForEach-Object { [Convert]::ToBase64String($_.Bytes) }) }
            if ($isMixed) { $live.mode = $room.mode }
            if (-not $roomVr) { $live.alignmentFile = [Convert]::ToBase64String($alignment.Bytes) }
            $liveRooms.Add($live)
            if ($BundleEntries -and -not $isVr -and -not $isMixed) { $publishedEndpoints[$session.ToString('D')] = $endpoint }
        }
        $row = [ordered]@{ roomId = $id; seats = $tickets.Count; endpoint = $endpoint }
        if ($isMixed) { $row.mode = $room.mode }
        if (-not $roomVr) { $row.alignmentSha256 = $alignment.Hash }
        [pscustomobject]$row
    }
    $expected = if ($manifest.topology -ceq 'Linked') { 1 } else { 5 }
    if ($sessions.Count -ne $expected -or $endpoints.Count -ne $expected) {
        throw "$($manifest.topology) requires $expected distinct session(s) and $expected distinct game-server endpoint(s)."
    }
    $report = [ordered]@{
        topology = $manifest.topology
        seats = $players.Count
        earliestExpiryUtc = $earliest.ToString('o')
        rooms = @($rooms | Sort-Object roomId)
    }
    if ($usesPins -or $isMixed) { $report.alignmentPinsVerified = $true }
    if ($isVr -or $isMixed) { $report.mode = $manifest.mode }
    return @{ Report = $report; Selected = $connections["$SelectedRoom/$SelectedSeat"]; Connections = $connections;
        EarliestExpiry = $earliest; LiveRooms = $liveRooms.ToArray(); PublishedEndpoints = $publishedEndpoints; SeatHeadsets = @{} }
}

function Confirm-VenueReadback($Venue) {
    if ($ManagementApi) {
        if ($Venue.Report.mode -cin @('VR','Mixed')) {
            $seats = @(Confirm-VenueWithManagement $ManagementApi $Venue.Report.topology $Venue.LiveRooms $Venue.PublishedEndpoints -Mode $Venue.Report.mode)
            foreach ($row in $seats) { $Venue.SeatHeadsets["$($row.roomId)/$($row.seat + 1)"] = $row.headset }
            $Venue.Report.quest3Seats = @($seats | Where-Object headset -CEQ 'Quest3').Count
        } else {
            if (-not $Venue.Report.alignmentPinsVerified) { throw 'The live venue check requires all 25 connection files to carry locked MR alignment hashes.' }
            Confirm-VenueWithManagement $ManagementApi $Venue.Report.topology $Venue.LiveRooms $Venue.PublishedEndpoints
        }
        $Venue.Report.managementVerified = $true
    }
    if ($Venue.EarliestExpiry -le [DateTimeOffset]::UtcNow) {
        throw 'A player ticket expired during venue preflight. Download fresh room connection ZIPs.'
    }
}

function Read-QuestDeviceMap([string]$Path, [switch]$Partial) {
    $map = (Read-DeploymentJson $Path 16384 'device map').Document
    $minimum = if ($Partial) { 1 } else { 25 }
    if (-not (Test-JsonInteger $map.version) -or $map.version -ne 1 -or $map.seats -isnot [array] -or
        $map.seats.Count -lt $minimum -or $map.seats.Count -gt 25 -or
        @($map.PSObject.Properties.Name | Where-Object { $_ -cnotin @('version','seats') }).Count) {
        if ($Partial) { throw 'Use a version 1 device map with 1 to 25 seats.' }
        throw 'Use a version 1 device map with exactly 25 seats.'
    }
    $seats = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $serials = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    foreach ($row in $map.seats) {
        if (-not (Test-JsonInteger $row.roomId) -or $row.roomId -notin 1..5 -or
            -not (Test-JsonInteger $row.seat) -or $row.seat -notin 1..5 -or
            $row.serial -isnot [string] -or $row.serial -cnotmatch '\A[A-Za-z0-9\[][A-Za-z0-9._:%\[\]-]{0,127}\z' -or
            @($row.PSObject.Properties.Name | Where-Object { $_ -cnotin @('roomId','seat','serial') }).Count) {
            throw 'Each device map row needs a roomId, seat and exact ADB serial.'
        }
        if (-not $seats.Add("$($row.roomId)/$($row.seat)")) { throw "Room $($row.roomId) seat $($row.seat) is mapped more than once." }
        if (-not $serials.Add($row.serial)) { throw "Room $($row.roomId) seat $($row.seat) repeats an ADB serial." }
    }
    $map.seats | Sort-Object roomId, seat
}

function Read-TrackedReadiness($Target, [Guid]$SessionId) {
    $url = [Uri]::new($Target.Origin, "/api/sessions/$SessionId/readiness")
    try {
        $response = Invoke-WebRequest -Uri $url -Method Get -Headers $Target.Headers -NoProxy `
            -MaximumRedirection 0 -TimeoutSec 10 -SkipHttpErrorCheck
        if ($response.StatusCode -ne 200) { return @{ Status = 'readiness-unavailable' } }
        $snapshot = ConvertFrom-Json -InputObject $response.Content
    } catch { return @{ Status = 'readiness-unavailable' } }
    if (-not (Test-JsonInteger $snapshot.version) -or $snapshot.version -ne 1 -or $snapshot.sessionId -cne $SessionId.ToString('D') -or
        $snapshot.players -isnot [array] -or $snapshot.players.Count -gt 25 -or
        $snapshot.sourceState -cnotin @('Fresh','Ended','NoRecording','WaitingFrame','UnknownCaptureTime','ClockSkew','Stale','Suspended','PhasePending') -or
        -not (Test-JsonInteger $snapshot.worldSequence) -or $snapshot.worldSequence -lt 0 -or
        -not (Test-JsonInteger $snapshot.sessionSequence) -or $snapshot.sessionSequence -lt 1 -or
        -not (Test-JsonInteger $snapshot.observedSequence) -or $snapshot.observedSequence -lt 0) {
        return @{ Status = 'readiness-invalid' }
    }
    return @{ Snapshot = $snapshot }
}

function Get-TrackedSeatStatus($Reading, $Connection) {
    if ($Reading.Status) { return $Reading.Status }
    $snapshot = $Reading.Snapshot
    $ticket = $Connection.Ticket
    $rows = @($snapshot.players | Where-Object { $_.roomId -eq $ticket.RoomId -and $_.seat -eq $ticket.Seat })
    if ($rows.Count -eq 0) { return 'seat-unavailable' }
    if ($rows.Count -ne 1) { return 'readiness-invalid' }
    $player = $rows[0]
    if (-not (Test-JsonInteger $player.roomId) -or -not (Test-JsonInteger $player.seat) -or
        $player.canParticipate -isnot [bool]) { return 'readiness-invalid' }
    if ($player.playerId -cne $ticket.PlayerId.ToString('D') -or $player.admissionId -cne $ticket.AdmissionId.ToString('D')) {
        return 'admission-changed'
    }
    if ($snapshot.sourceState -cne 'Fresh') { return 'source-not-fresh' }
    if ($snapshot.origin -cnotin @('Simulation','GameServer') -or $snapshot.worldSequence -eq 0 -or
        $snapshot.observedSequence -ne $snapshot.sessionSequence) { return 'source-revision-pending' }
    if ($Connection.Alignment -and ($snapshot.origin -cne 'GameServer' -or
        @($snapshot.mrStartState, $snapshot.mrResumeState, $snapshot.mrTrackingState).Where({ $_ -cin @('Ready','WaitingPlayers') }).Count -eq 0)) {
        return 'mr-profile-pending'
    }
    if ($player.state -cne 'Participating' -or -not $player.canParticipate) { return 'awaiting-tracked-pose' }
    if ($player.rigKind -cne 'Tracked') { return 'not-tracked' }
    return 'tracked-ready'
}

function Confirm-TrackedSeats($Venue, [object[]]$Map) {
    Confirm-VenueReadback $Venue
    $target = Get-ManagementTarget $ManagementApi
    $readings = @{}
    $hasHeadsets = $Venue.Report.mode -cin @('VR','Mixed')
    $seats = @(foreach ($row in $Map) {
        $key = "$($row.roomId)/$($row.seat)"
        if ($hasHeadsets -and $Venue.SeatHeadsets[$key] -cne 'Quest3') {
            if ($DeviceMap) { [ordered]@{ roomId = $row.roomId; seat = $row.seat; status = 'seat-headset-mismatch' } }
            continue
        }
        $connection = $Venue.Connections[$key]
        $session = $connection.Ticket.SessionId
        if (-not $readings.ContainsKey($session)) { $readings[$session] = Read-TrackedReadiness $target $session }
        $reading = $readings[$session]
        [ordered]@{ roomId = $row.roomId; seat = $row.seat; status = Get-TrackedSeatStatus $reading $connection;
            sourceState = $reading.Snapshot.sourceState; worldSequence = $reading.Snapshot.worldSequence }
    })
    return [ordered]@{ phase = 'tracked-readiness'; topology = $Venue.Report.topology; managementVerified = $true;
        complete = ($seats.Count -gt 0 -and -not ($seats | Where-Object { $_.status -cne 'tracked-ready' })); seats = $seats }
}

function Get-QuestDeviceInventory {
    $lines = @(& $AdbPath devices)
    if ($LASTEXITCODE -ne 0) { throw 'Could not list authorized Android devices.' }
    $inventory = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::Ordinal)
    foreach ($line in $lines) {
        if ($line -cnotmatch '\A(\S+)\t(\S+)\s*\z') { continue }
        $key = $Matches[1]; $status = $Matches[2]
        if ($inventory.ContainsKey($key)) { $status = 'ambiguous' }
        $inventory[$key] = $status
    }
    return ,$inventory
}

function Get-MappedQuestStatus($Row, $Inventory) {
    $result = [ordered]@{ roomId = $Row.roomId; seat = $Row.seat; status = 'ready' }
    $status = $Inventory[$Row.serial]
    if ($status -cne 'device') {
        $result.status = if (-not $status) { 'missing' } elseif ($status -cin @('unauthorized','offline','ambiguous')) { $status } else { 'unavailable' }
        return $result
    }
    $model = & $AdbPath -s $Row.serial shell getprop ro.product.model 2>$null
    if ($LASTEXITCODE -ne 0) { $result.status = 'model-unavailable'; return $result }
    if (([string]$model).Trim() -cne 'Quest 3') { $result.status = 'wrong-model'; return $result }
    $packages = @(& $AdbPath -s $Row.serial shell pm list packages -e --show-versioncode --user current com.vrcommand.quest 2>$null)
    if ($LASTEXITCODE -ne 0) { $result.status = 'package-query-failed'; return $result }
    $rows = @($packages | Where-Object { $_ -cmatch '\Apackage:com\.vrcommand\.quest versionCode:[0-9]+\s*\z' })
    $code = 0L
    if ($rows.Count -ne 1 -or -not [long]::TryParse(($rows[0] -csplit ':')[-1], [ref]$code)) {
        $result.status = 'package-unavailable'; return $result
    }
    $result.versionCode = $code
    if ($code -ne $ExpectedVersionCode) { $result.status = 'version-mismatch' }
    return $result
}

function Invoke-MappedQuestSeats($Venue, [object[]]$Map) {
    if (-not (Test-Path -LiteralPath $AdbPath -PathType Leaf)) { throw 'Android platform-tools are not installed.' }
    $inventory = Get-QuestDeviceInventory
    $devices = @($Map | ForEach-Object { Get-MappedQuestStatus $_ $inventory })
    $report = [ordered]@{ phase = 'preflight'; topology = $Venue.Report.topology; expectedVersionCode = $ExpectedVersionCode;
        earliestExpiryUtc = $Venue.Report.earliestExpiryUtc; complete = $false; devices = $devices }
    if ($AllowPartialMap) {
        $report.mappedSeats = $Map.Count
        $report.unmappedSeats = $Venue.Report.seats - $Map.Count
    }
    $isVr = $Venue.Report.mode -ceq 'VR'
    $checksHeadset = $Venue.Report.mode -cin @('VR','Mixed')
    if ($checksHeadset) { $report.mode = $Venue.Report.mode }
    if (-not $isVr) { $report.alignmentPinsVerified = $true }
    if ($devices | Where-Object { $_.status -cne 'ready' }) { return $report }
    Confirm-VenueReadback $Venue
    if ($Venue.Report.managementVerified) { $report.managementVerified = $true }
    if ($checksHeadset -and $Venue.Report.managementVerified) {
        foreach ($device in $devices) {
            if ($Venue.SeatHeadsets["$($device.roomId)/$($device.seat)"] -cne 'Quest3') { $device.status = 'seat-headset-mismatch' }
        }
        if ($devices | Where-Object status -CEQ 'seat-headset-mismatch') { return $report }
    }
    if (-not $DeployMappedSeats) { $report.complete = $true; return $report }

    $report.phase = 'deployment'
    $WarningPreference = 'SilentlyContinue'
    foreach ($device in $devices) { $device.status = 'not-attempted' }
    for ($index = 0; $index -lt $Map.Count; $index++) {
        $row = $Map[$index]; $device = $devices[$index]
        $connection = $Venue.Connections["$($row.roomId)/$($row.seat)"]
        if ($connection.Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) {
            $device.status = 'ticket-expired'; return $report
        }
        try {
            Set-QuestConnection $row.serial $connection.Ticket.Config $connection.Ticket $connection.Alignment -RequestMixedReality:($null -ne $connection.Alignment)
            $device.status = 'launch-requested'
        } catch {
            $device.status = 'deployment-failed'
            return $report
        }
    }
    $report.complete = $true
    return $report
}

function Enter-QuestDeployment {
    $lock = [Threading.Mutex]::new($false, 'VrCommand.QuestDeployment')
    try { $acquired = $lock.WaitOne(0) }
    catch [Threading.AbandonedMutexException] { $acquired = $true }
    if (-not $acquired) { $lock.Dispose(); throw 'Another Quest deployment is running on this computer.' }
    return $lock
}

function Publish-QuestFile([string]$TargetSerial, [string]$Local, [string]$Staging, [string]$Destination, [string]$Description,
    [string]$ExpectedHash) {
    try {
        & $AdbPath -s $TargetSerial push $Local $Staging | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "$Description could not be copied." }
        if ($ExpectedHash) {
            $stagedHash = (Get-FileHash -LiteralPath $Local -Algorithm SHA256).Hash.ToLowerInvariant()
            $command = 'current=$(sha256sum ''{0}'') && staged=$(sha256sum ''{1}'') && [ "${{current%% *}}" = ''{2}'' ] && [ "${{staged%% *}}" = ''{3}'' ] && mv -f ''{1}'' ''{0}''' `
                -f $Destination, $Staging, $ExpectedHash, $stagedHash
            & $AdbPath -s $TargetSerial shell $command *> $null
            if ($LASTEXITCODE -ne 0) { throw 'Could not confirm ticket replacement. Check the selected device and read its current configuration before retrying.' }
        } else {
            & $AdbPath -s $TargetSerial shell mv $Staging $Destination | Out-Null
            if ($LASTEXITCODE -ne 0) { throw "$Description could not be activated." }
        }
    } catch {
        $publishError = $_
        try {
            & $AdbPath -s $TargetSerial shell rm -f $Staging *> $null
            if ($LASTEXITCODE -ne 0) { throw 'ADB cleanup failed.' }
        } catch {
            Write-Warning 'Could not remove the temporary deployment file from the selected device.'
        }
        throw $publishError
    }
}

function Update-QuestPlayerTicket($Fresh, $Ticket) {
    if ($Serial -cnotmatch '\A[A-Za-z0-9\[][A-Za-z0-9._:%\[\]-]{0,127}\z') { throw 'Use an explicit ADB serial for the Quest 3.' }
    if (-not (Test-Path -LiteralPath $AdbPath -PathType Leaf)) { throw 'Provide the installed ADB executable.' }
    if ([Guid]::Empty -in @($Ticket.SessionId, $Ticket.PlayerId, $Ticket.AdmissionId)) { throw 'Use a player file for an original admission.' }
    $model = & $AdbPath -s $Serial shell getprop ro.product.model 2>$null
    if ($LASTEXITCODE -ne 0 -or ($model -join "`n").Trim() -cne 'Quest 3') { throw 'Select an authorized Meta Quest 3.' }

    $remote = '/sdcard/Android/data/com.vrcommand.quest/files'
    $destination = "$remote/vr-connection.json"
    $local = [IO.Path]::GetTempFileName()
    try {
        & $AdbPath -s $Serial pull $destination $local *> $null
        if ($LASTEXITCODE -ne 0) { throw 'Could not read the original player configuration on the selected Quest.' }
        $original = Read-DeploymentJson $local 4096 'installed Quest configuration'
        $current = $original.Document
        $installed = Read-PlayerConfig $current -Installed
        if ($Ticket.SessionId -ne $installed.SessionId -or $Ticket.PlayerId -ne $installed.PlayerId -or
            $Ticket.AdmissionId -ne $installed.AdmissionId -or $Ticket.RoomId -ne $installed.RoomId -or
            $Ticket.Seat -ne $installed.Seat -or $Fresh.address -cne $current.address -or $Fresh.port -ne $current.port) {
            throw 'Refresh requires the same original admission, seat and game endpoint.'
        }
        if (($Ticket.AlignmentHash -and $Ticket.AlignmentHash -cne $installed.AlignmentHash) -or
            ($current.requestMixedReality -and -not $Ticket.AlignmentHash)) {
            throw 'Refresh requires the original locked MR alignment.'
        }
        $sameTicket = $Fresh.joinTicket -ceq $current.joinTicket
        if ($Ticket.ExpiresAtUtc -lt $installed.ExpiresAtUtc) { throw 'Use a ticket with the same or a later expiry for this admission.' }
        if ($Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) { throw 'The replacement ticket expired before refresh.' }
        if (-not $sameTicket) {
            $expectedHash = (Get-FileHash -LiteralPath $local -Algorithm SHA256).Hash.ToLowerInvariant()
            $current.joinTicket = $Fresh.joinTicket
            [IO.File]::WriteAllText($local, ($current | ConvertTo-Json -Depth 4 -Compress))
            $staging = "$remote/vr-connection-$([Guid]::NewGuid().ToString('N')).tmp"
            Publish-QuestFile $Serial $local $staging $destination 'Player ticket file' $expectedHash
        }
    } finally { Remove-Item -LiteralPath $local }
    [ordered]@{ roomId = $Ticket.RoomId; seat = $Ticket.Seat + 1; expiresAtUtc = $Ticket.ExpiresAtUtc.ToString('o')
        status = if ($sameTicket) { 'ticket-file-current' } else { 'ticket-file-refreshed' } } | ConvertTo-Json -Compress
}

function Set-QuestConnection([string]$TargetSerial, $Config, $Ticket, $Alignment, [switch]$UsePassthrough, [switch]$RequestMixedReality) {
    & $AdbPath -s $TargetSerial shell am force-stop com.vrcommand.quest | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Quest app could not be stopped before copying configuration.' }
    $remoteDirectory = '/sdcard/Android/data/com.vrcommand.quest/files'
    & $AdbPath -s $TargetSerial shell mkdir -p $remoteDirectory | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'App data directory could not be prepared.' }
    $deploymentId = [Guid]::NewGuid().ToString('N')
    if ($Alignment) {
        $alignmentHash = $Alignment.Hash
        $stagedAlignment = [IO.Path]::GetTempFileName()
        try {
            [IO.File]::WriteAllBytes($stagedAlignment, $Alignment.Bytes)
            Publish-QuestFile $TargetSerial $stagedAlignment "$remoteDirectory/vr-room-alignment-$deploymentId.tmp" `
                "$remoteDirectory/vr-room-alignment-$alignmentHash.json" 'Room alignment file'
        } finally { Remove-Item -LiteralPath $stagedAlignment }
        if (-not $Ticket.AlignmentHash) { $Config | Add-Member -NotePropertyName 'roomAlignmentSha256' -NotePropertyValue $alignmentHash }
    }
    if ($UsePassthrough -or $RequestMixedReality) { $Config | Add-Member -NotePropertyName 'questPassthrough' -NotePropertyValue $true }
    if ($RequestMixedReality) { $Config | Add-Member -NotePropertyName 'requestMixedReality' -NotePropertyValue $true }
    $stagedConfig = [IO.Path]::GetTempFileName()
    try {
        if ($Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) { throw 'Player ticket expired during deployment. Download a fresh connection file.' }
        [IO.File]::WriteAllText($stagedConfig, ($Config | ConvertTo-Json -Depth 4 -Compress))
        Publish-QuestFile $TargetSerial $stagedConfig "$remoteDirectory/vr-connection-$deploymentId.tmp" "$remoteDirectory/vr-connection.json" 'Player connection file'
    } finally { Remove-Item -LiteralPath $stagedConfig }
    if ($Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) { throw 'Player ticket expired before launch. Download a fresh connection file.' }
    & $AdbPath -s $TargetSerial shell monkey -p com.vrcommand.quest -c android.intent.category.LAUNCHER 1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Quest app launch failed.' }
}

if ($PSCmdlet.ParameterSetName -eq 'Venue') {
    $manifest = (Read-DeploymentJson $VenueManifest 16384 'venue manifest').Document
    $directory = [IO.Path]::GetDirectoryName((Resolve-Path -LiteralPath $VenueManifest).ProviderPath)
    $venue = Read-Venue $manifest $directory
    Confirm-VenueReadback $venue
    $venue.Report | ConvertTo-Json -Depth 4 -Compress
    return
}

if ($PSCmdlet.ParameterSetName -eq 'CapturePlan') {
    if (-not $ReadCapturePlan) { throw 'Specify -ReadCapturePlan for offline log capture planning.' }
    $map = @(Read-QuestDeviceMap $DeviceMap -Partial:$AllowPartialMap)
    $venue = Read-VenueBundle $VenueBundle 0 0
    $seats = foreach ($row in $map) {
        $ticket = $venue.Connections["$($row.roomId)/$($row.seat)"].Ticket
        [ordered]@{
            roomId = $row.roomId; seat = $row.seat; serial = $row.serial; port = $ticket.Config.port
            sessionId = $ticket.SessionId.ToString('D'); playerId = $ticket.PlayerId.ToString('D')
            admissionId = $ticket.AdmissionId.ToString('D')
        }
    }
    [ordered]@{ version = 1; topology = $venue.Report.topology; seats = @($seats) } | ConvertTo-Json -Depth 4 -Compress
    return
}

if ($PSCmdlet.ParameterSetName -eq 'Refresh') {
    if (-not $RefreshPlayerTicket) { throw 'Specify -RefreshPlayerTicket for the live ticket update.' }
    $fresh = (Read-DeploymentJson $ClientConfig 4096 'new player connection').Document
    $ticket = Read-PlayerConfig $fresh
    $deploymentLock = Enter-QuestDeployment
    try { Update-QuestPlayerTicket $fresh $ticket }
    finally { $deploymentLock.ReleaseMutex(); $deploymentLock.Dispose() }
    return
}

$alignment = $null
$alignmentHash = $null
if ($PSCmdlet.ParameterSetName -eq 'Bundle') {
    if ($VerifyTrackedSeats) {
        if (-not $ManagementApi -or $RoomId -or $Seat -or $PSBoundParameters.ContainsKey('Serial') -or
            $ExpectedVersionCode -or $DeployMappedSeats -or $CheckOnly -or ($AllowPartialMap -and -not $DeviceMap)) {
            throw 'Use -VerifyTrackedSeats with -ManagementApi and an optional -DeviceMap; omit deployment and device-check parameters.'
        }
        $map = @(if ($DeviceMap) { Read-QuestDeviceMap $DeviceMap -Partial:$AllowPartialMap }
            else { foreach ($room in 1..5) { foreach ($seat in 1..5) { @{ roomId = $room; seat = $seat } } } })
        $result = Confirm-TrackedSeats (Read-VenueBundle $VenueBundle 0 0) $map
        $result | ConvertTo-Json -Depth 4 -Compress
        if (-not $result.complete) { exit 1 }
        return
    }
    if ($DeviceMap) {
        if ($RoomId -or $Seat -or $PSBoundParameters.ContainsKey('Serial') -or -not $ExpectedVersionCode) {
            throw 'Use -DeviceMap with -ExpectedVersionCode and omit -RoomId, -Seat and -Serial.'
        }
        if ($DeployMappedSeats -and ($CheckOnly -or -not $ManagementApi)) {
            throw '-DeployMappedSeats requires -ManagementApi and cannot be combined with -CheckOnly.'
        }
        $map = @(Read-QuestDeviceMap $DeviceMap -Partial:$AllowPartialMap)
        $venue = Read-VenueBundle $VenueBundle 0 0
        if ($DeployMappedSeats) {
            $deploymentLock = Enter-QuestDeployment
            try { $result = Invoke-MappedQuestSeats $venue $map }
            finally { $deploymentLock.ReleaseMutex(); $deploymentLock.Dispose() }
        } else { $result = Invoke-MappedQuestSeats $venue $map }
        $result | ConvertTo-Json -Depth 4 -Compress
        if (-not $result.complete) { exit 1 }
        return
    }
    if ($DeployMappedSeats -or $ExpectedVersionCode -or $AllowPartialMap) { throw 'Specify -DeviceMap for mapped deployment parameters.' }
    if ([bool]$RoomId -ne [bool]$Seat) { throw 'Specify both -RoomId and -Seat, or omit both for five-room preflight.' }
    if (-not $RoomId -and $Serial) { throw 'Specify -RoomId and -Seat when targeting a Quest device.' }
    if ($RoomId -and -not $CheckOnly -and [string]::IsNullOrWhiteSpace($Serial)) { throw 'Specify -Serial to deploy a bundle seat to a Quest 3.' }
    $venue = Read-VenueBundle $VenueBundle $RoomId $Seat
    $requiresLive = $venue.Report.mode -cin @('VR','Mixed')
    if ($requiresLive -and $RoomId -and -not $CheckOnly -and -not $ManagementApi) {
        throw 'Deploying a VR or mixed bundle seat requires -ManagementApi for a current signed seat and endpoint check.'
    }
    Confirm-VenueReadback $venue
    if (-not $RoomId) {
        $venue.Report | ConvertTo-Json -Depth 4 -Compress
        return
    }
    $ticket = $venue.Selected.Ticket
    $config = $ticket.Config
    $alignment = $venue.Selected.Alignment
    $isMixedReality = $null -ne $alignment
    $alignmentHash = $alignment.Hash
    if ($requiresLive -and -not $CheckOnly -and $venue.SeatHeadsets["$RoomId/$Seat"] -cne 'Quest3') {
        throw 'The selected seat is not assigned to a Quest 3 player.'
    }
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
    if ($PSCmdlet.ParameterSetName -eq 'Bundle' -and $requiresLive -and $ManagementApi) {
        $report.headset = $venue.SeatHeadsets["$RoomId/$Seat"]
    }
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
$deploymentLock = Enter-QuestDeployment
try {
    $model = & $AdbPath -s $Serial shell getprop ro.product.model
    if ($LASTEXITCODE -ne 0) { throw 'Could not identify the selected Android device.' }
    $model = ([string]$model).Trim()
    if ($model -ne 'Quest 3') { throw 'Selected device is not a Meta Quest 3. No app was installed.' }
    & $AdbPath -s $Serial install -r $apk
    if ($LASTEXITCODE -ne 0) { throw 'APK installation failed.' }
    Set-QuestConnection $Serial $config $ticket $alignment -UsePassthrough:$Passthrough -RequestMixedReality:$isMixedReality
} finally {
    $deploymentLock.ReleaseMutex(); $deploymentLock.Dispose()
}
Write-Host 'Quest client installed and launched. Ticket expiry and server admission still apply.'
