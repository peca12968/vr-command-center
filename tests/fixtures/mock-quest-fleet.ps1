$root = $env:VR_QUEST_FLEET_FIXTURE
if (-not $root -or -not (Test-Path -LiteralPath $root -PathType Container)) { exit 97 }
$faults = if ($env:VR_QUEST_FLEET_FAULTS) { ConvertFrom-Json -InputObject $env:VR_QUEST_FLEET_FAULTS -AsHashtable } else { @{} }
$transportBase = if ($env:VR_QUEST_FLEET_TRANSPORT_BASE) { [int]$env:VR_QUEST_FLEET_TRANSPORT_BASE } else { 100 }
[IO.File]::AppendAllText((Join-Path $root 'transport.log'), (($args -join ' ') + "`n"))
if ($args[0] -ceq '-t') {
    $transport = 0
    if (-not [int]::TryParse($args[1], [ref]$transport) -or $transport -le $transportBase -or $transport -gt $transportBase + 25) { exit 99 }
    $args[0] = '-s'
    $args[1] = 'fixture-{0:00}' -f ($transport - $transportBase)
    if ([IO.File]::Exists((Join-Path $root "disconnected-$($args[1])"))) { exit 1 }
}
if ($args[0] -ceq '-s' -and [IO.File]::Exists((Join-Path $root "disconnected-$($args[1])"))) {
    [IO.File]::AppendAllText((Join-Path $root 'replacement-device.log'), (($args[2..($args.Count - 1)] -join ' ') + "`n"))
    if (($args[2..4] -join ' ') -cne 'shell am force-stop') { exit 1 }
    exit 0
}
[bool]$longInventory = $args[0] -ceq 'devices' -and $args[1] -ceq '-l'
if ($longInventory) { $args = @('devices') }
[IO.File]::AppendAllText((Join-Path $root 'adb.log'), (($args -join ' ') + "`n"))
if ($args[0] -ceq 'devices') {
    'List of devices attached'
    if ($longInventory) { 'unmapped-device   device transport_id:1' } else { "unmapped-device`tdevice" }
    foreach ($index in 1..25) {
        $serial = 'fixture-{0:00}' -f $index
        $state = $faults[$serial]
        if ($state -ceq 'missing') { continue }
        if ($state -cnotin @('offline','unauthorized')) { $state = 'device' }
        if ($longInventory) {
            $id = if ($faults[$serial] -ceq 'transport-duplicate') { $transportBase + 1 } else { $transportBase + $index }
            $suffix = if ($faults[$serial] -ceq 'transport-missing') { '' } else { " transport_id:$id" }
            "$serial   $state$suffix"
        } else { "$serial`t$state" }
    }
    exit 0
}

$serial = $args[1]
if ($args[0] -cne '-s' -or $serial -cnotmatch '\Afixture-(0[1-9]|1[0-9]|2[0-5])\z') { exit 99 }
$fault = $faults[$serial]
$device = Join-Path $root $serial
$installedApk = Join-Path $device 'installed.apk'
$appMissing = ($env:VR_QUEST_FLEET_FRESH -csplit ',') -ccontains $serial -and -not [IO.File]::Exists($installedApk)
$gamePid = 4300 + [int]$serial.Substring(8)
$openxrProbe = Join-Path $device 'openxr-probe'
$versionCode = if ($env:VR_QUEST_FLEET_VERSION_CODE) { [int]$env:VR_QUEST_FLEET_VERSION_CODE } else { 61 }
$upgradedMarker = Join-Path $device 'upgraded-apk'
$previouslyInstalled = ($env:VR_QUEST_FLEET_PREVIOUS -csplit ',') -ccontains $serial -and -not [IO.File]::Exists($upgradedMarker)
if ($previouslyInstalled) { $versionCode = [int]$env:VR_QUEST_FLEET_PREVIOUS_VERSION_CODE }
if ($args[2] -ceq 'install') {
    if ($args.Count -ne 9 -or $args[3] -cnotin @('-R','-r') -or ($args[4..7] -join ' ') -cne '--user current --pkg com.vrcommand.quest') { exit 98 }
    $upgrade = $args[3] -ceq '-r'
    if ($fault -cin @('install-failed','upgrade-failed') -or ($upgrade -and (-not $previouslyInstalled -or $appMissing)) -or
        (-not $upgrade -and -not $appMissing)) { exit 1 }
    $null = [IO.Directory]::CreateDirectory($device)
    Copy-Item -LiteralPath $args[8] -Destination $installedApk
    if ($upgrade) { [IO.File]::WriteAllText($upgradedMarker, 'replaced') }
    if ($fault -ceq 'installed-apk-mismatch') { [IO.File]::AppendAllText($installedApk, 'different APK bytes') }
    'Success'
    exit 0
}
if ($args[2] -ceq 'push') {
    $null = [IO.Directory]::CreateDirectory($device)
    $file = Join-Path $device ($args[4].Split('/')[-1])
    Copy-Item -LiteralPath $args[3] -Destination $file
    if (($fault -ceq 'config-stage-changed' -and $args[4].Contains('/vr-connection-')) -or
        ($fault -ceq 'alignment-stage-changed' -and $args[4].Contains('/vr-room-alignment-'))) {
        [IO.File]::AppendAllText($file, "`n")
    }
    exit 0
}
if ($args[2] -ceq 'logcat') {
    if (($args[3..11] -join ' ') -cne "-d -t 1000 --pid=$gamePid -v brief -s Unity AndroidRuntime") { exit 98 }
    $nonce = [IO.File]::ReadAllText($openxrProbe)
    $inputRunning = if ($fault -ceq 'xr-not-ready') { 0 } else { 1 }
    "I/Unity  ($gamePid): VR_QUEST_OPENXR nonce=$nonce loader=1 display=1 input=$inputRunning"
    exit 0
}
if ($args[2] -cne 'shell') { exit 98 }
switch -CaseSensitive ($args[3]) {
    'getprop' {
        if ($args[4] -ceq 'ro.serialno') {
            if (($fault -ceq 'swap-after-install' -and [IO.File]::Exists($installedApk)) -or
                ($fault -ceq 'swap-after-staging' -and (Get-ChildItem -LiteralPath $device -Filter 'vr-connection-*.tmp' -ErrorAction SilentlyContinue)) -or
                ($fault -ceq 'swap-before-install' -and [IO.File]::Exists((Join-Path $root "before-install-$serial")))) {
                'HARDWARE-SERIAL-REPLACEMENT'; exit 0
            }
            if ($fault -ceq 'identity-timeout') { throw [TimeoutException]::new('ADB shell command timed out.') }
            if ($fault -ceq 'identity-missing') { exit 0 }
            if ($fault -ceq 'identity-invalid') { 'unknown'; exit 0 }
            if ($fault -ceq 'identity-duplicate') { 'HARDWARE-SERIAL-SHARED-CANARY'; exit 0 }
            if ($fault -ceq 'identity-first-device') { 'HARDWARE-SERIAL-fixture-01'; exit 0 }
            if ($fault -ceq 'identity-changed') {
                $reads = @(Get-Content -LiteralPath (Join-Path $root 'adb.log') |
                    Where-Object { $_ -ceq "-s $serial shell getprop ro.serialno" })
                if ($reads.Count -gt 1) { 'HARDWARE-SERIAL-CHANGED-CANARY'; exit 0 }
            }
            "HARDWARE-SERIAL-$serial"
            exit 0
        }
        if ($args[4] -cne 'ro.product.model') { exit 98 }
        if ($fault -ceq 'model-timeout') { throw [TimeoutException]::new('ADB shell command timed out.') }
        if ($fault -ceq 'wrong-model') { 'Quest 2' } else { 'Quest 3' }
        exit 0
    }
    'pm' {
        if ($fault -ceq 'upgrade-disappeared' -and @(Get-Content -LiteralPath (Join-Path $root 'adb.log') |
            Where-Object { $_ -ceq "-s $serial shell pm list packages -e --show-versioncode --user current com.vrcommand.quest" }).Count -gt 1) {
            $appMissing = $true
        }
        if (($args[4..9] -join ' ') -ceq 'list packages -u --user current com.vrcommand.quest') {
            if ($fault -ceq 'swap-before-install') {
                $query = $args -join ' '
                $calls = @(Get-Content -LiteralPath (Join-Path $root 'adb.log') | Where-Object { $_ -ceq $query })
                if ($calls.Count -ge 2) { [IO.File]::WriteAllText((Join-Path $root "before-install-$serial"), 'swapped') }
            }
            if (-not $appMissing -or $fault -ceq 'package-disabled') { 'package:com.vrcommand.quest' }
            exit 0
        }
        if (($args[4..13] -join ' ') -ceq 'resolve-activity --brief --user current -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p com.vrcommand.quest') {
            if ($fault -ceq 'missing-activity') { 'No activity found'; exit 0 }
            'com.vrcommand.quest/com.unity3d.player.UnityPlayerActivity'
            exit 0
        }
        if (($args[4..7] -join ' ') -ceq 'path --user current com.vrcommand.quest') {
            if ($fault -ceq 'apk-path-malformed') { 'package:/data/app/base.apk;UNEXPECTED-COMMAND'; exit 0 }
            'package:/data/app/~~VRGameHash==/com.vrcommand.quest-XR_Package+=/base.apk'
            if ($fault -ceq 'apk-split') { 'package:/data/app/extra/split_config.arm64_v8a.apk' }
            exit 0
        }
        if (($args[4..10] -join ' ') -cne 'list packages -e --show-versioncode --user current com.vrcommand.quest') { exit 98 }
        if ($appMissing -or $fault -ceq 'package-disabled') { exit 0 }
        if ($fault -ceq 'package-missing') { "package:com.vrcommand.quest.other versionCode:$versionCode" }
        elseif ($fault -ceq 'version-mismatch') { "package:com.vrcommand.quest versionCode:$($versionCode - 1)" }
        else { "package:com.vrcommand.quest versionCode:$versionCode" }
        exit 0
    }
    { $_.StartsWith('staged=$(sha256sum ') } {
        if ($args.Count -ne 4) { exit 96 }
        $isConnection = $args[3].EndsWith("/vr-connection.json'")
        if ($isConnection -and $fault -ceq 'config-move') { exit 1 }
        $shell = (Get-Command sh -ErrorAction SilentlyContinue).Source
        if (-not $shell -and $env:OS -eq 'Windows_NT') {
            $shell = Join-Path (Split-Path (Split-Path (Get-Command git).Source)) 'bin/sh.exe'
        }
        Push-Location -LiteralPath $device
        try { & $shell -c $args[3].Replace('/sdcard/Android/data/com.vrcommand.quest/files/', './') }
        finally { Pop-Location }
        if ($LASTEXITCODE -eq 0 -and $isConnection -and $fault -ceq 'config-active-changed') {
            [IO.File]::AppendAllText((Join-Path $device 'vr-connection.json'), "`n")
        }
        if ($LASTEXITCODE -eq 0 -and $isConnection -and $fault -ceq 'alignment-changed-after-activation') {
            $alignment = Get-ChildItem -LiteralPath $device -Filter 'vr-room-alignment-*.json' -File
            if (@($alignment).Count -ne 1) { exit 96 }
            [IO.File]::AppendAllText($alignment.FullName, "`n")
        }
        exit $LASTEXITCODE
    }
    'sha256sum' {
        $path = $args[4]
        if ($path -ceq '/data/app/~~VRGameHash==/com.vrcommand.quest-XR_Package+=/base.apk') {
            if ($fault -ceq 'apk-unreadable') { exit 1 }
            $apk = if ([IO.File]::Exists($installedApk)) { $installedApk } else { $env:VR_QUEST_FLEET_APK }
            $hash = (Get-FileHash -LiteralPath $apk -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($fault -ceq 'apk-changed') {
                $reads = @(Get-Content -LiteralPath (Join-Path $root 'adb.log') |
                    Where-Object { $_ -ceq "-s $serial shell sha256sum $path" })
                if ($reads.Count -gt 1) { $hash = '0' * 64 }
            }
            if ($fault -ceq 'apk-hash-mismatch') { $hash = '0' * 64 }
            if ($fault -ceq 'apk-hash-wrong-path') { "$hash  /data/app/other/base.apk"; exit 0 }
            "$hash  $path"
            exit 0
        }
        $file = Join-Path $device ($args[4].Split('/')[-1])
        $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($serial -ceq $env:VR_QUEST_FLEET_HOLD_AFTER_STAGE -and $path -cmatch '/vr-connection-[0-9a-f]+\.tmp$') {
            [IO.File]::WriteAllText((Join-Path $root 'connection-staged.request'), $hash)
            $deadline = [DateTimeOffset]::UtcNow.AddSeconds(25)
            while (-not [IO.File]::Exists((Join-Path $root 'continue.request'))) {
                if ([DateTimeOffset]::UtcNow -ge $deadline) { exit 96 }
                Start-Sleep -Milliseconds 50
            }
        }
        if ($fault -ceq 'disconnect-after-staging' -and $path -cmatch '/vr-connection-[0-9a-f]+\.tmp$') {
            [IO.File]::WriteAllText((Join-Path $root "disconnected-$serial"), 'The original transport went away')
        }
        "$hash  $($args[4])"
        exit 0
    }
    'rm' {
        Remove-Item -LiteralPath (Join-Path $device ($args[5].Split('/')[-1])) -ErrorAction SilentlyContinue
        exit 0
    }
    'pidof' {
        if ($args[4] -cne 'com.vrcommand.quest' -or -not (Test-Path -LiteralPath $openxrProbe)) { exit 1 }
        $gamePid
        exit 0
    }
    'ps' {
        if (($args[4..7] -join ' ') -cne '-A -w -o NAME') { exit 98 }
        if ($fault -ceq 'app-query-failed') { 'UNEXPECTED-HEADER'; exit 0 }
        'NAME'
        'init'
        if ($fault -ceq 'app-running') { 'com.vrcommand.quest:worker' }
        if ($fault -ceq 'app-started' -and @(Get-Content -LiteralPath (Join-Path $root 'adb.log') |
            Where-Object { $_ -ceq "-s $serial shell ps -A -w -o NAME" }).Count -gt 1) {
            'com.vrcommand.quest'
        }
        exit 0
    }
    'am' {
        if ($fault -ceq 'force-stop') { exit 1 }
        if ($args[4] -ceq 'force-stop' -and $fault -ceq 'config-changed-at-stop') {
            $staging = Get-ChildItem -LiteralPath $device -Filter 'vr-connection-*.tmp' -File
            if (@($staging).Count -ne 1) { exit 96 }
            [IO.File]::AppendAllText($staging.FullName, "`n")
        }
        if ($args[4] -ceq 'force-stop' -and $fault -ceq 'alignment-changed-at-stop') {
            $alignment = Get-ChildItem -LiteralPath $device -Filter 'vr-room-alignment-*.json' -File
            if (@($alignment).Count -ne 1) { exit 96 }
            [IO.File]::AppendAllText($alignment.FullName, "`n")
        }
        if ($args[4] -ceq 'start') {
            $activity = 'com.vrcommand.quest/com.unity3d.player.UnityPlayerActivity'
            $expected = "-W --user current -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n $activity"
            if (($args[5..13] -join ' ') -cne $expected) { exit 98 }
            if ($args.Count -gt 14) {
                if ($args.Count -ne 17 -or ($args[14..15] -join ' ') -cne '--es com.vrcommand.quest.OPENXR_PROBE' -or
                    $args[16] -cnotmatch '\A[a-f0-9]{32}\z') { exit 98 }
                [IO.File]::WriteAllText($openxrProbe, $args[16])
            }
            if ($fault -ceq 'launch') { 'Status: timeout'; exit 0 }
            if ($serial -ceq $env:VR_QUEST_FLEET_HOLD_AFTER_LAUNCH) {
                [IO.File]::WriteAllText((Join-Path $root 'first-launch.request'), 'original mock launch')
                $deadline = [DateTimeOffset]::UtcNow.AddSeconds(25)
                while (-not [IO.File]::Exists((Join-Path $root 'continue.request'))) {
                    if ([DateTimeOffset]::UtcNow -ge $deadline) { exit 96 }
                    Start-Sleep -Milliseconds 50
                }
            }
            'Status: ok'
            "Activity: $activity"
        }
        exit 0
    }
    'mkdir' { if ($fault -ceq 'directory') { exit 1 }; exit 0 }
}
exit 98
