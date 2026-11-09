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
if ($args[2] -ceq 'push') {
    $null = [IO.Directory]::CreateDirectory($device)
    Copy-Item -LiteralPath $args[3] -Destination (Join-Path $device ($args[4].Split('/')[-1]))
    exit 0
}
if ($args[2] -cne 'shell') { exit 98 }
switch -CaseSensitive ($args[3]) {
    'getprop' {
        if ($args[4] -cne 'ro.product.model') { exit 98 }
        if ($fault -ceq 'wrong-model') { 'Quest 2' } else { 'Quest 3' }
        exit 0
    }
    'pm' {
        if (($args[4..10] -join ' ') -cne 'list packages -e --show-versioncode --user current com.vrcommand.quest') { exit 98 }
        if ($fault -ceq 'package-missing') { 'package:com.vrcommand.quest.other versionCode:61' }
        elseif ($fault -ceq 'version-mismatch') { 'package:com.vrcommand.quest versionCode:60' }
        else { 'package:com.vrcommand.quest versionCode:61' }
        exit 0
    }
    'mv' {
        $name = $args[5].Split('/')[-1]
        if ($name -ceq 'vr-connection.json' -and $fault -ceq 'config-move') { exit 1 }
        Move-Item -Force -LiteralPath (Join-Path $device ($args[4].Split('/')[-1])) -Destination (Join-Path $device $name)
        exit 0
    }
    'rm' {
        Remove-Item -LiteralPath (Join-Path $device ($args[5].Split('/')[-1])) -ErrorAction SilentlyContinue
        exit 0
    }
    { $_ -cin @('am', 'mkdir', 'monkey') } { exit 0 }
}
exit 98
