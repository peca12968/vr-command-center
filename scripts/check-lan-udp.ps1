[CmdletBinding(DefaultParameterSetName = 'Network')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Key')][switch]$NewKey,
    [Parameter(Mandatory, ParameterSetName = 'Network')][ValidateSet('Listen', 'Probe')][string]$Mode,
    [Parameter(Mandatory, ParameterSetName = 'Key')][Parameter(Mandatory, ParameterSetName = 'Network')][string]$KeyFile,
    [Parameter(Mandatory, ParameterSetName = 'Pair')][string]$ListenerReport,
    [Parameter(Mandatory, ParameterSetName = 'Pair')][string]$ProbeReport,
    [Parameter(ParameterSetName = 'Pair')][string]$ExpectedServerAddress,
    [Parameter(ParameterSetName = 'Pair')][ValidateRange(1024, 65535)][int]$ExpectedGamePort,
    [Parameter(ParameterSetName = 'Pair')][string]$ExpectedPeerAddresses,
    [Parameter(ParameterSetName = 'Pair')][string]$BindingObservedAtUtc,
    [Parameter(ParameterSetName = 'Pair')][switch]$FailureReason,
    [Parameter(Mandatory, ParameterSetName = 'Network')][string]$LocalAddress,
    [Parameter(Mandatory, ParameterSetName = 'Network')][string]$PeerAddress,
    [Parameter(Mandatory, ParameterSetName = 'Network')][ValidateRange(1024, 65535)][int]$Port,
    [Parameter(ParameterSetName = 'Network')][ValidateRange(1, 20)][int]$Count = 5,
    [Parameter(ParameterSetName = 'Network')][ValidateRange(5, 180)][int]$Seconds = 60,
    [Parameter(ParameterSetName = 'Network')][ValidateRange(200, 3000)][int]$TimeoutMs = 900
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ascii = [Text.Encoding]::ASCII
$random = [Security.Cryptography.RandomNumberGenerator]::Create()
$hmac = $null
$udp = $null
$step = 'key'
$reason = 'invalid-report'

function Write-Result($Value) {
    [Console]::WriteLine((ConvertTo-Json -InputObject $Value -Depth 5 -Compress))
}

function Read-Address([string]$Value) {
    $address = [Net.IPAddress]::Parse($Value)
    if ($address.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork -or $address.ToString() -cne $Value) {
        throw 'Use an explicit canonical IPv4 address.'
    }
    $octets = $address.GetAddressBytes()
    if ($octets[0] -notin 10, 127 -and !($octets[0] -eq 172 -and $octets[1] -in 16..31) -and
        !($octets[0] -eq 192 -and $octets[1] -eq 168)) {
        throw 'Use a private LAN or loopback IPv4 address.'
    }
    return $address
}

function Get-Hex([byte[]]$Bytes) {
    return [BitConverter]::ToString($Bytes).Replace('-', '').ToLowerInvariant()
}

function Get-ExchangeHash([string]$Listener, [string]$Probe, [string[]]$Nonces) {
    if (!$Nonces.Count) { return }
    [Array]::Sort($Nonces, [StringComparer]::Ordinal)
    $portText = $Port.ToString([Globalization.CultureInfo]::InvariantCulture)
    $text = "VRLAN1`n$Listener`n$Probe`n$portText`n" + ($Nonces -join "`n")
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return Get-Hex ($sha.ComputeHash($ascii.GetBytes($text))) }
    finally { $sha.Dispose() }
}

function Test-ReportInteger($Value) { return $Value -is [int] -or $Value -is [long] }

function Read-UtcTime($Value) {
    if ($Value -is [DateTime] -and $Value.Kind -eq [DateTimeKind]::Utc) { return [DateTimeOffset]$Value }
    if ($Value -isnot [string] -or $Value -cnotmatch '\A\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?(?:Z|\+00:00)\z') {
        throw 'Use an explicit UTC timestamp.'
    }
    return [DateTimeOffset]::Parse($Value, [Globalization.CultureInfo]::InvariantCulture)
}

function Read-CompleteReport([string]$Path, [string]$Role) {
    $file = [IO.File]::OpenRead((Resolve-Path -LiteralPath $Path).ProviderPath)
    try {
        if ($file.Length -lt 1 -or $file.Length -gt 32KB) { throw 'Invalid report size.' }
        $reader = [IO.StreamReader]::new($file)
        try { $lines = $reader.ReadToEnd().Trim() -split '\r?\n' }
        finally { $reader.Dispose() }
    } finally { $file.Dispose() }
    if ($lines.Count -ne 1 -and !($Role -ceq 'listen' -and $lines.Count -eq 2)) { throw 'Invalid report lines.' }
    $report = ConvertFrom-Json -InputObject $lines[-1]
    if (!(Test-ReportInteger $report.version) -or $report.version -ne 1 -or $report.stage -cne 'finished' -or $report.mode -cne $Role -or
        $report.scope -cne 'authenticated-udp-only' -or $report.complete -isnot [bool] -or !$report.complete -or
        !(Test-ReportInteger $report.requested) -or $report.requested -notin 1..20 -or
        !(Test-ReportInteger $report.matched) -or $report.matched -ne $report.requested -or
        !(Test-ReportInteger $report.port) -or $report.port -lt 1024 -or $report.port -gt 65535 -or
        $report.exchangeSha256 -isnot [string] -or $report.exchangeSha256 -cnotmatch '\A[0-9a-f]{64}\z') {
        throw 'Expected a completed UDP report.'
    }
    $sampleCount = if ($Role -ceq 'probe') { $report.matched } else { 0 }
    if ($report.samples -isnot [array] -or $report.samples.Count -ne $sampleCount) { throw 'Unexpected sample count.' }
    for ($index = 0; $index -lt $sampleCount; $index++) {
        $sample = $report.samples[$index]
        $rtt = $sample.roundTripMs
        if (!(Test-ReportInteger $sample.sample) -or $sample.sample -ne ($index + 1) -or
            (!(Test-ReportInteger $rtt) -and $rtt -isnot [double] -and $rtt -isnot [decimal]) -or !(0 -le $rtt -and $rtt -le 3000)) {
            throw 'Invalid completed probe sample.'
        }
    }
    [void](Read-Address $report.localAddress)
    [void](Read-Address $report.peerAddress)
    if ($lines.Count -eq 2) {
        $bound = ConvertFrom-Json -InputObject $lines[0]
        if ($bound.version -ne 1 -or $bound.stage -cne 'listening' -or $bound.port -ne $report.port -or
            $bound.localAddress -cne $report.localAddress -or $bound.peerAddress -cne $report.peerAddress) {
            throw 'The listener bound a different endpoint.'
        }
    }
    return $report
}

function Get-Packet([string]$Kind, [string]$Nonce) {
    $prefix = "VRLAN1${Kind}:$Nonce"
    $tag = Get-Hex ($hmac.ComputeHash($ascii.GetBytes($prefix)))
    return "$prefix`:$tag"
}

function Read-Packet([int]$WaitMs) {
    if (!$udp.Client.Poll($WaitMs * 1000, [Net.Sockets.SelectMode]::SelectRead)) { return }
    $from = [Net.IPEndPoint]::new([Net.IPAddress]::Any, 0)
    try {
        $bytes = $udp.Receive([ref]$from)
        if ($bytes.Length -eq 105) {
            return [pscustomobject]@{ Peer = $from; Text = $ascii.GetString($bytes) }
        }
    } catch {
        $errorCode = $_.Exception.GetBaseException()
        if ($errorCode -is [Net.Sockets.SocketException] -and
            $errorCode.SocketErrorCode -in [Net.Sockets.SocketError]::ConnectionReset, [Net.Sockets.SocketError]::ConnectionRefused) {
            return
        }
        throw
    }
}

function Test-Packet([string]$Expected, [string]$Received) {
    $difference = 0
    for ($index = 0; $index -lt $Expected.Length; $index++) {
        $difference = $difference -bor ([int]$Expected[$index] -bxor [int]$Received[$index])
    }
    return $difference -eq 0
}

try {
    if ($PSCmdlet.ParameterSetName -eq 'Pair') {
        $step = 'reports'
        $listener = Read-CompleteReport $ListenerReport 'listen'
        $probe = Read-CompleteReport $ProbeReport 'probe'
        if ($listener.port -ne $probe.port -or $listener.matched -ne $probe.matched -or
            $listener.localAddress -cne $probe.peerAddress -or $listener.peerAddress -cne $probe.localAddress -or
            $listener.exchangeSha256 -cne $probe.exchangeSha256) {
            $reason = 'exchange-mismatch'
            throw 'The reports describe different UDP exchanges.'
        }
        $result = @{ version = 1; stage = 'pair-verified'; port = $listener.port; matched = $listener.matched
            exchangeSha256 = $listener.exchangeSha256; complete = $true; scope = 'authenticated-udp-only' }
        if ($ExpectedServerAddress -or $ExpectedGamePort -or $ExpectedPeerAddresses -or $BindingObservedAtUtc) {
            $step = 'binding'
            if (!$ExpectedServerAddress -or !$ExpectedGamePort -or !$ExpectedPeerAddresses -or !$BindingObservedAtUtc) {
                throw 'Provide all game binding and accepted peer fields.'
            }
            [void](Read-Address $ExpectedServerAddress)
            $peers = $ExpectedPeerAddresses.Split(',')
            if ($peers.Count -gt 25) { throw 'Too many expected peers.' }
            foreach ($peerAddress in $peers) { [void](Read-Address $peerAddress) }
            $binding = Read-UtcTime $BindingObservedAtUtc
            $finished = Read-UtcTime $listener.completedAtUtc
            if ($listener.localAddress -cne $ExpectedServerAddress -or $listener.port -ne $ExpectedGamePort -or $probe.localAddress -cnotin $peers) {
                $reason = 'binding-mismatch'
                throw 'The UDP exchange differs from the original binding, accepted peers or preflight window.'
            }
            if ($finished -ge $binding -or $binding - $finished -gt [TimeSpan]::FromMinutes(30)) {
                $reason = if ($finished -ge $binding) { 'clock-ahead' } else { 'expired' }
                throw 'The UDP exchange differs from the original binding, accepted peers or preflight window.'
            }
            $result.endpointVerified = $true
            $result.verifiedPeerIndex = [Array]::IndexOf($peers, [string]$probe.localAddress)
        }
        Write-Result $result
        exit 0
    }
    $key = [byte[]]::new(32)
    if ($NewKey) {
        $random.GetBytes($key)
        $file = [IO.File]::Open($KeyFile, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        try {
            $encoded = $ascii.GetBytes([Convert]::ToBase64String($key))
            $file.Write($encoded, 0, $encoded.Length)
        } finally { $file.Dispose() }
        Write-Result @{ version = 1; stage = 'key-created' }
        exit 0
    }

    $file = [IO.File]::OpenRead($KeyFile)
    try {
        if ($file.Length -lt 44 -or $file.Length -gt 46) { throw 'Invalid probe key size.' }
        $reader = [IO.StreamReader]::new($file, $ascii, $false)
        try { $encoded = $reader.ReadToEnd().Trim() } finally { $reader.Dispose() }
    } finally { $file.Dispose() }
    $key = [Convert]::FromBase64String($encoded)
    if ($key.Length -ne 32 -or [Convert]::ToBase64String($key) -cne $encoded) { throw 'Invalid probe key.' }
    $hmac = [Security.Cryptography.HMACSHA256]::new($key)

    $step = 'address'
    $local = Read-Address $LocalAddress
    $peer = Read-Address $PeerAddress
    $target = [Net.IPEndPoint]::new($peer, $Port)
    $step = 'bind'
    $udp = [Net.Sockets.UdpClient]::new([Net.Sockets.AddressFamily]::InterNetwork)
    $udp.ExclusiveAddressUse = $true
    $bindPort = if ($Mode -eq 'Listen') { $Port } else { 0 }
    $udp.Client.Bind([Net.IPEndPoint]::new($local, $bindPort))
    $step = 'exchange'

    $received = 0
    $samples = @()
    $seen = [Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    if ($Mode -eq 'Listen') {
        Write-Result @{ version = 1; stage = 'listening'; localAddress = $LocalAddress; peerAddress = $PeerAddress; port = $Port }
        $clock = [Diagnostics.Stopwatch]::StartNew()
        while ($received -lt $Count -and $clock.ElapsedMilliseconds -lt $Seconds * 1000) {
            $wait = [Math]::Max(1, [Math]::Min(200, $Seconds * 1000 - [int]$clock.ElapsedMilliseconds))
            $packet = Read-Packet $wait
            if (!$packet -or !$packet.Peer.Address.Equals($peer) -or
                $packet.Text -cnotmatch '^VRLAN1Q:([0-9a-f]{32}):[0-9a-f]{64}$') { continue }
            $nonce = $Matches[1]
            if (!(Test-Packet (Get-Packet Q $nonce) $packet.Text) -or !$seen.Add($nonce)) { continue }
            $reply = $ascii.GetBytes((Get-Packet R $nonce))
            [void]$udp.Send($reply, $reply.Length, $packet.Peer)
            $received++
        }
    } else {
        for ($sample = 1; $sample -le $Count; $sample++) {
            $challenge = [byte[]]::new(16)
            $random.GetBytes($challenge)
            $nonce = Get-Hex $challenge
            $payload = $ascii.GetBytes((Get-Packet Q $nonce))
            $expected = Get-Packet R $nonce
            $clock = [Diagnostics.Stopwatch]::StartNew()
            [void]$udp.Send($payload, $payload.Length, $target)
            $roundTrip = $null
            while ($clock.ElapsedMilliseconds -lt $TimeoutMs) {
                $packet = Read-Packet ([Math]::Max(1, $TimeoutMs - [int]$clock.ElapsedMilliseconds))
                $elapsed = $clock.Elapsed.TotalMilliseconds
                if ($packet -and $packet.Peer.Equals($target) -and (Test-Packet $expected $packet.Text)) {
                    if ($elapsed -le $TimeoutMs) {
                        $roundTrip = [Math]::Round($elapsed, 3)
                        [void]$seen.Add($nonce)
                        $received++
                    }
                    break
                }
            }
            $samples += @{ sample = $sample; roundTripMs = $roundTrip }
        }
    }
    $udp.Dispose()
    $udp = $null
    $completed = [DateTime]::UtcNow.ToString('O')
    $exchangeSha256 = if ($Mode -eq 'Listen') { Get-ExchangeHash $LocalAddress $PeerAddress @($seen) }
        else { Get-ExchangeHash $PeerAddress $LocalAddress @($seen) }
    Write-Result @{ version = 1; stage = 'finished'; mode = $Mode.ToLowerInvariant(); localAddress = $LocalAddress
        peerAddress = $PeerAddress; port = $Port; requested = $Count; matched = $received; samples = $samples
        exchangeSha256 = $exchangeSha256; complete = ($received -eq $Count); scope = 'authenticated-udp-only'; completedAtUtc = $completed }
    if ($received -eq $Count) { exit 0 }
    exit 1
} catch {
    $failed = @{ version = 1; stage = 'failed'; step = $step; complete = $false }
    if ($FailureReason) { $failed.reason = $reason }
    Write-Result $failed
    exit 1
} finally {
    if ($udp) { $udp.Dispose() }
    if ($hmac) { $hmac.Dispose() }
    $random.Dispose()
}
