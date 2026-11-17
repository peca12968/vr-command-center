param(
    [ValidateSet('Prepare', 'Desktop', 'Quest', 'Tests')][string]$Target = 'Prepare',
    [string]$EditorPath = 'F:\Tools\UnityEditors\6000.3.27f1\Editor\Unity.exe'
)
$ErrorActionPreference = 'Stop'
trap { Write-Error $_ -ErrorAction Continue; exit 1 }
$env:VR_COMMAND_UNATTENDED = '1'
. (Join-Path $PSScriptRoot 'windows-process.ps1')
$projectRoot = Split-Path -Parent $PSScriptRoot
$unityProject = Join-Path $projectRoot 'clients/unity'
$logDirectory = Join-Path $projectRoot 'artifacts/unity-logs'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$editor = Get-Item -LiteralPath $EditorPath
if ($editor -isnot [IO.FileInfo]) { throw "Unity Editor not found at $EditorPath" }
$EditorPath = $editor.FullName
$packageManager = Join-Path (Split-Path -Parent $EditorPath) 'Data/Resources/PackageManager/Server/UnityPackageManager.exe'
if (-not (Test-Path -LiteralPath $packageManager)) { throw 'Unity installation is not complete: the Package Manager component is missing. Wait for the active installer to finish.' }
foreach ($program in @($EditorPath, $packageManager)) {
    & (Join-Path $PSScriptRoot 'check-windows-firewall-notifications.ps1') -Executable $program -Unattended
    if ($LASTEXITCODE -ne 0) { throw "Unity startup skipped after the Windows Firewall check for $program." }
}
$method = switch ($Target) {
    'Prepare' { 'Prepare' }
    'Desktop' { 'BuildDesktop' }
    'Quest' { 'BuildQuest' }
}
$logPath = Join-Path $logDirectory ($Target.ToLowerInvariant() + '.log')
$editorArgs = @('-batchmode', '-nographics', '-quit', '-projectPath', $unityProject,
    '-executeMethod', "VrCommand.Unity.Editor.ProjectBuilder.$method", '-logFile', $logPath)
if ($Target -eq 'Quest') { $editorArgs += @('-buildTarget', 'Android') }
if ($Target -eq 'Desktop') { $editorArgs += @('-buildTarget', 'Win64') }
if ($Target -eq 'Tests') {
    $resultsPath = Join-Path $logDirectory 'editmode-results.xml'
    $editorArgs = @('-batchmode', '-nographics', '-projectPath', $unityProject, '-runTests', '-testPlatform', 'EditMode',
        '-testResults', $resultsPath, '-logFile', $logPath)
}
$startedAt = [DateTime]::UtcNow
$exitCode = Invoke-UnattendedWindowsProcess -Executable $EditorPath -Arguments $editorArgs -WorkingDirectory (Get-Location).ProviderPath
if ($exitCode -ne 0) { throw "Unity $Target exited with code $exitCode. Log: $logPath" }
$expectedOutput = switch ($Target) {
    'Prepare' { Join-Path $unityProject 'Assets/VrCommand/Generated/Arena.unity' }
    'Desktop' { Join-Path $projectRoot 'artifacts/desktop/VrCommand.exe' }
    'Quest' { Join-Path $projectRoot 'artifacts/quest/VrCommand.apk' }
    'Tests' { $resultsPath }
}
if (-not (Test-Path -LiteralPath $expectedOutput)) {
    throw "Unity did not produce a $Target output. Log: $logPath"
}
if ($Target -in @('Desktop', 'Quest')) {
    $receiptPath = Join-Path (Split-Path -Parent $expectedOutput) 'build-receipt.json'
    if (-not (Test-Path -LiteralPath $receiptPath) -or (Get-Item -LiteralPath $receiptPath).LastWriteTimeUtc -lt $startedAt.AddSeconds(-2)) {
        throw "Unity did not produce a fresh build receipt. Log: $logPath"
    }
    $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
    $expectedTarget = if ($Target -eq 'Quest') { 'Android' } else { 'StandaloneWindows64' }
    if ($receipt.schemaVersion -ne 1 -or $receipt.target -ne $expectedTarget -or [IO.Path]::GetFullPath($receipt.outputPath) -ne [IO.Path]::GetFullPath($expectedOutput) -or $receipt.sourceFingerprint -notmatch '^[a-f0-9]{64}$') {
        throw "Unity build receipt does not match $Target. Log: $logPath"
    }
} elseif ((Get-Item -LiteralPath $expectedOutput).LastWriteTimeUtc -lt $startedAt.AddSeconds(-2)) {
    throw "Unity did not produce a fresh $Target output. Log: $logPath"
}
if ($Target -eq 'Tests') {
    [xml]$results = Get-Content -LiteralPath $resultsPath -Raw
    $run = $results.'test-run'
    if (-not $run -or $run.result -ne 'Passed' -or [int]$run.total -lt 224 -or [int]$run.failed -ne 0) {
        throw "Unity EditMode checks did not pass. Results: $resultsPath"
    }
}
Write-Host "Unity $Target succeeded. Log: $logPath"
exit 0
