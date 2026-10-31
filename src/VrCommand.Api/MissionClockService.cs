using VrCommand.Core;
using VrCommand.Simulation;

namespace VrCommand.Api;

// No HTTP request is given an Internal actor. Only accepted world frames drive automatic expiry.
public sealed class MissionClockService(WorldRecordings worlds) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromMilliseconds(250));
        while (await timer.WaitForNextTickAsync(stoppingToken)) worlds.ExpireMissionClocks();
    }
}

public sealed partial class WorldRecordings
{
    public int ExpireMissionClocks()
    {
        var actor = SessionManager.ClockIdentity; var expired = 0;
        foreach (var session in manager.ClockCandidates(actor))
        {
            WorldRecordingInfo info;
            try { info = Info(session.Id, actor); }
            catch (KeyNotFoundException) { continue; }
            if (info.Complete || info.Header.missionClockVersion != 1 || info.Header.missionDurationSeconds != session.Mission.Definition.DurationSeconds
                || info.Header.streamId != session.CombatStream!.StreamId.ToString("D") || info.AcceptedSequence == 0) continue;
            var last = Frame(session.Id, info.AcceptedSequence, actor)?.Packet;
            if (last is null || last.frame.phase is not ("Running" or "Paused") || last.observedSequence < session.MissionClock!.ConfiguredAtSequence
                || !MissionClock.Due(last.frame.tick, info.Header.missionDurationSeconds)) continue;
            if (manager.ExpireMission(session.Id, new(session.CombatStream.StreamId, last.observedSequence, last.frame.tick), actor)) expired++;
        }
        return expired;
    }
}
