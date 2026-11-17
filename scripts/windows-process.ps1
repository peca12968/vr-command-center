function Invoke-UnattendedWindowsProcess {
    param([string]$Executable, [string[]]$Arguments, [string]$WorkingDirectory)

    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.WorkingDirectory = $WorkingDirectory
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.EnvironmentVariables['VR_COMMAND_UNATTENDED'] = '1'
    if ($start.PSObject.Properties['ArgumentList']) {
        foreach ($argument in $Arguments) { $start.ArgumentList.Add($argument) }
    } else {
        # Windows PowerShell uses a single native command line.
        $start.Arguments = ($Arguments | ForEach-Object {
            '"' + ($_ -creplace '(\\*)"', '$1$1\"' -creplace '(\\+)$', '$1$1') + '"'
        }) -join ' '
    }

    try {
        $child = [Diagnostics.Process]::Start($start)
    } catch {
        $failure = $_.Exception.GetBaseException()
        if ($failure -is [ComponentModel.Win32Exception] -and $failure.NativeErrorCode -eq 740) {
            throw "Startup skipped for $Executable. Windows requires elevation for this executable."
        }
        throw
    }
    try {
        $child.WaitForExit()
        return $child.ExitCode
    } finally { $child.Dispose() }
}
