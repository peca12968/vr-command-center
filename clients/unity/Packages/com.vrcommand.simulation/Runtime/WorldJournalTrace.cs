using System;
using System.Collections.Generic;
using System.Diagnostics;

namespace VrCommand.Simulation
{
    [Serializable] public struct WorldJournalTimingRow
    {
        public int stage, operation, managedThreadId;
        public long sequence, startedTimestamp, endedTimestamp, startedUtcTicks, endedUtcTicks;
        public bool succeeded;
    }
    // Diagnostic metadata only. No file IO, callbacks, payload, keys or Unity APIs.
    public sealed class WorldJournalTrace
    {
        public const int MaximumCapacity = 32768, MaximumInFlight = 64;
        private readonly object gate = new object();
        private readonly List<WorldJournalTimingRow> rows;
        private readonly HashSet<long> inFlight = new HashSet<long>();
        private readonly int capacity;
        private long next;
        private bool stopped, truncated;
        public WorldJournalTrace(int capacity = MaximumCapacity)
        {
            if (capacity < 1 || capacity > MaximumCapacity) throw new ArgumentOutOfRangeException(nameof(capacity));
            this.capacity = capacity; rows = new List<WorldJournalTimingRow>(capacity);
        }
        public int InFlight { get { lock(gate) return inFlight.Count; } }
        public bool Truncated { get { lock(gate) return truncated; } }
        public void Stop() { lock(gate) stopped = true; }
        public WorldJournalTimingRow[] Snapshot() { lock(gate) return rows.ToArray(); }
        public Stamp Begin(int stage, int operation, long sequence = 0)
        {
            if (stage < 0 || stage > 2 || operation < 0 || operation > 255 || sequence < 0) throw new ArgumentOutOfRangeException();
            lock(gate)
            {
                if (stopped) return default;
                if (inFlight.Count == MaximumInFlight) { truncated = true; return default; }
                var id = ++next; inFlight.Add(id);
                return new Stamp(this, id, new WorldJournalTimingRow { stage = stage, operation = operation, sequence = sequence,
                    managedThreadId = Environment.CurrentManagedThreadId, startedTimestamp = Stopwatch.GetTimestamp(), startedUtcTicks = DateTime.UtcNow.Ticks });
            }
        }
        public readonly struct Stamp
        {
            private readonly WorldJournalTrace owner;
            private readonly long id;
            private readonly WorldJournalTimingRow row;
            internal Stamp(WorldJournalTrace owner, long id, WorldJournalTimingRow row) { this.owner = owner; this.id = id; this.row = row; }
            public void Finish(bool succeeded)
            {
                if (owner == null) return;
                var result = row; result.endedTimestamp = Stopwatch.GetTimestamp(); result.endedUtcTicks = DateTime.UtcNow.Ticks; result.succeeded = succeeded;
                lock(owner.gate)
                {
                    if (!owner.inFlight.Remove(id)) return; // Copies / duplicate finishes cannot corrupt the count.
                    if (owner.rows.Count == owner.capacity) owner.truncated = true;
                    else owner.rows.Add(result);
                }
            }
        }
    }
}
