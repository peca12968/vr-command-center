using System.Security.Cryptography;
using System.Text;
using VrCommand.Simulation;

namespace VrCommand.Core;

public sealed partial class SessionManager
{
    // Never issued by HTTP authentication. A service reads already accepted source frames before calling this.
    public static OperatorIdentity ClockIdentity { get; } = new("mission-clock", OperatorRole.Internal);
    public SessionView[] ClockCandidates(OperatorIdentity actor)
    {
        if (actor != ClockIdentity) throw new AccessDeniedException("Only the internal mission clock may read expiry candidates.");
        lock (gate) return Active().Where(s => s.MissionClock is { AutoEnd: true, Version: 1 }
            && s.State is SessionState.Running or SessionState.Paused).Select(Snapshot).ToArray();
    }
    internal static void ValidateClockExpiration(SessionView view, MissionClockExpiration evidence)
    {
        if (view.MissionClock is not { AutoEnd: true, Version: 1 } clock || view.CombatStream is not { MissionClockVersion: 1 } stream
            || evidence.StreamId != stream.StreamId || evidence.ObservedSequence < clock.ConfiguredAtSequence
            || evidence.ObservedSequence > view.Sequence || view.State is not (SessionState.Running or SessionState.Paused)
            || !MissionClock.Due(evidence.Tick, view.Mission.Definition.DurationSeconds))
            throw new InvalidOperationException("Mission clock evidence does not satisfy the configured deadline.");
    }
    public bool ExpireMission(Guid id, MissionClockExpiration evidence, OperatorIdentity actor)
    {
        ArgumentNullException.ThrowIfNull(evidence);
        if (actor != ClockIdentity) throw new AccessDeniedException("Only the internal mission clock may expire a session.");
        lock (gate)
        {
            var history = Find(id); var view = history.View;
            if (view.State == SessionState.Ended) return false; // An operator End wins without adding another event.
            ValidateClockExpiration(view, evidence);
            var hash = SHA256.HashData(Encoding.UTF8.GetBytes("mission-clock-v1:" + id.ToString("D") + ":" + view.MissionClock!.ConfiguredAtSequence));
            var command = new ControlCommand(new Guid(hash.AsSpan(0, 16)), ControlAction.End, ClockExpiration: evidence);
            Execute(id, command, actor); return true;
        }
    }
}
