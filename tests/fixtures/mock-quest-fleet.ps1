$root = $env:VR_QUEST_FLEET_FIXTURE
if (-not $root -or -not (Test-Path -LiteralPath $root -PathType Container)) { exit 97 }
$faults = if ($env:VR_QUEST_FLEET_FAULTS) { ConvertFrom-Json -InputObject $env:VR_QUEST_FLEET_FAULTS -AsHashtable } else { @{} }
[IO.File]::AppendAllText((Join-Path $root 'adb.log'), (($args -join ' ') + "`n"))
if ($args[0] -ceq 'devices') {
    'List of devices attached'
    "unmapped-device`tdevice"
    foreach ($index in 1..25) {
        $serial = 'fixture-{0:00}' -f $index
        $state = $faults[$serial]
        if ($state -ceq 'missing') { continue }
        if ($state -cnotin @('offline','unauthorized')) { $state = 'device' }
        "$serial`t$state"
    }
    exit 0
}

$serial = $args[1]
if ($args[0] -cne '-s' -or $serial -cnotmatch '\Afixture-(0[1-9]|1[0-9]|2[0-5])\z') { exit 99 }
$fault = $faults[$serial]
$device = Join-Path $root $serial
$versionCode = if ($env:VR_QUEST_FLEET_VERSION_CODE) { [int]$env:VR_QUEST_FLEET_VERSION_CODE } else { 61 }
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
if ($args[2] -cne 'shell') { exit 98 }
switch -CaseSensitive ($args[3]) {
    'getprop' {
        if ($args[4] -ceq 'ro.serialno') {
            if ($fault -ceq 'identity-missing') { exit 0 }
            if ($fault -ceq 'identity-invalid') { 'unknown'; exit 0 }
            if ($fault -ceq 'identity-duplicate') { 'HARDWARE-SERIAL-SHARED-CANARY'; exit 0 }
            if ($fault -ceq 'identity-changed') {
                $reads = @(Get-Content -LiteralPath (Join-Path $root 'adb.log') |
                    Where-Object { $_ -ceq "-s $serial shell getprop ro.serialno" })
                if ($reads.Count -gt 1) { 'HARDWARE-SERIAL-CHANGED-CANARY'; exit 0 }
            }
            "HARDWARE-SERIAL-$serial"
            exit 0
        }
        if ($args[4] -cne 'ro.product.model') { exit 98 }
        if ($fault -ceq 'wrong-model') { 'Quest 2' } else { 'Quest 3' }
        exit 0
    }
    'pm' {
        if (($args[4..7] -join ' ') -ceq 'path --user current com.vrcommand.quest') {
            if ($fault -ceq 'apk-path-malformed') { 'package:/data/app/base.apk;UNEXPECTED-COMMAND'; exit 0 }
            'package:/data/app/~~VRGameHash==/com.vrcommand.quest-XR_Package+=/base.apk'
            if ($fault -ceq 'apk-split') { 'package:/data/app/extra/split_config.arm64_v8a.apk' }
            exit 0
        }
        if (($args[4..10] -join ' ') -cne 'list packages -e --show-versioncode --user current com.vrcommand.quest') { exit 98 }
        if ($fault -ceq 'package-missing') { "package:com.vrcommand.quest.other versionCode:$versionCode" }
        elseif ($fault -ceq 'version-mismatch') { "package:com.vrcommand.quest versionCode:$($versionCode - 1)" }
        else { "package:com.vrcommand.quest versionCode:$versionCode" }
        exit 0
    }
    'mv' {
        $name = $args[5].Split('/')[-1]
        if ($name -ceq 'vr-connection.json' -and $fault -ceq 'config-move') { exit 1 }
        Move-Item -Force -LiteralPath (Join-Path $device ($args[4].Split('/')[-1])) -Destination (Join-Path $device $name)
        if ($name -ceq 'vr-connection.json' -and $fault -ceq 'config-active-changed') {
            [IO.File]::AppendAllText((Join-Path $device $name), "`n")
        }
        exit 0
    }
    'sha256sum' {
        $path = $args[4]
        if ($path -ceq '/data/app/~~VRGameHash==/com.vrcommand.quest-XR_Package+=/base.apk') {
            if ($fault -ceq 'apk-unreadable') { exit 1 }
            $hash = (Get-FileHash -LiteralPath $env:VR_QUEST_FLEET_APK -Algorithm SHA256).Hash.ToLowerInvariant()
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
        "$hash  $($args[4])"
        exit 0
    }
    'rm' {
        Remove-Item -LiteralPath (Join-Path $device ($args[5].Split('/')[-1])) -ErrorAction SilentlyContinue
        exit 0
    }
    'am' { if ($fault -ceq 'force-stop') { exit 1 }; exit 0 }
    'mkdir' { if ($fault -ceq 'directory') { exit 1 }; exit 0 }
    'monkey' {
        if ($fault -ceq 'launch') { exit 1 }
        if ($serial -ceq $env:VR_QUEST_FLEET_HOLD_AFTER_LAUNCH) {
            [IO.File]::WriteAllText((Join-Path $root 'first-launch.request'), 'original mock launch')
            $deadline = [DateTimeOffset]::UtcNow.AddSeconds(25)
            while (-not [IO.File]::Exists((Join-Path $root 'continue.request'))) {
                if ([DateTimeOffset]::UtcNow -ge $deadline) { exit 96 }
                Start-Sleep -Milliseconds 50
            }
        }
        exit 0
    }
}
exit 98
