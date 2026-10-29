using System;
using System.Collections.Generic;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    // Only accepted synthetic poses, fenced by the same admission as the combat body.
    public sealed class DesktopResumeCache
    {
        private sealed class Entry { public Guid admission; public AvatarPose pose; }
        private readonly Dictionary<Guid, Entry> entries = new Dictionary<Guid, Entry>();

        public void Remember(Guid player, Guid admission, AvatarPose pose)
        {
            if (player == Guid.Empty || admission == Guid.Empty || !pose.Valid()) throw new ArgumentException("Invalid resume identity or pose.");
            if (pose.source != 1) { entries.Remove(player); return; }
            entries[player] = new Entry { admission = admission, pose = pose };
        }
        public bool TryRestore(Guid player, Guid admission, out AvatarPose pose)
        {
            if (admission != Guid.Empty && entries.TryGetValue(player, out var entry) && entry.admission == admission)
            { pose = entry.pose; return true; }
            pose = default; return false;
        }
        public void Retain(ManagedPlayer[] roster)
        {
            if (roster == null) throw new ArgumentNullException(nameof(roster));
            foreach (var player in new List<Guid>(entries.Keys))
            {
                var entry = entries[player];
                if (!Array.Exists(roster, candidate => candidate.id == player.ToString("D") && candidate.admissionId == entry.admission.ToString("D")))
                    entries.Remove(player);
            }
        }
    }
}
