using System.Globalization;
using System.Text;
using VrCommand.Api;
using VrCommand.Core;
using VrCommand.Persistence;

internal static class FinalReportChecks
{
    internal static void Run(Action<bool, string> check, string directory, Mission mission)
    {
        void Reject<T>(Action action, string message) where T : Exception
        {
            try { action(); } catch (T) { check(true, message); return; }
            throw new Exception($"Expected {typeof(T).Name}: {message}");
        }
        var master = new OperatorIdentity("reports-master", OperatorRole.Master);
        var room = new OperatorIdentity("reports-room", OperatorRole.RoomController, 1);
        var other = new OperatorIdentity("reports-other", OperatorRole.RoomController, 2);
        var server = new OperatorIdentity("reports-server", OperatorRole.GameServer);
        Guid id, player = Guid.NewGuid(), departed = Guid.NewGuid(), stream = Guid.NewGuid();
        byte[] csv;
        var data = Path.Combine(directory, "final-report-sqlite");
        using (var store = new SqliteSessionEventStore(data))
        {
            var manager = new SessionManager(store);
            id = manager.Create(SessionMode.Independent, [1], mission, master).Id;
            Reject<AccessDeniedException>(() => manager.FinalReport(id, other), "Report checks room scope before disclosing final readiness");
            Reject<AccessDeniedException>(() => manager.FinalReport(id, server), "Game-server credentials cannot export operator reports");
            Reject<ArgumentNullException>(() => manager.FinalReport(id, null!), "Report cannot fall back to an implicit Internal HTTP identity");
            Reject<InvalidOperationException>(() => manager.FinalReport(id, master), "Preparing session cannot export a final report");
            manager.Join(id, player, "台灣,\"Alpha\"", 1, HeadsetKind.Quest3, master);
            manager.Join(id, departed, "=1+1", 1, HeadsetKind.Quest3, master);
            manager.Leave(id, departed, master);
            manager.OpenStream(id, new(stream, CombatOrigin.Simulation), server);
            manager.Execute(id, new(Guid.NewGuid(), ControlAction.Begin), master);
            var observed = manager.Get(id).Sequence;
            Reject<InvalidOperationException>(() => manager.FinalReport(id, room), "Running session cannot export a final report");
            manager.Execute(id, new(Guid.NewGuid(), ControlAction.Pause), master);
            Reject<InvalidOperationException>(() => manager.FinalReport(id, master), "Paused session cannot export a final report");
            manager.End(id, master);
            Reject<InvalidOperationException>(() => manager.FinalReport(id, master), "Ended session with a missing combat tail cannot export a final report");
            var shot = Guid.NewGuid(); var enemy = Guid.NewGuid();
            StreamCombatRecord Record(long sequence, CombatKind kind, Guid? shotId = null, Guid? enemyId = null, int damage = 0) =>
                new(stream, sequence, observed, new(Guid.NewGuid(), kind, CombatOrigin.Simulation, player, shotId, enemyId, damage));
            var records = new[] { Record(1, CombatKind.ShotFired, shot), Record(2, CombatKind.ShotHit, shot, enemy),
                Record(3, CombatKind.EnemyEliminated, shot, enemy), Record(4, CombatKind.PlayerDamaged, damage: 20) };
            manager.ReportStreamBatch(id, records, server);
            Reject<InvalidOperationException>(() => manager.FinalReport(id, master), "Receiving all known reports without exact seal remains non-final");
            Reject<InvalidOperationException>(() => manager.SealStream(id, new(stream, 3), server), "A shorter seal cannot unlock final export");
            Parallel.Invoke(() => manager.SealStream(id, new(stream, 4), server), () =>
            {
                for (var i = 0; i < 40; i++)
                    try
                    {
                        var snapshot = manager.FinalReport(id, room);
                        if (snapshot.ThroughSequence != manager.Get(id).Sequence || snapshot.FinalStreamSequence != 4
                            || snapshot.Players.Single(p => p.PlayerId == player).AmmoUsed != 1) throw new Exception("Torn final report");
                    }
                    catch (InvalidOperationException) { /* The same lock may observe the pre-seal state. */ }
            });
            var final = manager.FinalReport(id, master);
            check(final.ReportVersion == 1 && final.StreamId == stream && final.FinalStreamSequence == 4 && final.Origin == CombatOrigin.Simulation
                && final.ThroughSequence == manager.Get(id).Sequence && final.EndedAtUtc == manager.Get(id).EndedAtUtc
                && final.MissionId == mission.Id && final.MissionName == mission.Definition.Name
                && final.PlannedDurationSeconds == mission.Definition.DurationSeconds && final.StartedAtUtc == manager.Get(id).StartedAtUtc,
                "Final report atomically captures identity, source and durable seal boundary");
            var metric = final.Players.Single(p => p.PlayerId == player);
            check(metric.AmmoUsed == 1 && metric.ShotsHit == 1 && metric.Kills == 1 && metric.DamageTaken == 20
                && metric.HitsReceived == 1 && metric.AccuracyPercent == 100 && metric.Health == 80
                && final.Players.Any(p => p.PlayerId == departed && p.AmmoUsed == 0),
                "Final report uses the accepted ledger including departed zero-shot players");
            csv = FinalReportCsv.Encode(final);
            check(csv.AsSpan(0, 3).SequenceEqual(new byte[] { 239, 187, 191 })
                && Encoding.UTF8.GetString(csv).Contains("\"台灣,\"\"Alpha\"\"\"")
                && Encoding.UTF8.GetString(csv).Contains("\"'=1+1\""),
                "UTF-8 BOM CSV quotes punctuation and neutralizes formula names without changing ledger values");
            check(manager.FinalReport(id, master).Players.Single(p => p.PlayerId == departed).Name == "=1+1",
                "CSV text protection never rewrites persisted names");
            var culture = CultureInfo.CurrentCulture;
            try
            {
                CultureInfo.CurrentCulture = CultureInfo.GetCultureInfo("fr-FR");
                check(FinalReportCsv.Encode(final).SequenceEqual(csv), "Report bytes and decimal format do not depend on host culture");
                var fractional = final with { Players = [metric with { AmmoUsed = 3, ShotsHit = 2 }] };
                check(Encoding.UTF8.GetString(FinalReportCsv.Encode(fractional)).Contains("\"66.67\""), "CSV preserves two-decimal accepted-shot accuracy with a dot");
            }
            finally { CultureInfo.CurrentCulture = culture; }
            foreach (var name in new[] { " +SUM(1)", "-1+2", "@cmd", "\t=1", "line\r\nnext" })
                check(Encoding.UTF8.GetString(FinalReportCsv.Encode(final with { MissionName = name })).Contains("\"'" + name + "\""),
                    "Spreadsheet formula or control text is explicitly prefixed: " + name.Replace("\r", "CR").Replace("\n", "LF").Replace("\t", "TAB"));
            final.RoomIds[0] = 99; final.Players[0] = metric with { Kills = 999 };
            check(FinalReportCsv.Encode(manager.FinalReport(id, master)).SequenceEqual(csv), "Returned report arrays cannot mutate the authoritative report");
            manager.ReportStreamBatch(id, records, server); manager.SealStream(id, new(stream, 4), server);
            check(FinalReportCsv.Encode(manager.FinalReport(id, room)).SequenceEqual(csv), "Accepted tail and seal retries leave final CSV byte-identical");
        }
        using (var store = new SqliteSessionEventStore(data))
            check(FinalReportCsv.Encode(new SessionManager(store).FinalReport(id, master)).SequenceEqual(csv), "SQLite restart produces the same final CSV bytes");
        var empty = new SessionManager(); var emptyId = empty.Create(SessionMode.Independent, [1], mission, master).Id;
        empty.End(emptyId, master);
        var emptyReport = empty.FinalReport(emptyId, master);
        check(emptyReport.StartedAtUtc is null && emptyReport.Origin is null && emptyReport.Players.Length == 0
            && Encoding.UTF8.GetString(FinalReportCsv.Encode(emptyReport)).Contains("\"Session\""),
            "Never-started empty session exports explicit metadata without inventing a participant or source");
        var linked = empty.Create(SessionMode.Linked, [1, 2, 3, 4, 5], mission, master).Id;
        empty.OpenStream(linked, new(Guid.NewGuid(), CombatOrigin.GameServer), server); empty.End(linked, master);
        var attached = empty.Get(linked).CombatStream!; empty.SealStream(linked, new(attached.StreamId, 0), server);
        check(empty.FinalReport(linked, room).Origin == CombatOrigin.GameServer && empty.FinalReport(linked, room).RoomIds.Length == 5,
            "Linked room controller follows existing read scope and zero-event stream retains its declared source");
    }
}
