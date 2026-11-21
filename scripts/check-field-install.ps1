[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Archive,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ArchiveSha256,
    [Parameter(Mandatory)][string]$InstallDirectory,
    [ValidateSet('All','Control','Server','Player','Quest','Hardware')][string]$Role = 'All'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression
$folders = @{ Control = 'VRCommand-ControlServer'; Server = 'VRCommand-GameServer'; Player = 'VRCommand-Player'
    Quest = 'Quest'; Hardware = 'VRCommand-HardwareSimulator' }
$prefix = if ($Role -eq 'All') { '' } else { $folders[$Role] + '/' }
$root = Get-Item -LiteralPath $InstallDirectory -Force
if (-not $root.PSIsContainer) { throw 'Choose the installed package directory.' }
$files = [Collections.Generic.Dictionary[string,IO.FileInfo]]::new([StringComparer]::OrdinalIgnoreCase)
$pending = [Collections.Generic.Stack[IO.DirectoryInfo]]::new()
$pending.Push($root)
while ($pending.Count -gt 0) {
    $dir = $pending.Pop()
    if ($dir.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked directory: $($dir.Name)" }
    foreach ($item in $dir.EnumerateFileSystemInfos()) {
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked package entry: $($item.Name)" }
        if ($item -is [IO.DirectoryInfo]) {
            $pending.Push($item)
        } else {
            $relative = $item.FullName.Substring($root.FullName.TrimEnd('\','/').Length + 1).Replace('\','/')
            $files.Add($relative, $item)
        }
    }
}

$archivePath = (Get-Item -LiteralPath $Archive).FullName
$inputFile = [IO.File]::OpenRead($archivePath)
try {
    if ((Get-FileHash -InputStream $inputFile -Algorithm SHA256).Hash -ne $ArchiveSha256) {
        throw 'Archive SHA-256 differs from the supplied delivery digest.'
    }
    $inputFile.Position = 0
    $zip = [IO.Compression.ZipArchive]::new($inputFile, [IO.Compression.ZipArchiveMode]::Read, $true)
    try {
        $verified = 0
        foreach ($entry in $zip.Entries) {
            if (-not $entry.Name -or -not $entry.FullName.StartsWith($prefix, [StringComparison]::Ordinal)) { continue }
            $name = $entry.FullName.Substring($prefix.Length)
            if (-not $files.ContainsKey($name)) { throw "Missing package file: $name" }
            $file = $files[$name]
            if ($file.Length -ne $entry.Length) { throw "Package file size differs: $name" }
            $packed = $entry.Open()
            try { $expected = (Get-FileHash -InputStream $packed -Algorithm SHA256).Hash }
            finally { $packed.Dispose() }
            if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne $expected) {
                throw "Package file content differs: $name"
            }
            [void]$files.Remove($name)
            $verified++
        }
        if ($verified -eq 0) { throw "No files for role $Role in this delivery." }
        if ($files.Count) { throw ('Unexpected package file: ' + ($files.Keys | Select-Object -First 1)) }
    } finally { $zip.Dispose() }
} finally { $inputFile.Dispose() }

[ordered]@{ verified = $true; scope = 'installed-files'; role = $Role; files = $verified
    archiveSha256 = $ArchiveSha256.ToLowerInvariant() } | ConvertTo-Json -Compress
