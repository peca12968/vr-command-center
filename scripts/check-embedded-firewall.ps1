#requires -Version 7.2
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Control,
    [Parameter(Mandatory)][string]$Server,
    [Parameter(Mandatory)][string]$Player
)

$ErrorActionPreference = 'Stop'
$expected = [IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'check-windows-firewall-notifications.ps1'))
$expectedHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($expected)).ToLowerInvariant()
$launchers = [ordered]@{}
foreach ($path in @($Control, $Server, $Player)) {
    $inputFile = [IO.File]::OpenRead($path)
    try {
        $hash = (Get-FileHash -InputStream $inputFile -Algorithm SHA256).Hash.ToLowerInvariant()
        $inputFile.Position = 0
        $pe = [Reflection.PortableExecutable.PEReader]::new($inputFile)
        try {
            $metadata = [Reflection.Metadata.PEReaderExtensions]::GetMetadataReader($pe)
            $directory = $pe.PEHeaders.CorHeader.ResourcesDirectory
            $section = $pe.GetSectionData($directory.RelativeVirtualAddress)
            $matchesFound = 0
            foreach ($handle in $metadata.ManifestResources) {
                $resource = $metadata.GetManifestResource($handle)
                if ($metadata.GetString($resource.Name) -cne 'FirewallPreflight.ps1') { continue }
                if (-not $resource.Implementation.IsNil -or $resource.Offset -gt $directory.Size - 4) {
                    throw "Invalid embedded firewall check in $path"
                }
                $offset = [int]$resource.Offset
                $length = [BitConverter]::ToInt32([byte[]]$section.GetContent($offset, 4), 0)
                if ($length -ne $expected.Length) { throw "Outdated embedded firewall check in $path" }
                if ($length -gt $directory.Size - $offset - 4) { throw "Truncated embedded firewall check in $path" }
                $content = [byte[]]$section.GetContent(($offset + 4), $length)
                if ([Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($content)) -ne $expectedHash) {
                    throw "Outdated embedded firewall check in $path"
                }
                $matchesFound++
            }
            if ($matchesFound -ne 1) { throw "Expected one embedded firewall check in $path" }
        } finally { $pe.Dispose() }
        $launchers.Add([IO.Path]::GetFileName($path), $hash)
    } finally { $inputFile.Dispose() }
}
[ordered]@{ scriptSha256 = $expectedHash; launchers = $launchers } | ConvertTo-Json -Compress
