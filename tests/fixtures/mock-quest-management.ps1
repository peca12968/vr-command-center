function Invoke-WebRequest {
    param($Uri, $Method, $ContentType, $Headers, $Body, [switch]$NoProxy,
          $MaximumRedirection, $TimeoutSec, [switch]$SkipHttpErrorCheck)
    if ($Uri.AbsolutePath -cne '/api/vr-deployment/venue-check' -or $Method -cne 'Post' -or
        $Headers.Authorization -cne 'Bearer fixture-master') { throw 'Unexpected management request' }
    $request = ConvertFrom-Json -InputObject $Body
    $stale = $request.requireLiveSource -and $env:VR_QUEST_TEST_SOURCE_STALE -and
        [IO.File]::Exists((Join-Path $env:VR_QUEST_FLEET_FIXTURE 'fixture-01/installed.apk'))
    $rows = foreach ($room in $request.rooms) {
        for ($seat = 0; $seat -lt $room.connectionFiles.Count; $seat++) {
            $status = if ($stale -and $room.roomId -eq 1 -and $seat -eq 0) { 'source-stale' } else { 'matched' }
            @{ roomId = $room.roomId; seat = $seat; status = $status; headset = 'Quest3' }
        }
    }
    $result = @{ topology = $request.topology; allMatched = -not $stale; seats = @($rows) }
    if ($request.requireLiveSource) { $result.liveSourceVerified = $result.allMatched }
    @{ StatusCode = 200; Content = ($result | ConvertTo-Json -Depth 5 -Compress) }
}
$options = $args[1..($args.Count - 1)]
& $args[0] @options
exit $LASTEXITCODE
