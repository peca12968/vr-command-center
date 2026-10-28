#Requires -Version 7.0
[CmdletBinding(SupportsShouldProcess)]
param([string]$EditorRoot = 'F:\Tools\UnityEditors\6000.3.27f1')
$ErrorActionPreference = 'Stop'
$editorDirectory = (Resolve-Path -LiteralPath $EditorRoot).Path
if ((Split-Path -Leaf $editorDirectory) -ne '6000.3.27f1' -or -not (Test-Path -LiteralPath (Join-Path $editorDirectory 'Editor/Unity.exe'))) {
    throw 'This repair only handles the known Unity 6000.3.27f1 Android module layout.'
}
$moduleRoot = [IO.Path]::GetFullPath((Join-Path $editorDirectory 'Editor/Data/PlaybackEngines/AndroidPlayer')).TrimEnd('\')
if (-not (Test-Path -LiteralPath $moduleRoot)) { throw 'Install Android Build Support before repairing its archive layout.' }
function Assert-ModulePath([string]$Path) {
    $absolute = [IO.Path]::GetFullPath($Path)
    if (-not $absolute.StartsWith($moduleRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing a path outside the named Android module: $absolute"
    }
    return $absolute
}
# Paths come from the selected official 6000.3.27f1 module metadata, not an arbitrary archive.
# Move only newly extracted children; never merge, overwrite or recursively delete a target.
$moves = [Collections.Generic.List[object]]::new()
$ndkRoot = Assert-ModulePath (Join-Path $moduleRoot 'NDK')
$nestedNdk = Assert-ModulePath (Join-Path $moduleRoot 'NDK/android-ndk-r27c')
if (-not (Test-Path -LiteralPath (Join-Path $ndkRoot 'source.properties'))) {
    if (-not (Test-Path -LiteralPath (Join-Path $nestedNdk 'source.properties'))) { throw 'Expected extracted NDK r27c files are missing.' }
    foreach ($child in Get-ChildItem -LiteralPath $nestedNdk -Force) {
        $moves.Add([pscustomobject]@{ Source = (Assert-ModulePath $child.FullName); Target = (Assert-ModulePath (Join-Path $ndkRoot $child.Name)) })
    }
}
$layouts = @(
    @{ Sources = @('SDK/cmake/cmake/cmake', 'SDK/cmake/cmake'); Target = 'SDK/cmake/3.22.1'; Marker = 'bin/cmake.exe' },
    @{ Sources = @('SDK/build-tools/android-16'); Target = 'SDK/build-tools/36.0.0'; Marker = 'aapt2.exe' },
    @{ Sources = @('SDK/cmdline-tools/cmdline-tools'); Target = 'SDK/cmdline-tools/16.0'; Marker = 'bin/sdkmanager.bat' }
)
foreach ($layout in $layouts) {
    $destination = Assert-ModulePath (Join-Path $moduleRoot $layout.Target)
    if (Test-Path -LiteralPath (Join-Path $destination $layout.Marker)) { continue }
    $sourceDirectory = $null
    foreach ($candidate in $layout.Sources) {
        $candidatePath = Assert-ModulePath (Join-Path $moduleRoot $candidate)
        if (Test-Path -LiteralPath (Join-Path $candidatePath $layout.Marker)) { $sourceDirectory = $candidatePath; break }
    }
    if (-not $sourceDirectory) { throw "Expected extracted component is missing: $($layout.Target)" }
    $moves.Add([pscustomobject]@{ Source = $sourceDirectory; Target = $destination })
}
# Validate every resolved absolute source and final target before any recursive directory move.
foreach ($move in $moves) {
    $sourcePath = Assert-ModulePath $move.Source; $targetPath = Assert-ModulePath $move.Target
    if (-not (Test-Path -LiteralPath $sourcePath) -or (Test-Path -LiteralPath $targetPath)) { throw "Unsafe or already occupied repair target: $targetPath" }
    if ((Get-Item -LiteralPath $sourcePath).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse points are not supported by this repair.' }
}
foreach ($move in $moves) {
    if ($PSCmdlet.ShouldProcess($move.Target, "Move extracted SDK component from $($move.Source)")) {
        Move-Item -LiteralPath $move.Source -Destination $move.Target
    }
}
if ($WhatIfPreference) { return }
$markers = @('NDK/source.properties', 'NDK/toolchains/llvm/prebuilt/windows-x86_64/bin/clang.exe', 'OpenJDK/bin/java.exe',
    'SDK/cmake/3.22.1/bin/cmake.exe', 'SDK/build-tools/36.0.0/aapt2.exe', 'SDK/platform-tools/adb.exe',
    'SDK/platforms/android-35/android.jar', 'SDK/cmdline-tools/16.0/bin/sdkmanager.bat')
foreach ($marker in $markers) {
    if (-not (Test-Path -LiteralPath (Join-Path $moduleRoot $marker))) { throw "Component verification failed: $marker" }
}
Write-Host 'Android module layout verified. Unity CLI registration and actual APK build still require separate verification.'
