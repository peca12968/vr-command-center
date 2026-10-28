using System.Text.Json;
using VrCommand.Core;

internal static class LifecycleChecks
{
    internal static void Run(Action<bool, string> check, string directory, Mission mission)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); }
            catch (T) { check(true, message); return; }
            throw new Exception($"Expected {typeof(T).Name}: {message}");
        }

        var data = Path.Combine(directory, "sessions");
        Guid sessionId;
        ControlCommand begin;
        ControlCommand end;
        long finalSequence;
        SessionEvent[] finalEvents;
        using (var journal = new FileSessionEventStore(data))
        {
            var manager = new SessionManager(journal);
            var session = manager.Create(SessionMode.Independent, [1], mission);
            sessionId = session.Id;
            check(session.State == SessionState.Preparing && session.StartedAtUtc is null && session.Sequence == 1,
                "Creating reserves a room in Preparing without starting play");
            Reject<InvalidOperationException>(() => manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.Begin)),
                "Empty session cannot begin");
            Reject<InvalidOperationException>(() => manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.Resume)),
                "Preparing cannot resume");
            Reject<ArgumentException>(() => manager.Execute(sessionId, new(Guid.Empty, ControlAction.Pause)), "Empty command ID rejected");
            Reject<ArgumentException>(() => manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.Unspecified)), "Missing action rejected");
            Reject<ArgumentException>(() => manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.SetEnvironment)), "Missing settings rejected");
            check(manager.Get(sessionId).Sequence == 1, "Rejected operations never enter event history");
            manager.Join(sessionId, Guid.NewGuid(), "Alpha", 1, HeadsetKind.Quest3);
            var other = manager.Create(SessionMode.Independent, [2], mission);
            var environment = new EnvironmentSettings(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false);
            manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.SetEnvironment, environment));
            check(manager.Get(sessionId).Environment == environment
                && manager.Get(sessionId).Mission.Definition.Environment == mission.Definition.Environment
                && manager.Get(other.Id).Environment == mission.Definition.Environment,
                "Environment override affects only its session and preserves mission template");
            manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.SetEnemies, Enemies: new(3, EnemyBehavior.Patrol, false)));
            check(manager.Get(sessionId).Enemies.Count == 3 && !manager.Get(sessionId).Enemies.AutoAttack,
                "Enemy control settings are tracked independently from the mission template");
            begin = new(Guid.NewGuid(), ControlAction.Begin, ExpectedSequence: manager.Get(sessionId).Sequence);
            var started = manager.Execute(sessionId, begin);
            check(started.Session.State == SessionState.Running && started.Session.StartedAtUtc.HasValue && !started.Duplicate,
                "Begin sets the authoritative start timestamp");
            var beforeRace = manager.Get(sessionId).Sequence;
            var applied = 0;
            var pause = new ControlCommand(Guid.NewGuid(), ControlAction.Pause);
            Parallel.For(0, 20, _ =>
            {
                if (!manager.Execute(sessionId, pause).Duplicate) Interlocked.Increment(ref applied);
            });
            check(applied == 1 && manager.Get(sessionId).Sequence == beforeRace + 1,
                "Concurrent retries append one pause event");
            var retry = manager.Execute(sessionId, begin);
            check(retry.Duplicate && retry.AppliedAtSequence == started.AppliedAtSequence
                && retry.Session.State == SessionState.Paused,
                "Retry returns original acceptance sequence plus latest state without applying Begin again");
            Reject<InvalidOperationException>(() => manager.Execute(sessionId, begin with { Action = ControlAction.Resume }),
                "Reusing a command ID with different content is rejected");
            Reject<InvalidOperationException>(() => manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.Resume, ExpectedSequence: 1)),
                "Stale expected sequence is rejected");
            Reject<InvalidOperationException>(() => manager.Join(sessionId, Guid.NewGuid(), "Late", 1, HeadsetKind.ViveXr),
                "Joining after the mission begins is rejected");
            manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.Resume));
            check(manager.Get(sessionId).State == SessionState.Running, "Paused session can resume");
            end = new(Guid.NewGuid(), ControlAction.End);
            manager.Execute(sessionId, end);
            var ended = manager.Get(sessionId);
            finalSequence = ended.Sequence;
            check(ended.EndedAtUtc.HasValue && ended.Players.Length == 1
                && manager.Rooms()[0].SessionId is null && manager.List().All(s => s.Id != sessionId)
                && manager.List(includeEnded: true).Any(s => s.Id == sessionId),
                "Ending archives player records and frees the room from active lists");
            check(manager.Execute(sessionId, end).Duplicate, "End retry remains idempotent after archival");
            Reject<InvalidOperationException>(() => manager.Execute(sessionId, new(Guid.NewGuid(), ControlAction.Resume)),
                "Archived sessions reject new commands");
            finalEvents = manager.Events(sessionId, limit: 500);
            check(finalEvents.Length == finalSequence && finalEvents.Select(e => e.Sequence).SequenceEqual(
                Enumerable.Range(1, finalEvents.Length).Select(i => (long)i)), "History sequences have no gaps");
            check(manager.Events(sessionId, after: 1, limit: 2).Select(e => e.Sequence).SequenceEqual([2L, 3L]),
                "Event pagination resumes strictly after the supplied sequence");
            Reject<ArgumentException>(() => manager.Events(sessionId, -1), "Negative cursor rejected");
            Reject<ArgumentException>(() => manager.Events(sessionId, limit: 501), "Unbounded event reads rejected");
            Reject<IOException>(() => { using var secondWriter = new FileSessionEventStore(data); }, "Concurrent process writer lease rejected");
            manager.Create(SessionMode.Independent, [1], mission);
        }
        using (var journal = new FileSessionEventStore(data))
        {
            var restored = new SessionManager(journal);
            check(restored.Get(sessionId).State == SessionState.Ended && restored.Get(sessionId).Sequence == finalSequence
                && restored.Get(sessionId).Enemies.Count == 3 && restored.Get(sessionId).Environment.Weather == Weather.Clear,
                "Restart rebuilds archived state and runtime settings from durable events");
            check(restored.Execute(sessionId, begin).Duplicate && restored.Execute(sessionId, end).Duplicate,
                "Command deduplication survives restart");
            check(restored.Rooms()[0].SessionId.HasValue && restored.Rooms()[1].SessionId.HasValue,
                "Restart also restores active room reservations");
        }

        var corrupted = finalEvents.ToArray();
        corrupted[1] = corrupted[1] with { Sequence = 99 };
        Reject<InvalidDataException>(() => new SessionManager(new SeedStore(corrupted)), "Non-contiguous history fails recovery");
        corrupted = finalEvents.ToArray();
        corrupted[0] = corrupted[0] with { SchemaVersion = 99 };
        Reject<InvalidDataException>(() => new SessionManager(new SeedStore(corrupted)), "Unknown event schema fails recovery");
        var historyFile = Path.Combine(data, $"{sessionId:D}.json");
        File.WriteAllText(historyFile, "not-json");
        using (var journal = new FileSessionEventStore(data))
            Reject<JsonException>(() => new SessionManager(journal), "Corrupt disk history fails startup instead of resetting data");

        var failingStore = new FailingStore();
        var durable = new SessionManager(failingStore);
        var saved = durable.Create(SessionMode.Independent, [3], mission);
        var stop = new ControlCommand(Guid.NewGuid(), ControlAction.End);
        failingStore.Fail = true;
        Reject<IOException>(() => durable.Execute(saved.Id, stop), "Storage error is surfaced to the caller");
        check(durable.Get(saved.Id).State == SessionState.Preparing && durable.Get(saved.Id).Sequence == 1
            && durable.Events(saved.Id).Length == 1 && durable.Rooms()[2].SessionId == saved.Id,
            "Failed persistence neither advances state nor releases reservations");
        failingStore.Fail = false;
        check(!durable.Execute(saved.Id, stop).Duplicate && durable.Get(saved.Id).State == SessionState.Ended,
            "Failed command can be retried after storage recovers");
        var disposedStore = new FileSessionEventStore(Path.Combine(directory, "disposed"));
        disposedStore.Dispose();
        Reject<ObjectDisposedException>(() => disposedStore.Load(), "Disposed store cannot read after releasing its writer lease");
        Reject<ObjectDisposedException>(() => disposedStore.Save(sessionId, finalEvents), "Disposed store cannot write after releasing its writer lease");
    }

    private sealed class SeedStore(SessionEvent[] entries) : ISessionEventStore
    {
        public SessionEvent[][] Load() => [entries];
        public void Save(Guid sessionId, SessionEvent[] events) => throw new NotSupportedException();
    }

    private sealed class FailingStore : ISessionEventStore
    {
        public bool Fail { get; set; }
        private readonly MemorySessionEventStore inner = new();
        public SessionEvent[][] Load() => inner.Load();
        public void Save(Guid sessionId, SessionEvent[] events)
        {
            if (Fail) throw new IOException("Simulated disk failure.");
            inner.Save(sessionId, events);
        }
    }
}
