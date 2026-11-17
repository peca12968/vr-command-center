using System.Text.Json;
using Microsoft.Data.Sqlite;
using VrCommand.Core;
using VrCommand.Persistence;

internal static class MissionLibraryChecks
{
    internal static void Run(Action<bool, string> check, string directory)
    {
        void Reject<T>(Action action, string message) where T : Exception
        { try { action(); } catch (T) { check(true, message); return; } throw new Exception("Expected " + typeof(T).Name + ": " + message); }
        static string Json<T>(T value) => JsonSerializer.Serialize(value, JsonFormat.Options);
        var master = new OperatorIdentity("mission-master", OperatorRole.Master);
        var room = new OperatorIdentity("mission-room", OperatorRole.RoomController, 1);
        var server = new OperatorIdentity("mission-server", OperatorRole.GameServer);
        var draft = new MissionDraft("第一版", "保持任務原始條件", 600,
            new(ExperienceMode.VR, Weather.Clear, TimeOfDay.Day, false), new(1, EnemyBehavior.Hold, true), [new("sandbag", new(1, 0, 2), 15)]);
        var path = Path.Combine(directory, "mission-library"); var legacy = new MissionStore(path).Create(draft);
        var legacyPath = Path.Combine(path, legacy.Id.ToString("D") + ".json"); var originalFile = File.ReadAllBytes(legacyPath);
        var eventPath = Path.Combine(directory, "mission-library-sessions"); Guid oldSession; Guid newSession; Guid head; Guid revisionRequest = Guid.NewGuid();
        var planRequest = Guid.NewGuid();
        VenueMissionPlan savedPlan;
        using (var library = new SqliteMissionLibrary(path))
        using (var events = new SqliteSessionEventStore(eventPath))
        {
            var manager = new SessionManager(events);
            check(Json(library.Get(legacy.Id)) == Json(legacy) && library.Version(legacy.Id).Number == 1 && library.Version(legacy.Id).SeriesId == legacy.Id,
                "Legacy mission JSON imports as an identical immutable revision one");
            check(File.ReadAllBytes(legacyPath).SequenceEqual(originalFile), "Mission migration leaves original JSON bytes untouched");
            Reject<ArgumentException>(() => library.Heads(room with { RoomId = null }), "Mission catalog reads validate the supplied operator identity");
            Reject<IOException>(() => { using var other = new SqliteMissionLibrary(path); }, "Mission library writer lease rejects another library instance");
            Reject<InvalidOperationException>(() => new MissionStore(path).Create(draft), "Legacy mission writer cannot silently bypass the version catalog");
            Reject<InvalidOperationException>(() => new MissionStore(path).List(), "Legacy mission reader cannot return an incomplete versioned library");
            oldSession = manager.Create(SessionMode.Independent, [1], library.Get(legacy.Id), master).Id;
            var revised = draft with { Name = "夜間第二版", DurationSeconds = 900, Environment = new(ExperienceMode.VR, Weather.Storm, TimeOfDay.Night, true), Props = [new("barrel", new(3, 0, 4), 45)] };
            var second = library.Revise(legacy.Id, revised, master, revisionRequest);
            var roomPlan = new VenueMissionPlanDraft("  五房測試  ", VenueMissionPlanMode.IndependentSet,
                [legacy.Id, second.Id, legacy.Id, second.Id, legacy.Id]);
            savedPlan = library.SaveVenuePlan(roomPlan, master, planRequest);
            check(savedPlan.Plan.Name == "五房測試" && savedPlan.Plan.MissionIds.SequenceEqual(roomPlan.MissionIds),
                "A named five-room plan retains the original version and position for every room");
            Reject<AccessDeniedException>(() => library.VenuePlans(room), "Room credentials cannot list venue-wide plans");
            Reject<AccessDeniedException>(() => library.VenuePlan(planRequest, room), "Room credentials cannot read an individual venue plan");
            Reject<KeyNotFoundException>(() => library.VenuePlan(Guid.NewGuid(), master), "An unknown venue plan is not replaced with another plan");
            Reject<AccessDeniedException>(() => library.SaveVenuePlan(roomPlan, server, Guid.NewGuid()), "Game servers cannot save venue-wide plans");
            Reject<ArgumentException>(() => library.SaveVenuePlan(roomPlan with { Mode = VenueMissionPlanMode.Linked }, master, Guid.NewGuid()),
                "A linked plan requires a single common saved version");
            Reject<KeyNotFoundException>(() => library.SaveVenuePlan(roomPlan with { MissionIds = [legacy.Id, second.Id, legacy.Id, second.Id, Guid.NewGuid()] },
                master, Guid.NewGuid()), "A plan referencing a missing mission is rejected as a whole");
            Reject<InvalidOperationException>(() => library.SaveVenuePlan(roomPlan with { Name = "Different" }, master, planRequest),
                "A saved plan request cannot be reused with a different name or assignment");
            Reject<InvalidOperationException>(() => library.SaveVenuePlan(roomPlan, master with { Id = "other-master" }, planRequest),
                "A saved plan retry preserves the original master identity");
            check(Json(library.SaveVenuePlan(roomPlan, master, planRequest)) == Json(savedPlan) && library.VenuePlans(master).Length == 1,
                "Retrying a named plan returns its original receipt without creating another plan");
            check(library.Version(second.Id) is { Number: 2 } info && info.SeriesId == legacy.Id && info.PreviousId == legacy.Id && info.Author == master,
                "Revision records its series, immutable parent and authenticated author");
            check(Json(library.Get(legacy.Id)) == Json(legacy) && manager.Get(oldSession).Mission.Definition.Environment.Weather == Weather.Clear,
                "Mission revision cannot change old snapshots or an existing preparing session");
            Reject<AccessDeniedException>(() => library.Revise(second.Id, revised, room, Guid.NewGuid()), "Room controller cannot author a mission revision");
            Reject<AccessDeniedException>(() => library.Create(draft, server), "GameServer cannot create shared missions");
            Reject<ArgumentException>(() => library.Revise(second.Id, revised, master, Guid.Empty), "Revision requires a nonempty request ID");
            Reject<ArgumentException>(() => library.Revise(second.Id, revised with { DurationSeconds = 0 }, master, Guid.NewGuid()), "Invalid revision definition is rejected without persistence");
            Reject<InvalidOperationException>(() => library.Revise(legacy.Id, revised with { Name = "stale" }, master, Guid.NewGuid()), "Stale base cannot fork or replace the latest mission revision");
            var attempts = Enumerable.Range(0, 8).Select(index => Task.Run(() => {
                try { return library.Revise(second.Id, revised with { Name = "Concurrent " + index }, master, Guid.NewGuid()); }
                catch (InvalidOperationException) { return null; }
            })).ToArray();
            Task.WaitAll(attempts); var accepted = attempts.Select(task => task.Result).Where(value => value is not null).ToArray();
            check(accepted.Length == 1 && library.History(second.Id).HeadNumber == 3, "Concurrent revisions from the same base accept exactly one next version");
            check(Json(library.Revise(legacy.Id, revised, master, revisionRequest)) == Json(second), "Accepted mission retry confirms its original revision after newer revisions exist");
            Reject<InvalidOperationException>(() => library.Revise(legacy.Id, revised with { Name = "different" }, master, revisionRequest), "Mission retry cannot change its saved definition");
            Reject<InvalidOperationException>(() => library.Revise(legacy.Id, revised, master with { Id = "other-master" }, revisionRequest), "Mission retry cannot change its authenticated author");
            Reject<InvalidOperationException>(() => library.Create(revised, master, revisionRequest), "Mission request IDs cannot switch between new series and revision operations");
            head = accepted.Single()!.Id;
            for (var number = 4; number <= 7; number++) head = library.Revise(head, draft with { Name = "第 " + number + " 版" }, master, Guid.NewGuid()).Id;
            var page = library.History(legacy.Id, limit: 2); var next = library.History(head, page.NextBefore, 2);
            check(page.Versions.Select(row => row.Number).SequenceEqual([7, 6]) && next.Versions.Select(row => row.Number).SequenceEqual([5, 4]),
                "History paginates version metadata by immutable revision number");
            Reject<ArgumentException>(() => library.History(head, 0), "History rejects invalid cursors");
            Reject<ArgumentException>(() => library.History(head, limit: 101), "History rejects an unbounded page size");
            check(library.Heads().Single().Mission.Id == head && library.List().Length == 7, "Latest library lists one head while exact legacy API can retain all snapshots");
            newSession = manager.Create(SessionMode.Independent, [2], library.Get(head), master).Id;
            check(manager.Get(newSession).Mission.Id == head && manager.Get(oldSession).Mission.Id == legacy.Id, "New and old sessions independently bind exact mission version IDs");
            var copyRequest = Guid.NewGuid(); var copy = library.Create(draft, master, copyRequest);
            check(Json(library.Create(draft, master, copyRequest)) == Json(copy) && library.Version(copy.Id).Number == 1 && library.Version(copy.Id).SeriesId == copy.Id,
                "Save-as-new creates a separate series and its accepted request is retryable");
            copy.Definition.Props[0] = new("changed", new(99, 0, 0), 0);
            check(library.Get(copy.Id).Definition.Props[0].AssetId == "sandbag", "Returned mission arrays cannot mutate the persisted library");
        }
        using (var library = new SqliteMissionLibrary(path))
        using (var events = new SqliteSessionEventStore(eventPath))
        {
            var manager = new SessionManager(events);
            check(library.History(legacy.Id).HeadId == head && library.Heads().Length == 2 && library.Version(head).Number == 7,
                "Library restart restores revision heads and separate series");
            check(Json(library.VenuePlans(master).Single()) == Json(savedPlan) && Json(library.VenuePlan(savedPlan.Id, master)) == Json(savedPlan)
                && !savedPlan.Plan.MissionIds.Contains(head),
                "Named venue plans keep exact historical version IDs through revisions and persistence restart");
            check(manager.Get(oldSession).Mission.Id == legacy.Id && manager.Get(newSession).Mission.Id == head,
                "Event-store restart retains each session's embedded immutable mission");
        }
        var failedPath = Path.Combine(directory, "mission-import-failure"); var good = new MissionStore(failedPath).Create(draft);
        var corruptId = Guid.NewGuid(); var corruptFile = Path.Combine(failedPath, corruptId.ToString("D") + ".json"); File.WriteAllText(corruptFile, "{broken");
        Reject<InvalidDataException>(() => { using var bad = new SqliteMissionLibrary(failedPath); }, "Malformed legacy mission aborts catalog migration");
        check(File.ReadAllText(corruptFile) == "{broken", "Failed migration preserves corrupt legacy evidence");
        File.WriteAllText(corruptFile, Json(good with { Id = corruptId }));
        using (var repaired = new SqliteMissionLibrary(failedPath)) check(repaired.List().Length == 2, "Migration can resume cleanly after fixing the original invalid source");
        using (var db = new SqliteConnection(new SqliteConnectionStringBuilder { DataSource = Path.Combine(failedPath, "missions.db"), Pooling = false }.ToString()))
        {
            db.Open(); using var mutate = db.CreateCommand(); mutate.CommandText = "UPDATE missions SET revision=2,previous=id WHERE id=$id"; mutate.Parameters.AddWithValue("$id", corruptId.ToString("D")); mutate.ExecuteNonQuery();
        }
        Reject<InvalidDataException>(() => { using var bad = new SqliteMissionLibrary(failedPath); }, "Inconsistent persisted revision lineage fails startup instead of inventing a head");
    }
}
