function ConvertFrom-QuestAdbDeviceRows([string[]]$Lines, [StringComparer]$Comparer) {
    $devices = [Collections.Generic.Dictionary[string,object]]::new($Comparer)
    $seen = [Collections.Generic.HashSet[long]]::new()
    $duplicates = [Collections.Generic.HashSet[long]]::new()
    $unidentified = 0
    foreach ($line in $Lines) {
        if ($line -eq '') { continue }
        if ($line -cnotmatch '\A(\(no serial number\)|\S+)[ \t]+(\S+)(?:[ \t]+([^\r\n]*))?\z') {
            throw 'Invalid ADB inventory row.'
        }
        $serial = $Matches[1]
        $state = $Matches[2]
        $metadata = $Matches[3] -csplit '[ \t]+'
        $fields = @($metadata | Where-Object { $_ -clike 'transport_id:*' })
        $transport = 0L
        foreach ($field in $fields) {
            $number = 0L
            if ($field -cmatch '\Atransport_id:([1-9][0-9]{0,18})\z' -and [long]::TryParse($Matches[1], [ref]$number)) {
                # Even an unselectable row can claim a transport used by another headset.
                if (-not $seen.Add($number)) { [void]$duplicates.Add($number) }
                if ($fields.Count -eq 1) { $transport = $number }
            }
        }
        if ($serial -ceq '(no serial number)') { $unidentified++; continue }
        if ($devices.ContainsKey($serial)) { $state = 'ambiguous' }
        elseif ($state -ceq 'device' -and $transport -eq 0) { $state = 'transport-unavailable' }
        $device = @{ Status = $state; TransportId = $transport }
        $model = @($metadata | Where-Object { $_ -clike 'model:*' })
        if ($model.Count -eq 1 -and $model[0] -cmatch '\Amodel:[A-Za-z0-9._-]{1,128}\z') {
            $device.ModelHint = if ($model[0] -ceq 'model:Quest_3') { 'quest-3' } else { 'other-model' }
        }
        $devices[$serial] = $device
    }
    foreach ($device in $devices.Values) {
        if ($device.Status -ceq 'device' -and $duplicates.Contains($device.TransportId)) { $device.Status = 'transport-ambiguous' }
    }
    return @{ Devices = $devices; Unidentified = $unidentified }
}

function Invoke-QuestAdbProcess([string]$Executable, [string[]]$Arguments, [int]$TimeoutMilliseconds, [string]$Operation) {
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardInput = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    if ($start.PSObject.Properties['ArgumentList']) {
        foreach ($argument in $Arguments) { $start.ArgumentList.Add($argument) }
    } else {
        # Windows PowerShell uses the native Windows command-line form instead of ArgumentList.
        $start.Arguments = ($Arguments | ForEach-Object {
            '"' + ($_ -creplace '(\\*)"', '$1$1\"' -creplace '(\\+)$', '$1$1') + '"'
        }) -join ' '
    }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    $started = $false
    $outputStream = $errorStream = $null
    $clock = [Diagnostics.Stopwatch]::StartNew()
    try {
        $started = $process.Start()
        if (-not $started) { throw "Could not start ADB $Operation." }
        $process.StandardInput.Close()
        $outputStream = $process.StandardOutput
        $errorStream = $process.StandardError
        $stdout = $outputStream.ReadToEndAsync()
        $stderr = $errorStream.ReadToEndAsync()
        $remaining = [int][Math]::Max(0, $TimeoutMilliseconds - $clock.ElapsedMilliseconds)
        if ($process.WaitForExit($remaining)) {
            $remaining = [int][Math]::Max(0, $TimeoutMilliseconds - $clock.ElapsedMilliseconds)
            if ([Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($stdout, $stderr), $remaining)) {
                $reader = [IO.StringReader]::new($stdout.Result)
                try {
                    $lines = [Collections.Generic.List[string]]::new()
                    while ($null -ne ($line = $reader.ReadLine())) { $lines.Add($line) }
                    return [pscustomobject]@{ ExitCode = $process.ExitCode; Lines = $lines.ToArray() }
                } finally { $reader.Dispose() }
            }
        }
        throw [TimeoutException]::new("ADB $Operation timed out. Check the current device state before retrying.")
    } finally {
        try {
            if ($started -and -not $process.HasExited) {
                try { $process.Kill() }
                catch [InvalidOperationException] { if (-not $process.HasExited) { throw } }
                if (-not $process.WaitForExit(3000)) { throw "Could not stop the timed-out ADB $Operation client." }
            }
        } finally {
            if ($outputStream) { $outputStream.Dispose() }
            if ($errorStream) { $errorStream.Dispose() }
            $process.Dispose()
        }
    }
}
