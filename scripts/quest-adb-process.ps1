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
