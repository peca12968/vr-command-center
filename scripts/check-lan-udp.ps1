[CmdletBinding(DefaultParameterSetName = 'Network')]
param(
    [Parameter(Mandatory, ParameterSetName = 'Key')][switch]$NewKey,
    [Parameter(Mandatory, ParameterSetName = 'Network')][ValidateSet('Listen', 'Probe')][string]$Mode,
    [Parameter(Mandatory)][string]$KeyFile,
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
    if ($Mode -eq 'Listen') {
        Write-Result @{ version = 1; stage = 'listening'; localAddress = $LocalAddress; peerAddress = $PeerAddress; port = $Port }
        $seen = [Collections.Generic.HashSet[string]]::new()
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
    Write-Result @{ version = 1; stage = 'finished'; mode = $Mode.ToLowerInvariant(); localAddress = $LocalAddress
        peerAddress = $PeerAddress; port = $Port; requested = $Count; matched = $received; samples = $samples
        complete = ($received -eq $Count); scope = 'authenticated-udp-only' }
    if ($received -eq $Count) { exit 0 }
    exit 1
} catch {
    Write-Result @{ version = 1; stage = 'failed'; step = $step; complete = $false }
    exit 1
} finally {
    if ($udp) { $udp.Dispose() }
    if ($hmac) { $hmac.Dispose() }
    $random.Dispose()
}
