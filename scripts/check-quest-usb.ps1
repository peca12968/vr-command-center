[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$AdbServerPort = 5037,
    [ValidateRange(1, 25)][int]$ExpectedDevices,
    [switch]$Summary
)

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

function Read-AdbInventoryStream($Stream) {
    $status = 'invalid-response'
    $entries = [Collections.Generic.Dictionary[string,string]]::new([StringComparer]::OrdinalIgnoreCase)
    $unidentified = 0
    try {
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
    return @{ Status = $status; Entries = $entries; Unidentified = $unidentified }
}

function Read-ExistingAdbInventory([int]$Port) {
    $client = [Net.Sockets.TcpClient]::new([Net.Sockets.AddressFamily]::InterNetwork)
    $status = 'unreachable'
    try {
        if (-not $client.ConnectAsync([Net.IPAddress]::Loopback, $Port).Wait(1000)) { throw 'ADB connection timed out.' }
        $status = 'invalid-response'
        return Read-AdbInventoryStream ($client.GetStream())
    } catch { return @{ Status = $status; Entries = @{}; Unidentified = 0 } }
    finally { $client.Dispose() }
}

function Get-QuestUsbReport($Inventory, [int]$Expected, $MappedSeats) {
    $usb = [ordered]@{
        observed = $false; metaUsbNodes = 0; portableMediaInterfaces = 0
        adbInterfaces = 0; adbInterfacesWithProblems = 0; unknownInterfaceDescriptors = 0; unknownAdbDriverStates = 0
    }
    $roots = 0
    $serials = [Collections.Generic.Dictionary[string,int]]::new([StringComparer]::OrdinalIgnoreCase)
    $rootBySerial = @{}
    $evidenceByRoot = @{}
    try {
        $nodes = @(Get-PnpDevice -PresentOnly -ErrorAction Stop | Where-Object { $_.InstanceId -match '^USB\\VID_2833&PID_[0-9a-f]{4}(?:&|\\)' })
        $usb.observed = $true
    } catch { $nodes = @() }
    $usb.metaUsbNodes = $nodes.Count
    foreach ($node in $nodes) {
        $rootId = $null
        if ($node.InstanceId -match '\AUSB\\VID_2833&PID_[0-9a-f]{4}\\([^\\]+)\z') {
            $roots++
            $instance = $Matches[1]
            $rootId = $node.InstanceId
            if ($instance -match '\A[a-z0-9._-]{1,128}\z') {
                $serials[$instance] = 1 + $serials[$instance]
                $rootBySerial[$instance] = $rootId
            }
        }
        $descriptor = Get-PnpDeviceProperty -InstanceId $node.InstanceId -KeyName DEVPKEY_Device_CompatibleIds -ErrorAction SilentlyContinue
        $compatible = @($descriptor.Data | Where-Object { $_ })
        if (-not $compatible.Count) { $usb.unknownInterfaceDescriptors++ }
        $observations = [Collections.Generic.List[string]]::new()
        if ($node.Class -eq 'WPD' -or $compatible -contains 'USB\MS_COMP_MTP') {
            $usb.portableMediaInterfaces++
            $observations.Add('portable-media')
        }
        if ($compatible -contains 'USB\Class_ff&SubClass_42&Prot_01' -or
            $compatible -contains 'USB\COMPAT_VID_2833&Class_ff&SubClass_42&Prot_01') {
            $usb.adbInterfaces++
            $observations.Add('adb-interface')
            $problem = Get-PnpDeviceProperty -InstanceId $node.InstanceId -KeyName DEVPKEY_Device_ProblemCode -ErrorAction SilentlyContinue
            if ($null -eq $problem.Data) {
                $usb.unknownAdbDriverStates++
                $observations.Add('adb-driver-state-unknown')
            } elseif ($problem.Data -ne 0) {
                $usb.adbInterfacesWithProblems++
                $observations.Add('adb-driver-problem')
            }
        }
        if ($MappedSeats -and $observations.Count) {
            if (-not $rootId) {
                $parent = Get-PnpDeviceProperty -InstanceId $node.InstanceId -KeyName DEVPKEY_Device_Parent -ErrorAction SilentlyContinue
                $rootId = $parent.Data
            }
            if ($rootId) {
                if (-not $evidenceByRoot.ContainsKey($rootId)) { $evidenceByRoot[$rootId] = @{} }
                foreach ($observation in $observations) { $evidenceByRoot[$rootId][$observation] = $true }
            }
        }
    }

    $matched = [ordered]@{ device = 0; unauthorized = 0; offline = 0; other = 0 }
    $unmatched = $inventory.Unidentified
    $entryCount = $inventory.Entries.Count + $inventory.Unidentified
    foreach ($entry in $inventory.Entries.GetEnumerator()) {
        if ($serials[$entry.Key] -eq 1) { $matched[$entry.Value]++ }
        else { $unmatched++ }
    }
    $status = if (-not $usb.observed) { 'windows-usb-inventory-unavailable' }
        elseif ($usb.metaUsbNodes -eq 0) { 'meta-usb-not-enumerated' }
        elseif ($entryCount -gt $unmatched -and $entryCount - $unmatched -lt $roots) { 'adb-usb-partial-inventory' }
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

    $report = [ordered]@{
        version = 1; status = $status; windows = $usb
        adb = [ordered]@{ server = $inventory.Status; entries = $entryCount; matchingMetaUsb = $matched; unmatchedEntries = $unmatched }
    }
    if ($Expected -gt 0) {
        $comparable = $usb.observed -and $inventory.Status -eq 'reachable'
        $report.group = [ordered]@{
            expected = $Expected
            metaUsbRoots = if ($usb.observed) { $roots }
            matchedRoots = if ($comparable) { $entryCount - $unmatched }
            unmatchedUsbRoots = if ($comparable) { $roots - ($entryCount - $unmatched) }
            allExpectedInDeviceState = if ($comparable) { $roots -eq $Expected -and $matched.device -eq $Expected }
        }
    }
    if ($MappedSeats) {
        # Windows USB instance identities are case-insensitive. Two mapped spellings
        # must never count one physical headset as two connected seats.
        $assigned = [Collections.Generic.Dictionary[string,int]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach ($row in $MappedSeats) { $assigned[$row.serial] = 1 + $assigned[$row.serial] }
        $seats = @(foreach ($row in $MappedSeats) {
            $id = $row.serial
            $state = if ($id -notmatch '\A[a-z0-9._-]{1,128}\z') { 'not-usb-serial' }
                elseif ($assigned[$id] -ne 1) { 'ambiguous-map' }
                elseif (-not $usb.observed) { 'usb-inventory-unavailable' }
                elseif (-not $serials.ContainsKey($id)) { 'usb-not-found' }
                elseif ($serials[$id] -ne 1) { 'ambiguous-usb' }
                elseif ($Inventory.Status -ne 'reachable') { 'adb-inventory-unavailable' }
                elseif (-not $Inventory.Entries.ContainsKey($id)) { 'adb-not-listed' }
                else { $Inventory.Entries[$id] }
            $seatReport = [ordered]@{ roomId = $row.roomId; seat = $row.seat; state = $state }
            if ($state -in @('adb-not-listed', 'adb-inventory-unavailable')) {
                $seen = $evidenceByRoot[$rootBySerial[$id]]
                if ($seen) {
                    $seatReport.windowsEvidence = @('portable-media', 'adb-interface', 'adb-driver-problem', 'adb-driver-state-unknown' |
                        Where-Object { $seen.ContainsKey($_) })
                }
            }
            $seatReport
        })
        $ready = @($seats | Where-Object state -EQ 'device').Count
        $report.mapped = [ordered]@{ seats = $seats; connected = $ready; allInDeviceState = $ready -eq $seats.Count }
    }
    return $report
}

function Write-QuestUsbReport($Report, [switch]$Summary) {
    if (-not $Summary) {
        $report | ConvertTo-Json -Depth 4 -Compress
        return
    }
    $messages = @{
        'windows-usb-inventory-unavailable' = '無法取得 Windows USB 清單。'
        'meta-usb-not-enumerated' = 'Windows 目前沒有列出 Meta USB 裝置。'
        'meta-usb-without-adb-interface' = 'Windows 已看到 Meta USB 裝置，尚未列出 USB 偵錯介面。'
        'meta-usb-interface-descriptors-incomplete' = 'Windows 已看到 Meta USB 裝置，部分介面資料仍無法讀取。'
        'adb-usb-driver-problem' = 'Windows 回報 USB 偵錯介面的驅動程式有問題。'
        'adb-server-inventory-unavailable' = 'Windows 已列出偵錯介面，目前無法取得 ADB 裝置清單。'
        'adb-usb-transport-unmatched' = 'ADB 清單沒有可唯一對應到 Windows Meta USB 裝置的項目。'
        'adb-usb-partial-inventory' = '只有部分 Windows Meta USB 裝置能對應到 ADB 清單。'
        'adb-usb-device' = '可對應的 Meta USB 裝置均已取得 USB 偵錯連線。'
        'adb-usb-unauthorized' = '可對應的 Meta USB 裝置正在等待頭盔端授權。'
        'adb-usb-offline' = '可對應的 Meta USB 裝置目前在 ADB 中顯示離線。'
        'adb-usb-other' = 'ADB 清單含有重複或無法辨識狀態的裝置。'
        'adb-usb-mixed-states' = '可對應的 Meta USB 裝置有不同的偵錯狀態。'
    }
    $messages[$report.status]
    if ($report.mapped) {
        $seatLabels = @{
            'not-usb-serial' = '此對應值不適用於 USB 核對'
            'ambiguous-map' = '座位表重複指定同一 USB 識別'
            'usb-inventory-unavailable' = '無法讀取 Windows USB 清單'
            'usb-not-found' = 'Windows USB 清單沒有這台裝置'
            'ambiguous-usb' = '多台 Windows 裝置符合此座位'
            'adb-inventory-unavailable' = '無法取得 ADB 清單'
            'adb-not-listed' = 'Windows 已看到，ADB 尚未列出'
            device = '已連線'; unauthorized = '待頭盔授權'; offline = '離線'; other = '偵錯狀態無法確認'
        }
        $evidenceLabels = @{
            'portable-media' = '檔案傳輸介面'; 'adb-interface' = 'USB 偵錯介面'
            'adb-driver-problem' = '驅動程式有問題'; 'adb-driver-state-unknown' = '驅動程式狀態未確認'
        }
        foreach ($row in $report.mapped.seats) {
            $detail = if ($row.windowsEvidence) {
                '（' + (($row.windowsEvidence | ForEach-Object { $evidenceLabels[$_] }) -join '、') + '）'
            }
            "第 $($row.roomId) 房第 $($row.seat) 席：$($seatLabels[$row.state])$detail"
        }
        "指定的 $($report.mapped.seats.Count) 席中，已確認 USB 偵錯連線 $($report.mapped.connected) 席。"
    }
    if ($report.group) {
        $g = $report.group
        "預期 $($g.expected) 台。"
        if ($null -ne $g.metaUsbRoots) { "Windows 列出 $($g.metaUsbRoots) 台 Meta USB 裝置。" }
        if ($null -ne $g.matchedRoots) {
            $counts = $report.adb.matchingMetaUsb
            "ADB 對應 $($g.matchedRoots) 台，其中已連線 $($counts.device)、待授權 $($counts.unauthorized)、離線 $($counts.offline)、其他 $($counts.other)。Windows 清單中另有 $($g.unmatchedUsbRoots) 台無法對應。"
        } else { '目前無法比對兩份裝置清單。' }
        if ($g.allExpectedInDeviceState -eq $true) { '已核對預期台數及 USB 偵錯連線。' }
        elseif ($g.allExpectedInDeviceState -eq $false) { '目前台數或偵錯狀態與預期不符。' }
    }
}

if ($MyInvocation.InvocationName -ne '.') {
    $report = Get-QuestUsbReport (Read-ExistingAdbInventory $AdbServerPort) $ExpectedDevices
    Write-QuestUsbReport $report -Summary:$Summary
}
