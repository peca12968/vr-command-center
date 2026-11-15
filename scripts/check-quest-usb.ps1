[CmdletBinding()]
param([ValidateRange(1, 65535)][int]$AdbServerPort = 5037)

$ErrorActionPreference = 'Stop'

function Read-AdbReplyBytes($Stream, [int]$Count, [Diagnostics.Stopwatch]$Clock) {
    $buffer = [byte[]]::new($Count)
    $offset = 0
    while ($offset -lt $Count) {
        $remaining = 2000 - $Clock.ElapsedMilliseconds
        if ($remaining -le 0) { throw 'ADB response timed out.' }
        $Stream.ReadTimeout = [int]$remaining
        $size = $Stream.Read($buffer, $offset, $Count - $offset)
        if ($size -eq 0) { throw 'Incomplete ADB response.' }
        $offset += $size
    }
    return ,$buffer
}

function Read-ExistingAdbInventory([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new([Net.Sockets.AddressFamily]::InterNetwork)
    $status = 'unreachable'
    $entries = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    $unidentified = 0
    try {
        if (-not $client.ConnectAsync([Net.IPAddress]::Loopback, $Port).Wait(1000)) { throw 'ADB connection timed out.' }
        $status = 'invalid-response'
        $stream = $client.GetStream()
        $stream.WriteTimeout = 1000
        $encoding = [Text.Encoding]::ASCII
        $message = $encoding.GetBytes('000ehost:devices-l')
        $stream.Write($message, 0, $message.Length)
        $clock = [Diagnostics.Stopwatch]::StartNew()
        if ($encoding.GetString((Read-AdbReplyBytes $stream 4 $clock)) -cne 'OKAY') { throw 'ADB inventory rejected.' }
        $length = $encoding.GetString((Read-AdbReplyBytes $stream 4 $clock))
        if ($length -notmatch '\A[0-9a-f]{4}\z') { throw 'Invalid ADB response length.' }
        $reply = $encoding.GetString((Read-AdbReplyBytes $stream ([Convert]::ToInt32($length, 16)) $clock))
        foreach ($line in $reply -split '\r?\n') {
            if ($line -eq '') { continue }
            if ($line -cnotmatch '\A(\(no serial number\)|\S+)[ \t]+(\S+)(?:[ \t]+[^\r\n]*)?\z') { throw 'Invalid ADB inventory row.' }
            $serial = $Matches[1]
            $state = $Matches[2]
            if ($serial -ceq '(no serial number)') { $unidentified++; continue }
            if ($entries.ContainsKey($serial) -or $state -cnotin @('device','unauthorized','offline')) { $state = 'other' }
            $entries[$serial] = $state
        }
        $status = 'reachable'
    } catch { $entries.Clear(); $unidentified = 0 }
    finally { $client.Dispose() }
    return @{ Status = $status; Entries = $entries; Unidentified = $unidentified }
}

$usb = [ordered]@{
    observed = $false; metaUsbNodes = 0; portableMediaInterfaces = 0
    adbInterfaces = 0; adbInterfacesWithProblems = 0; unknownInterfaceDescriptors = 0; unknownAdbDriverStates = 0
}
$serials = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
try {
    $nodes = @(Get-PnpDevice -PresentOnly -ErrorAction Stop | Where-Object { $_.InstanceId -match '^USB\\VID_2833&PID_[0-9a-f]{4}(?:&|\\)' })
    $usb.observed = $true
} catch { $nodes = @() }
$usb.metaUsbNodes = $nodes.Count
foreach ($node in $nodes) {
    if ($node.InstanceId -match '\AUSB\\VID_2833&PID_[0-9a-f]{4}\\([a-z0-9._-]{1,128})\z') {
        [void]$serials.Add($Matches[1])
    }
    $descriptor = Get-PnpDeviceProperty -InstanceId $node.InstanceId -KeyName DEVPKEY_Device_CompatibleIds -ErrorAction SilentlyContinue
    $compatible = @($descriptor.Data | Where-Object { $_ })
    if (-not $compatible.Count) { $usb.unknownInterfaceDescriptors++ }
    if ($node.Class -eq 'WPD' -or $compatible -contains 'USB\MS_COMP_MTP') { $usb.portableMediaInterfaces++ }
    if ($compatible -notcontains 'USB\Class_ff&SubClass_42&Prot_01' -and
        $compatible -notcontains 'USB\COMPAT_VID_2833&Class_ff&SubClass_42&Prot_01') { continue }
    $usb.adbInterfaces++
    $problem = Get-PnpDeviceProperty -InstanceId $node.InstanceId -KeyName DEVPKEY_Device_ProblemCode -ErrorAction SilentlyContinue
    if ($null -eq $problem.Data) { $usb.unknownAdbDriverStates++ }
    elseif ($problem.Data -ne 0) { $usb.adbInterfacesWithProblems++ }
}

$inventory = Read-ExistingAdbInventory $AdbServerPort
$matched = [ordered]@{ device = 0; unauthorized = 0; offline = 0; other = 0 }
$unmatched = $inventory.Unidentified
$entryCount = $inventory.Entries.Count + $inventory.Unidentified
foreach ($entry in $inventory.Entries.GetEnumerator()) {
    if ($serials.Contains($entry.Key)) { $matched[$entry.Value]++ }
    else { $unmatched++ }
}
$status = if (-not $usb.observed) { 'windows-usb-inventory-unavailable' }
    elseif ($usb.metaUsbNodes -eq 0) { 'meta-usb-not-enumerated' }
    elseif ($entryCount -gt $unmatched) {
        $activeStates = @($matched.Keys | Where-Object { $matched[$_] -gt 0 })
        if ($activeStates.Count -gt 1) { 'adb-usb-mixed-states' }
        else { "adb-usb-$($activeStates[0])" }
    }
    elseif ($usb.adbInterfacesWithProblems -gt 0) { 'adb-usb-driver-problem' }
    elseif ($usb.adbInterfaces -gt 0) {
        if ($inventory.Status -eq 'reachable') { 'adb-usb-transport-unmatched' }
        else { 'adb-server-inventory-unavailable' }
    }
    elseif ($usb.unknownInterfaceDescriptors -gt 0) { 'meta-usb-interface-descriptors-incomplete' }
    else { 'meta-usb-without-adb-interface' }

[ordered]@{
    version = 1; status = $status; windows = $usb
    adb = [ordered]@{ server = $inventory.Status; entries = $entryCount; matchingMetaUsb = $matched; unmatchedEntries = $unmatched }
} | ConvertTo-Json -Depth 4 -Compress
