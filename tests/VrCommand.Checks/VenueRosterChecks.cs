using VrCommand.Core;
using VrCommand.Persistence;

internal static class VenueRosterChecks
{
    internal static void Run(Action<bool, string> check, string directory, Mission original)
    {
        var master = new OperatorIdentity("venue-roster-master", OperatorRole.Master);
        var controller = new OperatorIdentity("venue-roster-room1", OperatorRole.RoomController, 1);
        var rooms = Enumerable.Range(1, 5).ToArray();
        var vr = original with { Definition = original.Definition with { Environment = original.Definition.Environment with { Mode = ExperienceMode.VR } } };
        var mr = vr with { Id = Guid.NewGuid(), Definition = vr.Definition with { Environment = vr.Definition.Environment with { Mode = ExperienceMode.MR } } };
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); }
            catch (T) { check(true, message); return; }
            throw new Exception("Expected " + typeof(T).Name + ": " + message);
        }

        foreach (var mode in new[] { SessionMode.Independent, SessionMode.Linked })
        {
            var path = Path.Combine(directory, "venue-roster-" + mode);
            VenueRosterSeat[] batch;
            VenueRosterReceipt originalReceipt;
            using (var store = new SqliteSessionEventStore(path))
            {
                var session = new SessionManager(store);
                var ids = mode == SessionMode.Linked ? Enumerable.Repeat(session.Create(mode, rooms, vr, master).Id, 5).ToArray()
                    : rooms.Select(room => session.Create(mode, [room], room == 3 ? mr : vr, master).Id).ToArray();
                batch = rooms.SelectMany(room => Enumerable.Range(0, 5).Select(seat =>
                    new VenueRosterSeat(ids[room - 1], Guid.NewGuid(), Guid.NewGuid(), $"Player {room}-{seat + 1}", room, seat,
                        room == 3 || seat % 2 == 0 ? HeadsetKind.Quest3 : HeadsetKind.ViveXr))).ToArray();

                Reject<AccessDeniedException>(() => session.JoinVenueRoster(batch, controller), $"{mode} rejects venue admission from a room controller");
                Reject<ArgumentException>(() => session.JoinVenueRoster([batch[0], batch[0]], master), $"{mode} rejects duplicate seats and IDs");
                Reject<KeyNotFoundException>(() => session.JoinVenueRoster([batch[0], batch[^1] with { SessionId = Guid.NewGuid() }], master),
                    $"{mode} rejects an unavailable original target");
                if (mode == SessionMode.Independent)
                    Reject<InvalidOperationException>(() => session.JoinVenueRoster([batch[0], batch[10] with { Headset = HeadsetKind.ViveXr }], master),
                        "MR roster rejection rolls back other rooms");
                var occupied = session.Join(batch[^1].SessionId, Guid.NewGuid(), "Occupied", 5, HeadsetKind.Quest3, master).Players.Single();
                var blocked = new[] { batch[0], batch[^1] with { Seat = occupied.Seat } };
                Reject<InvalidOperationException>(() => session.JoinVenueRoster(blocked, master), $"{mode} detects a competing join in the last room");
                check(session.List().Sum(view => view.Players.Length) == 1, $"{mode} blocked batches preserve earlier empty seats");
                session.Leave(batch[^1].SessionId, occupied.Id, master);

                originalReceipt = session.JoinVenueRoster(batch, master);
                check(!originalReceipt.Duplicate && originalReceipt.Admissions.Length == 25
                    && originalReceipt.Admissions.Select(row => row.Player.AdmissionId).Distinct().Count() == 25
                    && originalReceipt.Admissions.Zip(batch).All(pair => pair.First.Player.Seat == pair.Second.Seat
                        && pair.First.Player.Id == pair.Second.PlayerId && pair.First.SessionId == pair.Second.SessionId),
                    $"{mode} commits the 25 exact seats with independent admission IDs");
                var views = session.List();
                var scored = views.SelectMany(view => session.Statistics(view.Id).Players).Select(player => player.PlayerId).ToHashSet();
                check(batch.All(seat => scored.Contains(seat.PlayerId)) && scored.Contains(occupied.Id)
                    && views.SelectMany(view => view.Players).GroupBy(player => player.RoomId).All(group => group.Count() == 5),
                    $"{mode} registers new combat rows, preserves departed history and fills five seats per room");
                Reject<InvalidOperationException>(() => session.JoinVenueRoster([batch[0], batch[1] with { RequestId = Guid.NewGuid() }], master),
                    $"{mode} disallows a mixture of accepted and new row requests");
                session.Leave(batch[0].SessionId, batch[0].PlayerId, master);
            }
            using var reopened = new SqliteSessionEventStore(path);
            var restored = new SessionManager(reopened);
            var duplicate = restored.JoinVenueRoster(batch, master);
            check(duplicate.Duplicate && duplicate.Admissions.SequenceEqual(originalReceipt.Admissions)
                && restored.List().Sum(view => view.Players.Length) == 24,
                $"{mode} restart and retry return immutable admission receipts without rejoining a removed player");
        }

        var atomicPath = Path.Combine(directory, "venue-roster-atomic");
        using var sql = new SqliteSessionEventStore(atomicPath);
        var seed = new SessionManager();
        var created = seed.Create(SessionMode.Independent, [1], vr, master);
        seed.Join(created.Id, Guid.NewGuid(), "First", 1, HeadsetKind.Quest3, master);
        seed.Join(created.Id, Guid.NewGuid(), "Second", 1, HeadsetKind.Quest3, master);
        var entries = seed.Events(created.Id);
        sql.Append(entries[0]);
        Reject<InvalidOperationException>(() => sql.AppendBatch([entries[1], entries[2] with { Sequence = 4 }]),
            "Later invalid sequence causes SQLite to roll back the entire same-session batch");
        check(sql.Load().Single().Length == 1, "Failed same-session SQLite batch keeps the prior history");
        sql.AppendBatch(entries[1..]);
        check(sql.Load().Single().Length == 3, "The same-session batch can be retried with consecutive history");
    }
}
