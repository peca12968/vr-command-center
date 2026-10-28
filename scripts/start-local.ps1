param([int]$Port = 5080)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$dataPath = Join-Path $projectRoot 'data'
$keyPath = Join-Path $dataPath 'operator-keys.local.json'
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Use a port between 1024 and 65535.' }
if (-not (Test-Path -LiteralPath $keyPath)) {
    New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
    $keys = [ordered]@{}
    foreach ($name in @('Master', 'Room1', 'Room2', 'Room3', 'Room4', 'Room5', 'GameServer')) {
        $keys[$name] = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
    }
    @{ OperatorKeys = $keys } | ConvertTo-Json | Set-Content -LiteralPath $keyPath -Encoding utf8NoBOM
}
Write-Host "Local credential file: $keyPath (excluded from Git; keys are not printed)"
Write-Host "Operator console: http://127.0.0.1:$Port/console/"
Push-Location $projectRoot
try {
    dotnet run --project src/VrCommand.Api --configuration Release -- --urls "http://127.0.0.1:$Port" --OperatorKeyFile $keyPath
    if ($LASTEXITCODE -ne 0) { throw 'API exited with an error.' }
}
finally { Pop-Location }
