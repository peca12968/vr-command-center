[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$result = [ordered]@{ version = 1; scope = 'windows-openxr-runtime-files'; complete = $false; source = $null; status = 'unsupported-platform' }

function Test-X64Dll([string]$Path) {
    $reader = [IO.BinaryReader]::new([IO.File]::OpenRead($Path))
    try {
        $stream = $reader.BaseStream
        if ($stream.Length -lt 64 -or $reader.ReadUInt16() -ne 0x5A4D) { return $false }
        $stream.Position = 60
        $header = $reader.ReadInt32()
        if ($header -lt 64 -or $header -gt $stream.Length - 26) { return $false }
        $stream.Position = $header
        if ($reader.ReadUInt32() -ne 0x4550 -or $reader.ReadUInt16() -ne 0x8664) { return $false }
        $stream.Position = $header + 20L
        $optionalSize = $reader.ReadUInt16()
        $flags = $reader.ReadUInt16()
        return ($flags -band 0x2000) -ne 0 -and $optionalSize -ge 112 -and
            $header + 24L + $optionalSize -le $stream.Length -and $reader.ReadUInt16() -eq 0x20B
    } finally { $reader.Dispose() }
}

function Test-LocalFullPath([string]$Path) {
    # Inspect local runtime files without following a network or device path.
    return $Path -match '\A[A-Za-z]:[\\/]' -and $Path.Substring(2) -notmatch '[:\x00-\x1f]'
}

function Inspect-OpenXrRuntime {
    if ($env:OS -ne 'Windows_NT') { return 'unsupported-platform' }
    $manifest = $env:XR_RUNTIME_JSON
    $result.source = if ($manifest) { 'environment' } else { 'registry64' }
    if (-not $manifest) {
        try {
            $hive = [Microsoft.Win32.RegistryKey]::OpenBaseKey('LocalMachine', 'Registry64')
            try {
                $key = $hive.OpenSubKey('SOFTWARE\Khronos\OpenXR\1')
                if ($null -ne $key) {
                    try { $manifest = $key.GetValue('ActiveRuntime', $null, 'DoNotExpandEnvironmentNames') }
                    finally { $key.Dispose() }
                }
            } finally { $hive.Dispose() }
        } catch { return 'registry-unreadable' }
        if ($null -eq $manifest -or $manifest -ceq '') { return 'runtime-not-configured' }
    }
    if ($manifest -isnot [string] -or -not (Test-LocalFullPath $manifest)) { return 'manifest-path-invalid' }
    try {
        $file = [IO.File]::OpenRead($manifest)
        try {
            $size = $file.Length
            if ($size -lt 1 -or $size -gt 65536) { return 'manifest-invalid' }
            $reader = [IO.BinaryReader]::new($file, [Text.Encoding]::UTF8, $true)
            try {
                $raw = $reader.ReadBytes([int]$size)
                if ($raw.Length -ne $size -or $file.ReadByte() -ne -1) { return 'manifest-invalid' }
                $json = [Text.UTF8Encoding]::new($false, $true).GetString($raw).TrimStart([char]0xFEFF)
                $doc = ConvertFrom-Json -InputObject $json
            } finally { $reader.Dispose() }
        } finally { $file.Dispose() }
    } catch [IO.FileNotFoundException], [IO.DirectoryNotFoundException] { return 'manifest-missing' }
    catch { return 'manifest-invalid' }
    if (-not $json.TrimStart().StartsWith('{') -or $doc.file_format_version -isnot [string] -or
        $doc.file_format_version -cne '1.0.0' -or $doc.runtime.library_path -isnot [string] -or
        $doc.runtime.library_path -notmatch '(?i)\.dll\z') { return 'manifest-invalid' }
    $library = $doc.runtime.library_path
    if ($library -notmatch '[\\/]') { return 'library-search-required' }
    if (-not [IO.Path]::IsPathRooted($library)) {
        $library = [IO.Path]::Combine([IO.Path]::GetDirectoryName($manifest), $library)
    }
    if (-not (Test-LocalFullPath $library)) { return 'library-path-invalid' }
    try {
        if (Test-X64Dll $library) { return 'x64-runtime-files-found' }
        return 'library-not-x64-dll'
    } catch [IO.FileNotFoundException], [IO.DirectoryNotFoundException] { return 'library-missing' }
    catch { return 'library-unreadable' }
}

$result.status = Inspect-OpenXrRuntime
$result.complete = $result.status -ceq 'x64-runtime-files-found'
$result | ConvertTo-Json -Compress
if (-not $result.complete) { exit 1 }
