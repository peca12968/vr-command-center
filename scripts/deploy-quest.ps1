[CmdletBinding(DefaultParameterSetName='Player')]
param(
    [Parameter(Mandatory, ParameterSetName='Player')][Parameter(Mandatory, ParameterSetName='Refresh')][Parameter(Mandatory, ParameterSetName='PlayerTracking')][string]$ClientConfig,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][Parameter(Mandatory, ParameterSetName='Refresh')][Parameter(Mandatory, ParameterSetName='Smoke')][string]$Serial,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][Parameter(ParameterSetName='Refresh')][Parameter(ParameterSetName='Smoke')][Parameter(ParameterSetName='PrepareApks')][string]$AdbPath = 'F:\Tools\UnityEditors\6000.3.27f1\Editor\Data\PlaybackEngines\AndroidPlayer\SDK\platform-tools\adb.exe',
    [Parameter(Mandatory, ParameterSetName='Smoke')][switch]$SmokeTest,
    [Parameter(ParameterSetName='Smoke')][switch]$ResumeSmokeTest,
    [Parameter(ParameterSetName='Smoke')][Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][switch]$RequireOpenXR,
    [Parameter(Mandatory, ParameterSetName='Refresh')][switch]$RefreshPlayerTicket,
    [Parameter(Mandatory, ParameterSetName='PlayerTracking')][switch]$VerifyPlayerTracking,
    [Parameter(ParameterSetName='Player')][string]$AlignmentFile,
    [Parameter(ParameterSetName='Player')][switch]$Passthrough,
    [Parameter(ParameterSetName='Player')][switch]$MixedReality,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][Parameter(ParameterSetName='PrepareApks')][switch]$CheckOnly,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][switch]$RecordLinkMetrics,
    [Parameter(Mandatory, ParameterSetName='Venue')][string]$VenueManifest,
    [Parameter(Mandatory, ParameterSetName='Bundle')][Parameter(Mandatory, ParameterSetName='CapturePlan')][Parameter(Mandatory, ParameterSetName='Windows')][string]$VenueBundle,
    [Parameter(ParameterSetName='Bundle')][ValidateRange(1,5)][int]$RoomId,
    [Parameter(ParameterSetName='Bundle')][ValidateRange(1,5)][int]$Seat,
    [Parameter(ParameterSetName='Bundle')][Parameter(Mandatory, ParameterSetName='CapturePlan')][Parameter(Mandatory, ParameterSetName='PrepareApks')][ValidateNotNullOrEmpty()][string]$DeviceMap,
    [Parameter(ParameterSetName='Bundle')][Parameter(ParameterSetName='CapturePlan')][switch]$AllowPartialMap,
    [Parameter(Mandatory, ParameterSetName='CapturePlan')][switch]$ReadCapturePlan,
    [Parameter(ParameterSetName='Bundle')][ValidateRange(1,2147483647)][int]$ExpectedVersionCode,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][Parameter(Mandatory, ParameterSetName='Smoke')][Parameter(Mandatory, ParameterSetName='PrepareApks')][ValidateNotNullOrEmpty()][string]$ReleaseReport,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Bundle')][Parameter(ParameterSetName='Smoke')][Parameter(ParameterSetName='PrepareApks')][ValidateNotNullOrEmpty()][string]$ApkPath,
    [Parameter(Mandatory, ParameterSetName='PrepareApks')][switch]$PrepareQuestApks,
    [Parameter(ParameterSetName='Bundle')][switch]$DeployMappedSeats,
    [Parameter(ParameterSetName='Bundle')][switch]$InstallMissing,
    [Parameter(ParameterSetName='Bundle')][ValidateNotNullOrEmpty()][string]$SaveDeploymentReport,
    [Parameter(ParameterSetName='Bundle')][ValidateNotNullOrEmpty()][string]$RetryIncomplete,
    [Parameter(ParameterSetName='Bundle')][switch]$VerifyTrackedSeats,
    [Parameter(ParameterSetName='Bundle')][ValidateNotNullOrEmpty()][string]$DeploymentReport,
    [Parameter(ParameterSetName='Bundle')][ValidateNotNullOrEmpty()][string]$DeploymentReportsFile,
    [Parameter(ParameterSetName='Bundle')][ValidateRange(1,120)][int]$WaitForTrackedSeconds,
    [Parameter(ParameterSetName='Bundle')][switch]$AllHeadsets,
    [Parameter(ParameterSetName='Player')][Parameter(ParameterSetName='Refresh')][Parameter(ParameterSetName='Venue')][Parameter(ParameterSetName='Bundle')][Parameter(Mandatory, ParameterSetName='Windows')][Parameter(Mandatory, ParameterSetName='PlayerTracking')][ValidateNotNullOrEmpty()][string]$ManagementApi,
    [Parameter(Mandatory, ParameterSetName='Windows')][ValidateNotNullOrEmpty()][string]$WindowsSeatMap,
    [Parameter(Mandatory, ParameterSetName='Windows')][ValidateNotNullOrEmpty()][string]$WindowsOutputDirectory
)
$ErrorActionPreference = 'Stop'
# Handle ADB exit codes here so both Windows PowerShell and PowerShell report the failing step.
$PSNativeCommandUseErrorActionPreference = $false
. (Join-Path $PSScriptRoot 'quest-adb-process.ps1')

function Confirm-QuestAdbStartup([string]$MissingMessage) {
    if (-not (Test-Path -LiteralPath $AdbPath -PathType Leaf)) { throw $MissingMessage }
    if ($env:OS -eq 'Windows_NT' -and [IO.Path]::GetExtension($AdbPath) -eq '.exe') {
        & (Join-Path $PSScriptRoot 'check-windows-firewall-notifications.ps1') -Executable $AdbPath -Unattended
        if ($LASTEXITCODE -ne 0) { throw 'ADB startup skipped after the Windows Firewall check.' }
    }
}

function Invoke-QuestAdb([string[]]$ArgumentList, [int]$MaximumMilliseconds = 0) {
    if ([IO.Path]::GetExtension($AdbPath) -in '.ps1', '.cmd', '.bat') {
        & $AdbPath @ArgumentList
        return
    }
    $command = if ($ArgumentList[0] -ceq '-t') { $ArgumentList[2] } else { $ArgumentList[0] }
    $operation = if ($command -eq 'shell' -and $ArgumentList[3] -eq 'am' -and $ArgumentList[4] -eq 'start') { 'activity launch' }
        elseif ($command -in 'install', 'devices', 'push', 'pull', 'logcat') { $command }
        else { 'shell command' }
    $timeout = switch ($operation) {
        'install' { 180000 }
        'push' { 30000 }
        'pull' { 30000 }
        'activity launch' { 30000 }
        default { 10000 }
    }
    if ($MaximumMilliseconds -gt 0) { $timeout = [Math]::Min($timeout, $MaximumMilliseconds) }
    $executable = (Resolve-Path -LiteralPath $AdbPath).ProviderPath
    $result = Invoke-QuestAdbProcess $executable $ArgumentList $timeout $operation
    $global:LASTEXITCODE = $result.ExitCode
    return $result.Lines
}

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
    if ($Installed) { $fields += 'questPassthrough','requestMixedReality','recordQuestLinkMetrics' }
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
        foreach ($flag in 'questPassthrough','requestMixedReality','recordQuestLinkMetrics') {
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

function Read-VenueRoomTickets([string]$Path, [int]$RoomId, [Guid]$SessionId, [int]$PlayersPerRoom = 5) {
    try { $file = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).ProviderPath) }
    catch { throw "Room $RoomId needs a readable room connection ZIP." }
    try {
        if ($file.Length -lt 1 -or $file.Length -gt 65536) { throw "Room $RoomId connection ZIP has an invalid size." }
        Read-VenueTicketStream $file $RoomId $SessionId -PlayersPerRoom $PlayersPerRoom
    } finally { $file.Dispose() }
}

function Read-VenueTicketStream([IO.Stream]$InputStream, [int]$RoomId, [Guid]$SessionId, [switch]$ForBundle, [int]$PlayersPerRoom = 5) {
    try { $archive = [IO.Compression.ZipArchive]::new($InputStream, [IO.Compression.ZipArchiveMode]::Read, $true) }
    catch { throw "Room $RoomId needs a valid room connection ZIP." }
    try {
        if ($archive.Entries.Count -ne $PlayersPerRoom) {
            $count = if ($PlayersPerRoom -eq 5) { 'five' } else { $PlayersPerRoom }
            throw "Room $RoomId must contain exactly $count seat connection files."
        }
        foreach ($seat in 1..$PlayersPerRoom) {
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
    if ([string]::IsNullOrWhiteSpace($masterKey)) { throw 'Set VR_COMMAND_MASTER_KEY for the live management check.' }
    return @{ Origin = $uri; Headers = @{ Authorization = 'Bearer ' + $masterKey } }
}

function Confirm-VenueWithManagement([string]$Address, [string]$Topology, [object[]]$Rooms, $PublishedEndpoints, [string]$Mode = 'MR',
    [switch]$RequireLiveSource, [switch]$AllowLoopback) {
    $target = Get-ManagementTarget $Address
    $endpoint = [Uri]::new($target.Origin, "/api/$($Mode.ToLowerInvariant())-deployment/venue-check")
    $checksHeadset = $Mode -cin @('VR','Mixed')
    $requestBody = @{ topology = $Topology; rooms = $Rooms }
    $playersPerRoom = $Rooms[0].connectionFiles.Count
    if ($playersPerRoom -ne 5) { $requestBody.playersPerRoom = $playersPerRoom }
    $expectedSeats = 5 * $playersPerRoom
    if ($RequireLiveSource) { $requestBody.requireLiveSource = $true }
    if ($AllowLoopback -and $Mode -ceq 'VR') { $requestBody.allowLoopback = $true }
    $body = $requestBody | ConvertTo-Json -Compress -Depth 6
    try {
        $response = Invoke-WebRequest -Uri $endpoint -Method Post -ContentType 'application/json' `
            -Headers $target.Headers -Body $body -NoProxy -MaximumRedirection 0 -TimeoutSec 10 -SkipHttpErrorCheck
    } catch { throw 'The live venue check could not reach the management service.' }
    if ($response.StatusCode -in 401,403) { throw 'The management service requires the current Master key for the live venue check.' }
    if ($response.StatusCode -ne 200) { throw 'The management service did not accept the live venue check. Verify the management version and service status.' }
    try { $result = ConvertFrom-Json -InputObject $response.Content }
    catch { throw 'The management service returned an invalid venue check receipt.' }
    if ($result.topology -cne $Topology -or $result.allMatched -isnot [bool] -or
        $result.seats -isnot [array] -or $result.seats.Count -ne $expectedSeats) {
        throw 'The management service returned an invalid venue check receipt.'
    }
    if ($RequireLiveSource -and ($result.liveSourceVerified -isnot [bool] -or $result.liveSourceVerified -ne $result.allMatched)) {
        throw 'The management service did not return a current-source verification receipt.'
    }
    $validStatuses = @('matched', 'session-unavailable', 'seat-unavailable', 'connection-invalid', 'ticket-invalid', 'wrong-seat', 'admission-changed')
    if ($checksHeadset) { $validStatuses += @('endpoint-mismatch', 'venue-unavailable') }
    if ($RequireLiveSource) { $validStatuses += @('source-stale', 'endpoint-mismatch') }
    if ($Mode -cne 'VR') { $validStatuses += @('alignment-not-locked', 'connection-hash-mismatch', 'alignment-invalid', 'alignment-wrong-room', 'alignment-hash-mismatch') }
    $failures = for ($i = 0; $i -lt $expectedSeats; $i++) {
        $room = [int][Math]::Floor($i / $playersPerRoom) + 1
        $seat = $i % $playersPerRoom
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
    if ($RequireLiveSource) { return }
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

function Read-VenueBundle([string]$Path, [int]$SelectedRoom, [int]$SelectedSeat, [switch]$Fingerprint) {
    try { $file = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).ProviderPath) }
    catch { throw 'Use a readable five-room deployment ZIP from the management console.' }
    try {
        if ($file.Length -lt 1 -or $file.Length -gt 512KB) { throw 'The five-room deployment ZIP has an invalid size.' }
        if ($Fingerprint) {
            $bundleHash = (Get-FileHash -InputStream $file -Algorithm SHA256).Hash.ToLowerInvariant()
            $file.Position = 0
        }
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
            $venue = Read-Venue $manifest '' $entries $SelectedRoom $SelectedSeat
            if ($Fingerprint) { $venue.BundleSha256 = $bundleHash }
            return $venue
        } finally { $archive.Dispose() }
    } finally { $file.Dispose() }
}

function Read-Venue($Manifest, [string]$Directory, $BundleEntries, [int]$SelectedRoom, [int]$SelectedSeat) {
    $isVr = $BundleEntries -and $manifest.mode -ceq 'VR'
    $isMixed = $BundleEntries -and $manifest.mode -ceq 'Mixed'
    $manifestFields = @('version','topology','rooms')
    if ($isVr -or $isMixed) { $manifestFields += 'mode' }
    $playersPerRoom = 5
    if ($manifest.PSObject.Properties['playersPerRoom']) {
        if (-not (Test-JsonInteger $manifest.playersPerRoom) -or $manifest.playersPerRoom -notin 1,2,5) {
            throw 'Venue bundles require 1, 2 or 5 seats per room.'
        }
        $playersPerRoom = [int]$manifest.playersPerRoom
        $manifestFields += 'playersPerRoom'
    }
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
                $room.seats -isnot [array] -or $room.seats.Count -ne $playersPerRoom -or
                @($room.PSObject.Properties.Name | Where-Object { $_ -cnotin @('roomId','sessionId','ticketsZip','address','port','seats') }).Count -gt 0) {
                throw 'Provide the original VR venue room endpoints and seats.'
            }
            for ($i = 0; $i -lt $playersPerRoom; $i++) {
                $listed = $room.seats[$i]
                if (-not (Test-JsonInteger $listed.seat) -or $listed.seat -ne ($i + 1) -or
                    $listed.name -isnot [string] -or [string]::IsNullOrWhiteSpace($listed.name) -or
                    @($listed.PSObject.Properties.Name | Where-Object { $_ -cnotin @('seat','name') }).Count -gt 0) {
                    throw "Room $($room.roomId) needs the original named VR seats."
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
            try { $tickets = @(Read-VenueTicketStream $inner $id $session -ForBundle -PlayersPerRoom $playersPerRoom) }
            finally { $inner.Dispose() }
        } else {
            $alignment = Read-RoomAlignment (Get-VenueInputPath $directory $room.alignmentFile) $id
            $tickets = @(Read-VenueRoomTickets (Get-VenueInputPath $directory $room.ticketsZip) $id $session $playersPerRoom)
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
    if ($playersPerRoom -ne 5) { $report.playersPerRoom = $playersPerRoom }
    if ($SelectedRoom -and -not $connections.ContainsKey("$SelectedRoom/$SelectedSeat")) {
        throw "Room $SelectedRoom seat $SelectedSeat is outside the original venue bundle."
    }
    return @{ Report = $report; Selected = $connections["$SelectedRoom/$SelectedSeat"]; Connections = $connections;
        EarliestExpiry = $earliest; LiveRooms = $liveRooms.ToArray(); PublishedEndpoints = $publishedEndpoints; SeatHeadsets = @{};
        SessionIds = @($sessions | ForEach-Object { $_.ToString('D') } | Sort-Object) }
}

function Confirm-VenueReadback($Venue, [switch]$RequireLiveSource, [switch]$AllowLoopback) {
    if ($ManagementApi) {
        if ($Venue.Report.mode -cin @('VR','Mixed')) {
            $seats = @(Confirm-VenueWithManagement $ManagementApi $Venue.Report.topology $Venue.LiveRooms $Venue.PublishedEndpoints `
                -Mode $Venue.Report.mode -RequireLiveSource:$RequireLiveSource -AllowLoopback:$AllowLoopback)
            foreach ($row in $seats) { $Venue.SeatHeadsets["$($row.roomId)/$($row.seat + 1)"] = $row.headset }
            $Venue.Report.quest3Seats = @($seats | Where-Object headset -CEQ 'Quest3').Count
        } else {
            if (-not $Venue.Report.alignmentPinsVerified) { throw 'The live venue check requires all 25 connection files to carry locked MR alignment hashes.' }
            Confirm-VenueWithManagement $ManagementApi $Venue.Report.topology $Venue.LiveRooms $Venue.PublishedEndpoints `
                -RequireLiveSource:$RequireLiveSource
        }
        $Venue.Report.managementVerified = $true
    }
    if ($Venue.EarliestExpiry -le [DateTimeOffset]::UtcNow) {
        throw 'A player ticket expired during venue preflight. Download fresh room connection ZIPs.'
    }
}

function Confirm-WindowsVenueSeats($Venue, $Seats) {
    Confirm-VenueReadback $Venue -RequireLiveSource -AllowLoopback
    foreach ($row in $Seats) {
        if ($Venue.SeatHeadsets["$($row.roomId)/$($row.seat)"] -cne 'ViveXr') {
            throw "Room $($row.roomId) seat $($row.seat) is not assigned to VIVE XR."
        }
    }
}

function Export-WindowsVenueSeats {
    $map = (Read-DeploymentJson $WindowsSeatMap 16384 'Windows seat map').Document
    if (-not (Test-JsonInteger $map.version) -or $map.version -ne 1 -or $map.seats -isnot [array] -or
        $map.seats.Count -lt 1 -or $map.seats.Count -gt 25 -or
        @($map.PSObject.Properties.Name | Where-Object { $_ -cnotin @('version','seats') }).Count) {
        throw 'Use a version 1 Windows seat map with 1 to 25 seats.'
    }
    $seats = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $stations = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($row in $map.seats) {
        if (-not (Test-JsonInteger $row.roomId) -or $row.roomId -notin 1..5 -or
            -not (Test-JsonInteger $row.seat) -or $row.seat -notin 1..5 -or
            $row.station -isnot [string] -or $row.station -cnotmatch '\A[A-Za-z0-9][A-Za-z0-9-]{0,31}\z' -or
            @($row.PSObject.Properties.Name | Where-Object { $_ -cnotin @('roomId','seat','station') }).Count) {
            throw 'Each Windows seat needs roomId, seat and a station label of up to 32 ASCII letters, digits or hyphens.'
        }
        if (-not $seats.Add("$($row.roomId)/$($row.seat)") -or -not $stations.Add($row.station)) {
            throw 'Each Windows seat and station must appear only once.'
        }
    }

    $provider = $null
    $drive = $null
    $output = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($WindowsOutputDirectory, [ref]$provider, [ref]$drive)
    if ($provider.Name -ne 'FileSystem') { throw 'Use a filesystem path for the Windows output directory.' }
    $output = [IO.Path]::TrimEndingDirectorySeparator($output)
    $parent = [IO.Path]::GetDirectoryName($output)
    if (-not $parent -or -not [IO.Directory]::Exists($parent) -or (Test-Path -LiteralPath $output)) {
        throw 'Use a new Windows output directory inside an existing private directory.'
    }
    $venue = Read-VenueBundle $VenueBundle 0 0
    if ($venue.Report.mode -cnotin @('VR','Mixed')) { throw 'Windows staging requires an original VR or mixed venue bundle.' }
    foreach ($row in $map.seats) {
        $connection = $venue.Connections["$($row.roomId)/$($row.seat)"]
        if (-not $connection) { throw "Room $($row.roomId) seat $($row.seat) is outside the original venue bundle." }
        if ($connection.Alignment) {
            throw "Room $($row.roomId) seat $($row.seat) belongs to an MR room."
        }
    }
    Confirm-WindowsVenueSeats $venue $map.seats
    $selected = foreach ($row in ($map.seats | Sort-Object roomId, seat)) {
        $key = "$($row.roomId)/$($row.seat)"
        $ticket = $venue.Connections[$key].Ticket
        [pscustomobject]@{ RoomId = $row.roomId; Seat = $row.seat; Station = $row.station; Ticket = $ticket
            File = 'pc-{0}-room-{1:00}-seat-{2:00}.json' -f $row.station,$row.roomId,$row.seat }
    }

    $staging = Join-Path $parent ('.vr-windows-' + [Guid]::NewGuid().ToString('N'))
    $null = [IO.Directory]::CreateDirectory($staging)
    try {
        foreach ($row in $selected) {
            [IO.File]::WriteAllBytes((Join-Path $staging $row.File), $row.Ticket.Bytes)
        }
        Confirm-WindowsVenueSeats $venue $map.seats
        [IO.Directory]::Move($staging, $output)
    } finally {
        if ([IO.Directory]::Exists($staging)) {
            foreach ($row in $selected) { [IO.File]::Delete((Join-Path $staging $row.File)) }
            [IO.Directory]::Delete($staging)
        }
    }
    [ordered]@{ version = 1; topology = $venue.Report.topology; managementVerified = $true; liveSourceVerified = $true; seats = @(
        foreach ($row in $selected) {
            [ordered]@{ roomId = $row.RoomId; seat = $row.Seat; station = $row.Station; file = $row.File
                endpoint = $row.Ticket.Endpoint; expiresAtUtc = $row.Ticket.ExpiresAtUtc.ToString('o') }
        }
    ) } | ConvertTo-Json -Depth 4 -Compress
}

function Read-QuestVenueMap($Venue, [string]$Path, [switch]$Partial) {
    $map = (Read-DeploymentJson $Path 16384 'device map').Document
    $count = if ($Venue) { $Venue.Report.seats } else { 25 }
    $minimum = if ($Partial) { 1 } else { $count }
    if (-not (Test-JsonInteger $map.version) -or $map.version -ne 1 -or $map.seats -isnot [array] -or
        $map.seats.Count -lt $minimum -or $map.seats.Count -gt $count -or
        @($map.PSObject.Properties.Name | Where-Object { $_ -cnotin @('version','seats') }).Count) {
        if ($Partial) { throw "Use a version 1 device map with 1 to $count seats." }
        throw "Use a version 1 device map with exactly $count seats."
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
        if ($Venue -and -not $Venue.Connections.ContainsKey("$($row.roomId)/$($row.seat)")) {
            throw "Room $($row.roomId) seat $($row.seat) is outside the original venue bundle."
        }
    }
    $map.seats | Sort-Object roomId, seat
}

function Read-ManagementJson($Target, [Uri]$Url, [int]$RequestMilliseconds, [string]$Body, [string]$AdmissionId) {
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.UseProxy = $handler.AllowAutoRedirect = $false
    $client = [Net.Http.HttpClient]::new($handler)
    $client.MaxResponseContentBufferSize = 256KB
    $cancellation = [Threading.CancellationTokenSource]::new($RequestMilliseconds)
    $content = $null
    $response = $null
    $timer = [Diagnostics.Stopwatch]::StartNew()
    try {
        $client.DefaultRequestHeaders.Add('Authorization', $Target.Headers.Authorization)
        if ($AdmissionId) { $client.DefaultRequestHeaders.Add('If-Match-Admission', $AdmissionId) }
        if ($Body) {
            $content = [Net.Http.StringContent]::new($Body, [Text.Encoding]::UTF8, 'application/json')
            $response = $client.PostAsync($Url, $content, $cancellation.Token).GetAwaiter().GetResult()
            if ($response.StatusCode -eq 409) { return @{ Status = 'management-conflict' } }
        } else {
            $response = $client.GetAsync($Url, $cancellation.Token).GetAwaiter().GetResult()
        }
        if ($response.StatusCode -in 401,403) { return @{ Status = 'readiness-access-denied' } }
        if ($response.StatusCode -ne 200) { return @{ Status = 'readiness-unavailable' } }
        $raw = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    } catch { return @{ Status = 'readiness-unavailable' } }
    finally {
        if ($response) { $response.Dispose() }
        if ($content) { $content.Dispose() }
        $cancellation.Dispose(); $client.Dispose()
    }
    try { return @{ Document = ConvertFrom-Json -InputObject $raw; Elapsed = $timer.Elapsed.TotalMilliseconds } }
    catch { return @{ Status = 'readiness-invalid' } }
}

function New-QuestPlayerReadback($Target, $ConnectionFile, $Ticket, $Alignment) {
    $body = @{ connectionFile = [Convert]::ToBase64String($ConnectionFile.Bytes) }
    if ($Alignment) { $body.alignmentFile = [Convert]::ToBase64String($Alignment.Bytes) }
    return @{ Target = $Target; Body = $body | ConvertTo-Json -Compress; Ticket = $Ticket
        Address = $ConnectionFile.Document.address; Port = $ConnectionFile.Document.port }
}

function Confirm-QuestPlayerReadback($LiveSeat) {
    $ticket = $LiveSeat.Ticket
    $path = "/api/sessions/$($ticket.SessionId)/rooms/$($ticket.RoomId)/players/$($ticket.PlayerId)/quest-deployment-check"
    $url = [Uri]::new($LiveSeat.Target.Origin, $path)
    $reading = Read-ManagementJson $LiveSeat.Target $url 10000 $LiveSeat.Body ($ticket.AdmissionId.ToString('D'))
    if ($reading.Status -ceq 'management-conflict') { throw 'Quest deployment refused because the session or admission changed.' }
    if ($reading.Status) { throw 'Could not verify the Quest seat with the management service.' }
    $receipt = $reading.Document
    if (-not (Test-JsonInteger $receipt.roomId) -or $receipt.roomId -ne $ticket.RoomId -or
        -not (Test-JsonInteger $receipt.seat) -or $receipt.seat -ne $ticket.Seat -or $receipt.status -isnot [string]) {
        throw 'The management service returned an invalid Quest deployment receipt.'
    }
    if ($receipt.status -cin @('headset-mismatch','mode-mismatch','endpoint-unpublished','source-stale','endpoint-mismatch',
        'connection-invalid','ticket-invalid','wrong-seat','admission-changed','alignment-not-locked','connection-hash-mismatch',
        'alignment-invalid','alignment-wrong-room','alignment-hash-mismatch')) {
        throw "Quest deployment refused: $($receipt.status)."
    }
    try { $expiry = [DateTimeOffset]$receipt.expiresAtUtc }
    catch { throw 'The management service returned an invalid Quest deployment receipt.' }
    if ($receipt.status -cne 'matched' -or $receipt.address -isnot [string] -or $receipt.address -cne $LiveSeat.Address -or
        -not (Test-JsonInteger $receipt.port) -or $receipt.port -ne $LiveSeat.Port -or $expiry -ne $ticket.ExpiresAtUtc -or
        $expiry -le [DateTimeOffset]::UtcNow) {
        throw 'The management service returned an invalid Quest deployment receipt.'
    }
}

function Test-TrackedReadinessSnapshot($Snapshot, [int]$MaxAge) {
    return (Test-JsonInteger $Snapshot.version) -and $Snapshot.version -eq 1 -and
        $Snapshot.sessionId -is [string] -and $Snapshot.sampledAtUtc -and
        $Snapshot.players -is [array] -and $Snapshot.players.Count -le 25 -and
        $Snapshot.sourceState -is [string] -and
        $Snapshot.sourceState -cin @('Fresh','Ended','NoRecording','WaitingFrame','UnknownCaptureTime','ClockSkew','Stale','Suspended','PhasePending') -and
        (Test-JsonInteger $Snapshot.worldSequence) -and $Snapshot.worldSequence -ge 0 -and
        (Test-JsonInteger $Snapshot.sessionSequence) -and $Snapshot.sessionSequence -ge 1 -and
        (Test-JsonInteger $Snapshot.observedSequence) -and $Snapshot.observedSequence -ge 0 -and
        ($Snapshot.sourceState -cne 'Fresh' -or (((Test-JsonInteger $Snapshot.sourceAgeMilliseconds) -or
            $Snapshot.sourceAgeMilliseconds -is [double]) -and [double]::IsFinite($Snapshot.sourceAgeMilliseconds) -and
            $Snapshot.sourceAgeMilliseconds -ge -1000 -and $Snapshot.sourceAgeMilliseconds -le $MaxAge))
}

function Read-VenueTrackedReadiness($Target, $Venue, [int]$RequestMilliseconds) {
    $url = [Uri]::new($Target.Origin, '/api/venue/tracked-readiness')
    $rooms = @($Venue.LiveRooms | ForEach-Object { @{ roomId = $_.roomId; sessionId = $_.sessionId } })
    $ids = @($rooms.sessionId | Sort-Object -Unique)
    $body = @{ topology = $Venue.Report.topology; rooms = $rooms } | ConvertTo-Json -Compress -Depth 3
    $response = Read-ManagementJson $Target $url $RequestMilliseconds $body
    if ($response.Status -ceq 'management-conflict') { return @{ Status = 'venue-changed' } }
    if ($response.Status) { return $response }
    $batch = $response.Document
    if (-not (Test-JsonInteger $batch.version) -or $batch.version -ne 1 -or $batch.topology -cne $Venue.Report.topology -or
        -not $batch.sampledAtUtc -or -not (Test-JsonInteger $batch.maxSourceAgeMilliseconds) -or $batch.maxSourceAgeMilliseconds -ne 1500 -or
        $batch.sessions -isnot [array] -or $batch.sessions.Count -ne $ids.Count) {
        return @{ Status = 'readiness-invalid' }
    }
    $readings = @{}
    foreach ($snapshot in $batch.sessions) {
        if (-not (Test-TrackedReadinessSnapshot $snapshot $batch.maxSourceAgeMilliseconds) -or $snapshot.sessionId -cnotin $ids -or
            $readings.ContainsKey($snapshot.sessionId) -or $snapshot.sampledAtUtc -cne $batch.sampledAtUtc) {
            return @{ Status = 'readiness-invalid' }
        }
        $readings[$snapshot.sessionId] = $snapshot
    }
    return @{ Sessions = $readings; SampledAtUtc = $batch.sampledAtUtc; MaxAge = $batch.maxSourceAgeMilliseconds;
        Elapsed = $response.Elapsed }
}

function Get-TrackedSeatStatus($Batch, $Snapshot, $Ticket, [bool]$RequiresMr) {
    if ($Batch.Status) { return $Batch.Status }
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
    if ($snapshot.sourceAgeMilliseconds + $Batch.Elapsed -gt $Batch.MaxAge) { return 'source-expired-in-transit' }
    if ($snapshot.origin -cnotin @('Simulation','GameServer') -or $snapshot.worldSequence -eq 0 -or
        $snapshot.observedSequence -ne $snapshot.sessionSequence) { return 'source-revision-pending' }
    if ($RequiresMr -and ($snapshot.origin -cne 'GameServer' -or
        @($snapshot.mrStartState, $snapshot.mrResumeState, $snapshot.mrTrackingState).Where({ $_ -cin @('Ready','WaitingPlayers') }).Count -eq 0)) {
        return 'mr-profile-pending'
    }
    if ($player.state -cne 'Participating' -or -not $player.canParticipate) { return 'awaiting-tracked-pose' }
    if ($player.rigKind -cne 'Tracked') { return 'not-tracked' }
    return 'tracked-ready'
}

function New-TrackedSeatReport($Venue, [object[]]$Map, $Batch, [switch]$IncludeAllHeadsets) {
    $hasHeadsets = $Venue.Report.mode -cin @('VR','Mixed')
    $seats = @(foreach ($row in $Map) {
        $key = "$($row.roomId)/$($row.seat)"
        $headset = if ($hasHeadsets) { $Venue.SeatHeadsets[$key] } else { 'Quest3' }
        if (-not $IncludeAllHeadsets -and $headset -cne 'Quest3') {
            if ($DeviceMap) { [ordered]@{ roomId = $row.roomId; seat = $row.seat; status = 'seat-headset-mismatch' } }
            continue
        }
        $connection = $Venue.Connections[$key]
        $snapshot = if ($batch.Sessions) { $batch.Sessions[$connection.Ticket.SessionId.ToString('D')] }
        $result = [ordered]@{ roomId = $row.roomId; seat = $row.seat; status = Get-TrackedSeatStatus $batch $snapshot $connection.Ticket ([bool]$connection.Alignment);
            sourceState = $snapshot.sourceState; worldSequence = $snapshot.worldSequence }
        if ($IncludeAllHeadsets) { $result.registeredHeadset = $headset }
        if ($DeploymentReport -or $DeploymentReportsFile) {
            $result.sessionId = $connection.Ticket.SessionId.ToString('D')
            $result.observedSequence = $snapshot.observedSequence
            $result.capturedAtUtc = $snapshot.capturedAtUtc
            if ($result.status -ceq 'tracked-ready' -and ($snapshot.origin -cne 'GameServer' -or -not $snapshot.capturedAtUtc)) {
                $result.status = 'source-capture-unverified'
            }
        }
        $result
    })
    $report = [ordered]@{ phase = 'tracked-readiness'; topology = $Venue.Report.topology; managementVerified = $true;
        complete = ($seats.Count -gt 0 -and -not ($seats | Where-Object { $_.status -cne 'tracked-ready' })); seats = $seats }
    if ($batch.SampledAtUtc) { $report.sampledAtUtc = $batch.SampledAtUtc }
    if ($IncludeAllHeadsets) { $report.scope = 'venue' }
    return $report
}

function Confirm-PreparingReadinessFrames($Target, $Report, [hashtable]$PlayersBySeat, [int]$RequestMilliseconds) {
    $handler = [Net.Http.HttpClientHandler]::new()
    $handler.UseProxy = $handler.AllowAutoRedirect = $false
    $client = [Net.Http.HttpClient]::new($handler)
    $client.MaxResponseContentBufferSize = 256KB
    $cancellation = [Threading.CancellationTokenSource]::new()
    if ($RequestMilliseconds -gt 0) { $cancellation.CancelAfter($RequestMilliseconds) }
    else { $cancellation.Cancel() }
    try {
        $client.DefaultRequestHeaders.Add('Authorization', $Target.Headers.Authorization)
        foreach ($session in ($Report.seats | Group-Object { $_.sessionId })) {
            $sample = $session.Group[0]
            $url = [Uri]::new($Target.Origin, "/api/sessions/$($sample.sessionId)/world/frames/$($sample.worldSequence)")
            $status = 'source-frame-unverified'
            $players = $null
            $response = $null
            try {
                $response = $client.GetAsync($url, $cancellation.Token).GetAwaiter().GetResult()
                if ($response.StatusCode -eq 200) {
                    $stored = ConvertFrom-Json -InputObject ($response.Content.ReadAsStringAsync().GetAwaiter().GetResult())
                    $packet = $stored.packet
                    if ((Test-JsonInteger $packet.sequence) -and $packet.sequence -eq $sample.worldSequence -and
                        (Test-JsonInteger $packet.observedSequence) -and $packet.observedSequence -eq $sample.observedSequence -and
                        $packet.suspended -is [bool] -and -not $packet.suspended -and $packet.frame.phase -is [string] -and
                        (Test-JsonInteger $packet.frame.tick)) {
                        if ($packet.frame.phase -ceq 'Preparing' -and $packet.frame.tick -eq 0 -and
                            $packet.frame.players -is [array] -and $packet.frame.players.Count -le 25) {
                            $players = $packet.frame.players
                            $status = 'tracked-ready'
                        }
                        elseif ($packet.frame.phase -cin @('Running','Paused','Ended')) { $status = 'source-outside-preparing' }
                    }
                }
            } catch { $status = 'source-frame-unverified' }
            finally { if ($response) { $response.Dispose() } }
            if ($status -cne 'tracked-ready') {
                $session.Group | ForEach-Object { $_.status = $status }
                $Report.complete = $false
                continue
            }
            foreach ($seat in $session.Group) {
                $playerId = $PlayersBySeat["$($seat.roomId)/$($seat.seat)"]
                $matches = @($players | Where-Object { $_.id -is [string] -and $_.id -ceq $playerId })
                $player = $matches | Select-Object -First 1
                if ($matches.Count -ne 1 -or -not (Test-JsonInteger $player.roomId) -or $player.roomId -ne $seat.roomId -or
                    $player.connected -isnot [bool] -or -not $player.connected -or -not (Test-JsonInteger $player.health) -or
                    $player.health -lt 1 -or $player.health -gt 100 -or $player.rig.kind -isnot [string] -or $player.rig.kind -cne 'Tracked') {
                    $seat.status = 'source-seat-unverified'
                    $Report.complete = $false
                }
            }
        }
    } finally { $cancellation.Dispose(); $client.Dispose() }
}

function Confirm-PlayerTrackedSeat($Target, $Ticket) {
    $sessionId = $Ticket.SessionId.ToString('D')
    $url = [Uri]::new($Target.Origin, "/api/sessions/$sessionId/readiness")
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $reading = Read-ManagementJson $Target $url 10000
    $snapshot = $reading.Document
    $sample = @{ Status = $reading.Status; Elapsed = $reading.Elapsed; MaxAge = 1500 }
    if (-not $sample.Status -and (-not (Test-TrackedReadinessSnapshot $snapshot $sample.MaxAge) -or $snapshot.sessionId -cne $sessionId)) {
        $sample.Status = 'readiness-invalid'
        $snapshot = $null
    }
    $status = Get-TrackedSeatStatus $sample $snapshot $Ticket ([bool]$Ticket.AlignmentHash)
    if ($status -ceq 'tracked-ready' -and ($snapshot.origin -cne 'GameServer' -or -not $snapshot.capturedAtUtc)) {
        $status = 'source-capture-unverified'
    }
    $seat = [ordered]@{ sessionId = $sessionId; roomId = $Ticket.RoomId; seat = $Ticket.Seat + 1; status = $status
        sourceState = $snapshot.sourceState; worldSequence = $snapshot.worldSequence; observedSequence = $snapshot.observedSequence
        capturedAtUtc = $snapshot.capturedAtUtc }
    $report = [ordered]@{ phase = 'tracked-readiness'; scope = 'player'; complete = $status -ceq 'tracked-ready'
        sampledAtUtc = $snapshot.sampledAtUtc; seats = @($seat) }
    if ($report.complete) {
        $playersBySeat = @{ "$($seat.roomId)/$($seat.seat)" = $Ticket.PlayerId.ToString('D') }
        Confirm-PreparingReadinessFrames $Target $report $playersBySeat ([int][Math]::Floor(10000 - $timer.Elapsed.TotalMilliseconds))
    }
    if ($Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) {
        $seat.status = 'ticket-expired'
        $report.complete = $false
    }
    if ($report.complete) {
        $admission = "quest-player-readiness-v1/$sessionId/$($Ticket.PlayerId.ToString('D'))/$($Ticket.AdmissionId.ToString('D'))"
        $seat.admissionSha256 = Get-QuestSha256 ([Text.Encoding]::UTF8.GetBytes($admission))
        $report.evidenceVersion = 1
    }
    return $report
}

function Read-TrackedSeatReport($Target, $Venue, [object[]]$Map, [int]$RequestMilliseconds, [switch]$IncludeAllHeadsets) {
    $timer = [Diagnostics.Stopwatch]::StartNew()
    $batch = Read-VenueTrackedReadiness $Target $Venue $RequestMilliseconds
    $report = New-TrackedSeatReport $Venue $Map $batch -IncludeAllHeadsets:$IncludeAllHeadsets
    if (($DeploymentReport -or $DeploymentReportsFile) -and $report.complete) {
        $playersBySeat = @{}
        foreach ($seat in $report.seats) {
            $key = "$($seat.roomId)/$($seat.seat)"
            $playersBySeat[$key] = $Venue.Connections[$key].Ticket.PlayerId.ToString('D')
        }
        $remaining = [int][Math]::Floor($RequestMilliseconds - $timer.Elapsed.TotalMilliseconds)
        Confirm-PreparingReadinessFrames $Target $report $playersBySeat $remaining
    }
    return $report
}

function Confirm-TrackedSeats($Venue, [object[]]$Map, [switch]$IncludeAllHeadsets) {
    Confirm-VenueReadback $Venue
    $target = Get-ManagementTarget $ManagementApi
    if (-not $WaitForTrackedSeconds) {
        return Read-TrackedSeatReport $target $Venue $Map 10000 -IncludeAllHeadsets:$IncludeAllHeadsets
    }

    $timer = [Diagnostics.Stopwatch]::StartNew()
    $limit = 1000 * $WaitForTrackedSeconds
    $samples = 0
    $terminal = @('venue-changed','seat-unavailable','admission-changed','seat-headset-mismatch','readiness-invalid','readiness-access-denied',
        'source-capture-unverified','source-outside-preparing')
    $report = $null
    do {
        $ticketMilliseconds = ($Venue.EarliestExpiry - [DateTimeOffset]::UtcNow).TotalMilliseconds
        $remaining = $limit - $timer.Elapsed.TotalMilliseconds
        if ($ticketMilliseconds -lt 1) {
            $report = New-TrackedSeatReport $Venue $Map @{ Status = 'ticket-expired' } -IncludeAllHeadsets:$IncludeAllHeadsets
            $outcome = 'ticket-expired'; break
        }
        if ($remaining -lt 1) { $outcome = 'timed-out'; break }
        $timeout = [int][Math]::Floor([Math]::Min(10000, [Math]::Min($remaining, $ticketMilliseconds)))
        $sample = Read-TrackedSeatReport $target $Venue $Map $timeout -IncludeAllHeadsets:$IncludeAllHeadsets
        $samples++
        if ($Venue.EarliestExpiry -le [DateTimeOffset]::UtcNow) {
            $report = New-TrackedSeatReport $Venue $Map @{ Status = 'ticket-expired' } -IncludeAllHeadsets:$IncludeAllHeadsets
            $outcome = 'ticket-expired'; break
        }
        if ($timer.Elapsed.TotalMilliseconds -ge $limit) { $outcome = 'timed-out'; break }
        $report = $sample
        if ($report.complete) { $outcome = 'ready'; break }
        if (-not $report.seats.Count) { $outcome = 'no-selected-seats'; break }
        $invalid = $report.seats | Where-Object { $_.status -cin $terminal } | Select-Object -First 1
        if ($invalid) { $outcome = $invalid.status; break }
        $remaining = [Math]::Min($limit - $timer.Elapsed.TotalMilliseconds, ($Venue.EarliestExpiry - [DateTimeOffset]::UtcNow).TotalMilliseconds)
        if ($remaining -ge 1) { Start-Sleep -Milliseconds ([int][Math]::Floor([Math]::Min(1000, $remaining))) }
    } while ($true)
    if (-not $report) {
        $report = New-TrackedSeatReport $Venue $Map @{ Status = 'readiness-unavailable' } -IncludeAllHeadsets:$IncludeAllHeadsets
    }
    $report.wait = [ordered]@{ maximumSeconds = $WaitForTrackedSeconds; samples = $samples; outcome = $outcome }
    return $report
}

function Get-QuestDeviceInventory {
    $lines = @(Invoke-QuestAdb @('devices', '-l'))
    if ($LASTEXITCODE -ne 0) { throw 'Could not list authorized Android devices.' }
    $inventory = [Collections.Generic.Dictionary[string,object]]::new([StringComparer]::Ordinal)
    $seenTransports = [Collections.Generic.HashSet[long]]::new()
    $duplicateTransports = [Collections.Generic.HashSet[long]]::new()
    foreach ($line in $lines) {
        if ($line -ceq 'List of devices attached' -or $line -cnotmatch '\A(\S+)[ \t]+(\S+)(?:[ \t]+(.*))?\z') { continue }
        $key = $Matches[1]; $status = $Matches[2]
        $transportId = 0L
        $fields = @($Matches[3] -csplit '[ \t]+' | Where-Object { $_ -clike 'transport_id:*' })
        if ($fields.Count -eq 1 -and $fields[0] -cmatch '\Atransport_id:([1-9][0-9]{0,18})\z' -and
            [long]::TryParse($Matches[1], [ref]$transportId)) {
            if (-not $seenTransports.Add($transportId)) { [void]$duplicateTransports.Add($transportId) }
        } elseif ($status -ceq 'device') { $status = 'transport-unavailable' }
        if ($inventory.ContainsKey($key)) { $status = 'ambiguous' }
        $inventory[$key] = @{ Status = $status; TransportId = $transportId }
    }
    foreach ($device in $inventory.Values) {
        if ($device.Status -ceq 'device' -and $duplicateTransports.Contains($device.TransportId)) { $device.Status = 'transport-ambiguous' }
    }
    return ,$inventory
}

function Get-SingleQuestTarget([string]$RequestedSerial) {
    if ($RequestedSerial -and $RequestedSerial -cnotmatch '\A[A-Za-z0-9\[][A-Za-z0-9._:%\[\]-]{0,127}\z') {
        throw 'Use an explicit ADB serial for the Quest 3.'
    }
    Confirm-QuestAdbStartup 'Provide the installed ADB executable.'
    $inventory = Get-QuestDeviceInventory
    if (-not $RequestedSerial) {
        $available = @($inventory.GetEnumerator() | Where-Object {
            $_.Value.Status -cin @('device', 'ambiguous', 'transport-unavailable', 'transport-ambiguous')
        })
        if ($available.Count -ne 1) {
            throw 'Connect and authorize one Quest 3, or specify -Serial explicitly. On Windows, check USB and ADB with scripts/check-quest-usb.ps1.'
        }
        $RequestedSerial = $available[0].Key
    }
    $device = $inventory[$RequestedSerial]
    if ($device.Status -cne 'device') {
        $status = if ($device.Status -cin @('unauthorized', 'offline', 'ambiguous', 'transport-unavailable', 'transport-ambiguous')) {
            $device.Status
        } else { 'missing or unavailable' }
        throw "Quest 3 ADB state: $status. On Windows, use scripts/check-quest-usb.ps1 to distinguish USB enumeration from ADB authorization."
    }
    # Keep using this transport even if the same serial becomes visible on a new connection.
    return @('-t', [string]$device.TransportId)
}

function Read-QuestRelease([string]$Path) {
    $original = Read-DeploymentJson $Path 8192 'venue release report'
    $report = $original.Document
    $quest = $report.quest
    if ($report.verified -isnot [bool] -or -not $report.verified -or
        $report.scope -isnot [string] -or $report.scope -cne 'offline-package-consistency' -or
        $quest.applicationId -isnot [string] -or $quest.applicationId -cne 'com.vrcommand.quest' -or
        $quest.architecture -isnot [string] -or $quest.architecture -cne 'arm64-v8a' -or
        $quest.signatureV2 -isnot [bool] -or -not $quest.signatureV2 -or
        -not (Test-JsonInteger $quest.versionCode) -or $quest.versionCode -lt 1 -or $quest.versionCode -gt [int]::MaxValue -or
        $quest.sha256 -isnot [string] -or $quest.sha256 -cnotmatch '\A[0-9a-f]{64}\z') {
        throw 'Use the successful offline venue release report for the original Quest APK.'
    }
    if ($RecordLinkMetrics -and $quest.versionCode -lt 75) { throw 'Quest link metrics require an APK with version code 75 or later.' }
    if ($RequireOpenXR -and $quest.versionCode -lt 74) { throw 'The OpenXR check requires a Quest APK with version code 74 or later.' }
    return @{ versionCode = $quest.versionCode; sha256 = $quest.sha256; reportSha256 = Get-QuestSha256 $original.Bytes }
}

function Get-QuestApkStatus([string[]]$Target, [string]$ExpectedHash) {
    $paths = @(Invoke-QuestAdb ($Target + @('shell', 'pm', 'path', '--user', 'current', 'com.vrcommand.quest')) 2>$null)
    # A release is one standalone APK. Never pass an unexpected path to the remote shell.
    if ($LASTEXITCODE -ne 0 -or $paths.Count -ne 1 -or $paths[0] -cnotmatch '\Apackage:((?:/[A-Za-z0-9._=+~-]+)+/base\.apk)\z') {
        return 'apk-unverified'
    }
    $hash = Read-QuestFileHash $Target $Matches[1]
    if (-not $hash) { return 'apk-unverified' }
    if ($hash -cne $ExpectedHash) { return 'apk-hash-mismatch' }
    return 'ready'
}

function Confirm-LocalQuestApk([string]$Path, [string]$ExpectedHash) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw 'Choose the original Quest APK for this release.' }
    if ((Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $ExpectedHash) {
        throw 'Local Quest APK SHA-256 differs from the release report.'
    }
}

function New-VerifiedQuestApk([string]$Path, [string]$ExpectedHash) {
    $stagePath = Join-Path ([IO.Path]::GetTempPath()) ('vr-command-' + [Guid]::NewGuid().ToString('N') + '.apk')
    $source = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).ProviderPath)
    try {
        $destination = [IO.File]::Open($stagePath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            try { $source.CopyTo($destination) }
            finally { $destination.Dispose() }
            Confirm-LocalQuestApk $stagePath $ExpectedHash
        } catch {
            Remove-Item -LiteralPath $stagePath -ErrorAction SilentlyContinue
            throw
        }
    } finally { $source.Dispose() }
    return $stagePath
}

function Install-QuestReleaseApk([string[]]$Target, [string]$Path) {
    $output = @(Invoke-QuestAdb ($Target + @('install', '-R', '--user', 'current', '--pkg', 'com.vrcommand.quest', $Path)) 2>$null)
    if ($LASTEXITCODE -ne 0 -or $output -cnotcontains 'Success') { throw 'Quest APK installation did not return Success.' }
}

function Get-MappedQuestStatus($Row, $Inventory, [int]$VersionCode, [string]$ExpectedHash, [switch]$AllowMissingApk) {
    $result = [ordered]@{ roomId = $Row.roomId; seat = $Row.seat; status = 'ready' }
    $connected = $Inventory[$Row.serial]
    $status = $connected.Status
    if ($status -cne 'device') {
        $result.status = if (-not $status) { 'missing' }
            elseif ($status -cin @('unauthorized','offline','ambiguous','transport-unavailable','transport-ambiguous')) { $status }
            else { 'unavailable' }
        return $result
    }
    $target = @('-t', [string]$connected.TransportId)
    $model = Invoke-QuestAdb ($target + @('shell', 'getprop', 'ro.product.model')) 2>$null
    if ($LASTEXITCODE -ne 0) { $result.status = 'model-unavailable'; return $result }
    if (([string]$model).Trim() -cne 'Quest 3') { $result.status = 'wrong-model'; return $result }
    $packages = @(Invoke-QuestAdb ($target + @('shell', 'pm', 'list', 'packages', '-e', '--show-versioncode', '--user', 'current', 'com.vrcommand.quest')) 2>$null)
    if ($LASTEXITCODE -ne 0) { $result.status = 'package-query-failed'; return $result }
    $rows = @($packages | Where-Object { $_ -cmatch '\Apackage:com\.vrcommand\.quest versionCode:[0-9]+\s*\z' })
    if ($AllowMissingApk -and $packages.Count -eq 0) {
        $knownPackages = @(Invoke-QuestAdb ($target + @('shell', 'pm', 'list', 'packages', '-u', '--user', 'current', 'com.vrcommand.quest')) 2>$null)
        if ($LASTEXITCODE -ne 0) { $result.status = 'package-query-failed'; return $result }
        if ($knownPackages.Count -eq 0) {
            $result.status = 'install-required'
            return $result
        }
    }
    $code = 0L
    if ($rows.Count -ne 1 -or -not [long]::TryParse(($rows[0] -csplit ':')[-1], [ref]$code)) {
        $result.status = 'package-unavailable'; return $result
    }
    $result.versionCode = $code
    if ($code -ne $VersionCode) { $result.status = 'version-mismatch'; return $result }
    if ($ExpectedHash) {
        $result.status = Get-QuestApkStatus $target $ExpectedHash
        if ($result.status -ceq 'ready') { $result.apkVerified = $true }
    }
    return $result
}

function Read-QuestDeviceSerial([string[]]$Target) {
    $lines = @(Invoke-QuestAdb ($Target + @('shell', 'getprop', 'ro.serialno')) 2>$null)
    if ($LASTEXITCODE -ne 0 -or $lines.Count -ne 1 -or $lines[0] -cnotmatch '\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\z' -or
        $lines[0] -match '\A(?:unknown|0+)\z') { return $null }
    return [string]$lines[0]
}

function Get-QuestSha256([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($Bytes)).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Get-QuestDeploymentFingerprint([string]$Salt, [string]$Value) {
    return Get-QuestSha256 ([Text.Encoding]::UTF8.GetBytes("$Salt`n$Value"))
}

function Get-QuestMapFingerprint([object[]]$Map, [string]$Salt) {
    $assignments = $Map | ForEach-Object { "$($_.roomId)/$($_.seat)=$($_.serial)" }
    return Get-QuestDeploymentFingerprint $Salt ($assignments -join "`n")
}

function Get-QuestVenueDeviceScope($Venue) {
    $sessionIds = $Venue.SessionIds -join "`n"
    return Get-QuestDeploymentFingerprint 'vrcommand-quest-venue-devices-v1' "$($Venue.Report.topology)`n$sessionIds"
}

function Test-QuestVenueDeviceProof($Venue, [int]$Count, $Proof) {
    if (-not $Proof.PSObject.Properties['venueDevices']) { return $true }
    $stamped = $Proof.venueDevices
    return ($stamped -is [pscustomobject] -and @($stamped.PSObject.Properties.Name).Count -eq 2 -and
        $stamped.scopeSha256 -is [string] -and $stamped.scopeSha256 -ceq (Get-QuestVenueDeviceScope $Venue) -and
        $stamped.devices -is [array] -and $stamped.devices.Count -eq $Count -and
        @($stamped.devices | Where-Object { $_ -isnot [string] -or $_ -cnotmatch '\A[0-9a-f]{64}\z' }).Count -eq 0 -and
        @($stamped.devices | Sort-Object -Unique).Count -eq $Count)
}

function Test-QuestDeploymentMap($Venue, [object[]]$Map, $Report) {
    $proof = $Report.retry
    return ('deployment' -ceq $Report.phase -and $Report.managementVerified -is [bool] -and $Report.managementVerified -and
        $Venue.Report.topology -ceq $Report.topology -and
        (Test-JsonInteger $proof.version) -and $proof.version -eq 1 -and $Venue.BundleSha256 -ceq $proof.venueSha256 -and
        $proof.salt -is [string] -and $proof.salt -cmatch '\A[0-9a-f]{32}\z' -and
        (Get-QuestMapFingerprint $Map $proof.salt) -ceq $proof.mapSha256 -and
        $proof.devices -is [array] -and $proof.devices.Count -eq $Map.Count -and
        @($proof.devices | Sort-Object -Unique).Count -eq $Map.Count -and
        (Test-QuestVenueDeviceProof $Venue $Map.Count $proof) -and
        $Report.devices -is [array] -and $Report.devices.Count -eq $Map.Count)
}

function Test-QuestDeploymentRow($Entry, $Row, $DeviceFingerprint, [int]$VersionCode, [switch]$AllowMissingVersion) {
    $versionMatches = if ($AllowMissingVersion -and $null -eq $Entry.versionCode) { $true }
        else { (Test-JsonInteger $Entry.versionCode) -and $Entry.versionCode -eq $VersionCode }
    return ($DeviceFingerprint -is [string] -and $DeviceFingerprint -cmatch '\A[0-9a-f]{64}\z' -and
        (Test-JsonInteger $Entry.roomId) -and $Entry.roomId -eq $Row.roomId -and
        (Test-JsonInteger $Entry.seat) -and $Entry.seat -eq $Row.seat -and $versionMatches)
}

function Test-QuestDeployedAdmission($Entry, $Ticket) {
    return ($Entry.apkVerified -is [bool] -and $Entry.apkVerified -and
        $Ticket.SessionId.ToString('D') -ceq $Entry.sessionId -and $Ticket.PlayerId.ToString('D') -ceq $Entry.playerId -and
        $Ticket.AdmissionId.ToString('D') -ceq $Entry.admissionId -and $Ticket.Config.port -eq $Entry.port)
}

function Test-QuestOpenXRProof($Proof) {
    return ($Proof -and (Test-JsonInteger $Proof.processId) -and $Proof.processId -ge 1 -and
        $Proof.processId -le [int]::MaxValue -and $Proof.nonce -is [string] -and
        $Proof.nonce -cmatch '\A[0-9a-f]{32}\z' -and $Proof.nonce -cne ('0' * 32))
}

function Get-QuestDeploymentReleaseHash($Report) {
    if ($Report.PSObject.Properties['venueReleaseReportSha256']) {
        $digest = $Report.venueReleaseReportSha256
        if ($digest -isnot [string] -or $digest -cnotmatch '\A[0-9a-f]{64}\z') {
            throw 'Invalid original Quest venue release report digest.'
        }
        return $digest
    }
}

function Read-QuestTrackedDeployment($Venue, [object[]]$Map, [string]$Path, [switch]$AllowSuccessfulPrefix) {
    $original = Read-DeploymentJson $Path 32768 'original deployment report'
    $report = $original.Document
    if ($AllowSuccessfulPrefix) {
        $reported = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        if ($report.devices -isnot [array] -or $report.devices.Count -lt 1 -or $report.devices.Count -gt 25) {
            throw 'Use original deployment reports with valid mapped seats.'
        }
        foreach ($entry in $report.devices) {
            if (-not (Test-JsonInteger $entry.roomId) -or $entry.roomId -notin 1..5 -or
                -not (Test-JsonInteger $entry.seat) -or $entry.seat -notin 1..5 -or
                -not $reported.Add("$($entry.roomId)/$($entry.seat)")) {
                throw 'Use original deployment reports with valid mapped seats.'
            }
        }
        $Map = @($Map | Where-Object { $reported.Contains("$($_.roomId)/$($_.seat)") })
    }
    if ($report.complete -isnot [bool] -or (-not $AllowSuccessfulPrefix -and -not $report.complete) -or
        -not (Test-JsonInteger $report.expectedVersionCode) -or $report.expectedVersionCode -lt 1 -or
        $report.expectedVersionCode -gt [int]::MaxValue -or
        $report.expectedApkSha256 -isnot [string] -or $report.expectedApkSha256 -cnotmatch '\A[0-9a-f]{64}\z' -or
        -not (Test-JsonInteger $report.apkVerificationVersion) -or $report.apkVerificationVersion -ne 1 -or
        -not (Test-QuestDeploymentMap $Venue $Map $report)) {
        if ($AllowSuccessfulPrefix) { throw 'Use release-verified deployment reports for this original ZIP and device map.' }
        throw 'Use a complete release-verified deployment report for this original ZIP and device map.'
    }
    if (($report.PSObject.Properties['requireOpenXR'] -and $report.requireOpenXR -isnot [bool]) -or
        ($report.requireOpenXR -and $report.expectedVersionCode -lt 74)) {
        throw 'Invalid OpenXR requirement in the original Quest deployment.'
    }
    $launched = [Collections.Generic.List[string]]::new()
    $venueDevices = @{}
    $unlaunched = $false
    for ($index = 0; $index -lt $Map.Count; $index++) {
        $entry = $report.devices[$index]
        $row = $Map[$index]
        $seatKey = "$($row.roomId)/$($row.seat)"
        if (-not (Test-QuestDeploymentRow $entry $row $report.retry.devices[$index] $report.expectedVersionCode) -or
            $entry.status -isnot [string]) {
            throw 'The deployment report does not match the original completed seat admissions.'
        }
        if ($AllowSuccessfulPrefix -and $entry.status -cne 'launch-requested') {
            $unlaunched = $true
            continue
        }
        $ticket = $Venue.Connections[$seatKey].Ticket
        if ($unlaunched -or 'launch-requested' -cne $entry.status -or $entry.filesVerified -isnot [bool] -or -not $entry.filesVerified -or
            ($report.requireOpenXR -eq $true -and -not (Test-QuestOpenXRProof $entry.openXR)) -or
            -not (Test-JsonInteger $entry.port) -or -not (Test-QuestDeployedAdmission $entry $ticket)) {
            throw 'The deployment report does not match the original completed seat admissions.'
        }
        $launched.Add($seatKey)
        if ($report.retry.venueDevices) { $venueDevices[$seatKey] = $report.retry.venueDevices.devices[$index] }
    }
    if (-not $launched.Count -or $report.complete -ne ($launched.Count -eq $Map.Count)) {
        throw 'The deployment report has no valid successful launch prefix.'
    }
    return @{ Sha256 = Get-QuestSha256 $original.Bytes; Seats = $launched; VenueDevices = $venueDevices
        ApkSha256 = $report.expectedApkSha256; VersionCode = $report.expectedVersionCode
        ReleaseReportSha256 = Get-QuestDeploymentReleaseHash $report }
}

function Read-QuestTrackedDeployments($Venue, [object[]]$Map, [string]$Path) {
    $list = (Read-DeploymentJson $Path 32768 'deployment report list').Document
    if (-not (Test-JsonInteger $list.version) -or $list.version -ne 1 -or $list.reports -isnot [array] -or
        $list.reports.Count -lt 2 -or $list.reports.Count -gt 25 -or
        @($list.PSObject.Properties.Name | Where-Object { $_ -cnotin @('version','reports') }).Count) {
        throw 'Use a version 1 deployment report list with 2 to 25 original Quest reports.'
    }
    $directory = Split-Path -Parent (Resolve-Path -LiteralPath $Path).ProviderPath
    $bindings = @{}
    $seenDevices = @{}
    $digests = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    $release = $null
    $releaseReportHash = $null
    foreach ($name in $list.reports) {
        if ($name -isnot [string] -or [string]::IsNullOrWhiteSpace($name)) { throw 'Use valid paths to original Quest deployment reports.' }
        $reportPath = if ([IO.Path]::IsPathRooted($name)) { $name } else { Join-Path $directory $name }
        $deployment = Read-QuestTrackedDeployment $Venue $Map $reportPath -AllowSuccessfulPrefix
        if (-not $digests.Add($deployment.Sha256)) { throw 'The deployment report list repeats an original report.' }
        if ($release -and ($release.ApkSha256 -cne $deployment.ApkSha256 -or $release.VersionCode -ne $deployment.VersionCode)) {
            throw 'Combined Quest tracking requires the same verified APK for every deployment.'
        }
        if ($deployment.ReleaseReportSha256) {
            if ($releaseReportHash -and $releaseReportHash -cne $deployment.ReleaseReportSha256) {
                throw 'Combined Quest tracking requires the same original venue release report.'
            }
            $releaseReportHash = $deployment.ReleaseReportSha256
        }
        $release = $deployment
        foreach ($seat in $deployment.Seats) {
            if ($bindings.ContainsKey($seat)) { throw 'Quest deployment reports repeat a successfully launched seat.' }
            $device = $deployment.VenueDevices[$seat]
            if ($device) {
                if ($seenDevices.ContainsKey($device)) {
                    throw "Quest deployment reports reused the same device for room/seat $($seenDevices[$device]) and $seat."
                }
                $seenDevices.Add($device, $seat)
            }
            $bindings.Add($seat, $deployment.Sha256)
        }
    }
    if ($bindings.Count -ne $Map.Count) { throw 'Quest deployments must cover every selected seat before a combined tracking sample.' }
    return $bindings
}

function Read-QuestDeploymentRetry($Venue, [object[]]$Map, [int]$VersionCode, $Release) {
    $original = Read-DeploymentJson $RetryIncomplete 32768 'original deployment report'
    $previous = $original.Document
    $proof = $previous.retry
    $expectedHash = [string]$Release.sha256
    if ($previous.complete -isnot [bool] -or $previous.complete -or $previous.expectedVersionCode -ne $VersionCode -or
        [string]$previous.expectedApkSha256 -cne $ExpectedHash -or -not (Test-QuestDeploymentMap $Venue $Map $previous)) {
        throw 'Use an incomplete deployment report for this original ZIP, device map and APK requirement.'
    }
    $releaseReportHash = Get-QuestDeploymentReleaseHash $previous
    if ($releaseReportHash -and $releaseReportHash -cne $Release.reportSha256) {
        throw 'Retry with the exact original Quest venue release report.'
    }
    if (($previous.PSObject.Properties['requireOpenXR'] -and $previous.requireOpenXR -isnot [bool]) -or
        [bool]$previous.requireOpenXR -ne [bool]$RequireOpenXR) {
        throw 'Retry with the original OpenXR requirement.'
    }
    if (($previous.PSObject.Properties['installMissing'] -and $previous.installMissing -isnot [bool]) -or
        [bool]$previous.installMissing -ne [bool]$InstallMissing) {
        throw 'Retry with the original APK installation option.'
    }
    $completed = [Collections.Generic.List[object]]::new()
    $statuses = @('not-attempted','device-identity-unavailable','device-identity-changed','apk-unverified',
        'apk-hash-mismatch','ticket-expired','venue-check-failed','seat-headset-mismatch','file-verification-failed','deployment-failed','adb-timeout')
    $fileSteps = @('resolve-launcher','prepare-device','stage-alignment','stage-connection','check-expiry-before-staging',
        'check-expiry-before-stop','stop-game','activate-connection','verify-active-connection',
        'clean-local-connection','check-expiry-before-launch','launch-game','observe-openxr',
        'check-apk-before-install','install-apk','verify-installed-apk','save-before-launch')
    for ($index = 0; $index -lt $Map.Count; $index++) {
        $entry = $previous.devices[$index]
        $row = $Map[$index]
        $allowMissingVersion = $InstallMissing -and $entry.status -cne 'launch-requested'
        if (-not (Test-QuestDeploymentRow $entry $row $proof.devices[$index] $VersionCode -AllowMissingVersion:$allowMissingVersion)) {
            throw 'Deployment report rows do not match the original mapped seats.'
        }
        if ($entry.status -ceq 'launch-requested') {
            $ticket = $Venue.Connections["$($row.roomId)/$($row.seat)"].Ticket
            if ($completed.Count -ne $index -or $entry.filesVerified -isnot [bool] -or -not $entry.filesVerified -or
                ($RequireOpenXR -and -not (Test-QuestOpenXRProof $entry.openXR)) -or
                ($ExpectedHash -and ($previous.apkVerificationVersion -ne 1 -or -not (Test-QuestDeployedAdmission $entry $ticket)))) {
                throw 'Deployment report has inconsistent completed seats.'
            }
            $seatResult = [ordered]@{ roomId = $row.roomId; seat = $row.seat; status = 'launch-requested';
                versionCode = $VersionCode; filesVerified = $true }
            if ($ExpectedHash) {
                $seatResult.apkVerified = $true
                $seatResult.sessionId = $entry.sessionId; $seatResult.playerId = $entry.playerId
                $seatResult.admissionId = $entry.admissionId; $seatResult.port = $entry.port
            }
            if ($RequireOpenXR) {
                $seatResult.openXR = [ordered]@{ processId = [int]$entry.openXR.processId; nonce = $entry.openXR.nonce }
            }
            if ($InstallMissing -and $entry.installedApk -is [bool] -and $entry.installedApk) {
                $seatResult.installedApk = $true
            }
            $completed.Add($seatResult)
        } elseif ($entry.status -cnotin $statuses) {
            throw 'Deployment report has an unknown seat status.'
        }
        if ($entry.status -cin @('file-verification-failed','deployment-failed') -and $entry.failedStep -cnotin $fileSteps) {
            throw 'Deployment report is missing the original failure step.'
        }
        if ($entry.failedStep -cin @('launch-game','observe-openxr')) {
            throw 'Confirm the previous launch outcome on the affected headset before retrying that seat manually.'
        }
    }
    if ($completed.Count -eq $Map.Count) { throw 'This deployment report has no seats left to retry.' }
    return @{ Proof = $proof; Completed = $completed.ToArray(); PreviousSha256 = Get-QuestSha256 $original.Bytes
        ReleaseReportSha256 = $releaseReportHash }
}

function Read-MappedQuestPreflight([object[]]$Map, [int]$VersionCode, [string]$ExpectedHash, $Retry, [switch]$AllowMissingApk) {
    Confirm-QuestAdbStartup 'Android platform-tools are not installed.'
    $inventory = Get-QuestDeviceInventory
    $devices = @($Map | ForEach-Object {
        $preflightSeat = $_
        try { Get-MappedQuestStatus $preflightSeat $inventory $VersionCode $ExpectedHash -AllowMissingApk:$AllowMissingApk }
        catch [TimeoutException] { [ordered]@{ roomId = $preflightSeat.roomId; seat = $preflightSeat.seat; status = 'adb-timeout' } }
    })
    $reportedSerials = [string[]]::new($Map.Count)
    $firstSeatBySerial = [Collections.Generic.Dictionary[string,int]]::new([StringComparer]::OrdinalIgnoreCase)
    for ($index = 0; $index -lt $Map.Count; $index++) {
        if ($devices[$index].status -cnotin @('ready','install-required')) { continue }
        $target = @('-t', [string]$inventory[$Map[$index].serial].TransportId)
        try { $reportedSerial = Read-QuestDeviceSerial $target }
        catch [TimeoutException] { $devices[$index].status = 'adb-timeout'; continue }
        if (-not $reportedSerial) { $devices[$index].status = 'device-identity-unavailable'; continue }
        if ($Retry) {
            $originalIndex = $Retry.Completed.Count + $index
            $scoped = $Retry.Proof.venueDevices
            if ((Get-QuestDeploymentFingerprint $Retry.Proof.salt $reportedSerial.ToUpperInvariant()) -cne $Retry.Proof.devices[$originalIndex] -or
                ($scoped -and (Get-QuestDeploymentFingerprint $scoped.scopeSha256 $reportedSerial.ToUpperInvariant()) -cne $scoped.devices[$originalIndex])) {
                $devices[$index].status = 'device-identity-changed'
                continue
            }
        }
        $reportedSerials[$index] = $reportedSerial
        if ($firstSeatBySerial.ContainsKey($reportedSerial)) {
            $devices[$firstSeatBySerial[$reportedSerial]].status = 'duplicate-device'
            $devices[$index].status = 'duplicate-device'
        } else {
            $firstSeatBySerial.Add($reportedSerial, $index)
        }
    }
    return @{ Inventory = $inventory; Devices = $devices; Serials = $reportedSerials }
}

function Install-MappedQuestApk($Row, $Inventory, $Release, [string]$StagedApk, $Device, $Operation) {
    $Operation.Step = 'install-apk'
    $target = @('-t', [string]$Inventory[$Row.serial].TransportId)
    Install-QuestReleaseApk $target $StagedApk
    $Device.installedApk = $true
    $Operation.Step = 'verify-installed-apk'
    return Get-MappedQuestStatus $Row $Inventory $Release.versionCode $Release.sha256
}

function Invoke-QuestApkPreparation([object[]]$Map, $Release, [string]$StagedApk) {
    $preflight = Read-MappedQuestPreflight $Map $Release.versionCode $Release.sha256 -AllowMissingApk
    $devices = $preflight.Devices
    $report = [ordered]@{ phase = 'apk-preflight'; expectedVersionCode = $Release.versionCode;
        expectedApkSha256 = $Release.sha256; venueReleaseReportSha256 = $Release.reportSha256;
        complete = $false; devices = $devices }
    if ($devices | Where-Object { $_.status -cnotin @('ready','install-required') }) { return $report }
    if ($CheckOnly) { $report.complete = $true; return $report }

    $report.phase = 'apk-preparation'
    foreach ($device in $devices) { $device.status = 'not-attempted'; $device.Remove('apkVerified') }
    for ($index = 0; $index -lt $Map.Count; $index++) {
        $row = $Map[$index]; $device = $devices[$index]
        $target = @('-t', [string]$preflight.Inventory[$row.serial].TransportId)
        $operation = @{ Step = 'verify-device' }
        try {
            $serial = Read-QuestDeviceSerial $target
            if (-not $serial) { $device.status = 'device-identity-unavailable'; return $report }
            if ($serial -cne $preflight.Serials[$index]) { $device.status = 'device-identity-changed'; return $report }
            $operation.Step = 'check-apk-before-install'
            $current = Get-MappedQuestStatus $row $preflight.Inventory $Release.versionCode $Release.sha256 -AllowMissingApk
            if ($current.status -ceq 'install-required') {
                $current = Install-MappedQuestApk $row $preflight.Inventory $Release $StagedApk $device $operation
            }
            $device.status = $current.status
            if ($current.status -cne 'ready') { $device.failedStep = $operation.Step; return $report }
            $device.versionCode = $current.versionCode
            $device.apkVerified = $true
        } catch {
            $device.status = if ($_.Exception -is [TimeoutException]) { 'adb-timeout' } else { 'apk-preparation-failed' }
            $device.failedStep = $operation.Step
            return $report
        }
    }
    $report.complete = $true
    return $report
}

function Write-QuestDeploymentReport($Output, $Report) {
    $name = '.quest-deploy-' + [Guid]::NewGuid().ToString('N') + '.tmp'
    $temporary = Join-Path (Split-Path -Parent $Output.Path) $name
    $bytes = [Text.Encoding]::UTF8.GetBytes(($Report | ConvertTo-Json -Depth 4 -Compress) + "`n")
    $file = [IO.File]::Open($temporary, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        try { $file.Write($bytes, 0, $bytes.Length); $file.Flush($true) }
        finally { $file.Dispose() }
        [IO.File]::Move($temporary, $Output.Path, $Output.Published)
        $Output.Published = $true
    } finally {
        if ([IO.File]::Exists($temporary)) { [IO.File]::Delete($temporary) }
    }
}

function Invoke-MappedQuestSeats($Venue, [object[]]$Map, [int]$VersionCode, $Release, $Retry, [string]$StagedApk, $ReportOutput) {
    $expectedHash = [string]$Release.sha256
    $originalMap = $Map
    if ($Retry) { $Map = @($Map | Select-Object -Skip $Retry.Completed.Count) }
    $preflight = Read-MappedQuestPreflight $Map $VersionCode $ExpectedHash $Retry -AllowMissingApk:([bool]$StagedApk)
    $inventory = $preflight.Inventory
    $devices = $preflight.Devices
    $reportedSerials = $preflight.Serials
    $report = [ordered]@{ phase = 'preflight'; topology = $Venue.Report.topology; expectedVersionCode = $VersionCode;
        earliestExpiryUtc = $Venue.Report.earliestExpiryUtc; complete = $false; devices = $devices }
    if ($ExpectedHash) { $report.expectedApkSha256 = $ExpectedHash }
    if ($Release -and (-not $Retry -or $Retry.ReleaseReportSha256)) {
        $report.venueReleaseReportSha256 = $Release.reportSha256
    }
    if ($AllowPartialMap) {
        $report.mappedSeats = $Map.Count
        $report.unmappedSeats = $Venue.Report.seats - $Map.Count
    }
    $isVr = $Venue.Report.mode -ceq 'VR'
    $checksHeadset = $Venue.Report.mode -cin @('VR','Mixed')
    if ($checksHeadset) { $report.mode = $Venue.Report.mode }
    if (-not $isVr) { $report.alignmentPinsVerified = $true }
    if ($devices | Where-Object { $_.status -cnotin @('ready','install-required') }) { return $report }
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
    if ($ExpectedHash) { $report.apkVerificationVersion = 1 }
    if ($RequireOpenXR) { $report.requireOpenXR = $true }
    if ($StagedApk) { $report.installMissing = $true }
    if ($Retry) {
        $report.retry = $Retry.Proof
        $report.previousDeploymentSha256 = $Retry.PreviousSha256
        $report.devices = $Retry.Completed + $devices
        if ($AllowPartialMap) {
            $report.mappedSeats = $originalMap.Count
            $report.unmappedSeats = $Venue.Report.seats - $originalMap.Count
        }
    } else {
        $salt = [Guid]::NewGuid().ToString('N')
        $scope = Get-QuestVenueDeviceScope $Venue
        $report.retry = [ordered]@{ version = 1; venueSha256 = $Venue.BundleSha256; salt = $salt;
            mapSha256 = Get-QuestMapFingerprint $originalMap $salt;
            devices = @($reportedSerials | ForEach-Object { Get-QuestDeploymentFingerprint $salt $_.ToUpperInvariant() });
            venueDevices = [ordered]@{ scopeSha256 = $scope;
                devices = @($reportedSerials | ForEach-Object { Get-QuestDeploymentFingerprint $scope $_.ToUpperInvariant() }) } }
    }
    $WarningPreference = 'SilentlyContinue'
    foreach ($device in $devices) { $device.status = 'not-attempted'; $device.Remove('apkVerified') }
    if ($ReportOutput) { Write-QuestDeploymentReport $ReportOutput $report }
    for ($index = 0; $index -lt $Map.Count; $index++) {
        $row = $Map[$index]; $device = $devices[$index]
        $target = @('-t', [string]$inventory[$row.serial].TransportId)
        $connection = $Venue.Connections["$($row.roomId)/$($row.seat)"]
        try { $reportedSerial = Read-QuestDeviceSerial $target }
        catch [TimeoutException] { $device.status = 'adb-timeout'; return $report }
        if (-not $reportedSerial) { $device.status = 'device-identity-unavailable'; return $report }
        if ($reportedSerial -cne $reportedSerials[$index]) { $device.status = 'device-identity-changed'; return $report }
        if ($ExpectedHash -and -not $StagedApk) {
            try { $apkStatus = Get-QuestApkStatus $target $ExpectedHash }
            catch [TimeoutException] { $device.status = 'adb-timeout'; return $report }
            if ($apkStatus -cne 'ready') { $device.status = $apkStatus; return $report }
            $device.apkVerified = $true
        }
        if ($connection.Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) {
            $device.status = 'ticket-expired'; return $report
        }
        try { Confirm-VenueReadback $Venue -RequireLiveSource }
        catch {
            $device.status = 'venue-check-failed'
            $device.failedStep = 'verify-live-venue'
            return $report
        }
        if ($checksHeadset -and $Venue.SeatHeadsets["$($row.roomId)/$($row.seat)"] -cne 'Quest3') {
            $device.status = 'seat-headset-mismatch'; return $report
        }
        $deployment = @{}
        try {
            if ($StagedApk) {
                $deployment.Step = 'check-apk-before-install'
                $current = Get-MappedQuestStatus $row $inventory $VersionCode $ExpectedHash -AllowMissingApk
                if ($current.status -ceq 'install-required') {
                    if ($connection.Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) {
                        $device.status = 'ticket-expired'; return $report
                    }
                    $current = Install-MappedQuestApk $row $inventory $Release $StagedApk $device $deployment
                }
                if ($current.status -cne 'ready') { throw 'The installed Quest app could not be verified for this release.' }
                $device.versionCode = $current.versionCode
                $device.apkVerified = $true
                if ($device.installedApk) {
                    if ($connection.Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) {
                        $device.status = 'ticket-expired'; return $report
                    }
                    $deployment.Step = 'verify-live-venue-after-install'
                    Confirm-VenueReadback $Venue -RequireLiveSource
                    if ($checksHeadset -and $Venue.SeatHeadsets["$($row.roomId)/$($row.seat)"] -cne 'Quest3') {
                        $device.status = 'seat-headset-mismatch'; return $report
                    }
                }
            }
            $saveLaunch = if ($ReportOutput) {
                {
                    $device.filesVerified = $true
                    $device.status = 'deployment-failed'
                    $device.failedStep = 'launch-game'
                    Write-QuestDeploymentReport $ReportOutput $report
                }
            }
            Set-QuestConnection $target $connection.Ticket.Config $connection.Ticket $connection.Alignment `
                -RequestMixedReality:($null -ne $connection.Alignment) -Deployment $deployment -LiveVenue $Venue -BeforeLaunch $saveLaunch
            $device.filesVerified = $true
            $device.status = 'launch-requested'
            $device.Remove('failedStep')
            if ($RequireOpenXR) { $device.openXR = $deployment.OpenXR }
            if ($ExpectedHash) {
                $device.sessionId = $connection.Ticket.SessionId.ToString('D')
                $device.playerId = $connection.Ticket.PlayerId.ToString('D')
                $device.admissionId = $connection.Ticket.AdmissionId.ToString('D')
                $device.port = $connection.Ticket.Config.port
            }
        } catch {
            $device.status = if ($deployment.Step -cin @('verify-live-venue-before-stop','verify-live-venue-after-install')) { 'venue-check-failed' }
                elseif ($_.Exception -is [IO.InvalidDataException]) { 'file-verification-failed' }
                else { 'deployment-failed' }
            $device.failedStep = $deployment.Step
            if ($_.Exception -is [TimeoutException]) { $device.adbTimedOut = $true }
            if ($deployment.Step -ceq 'observe-openxr') {
                $device.filesVerified = $true
                $device.openXRFailure = if ($_.Exception -is [InvalidOperationException]) { $_.Exception.Message }
                    else { 'Could not verify the launched Quest process.' }
            }
            return $report
        }
        if ($ReportOutput -and $index -lt $Map.Count - 1) { Write-QuestDeploymentReport $ReportOutput $report }
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

function Read-QuestFileHash([string[]]$Target, [string]$Path) {
    $lines = @(Invoke-QuestAdb ($Target + @('shell', 'sha256sum', $Path)) 2>$null)
    if ($LASTEXITCODE -eq 0 -and $lines.Count -eq 1 -and $lines[0] -cmatch '\A([0-9a-f]{64})[ \t]+(.+)\z' -and $Matches[2] -ceq $Path) {
        return $Matches[1]
    }
}

function Confirm-QuestFileHash([string[]]$Target, [string]$Path, [string]$ExpectedHash, [string]$Description) {
    if ((Read-QuestFileHash $Target $Path) -cne $ExpectedHash) {
        throw [IO.InvalidDataException]::new("$Description could not be verified on the selected Quest.")
    }
}

function Publish-QuestFile([string[]]$Target, [string]$Local, [string]$Staging, [string]$Destination, [string]$Description,
    [string]$ExpectedHash, [string]$ContentHash, [scriptblock]$BeforeActivation, [hashtable]$ConnectionDeployment,
    [hashtable]$RequiredAlignment) {
    $stagedHash = if ($ContentHash) { $ContentHash } else { (Get-FileHash -LiteralPath $Local -Algorithm SHA256).Hash.ToLowerInvariant() }
    try {
        Invoke-QuestAdb ($Target + @('push', $Local, $Staging)) | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "$Description could not be copied." }
        if (-not $ExpectedHash) { Confirm-QuestFileHash $Target $Staging $stagedHash $Description }
        if ($BeforeActivation) { & $BeforeActivation }
        if ($null -ne $ConnectionDeployment) { $ConnectionDeployment.Step = 'activate-connection' }
        $command = ''
        if ($ExpectedHash) {
            $command = 'current=$(sha256sum ''{0}'') && [ "${{current%% *}}" = ''{1}'' ] || exit 41; ' -f $Destination, $ExpectedHash
        }
        # Check all files used by the replacement in the same device command as the rename.
        $command += 'staged=$(sha256sum ''{0}'') && [ "${{staged%% *}}" = ''{1}'' ] || exit 42; ' -f $Staging, $stagedHash
        if ($RequiredAlignment) {
            $command += 'alignment=$(sha256sum ''{0}'') && [ "${{alignment%% *}}" = ''{1}'' ] || exit 43; ' `
                -f $RequiredAlignment.Path, $RequiredAlignment.Hash
        }
        $command += 'mv -f ''{0}'' ''{1}''' -f $Staging, $Destination
        Invoke-QuestAdb ($Target + @('shell', $command)) *> $null
        if ($LASTEXITCODE -eq 43 -and $RequiredAlignment) {
            throw [IO.InvalidDataException]::new('Room alignment file could not be verified on the selected Quest.')
        }
        if ($ExpectedHash -and $LASTEXITCODE -ne 0) {
            throw 'Could not confirm ticket replacement. Check the selected device and read its current configuration before retrying.'
        }
        if ($LASTEXITCODE -eq 42) {
            throw [IO.InvalidDataException]::new("$Description could not be verified on the selected Quest.")
        }
        if ($LASTEXITCODE -ne 0) { throw "$Description could not be activated." }
        if ($null -ne $ConnectionDeployment) { $ConnectionDeployment.Step = 'verify-active-connection' }
        Confirm-QuestFileHash $Target $Destination $stagedHash $Description
        if ($RequiredAlignment) { Confirm-QuestFileHash $Target $RequiredAlignment.Path $RequiredAlignment.Hash 'Room alignment file' }
    } catch {
        $publishError = $_
        try {
            Invoke-QuestAdb ($Target + @('shell', 'rm', '-f', $Staging)) *> $null
            if ($LASTEXITCODE -ne 0) { throw 'ADB cleanup failed.' }
        } catch {
            Write-Warning 'Could not remove the temporary deployment file from the selected device.'
        }
        throw $publishError
    }
}

function Update-QuestPlayerTicket($ConnectionFile, $Ticket, $Target) {
    $fresh = $ConnectionFile.Document
    if ([Guid]::Empty -in @($Ticket.SessionId, $Ticket.PlayerId, $Ticket.AdmissionId)) { throw 'Use a player file for an original admission.' }
    $deviceTarget = Get-SingleQuestTarget $Serial
    $model = Invoke-QuestAdb ($deviceTarget + @('shell', 'getprop', 'ro.product.model')) 2>$null
    if ($LASTEXITCODE -ne 0 -or ($model -join "`n").Trim() -cne 'Quest 3') { throw 'Select an authorized Meta Quest 3.' }

    $remote = '/sdcard/Android/data/com.vrcommand.quest/files'
    $destination = "$remote/vr-connection.json"
    $liveSeat = $null
    $local = [IO.Path]::GetTempFileName()
    try {
        Invoke-QuestAdb ($deviceTarget + @('pull', $destination, $local)) *> $null
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
        $requiredAlignment = if ($installed.AlignmentHash) {
            @{ Path = "$remote/vr-room-alignment-$($installed.AlignmentHash).json"; Hash = $installed.AlignmentHash }
        }
        if ($Target) {
            $alignment = $null
            if ($Ticket.AlignmentHash) {
                $alignmentCopy = [IO.Path]::GetTempFileName()
                try {
                    Invoke-QuestAdb ($deviceTarget + @('pull', $requiredAlignment.Path, $alignmentCopy)) *> $null
                    if ($LASTEXITCODE -ne 0) { throw 'Could not read the original locked MR alignment on the selected Quest.' }
                    $alignment = Read-RoomAlignment $alignmentCopy $Ticket.RoomId
                    if ($alignment.Hash -cne $Ticket.AlignmentHash) { throw 'The installed MR alignment does not match the locked hash.' }
                } finally { Remove-Item -LiteralPath $alignmentCopy }
            }
            $liveSeat = New-QuestPlayerReadback $Target $ConnectionFile $Ticket $alignment
            Confirm-QuestPlayerReadback $liveSeat
        }
        $expectedHash = Get-QuestSha256 $original.Bytes
        if ($sameTicket) {
            Confirm-QuestFileHash $deviceTarget $destination $expectedHash 'Player ticket file'
            if ($requiredAlignment) { Confirm-QuestFileHash $deviceTarget $requiredAlignment.Path $requiredAlignment.Hash 'Room alignment file' }
        } else {
            $current.joinTicket = $Fresh.joinTicket
            $replacement = [Text.Encoding]::UTF8.GetBytes(($current | ConvertTo-Json -Depth 4 -Compress))
            [IO.File]::WriteAllBytes($local, $replacement)
            $staging = "$remote/vr-connection-$([Guid]::NewGuid().ToString('N')).tmp"
            Publish-QuestFile $deviceTarget $local $staging $destination 'Player ticket file' -ExpectedHash $expectedHash `
                -ContentHash (Get-QuestSha256 $replacement) -RequiredAlignment $requiredAlignment -BeforeActivation {
                if ($liveSeat) { Confirm-QuestPlayerReadback $liveSeat }
                if ($Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) { throw 'The replacement ticket expired before refresh.' }
            }
        }
    } finally { Remove-Item -LiteralPath $local }
    $report = [ordered]@{ roomId = $Ticket.RoomId; seat = $Ticket.Seat + 1; expiresAtUtc = $Ticket.ExpiresAtUtc.ToString('o')
        status = if ($sameTicket) { 'ticket-file-current' } else { 'ticket-file-refreshed' } }
    if ($liveSeat) { $report.managementVerified = $true }
    $report | ConvertTo-Json -Compress
}

function Set-QuestConnection([string[]]$Target, $Config, $Ticket, $Alignment, [switch]$UsePassthrough, [switch]$RequestMixedReality,
    [hashtable]$Deployment = @{}, $LiveVenue, $LiveSeat, [scriptblock]$BeforeLaunch) {
    $Deployment.Step = 'resolve-launcher'
    $activity = Get-QuestLauncherActivity $Target
    $nonce = if ($RequireOpenXR) { [Guid]::NewGuid().ToString('N') }
    $Deployment.Step = 'prepare-device'
    $remoteDirectory = '/sdcard/Android/data/com.vrcommand.quest/files'
    Invoke-QuestAdb ($Target + @('shell', 'mkdir', '-p', $remoteDirectory)) | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'App data directory could not be prepared.' }
    $deploymentId = [Guid]::NewGuid().ToString('N')
    $requiredAlignment = $null
    if ($Alignment) {
        $Deployment.Step = 'stage-alignment'
        $alignmentHash = $Alignment.Hash
        $requiredAlignment = @{ Path = "$remoteDirectory/vr-room-alignment-$alignmentHash.json"; Hash = $alignmentHash }
        $stagedAlignment = [IO.Path]::GetTempFileName()
        try {
            [IO.File]::WriteAllBytes($stagedAlignment, $Alignment.Bytes)
            Publish-QuestFile $Target $stagedAlignment "$remoteDirectory/vr-room-alignment-$deploymentId.tmp" `
                $requiredAlignment.Path 'Room alignment file' -ContentHash $alignmentHash
        } finally { Remove-Item -LiteralPath $stagedAlignment }
        if (-not $Ticket.AlignmentHash) { $Config | Add-Member -NotePropertyName 'roomAlignmentSha256' -NotePropertyValue $alignmentHash }
    }
    $Deployment.Step = 'stage-connection'
    if ($UsePassthrough -or $RequestMixedReality) { $Config | Add-Member -NotePropertyName 'questPassthrough' -NotePropertyValue $true }
    if ($RequestMixedReality) { $Config | Add-Member -NotePropertyName 'requestMixedReality' -NotePropertyValue $true }
    if ($RecordLinkMetrics) { $Config | Add-Member -NotePropertyName 'recordQuestLinkMetrics' -NotePropertyValue $true }
    $stagedConfig = [IO.Path]::GetTempFileName()
    try {
        $Deployment.Step = 'check-expiry-before-staging'
        if ($Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) { throw 'Player ticket expired during deployment. Download a fresh connection file.' }
        $Deployment.Step = 'stage-connection'
        [IO.File]::WriteAllText($stagedConfig, ($Config | ConvertTo-Json -Depth 4 -Compress))
        # The active config is the commit point. Its referenced alignment is already verified by hash.
        Publish-QuestFile $Target $stagedConfig "$remoteDirectory/vr-connection-$deploymentId.tmp" `
            "$remoteDirectory/vr-connection.json" 'Player connection file' -ConnectionDeployment $Deployment `
            -RequiredAlignment $requiredAlignment -BeforeActivation {
                if ($LiveVenue) {
                    $Deployment.Step = 'verify-live-venue-before-stop'
                    Confirm-VenueReadback $LiveVenue -RequireLiveSource
                    $seatKey = "$($Ticket.RoomId)/$($Ticket.Seat + 1)"
                    if ($LiveVenue.Report.mode -cin @('VR','Mixed') -and $LiveVenue.SeatHeadsets[$seatKey] -cne 'Quest3') {
                        throw 'The selected seat is not assigned to a Quest 3 player.'
                    }
                }
                if ($LiveSeat) { Confirm-QuestPlayerReadback $LiveSeat }
                $Deployment.Step = 'check-expiry-before-stop'
                if ($Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) { throw 'Player ticket expired before activation. Download a fresh connection file.' }
                $Deployment.Step = 'stop-game'
                Invoke-QuestAdb ($Target + @('shell', 'am', 'force-stop', 'com.vrcommand.quest')) | Out-Null
                if ($LASTEXITCODE -ne 0) { throw 'Quest app could not be stopped before activating configuration.' }
            }
        $Deployment.Step = 'clean-local-connection'
    } finally { Remove-Item -LiteralPath $stagedConfig }
    $Deployment.Step = 'check-expiry-before-launch'
    if ($Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) { throw 'Player ticket expired before launch. Download a fresh connection file.' }
    if ($BeforeLaunch) {
        $Deployment.Step = 'save-before-launch'
        & $BeforeLaunch
        $Deployment.Step = 'check-expiry-before-launch'
        if ($Ticket.ExpiresAtUtc -le [DateTimeOffset]::UtcNow) { throw 'Player ticket expired before launch. Download a fresh connection file.' }
    }
    $Deployment.Step = 'launch-game'
    Start-QuestCheckedActivity $Target $activity $nonce
    if ($RequireOpenXR) {
        $Deployment.Step = 'observe-openxr'
        $observation = Read-QuestLaunchedProcess $Target $nonce
        $Deployment.OpenXR = [ordered]@{ processId = $observation.processId; nonce = $nonce }
    }
}

function Invoke-QuestFirstLaunch([string]$Apk, $Release) {
    $deviceTarget = Get-SingleQuestTarget $Serial
    $model = @(Invoke-QuestAdb ($deviceTarget + @('shell', 'getprop', 'ro.product.model')) 2>$null)
    if ($LASTEXITCODE -ne 0 -or $model.Count -ne 1 -or $model[0].Trim() -cne 'Quest 3') { throw 'Select an authorized Meta Quest 3.' }

    $package = 'com.vrcommand.quest'
    $installed = @(Invoke-QuestAdb ($deviceTarget + @('shell', 'pm', 'list', 'packages', '-u', '--user', 'current', $package)) 2>$null)
    if ($LASTEXITCODE -ne 0) { throw 'Could not check if the app is already present.' }
    $appPresent = $installed -ccontains "package:$package"
    if ($ResumeSmokeTest) {
        if (-not $appPresent) { throw 'No existing VR Command app to resume. Run -SmokeTest without -ResumeSmokeTest to install.' }
    } else {
        if ($appPresent) { throw 'The first-launch test requires a headset without an existing VR Command app. Use -ResumeSmokeTest to check the matching APK without a player configuration.' }
        $stagedApk = New-VerifiedQuestApk $Apk $Release.sha256
        try { Install-QuestReleaseApk $deviceTarget $stagedApk }
        finally { Remove-Item -LiteralPath $stagedApk -ErrorAction SilentlyContinue }
    }
    if ((Get-QuestApkStatus $deviceTarget $Release.sha256) -cne 'ready') { throw 'Installed Quest APK could not be verified against the release report.' }

    $config = '/sdcard/Android/data/com.vrcommand.quest/files/vr-connection.json'
    Invoke-QuestAdb ($deviceTarget + @('shell', 'test', '!', '-e', $config)) | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not confirm the Quest has no existing player configuration. App launch was skipped.' }
    $activity = Get-QuestLauncherActivity $deviceTarget
    $nonce = if ($RequireOpenXR) { [Guid]::NewGuid().ToString('N') }
    Start-QuestCheckedActivity $deviceTarget $activity $nonce -Restart:$ResumeSmokeTest
    $observation = Read-QuestLaunchedProcess $deviceTarget $nonce
    $report = [ordered]@{
        phase = 'quest-first-launch'; status = 'process-observed'; model = 'Quest 3'; versionCode = $Release.versionCode
        apkVerified = $true; apkSha256 = $Release.sha256; venueReleaseReportSha256 = $Release.reportSha256
        installedThisRun = -not $ResumeSmokeTest; processObservationSeconds = 3
        unityLogLines = $observation.unityLogLines
    }
    if ($RequireOpenXR) {
        $report.status = 'openxr-ready'
        $report.processObservationSeconds = $observation.observationSeconds
        $report['openXR'] = [ordered]@{ loader = 'OpenXR'; displayRunning = $true; inputRunning = $true }
    }
    return $report
}

function Get-QuestLauncherActivity([string[]]$Target) {
    $resolved = @(Invoke-QuestAdb ($Target + @('shell', 'pm', 'resolve-activity', '--brief', '--user', 'current',
        '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.LAUNCHER', '-p', 'com.vrcommand.quest')) 2>$null)
    $activities = @($resolved -cmatch '\Acom\.vrcommand\.quest/[A-Za-z0-9._]+\z')
    if ($LASTEXITCODE -ne 0 -or $activities.Count -ne 1) { throw 'Could not resolve a launcher activity for the installed Quest app.' }
    return $activities[0]
}

function Start-QuestCheckedActivity([string[]]$Target, [string]$Activity, [string]$Nonce, [switch]$Restart) {
    $launchOptions = @('-W')
    if ($Restart) { $launchOptions += '-S' }
    $extras = @()
    if ($Nonce) { $extras = @('--es', 'com.vrcommand.quest.OPENXR_PROBE', $Nonce) }
    $launchArguments = $Target + @('shell', 'am', 'start') + $launchOptions + @('--user', 'current',
        '-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.LAUNCHER', '-n', $Activity) + $extras
    $startup = @(Invoke-QuestAdb $launchArguments 2>$null)
    $exitCode = $LASTEXITCODE
    $statuses = @($startup -cmatch '\AStatus:')
    $activities = @($startup -cmatch '\AActivity:')
    $shortClass = '\AActivity: com\.vrcommand\.quest/\.'
    $fullClass = 'Activity: com.vrcommand.quest/com.vrcommand.quest.'
    if ($exitCode -ne 0 -or ($startup -cmatch '\A(?:Warning: Activity not started|Error:)') -or
        $statuses.Count -ne 1 -or $statuses[0] -cne 'Status: ok' -or $activities.Count -ne 1 -or
        ($activities[0] -creplace $shortClass, $fullClass) -cne ("Activity: $Activity" -creplace $shortClass, $fullClass)) {
        throw 'Android did not confirm that the Quest launcher activity started.'
    }
}

function Read-QuestLaunchedProcess([string[]]$Target, [string]$Nonce) {
    $pidCommand = $Target + @('shell', 'pidof', 'com.vrcommand.quest')
    $appPid = Invoke-QuestAdb $pidCommand 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]$appPid -cnotmatch '\A[1-9][0-9]{0,9}\z' -or [long]$appPid -gt [int]::MaxValue) {
        throw [InvalidOperationException]::new('Quest game process was not present after launch.')
    }
    $clock = [Diagnostics.Stopwatch]::StartNew()
    Start-Sleep -Seconds 3
    do {
        $remaining = [int](20000 - $clock.ElapsedMilliseconds)
        if ($remaining -le 0) { throw [InvalidOperationException]::new('No OpenXR evidence was observed for the current Quest launch.') }
        $logs = @(Invoke-QuestAdb ($Target + @('logcat', '-d', '-t', '1000', "--pid=$appPid", '-v', 'brief',
            '-s', 'Unity', 'AndroidRuntime')) -MaximumMilliseconds $remaining 2>$null)
        if ($LASTEXITCODE -ne 0) { throw [InvalidOperationException]::new('Could not read the launched Quest process logs.') }
        $remaining = [int](20000 - $clock.ElapsedMilliseconds)
        if ($remaining -le 0) { throw [InvalidOperationException]::new('Could not confirm the original Quest process before the observation deadline.') }
        $remainingPid = Invoke-QuestAdb $pidCommand -MaximumMilliseconds $remaining 2>$null
        if ($LASTEXITCODE -ne 0 -or [string]$remainingPid -cne [string]$appPid -or ($logs -cmatch '^E/AndroidRuntime\s*\([^)]*\): FATAL EXCEPTION')) {
            throw [InvalidOperationException]::new('The Quest game process exited, restarted or reported a fatal error during launch.')
        }
        if (-not $Nonce) { break }
        $prefix = "\AI/Unity\s*\(\s*$appPid\s*\): VR_QUEST_OPENXR nonce=$nonce "
        $probe = @($logs -cmatch $prefix)
        if ($probe.Count -gt 0) {
            if ($probe.Count -ne 1 -or $probe[0] -cnotmatch ($prefix + 'loader=([01]) display=([01]) input=([01])\z')) {
                throw [InvalidOperationException]::new('The current Quest launch produced conflicting or invalid OpenXR evidence.')
            }
            if ($Matches[1] -ne '1' -or $Matches[2] -ne '1' -or $Matches[3] -ne '1') {
                throw [InvalidOperationException]::new("Quest OpenXR did not become ready (loader=$($Matches[1]), display=$($Matches[2]), input=$($Matches[3])).")
            }
            break
        }
        $remaining = [int](20000 - $clock.ElapsedMilliseconds)
        if ($remaining -gt 0) { Start-Sleep -Milliseconds ([Math]::Min($remaining, 500)) }
    } while ($true)
    return @{
        processId = [int]$appPid
        observationSeconds = [Math]::Round($clock.Elapsed.TotalSeconds, 2)
        unityLogLines = @($logs -cmatch '^[VDIWEF]/Unity\s*\(').Count
    }
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
    $venue = Read-VenueBundle $VenueBundle 0 0 -Fingerprint
    $map = @(Read-QuestVenueMap $venue $DeviceMap -Partial:$AllowPartialMap)
    $seats = foreach ($row in $map) {
        $ticket = $venue.Connections["$($row.roomId)/$($row.seat)"].Ticket
        [ordered]@{
            roomId = $row.roomId; seat = $row.seat; serial = $row.serial; port = $ticket.Config.port
            sessionId = $ticket.SessionId.ToString('D'); playerId = $ticket.PlayerId.ToString('D')
            admissionId = $ticket.AdmissionId.ToString('D')
        }
    }
    [ordered]@{ version = 1; topology = $venue.Report.topology; venueSha256 = $venue.BundleSha256; seats = @($seats) } | ConvertTo-Json -Depth 4 -Compress
    return
}

if ($PSCmdlet.ParameterSetName -eq 'Refresh') {
    if (-not $RefreshPlayerTicket) { throw 'Specify -RefreshPlayerTicket for the live ticket update.' }
    $freshFile = Read-DeploymentJson $ClientConfig $(if ($ManagementApi) { 2048 } else { 4096 }) 'new player connection'
    $ticket = Read-PlayerConfig $freshFile.Document
    $target = if ($ManagementApi) { Get-ManagementTarget $ManagementApi }
    $deploymentLock = Enter-QuestDeployment
    try { Update-QuestPlayerTicket $freshFile $ticket $target }
    finally { $deploymentLock.ReleaseMutex(); $deploymentLock.Dispose() }
    return
}

if ($PSCmdlet.ParameterSetName -eq 'Windows') { Export-WindowsVenueSeats; return }

if ($PSCmdlet.ParameterSetName -eq 'PlayerTracking') {
    if (-not $VerifyPlayerTracking) { throw 'Specify -VerifyPlayerTracking to check the player seat before Begin.' }
    $connection = (Read-DeploymentJson $ClientConfig 4096 'player connection').Document
    $ticket = Read-PlayerConfig $connection
    $result = Confirm-PlayerTrackedSeat (Get-ManagementTarget $ManagementApi) $ticket
    $result | ConvertTo-Json -Depth 4 -Compress
    if (-not $result.complete) { exit 1 }
    return
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$apk = if ($ApkPath) { $ApkPath } else { Join-Path $projectRoot 'artifacts/quest/VrCommand.apk' }
if ($PSCmdlet.ParameterSetName -eq 'PrepareApks') {
    if (-not $PrepareQuestApks) { throw 'Specify -PrepareQuestApks to prepare the mapped Quest APKs.' }
    $map = @(Read-QuestVenueMap $null $DeviceMap -Partial)
    $release = Read-QuestRelease $ReleaseReport
    if ($CheckOnly) {
        Confirm-LocalQuestApk $apk $release.sha256
        $result = Invoke-QuestApkPreparation $map $release
    } else {
        $deploymentLock = Enter-QuestDeployment
        $stagedApk = $null
        try {
            $stagedApk = New-VerifiedQuestApk $apk $release.sha256
            $result = Invoke-QuestApkPreparation $map $release $stagedApk
        } finally {
            if ($stagedApk) { Remove-Item -LiteralPath $stagedApk -ErrorAction SilentlyContinue }
            $deploymentLock.ReleaseMutex(); $deploymentLock.Dispose()
        }
    }
    $result | ConvertTo-Json -Depth 4 -Compress
    if (-not $result.complete) { exit 1 }
    return
}
if ($PSCmdlet.ParameterSetName -eq 'Smoke') {
    if (-not $SmokeTest) { throw 'Specify -SmokeTest to install and check a first launch.' }
    $release = Read-QuestRelease $ReleaseReport
    Confirm-LocalQuestApk $apk $release.sha256
    $deploymentLock = Enter-QuestDeployment
    try { Invoke-QuestFirstLaunch $apk $release | ConvertTo-Json -Compress }
    finally { $deploymentLock.ReleaseMutex(); $deploymentLock.Dispose() }
    return
}

$alignment = $null
$alignmentHash = $null
$liveSeat = $null
if ($RecordLinkMetrics -and (-not $ReleaseReport -or $CheckOnly -or $VerifyTrackedSeats -or ($DeviceMap -and -not $DeployMappedSeats))) {
    throw 'Use -RecordLinkMetrics with -ReleaseReport when launching a Quest player; a device map also needs -DeployMappedSeats.'
}
if ($RequireOpenXR -and (-not $ReleaseReport -or $CheckOnly -or $VerifyTrackedSeats -or ($DeviceMap -and -not $DeployMappedSeats))) {
    throw 'Use -RequireOpenXR with -ReleaseReport when launching a Quest player; a device map also needs -DeployMappedSeats.'
}
if ($ApkPath -and (-not $ReleaseReport -or ($DeviceMap -and -not $InstallMissing))) {
    throw 'Use -ApkPath only for a single-seat install with -ReleaseReport, or a mapped deployment with -InstallMissing.'
}
if ($PSCmdlet.ParameterSetName -eq 'Bundle') {
    if ($InstallMissing -and (-not $DeployMappedSeats -or -not $DeviceMap -or -not $ReleaseReport -or $CheckOnly -or $VerifyTrackedSeats)) {
        throw 'Use -InstallMissing with -DeviceMap, -DeployMappedSeats and -ReleaseReport for live Quest deployment.'
    }
    if ($WaitForTrackedSeconds -and -not $VerifyTrackedSeats) { throw 'Use -WaitForTrackedSeconds only with -VerifyTrackedSeats.' }
    if ($DeploymentReport -and $DeploymentReportsFile) { throw 'Specify either -DeploymentReport or -DeploymentReportsFile.' }
    if (($DeploymentReport -or $DeploymentReportsFile) -and (-not $VerifyTrackedSeats -or -not $DeviceMap)) {
        throw 'Use deployment reports only with -VerifyTrackedSeats and the original -DeviceMap.'
    }
    if ($RetryIncomplete -and (-not $DeployMappedSeats -or -not $DeviceMap)) {
        throw 'Use -RetryIncomplete with -DeployMappedSeats and the original -DeviceMap.'
    }
    if ($SaveDeploymentReport -and (-not $DeployMappedSeats -or -not $DeviceMap -or $CheckOnly -or $VerifyTrackedSeats)) {
        throw 'Use -SaveDeploymentReport with -DeployMappedSeats and -DeviceMap.'
    }
    if ($AllHeadsets -and (-not $VerifyTrackedSeats -or $DeviceMap -or $AllowPartialMap)) {
        throw 'Use -AllHeadsets only with -VerifyTrackedSeats and without a device map or partial selection.'
    }
    if ($VerifyTrackedSeats) {
        if (-not $ManagementApi -or $RoomId -or $Seat -or $PSBoundParameters.ContainsKey('Serial') -or
            $ExpectedVersionCode -or $ReleaseReport -or $DeployMappedSeats -or $CheckOnly -or ($AllowPartialMap -and -not $DeviceMap)) {
            throw 'Use -VerifyTrackedSeats with -ManagementApi and an optional -DeviceMap; omit deployment and device-check parameters.'
        }
        $venue = Read-VenueBundle $VenueBundle 0 0 -Fingerprint:($DeploymentReport -or $DeploymentReportsFile)
        $map = @(if ($DeviceMap) { Read-QuestVenueMap $venue $DeviceMap -Partial:$AllowPartialMap }
            else { foreach ($room in $venue.Report.rooms) { foreach ($seat in 1..$room.seats) { @{ roomId = $room.roomId; seat = $seat } } } })
        if ($DeploymentReport) { $deployment = Read-QuestTrackedDeployment $venue $map $DeploymentReport }
        if ($DeploymentReportsFile) { $bindings = Read-QuestTrackedDeployments $venue $map $DeploymentReportsFile }
        $result = Confirm-TrackedSeats $venue $map -IncludeAllHeadsets:$AllHeadsets
        if ($DeploymentReport) {
            $result.evidenceVersion = 1
            $result.venueSha256 = $venue.BundleSha256
            $result.deploymentSha256 = $deployment.Sha256
        }
        if ($DeploymentReportsFile) {
            $result.evidenceVersion = 2
            $result.venueSha256 = $venue.BundleSha256
            foreach ($row in $result.seats) {
                $row.deploymentSha256 = $bindings["$($row.roomId)/$($row.seat)"]
            }
        }
        $result | ConvertTo-Json -Depth 4 -Compress
        if (-not $result.complete) { exit 1 }
        return
    }
    if ($DeviceMap) {
        if ($RoomId -or $Seat -or $PSBoundParameters.ContainsKey('Serial') -or [bool]$ExpectedVersionCode -eq [bool]$ReleaseReport) {
            throw 'Use -DeviceMap with either -ExpectedVersionCode or -ReleaseReport and omit -RoomId, -Seat and -Serial.'
        }
        if ($DeployMappedSeats -and ($CheckOnly -or -not $ManagementApi)) {
            throw '-DeployMappedSeats requires -ManagementApi and cannot be combined with -CheckOnly.'
        }
        $venue = Read-VenueBundle $VenueBundle 0 0 -Fingerprint:$DeployMappedSeats
        $map = @(Read-QuestVenueMap $venue $DeviceMap -Partial:$AllowPartialMap)
        $release = if ($ReleaseReport) { Read-QuestRelease $ReleaseReport }
        $versionCode = if ($release) { $release.versionCode } else { $ExpectedVersionCode }
        if ($DeployMappedSeats) {
            $reportOutput = if ($SaveDeploymentReport) {
                $path = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($SaveDeploymentReport)
                if (-not [IO.Directory]::Exists((Split-Path -Parent $path)) -or (Test-Path -LiteralPath $path)) {
                    throw 'Choose a new deployment report file in an existing directory.'
                }
                @{ Path = $path; Published = $false }
            }
            $retry = if ($RetryIncomplete) { Read-QuestDeploymentRetry $venue $map $versionCode $release }
            $deploymentLock = Enter-QuestDeployment
            $stagedApk = $null
            try {
                if ($InstallMissing) { $stagedApk = New-VerifiedQuestApk $apk $release.sha256 }
                $result = Invoke-MappedQuestSeats $venue $map $versionCode $release $retry $stagedApk $reportOutput
                if ($reportOutput) { Write-QuestDeploymentReport $reportOutput $result }
            } finally {
                if ($stagedApk) { Remove-Item -LiteralPath $stagedApk -ErrorAction SilentlyContinue }
                $deploymentLock.ReleaseMutex(); $deploymentLock.Dispose()
            }
        } else { $result = Invoke-MappedQuestSeats $venue $map $versionCode $release }
        $result | ConvertTo-Json -Depth 4 -Compress
        if (-not $result.complete) { exit 1 }
        return
    }
    if ($DeployMappedSeats -or $ExpectedVersionCode -or $AllowPartialMap) { throw 'Specify -DeviceMap for mapped deployment parameters.' }
    if ([bool]$RoomId -ne [bool]$Seat) { throw 'Specify both -RoomId and -Seat, or omit both for five-room preflight.' }
    if ($ReleaseReport -and -not $RoomId) { throw 'Specify both -RoomId and -Seat to check an APK for a single bundle seat.' }
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
    $connectionFile = Read-DeploymentJson $ClientConfig $(if ($ManagementApi) { 2048 } else { 4096 }) 'player connection'
    $config = $connectionFile.Document
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
    if ($ManagementApi) {
        $liveSeat = New-QuestPlayerReadback (Get-ManagementTarget $ManagementApi) $connectionFile $ticket $(if ($isMixedReality) { $alignment })
        Confirm-QuestPlayerReadback $liveSeat
    }
}
$release = if ($ReleaseReport) { Read-QuestRelease $ReleaseReport }
if ($release) { Confirm-LocalQuestApk $apk $release.sha256 }
if ($CheckOnly) {
    $report = [ordered]@{
        roomId = $ticket.RoomId
        seat = $ticket.Seat + 1
        expiresAtUtc = $ticket.ExpiresAtUtc.ToString('o')
        mode = if ($isMixedReality) { 'MR' } elseif ($Passthrough) { 'VR with passthrough' } else { 'VR' }
        alignmentSha256 = $alignmentHash
    }
    if ($ticket.AlignmentHash) { $report.alignmentPinsVerified = $true }
    if ($release) {
        $report.localApkVerified = $true; $report.expectedVersionCode = $release.versionCode
        $report.venueReleaseReportSha256 = $release.reportSha256
    }
    if ($ManagementApi) { $report.managementVerified = $true }
    if ($PSCmdlet.ParameterSetName -eq 'Bundle' -and $requiresLive -and $ManagementApi) {
        $report.headset = $venue.SeatHeadsets["$RoomId/$Seat"]
    }
    $report | ConvertTo-Json -Compress
    return
}

if (-not (Test-Path -LiteralPath $apk -PathType Leaf)) { throw 'Build the Quest APK before deploying.' }
$deploymentLock = Enter-QuestDeployment
$stagedApk = $null
$deployment = @{}
try {
    $deviceTarget = Get-SingleQuestTarget $Serial
    $model = Invoke-QuestAdb ($deviceTarget + @('shell', 'getprop', 'ro.product.model'))
    if ($LASTEXITCODE -ne 0) { throw 'Could not identify the selected Android device. On Windows, check USB and ADB with scripts/check-quest-usb.ps1.' }
    $model = ([string]$model).Trim()
    if ($model -ne 'Quest 3') { throw 'Selected device is not a Meta Quest 3. No app was installed.' }
    if ($ManagementApi -and $PSCmdlet.ParameterSetName -eq 'Bundle') { Confirm-VenueReadback $venue -RequireLiveSource }
    if ($release) {
        $stagedApk = New-VerifiedQuestApk $apk $release.sha256
        $apk = $stagedApk
    }
    if ($liveSeat) { Confirm-QuestPlayerReadback $liveSeat }
    if ($RequireOpenXR) { Invoke-QuestAdb ($deviceTarget + @('install', '-r', $apk)) *> $null }
    else { Invoke-QuestAdb ($deviceTarget + @('install', '-r', $apk)) }
    if ($LASTEXITCODE -ne 0) { throw 'APK installation failed.' }
    if ($release -and (Get-QuestApkStatus $deviceTarget $release.sha256) -cne 'ready') {
        throw 'Installed Quest APK could not be verified against the release report.'
    }
    if ($ManagementApi -and $PSCmdlet.ParameterSetName -eq 'Bundle') { Confirm-VenueReadback $venue -RequireLiveSource }
    Set-QuestConnection $deviceTarget $config $ticket $alignment -UsePassthrough:$Passthrough -RequestMixedReality:$isMixedReality `
        -LiveVenue $(if ($ManagementApi -and $PSCmdlet.ParameterSetName -eq 'Bundle') { $venue }) -LiveSeat $liveSeat -Deployment $deployment
} finally {
    $deploymentLock.ReleaseMutex(); $deploymentLock.Dispose()
    if ($stagedApk) { Remove-Item -LiteralPath $stagedApk -ErrorAction SilentlyContinue }
}
if ($RequireOpenXR) {
    [ordered]@{ status = 'openxr-ready'; roomId = $ticket.RoomId; seat = $ticket.Seat + 1;
        apkVerified = $true; filesVerified = $true; openXR = $deployment.OpenXR
        venueReleaseReportSha256 = $release.reportSha256 } | ConvertTo-Json -Compress
} else { Write-Host 'Quest client installed and launched. Ticket expiry and server admission still apply.' }
