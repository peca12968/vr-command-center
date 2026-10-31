using System;
using System.Globalization;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    // Targeted to one existing admission; never contains another player's statistics or credentials.
    [Serializable] public sealed class MissionDebrief
    {
        public int version = 1, roomId, health;
        public string sessionId, playerId, admissionId, origin, streamId;
        public long throughSequence, finalStreamSequence, worldSequence;
        public long ammoUsed, shotsHit, kills, hitsReceived, damageTaken;
        public double accuracyPercent;
        // This is an expected terminal boundary, never proof of persistence or delivery.
        public static long PendingWorldSequence(QueuedWorldRecorder writer) => writer != null && writer.EndQueued && !writer.Faulted ? writer.CapturedSequence : 0;
        public bool MatchesSealedWorld(WorldOutbox recording)
        {
            if (recording == null || worldSequence < 1) return false;
            var state = recording.State;
            if (!state.Sealed || !state.Complete || state.LastSequence != worldSequence || state.AcknowledgedSequence != worldSequence) return false;
            var header = recording.Header;
            return header.sessionId == sessionId && header.streamId == streamId && header.origin == origin;
        }
        public bool Valid()
        {
            return version == 1 && Guid.TryParse(sessionId, out var s) && s != Guid.Empty
                && Guid.TryParse(playerId, out var p) && p != Guid.Empty && Guid.TryParse(admissionId, out var a) && a != Guid.Empty
                && Guid.TryParse(streamId, out var stream) && stream != Guid.Empty && roomId >= 1 && roomId <= 5
                && (origin == "Simulation" || origin == "GameServer") && throughSequence > 0 && finalStreamSequence >= 0 && worldSequence > 0
                && ammoUsed >= 0 && shotsHit >= 0 && shotsHit <= ammoUsed && kills >= 0 && kills <= shotsHit
                && hitsReceived >= 0 && damageTaken >= 0 && health >= 0 && health <= 100
                && double.IsFinite(accuracyPercent) && Math.Abs(accuracyPercent - ExpectedAccuracy(ammoUsed, shotsHit)) < .00001;
        }
        public static double ExpectedAccuracy(long shots, long hits) => shots == 0 ? 0 : (double)decimal.Round(100m * hits / shots, 2);
        public bool SameAdmission(MissionDebrief other) => other != null && sessionId == other.sessionId && playerId == other.playerId
            && admissionId == other.admissionId && roomId == other.roomId;
        public string Display => "MISSION COMPLETE - SEALED RESULTS\nRoom " + roomId + "  |  " + origin
            + "\nAmmo used: " + ammoUsed + "     Hits: " + shotsHit + "     Kills: " + kills
            + "\nAccuracy: " + accuracyPercent.ToString("0.00", CultureInfo.InvariantCulture) + "%"
            + "\nHits received: " + hitsReceived + "     Damage: " + damageTaken + "     Health: " + health + "/100"
            + "\nCombat and replay sealed. Contact the control desk for your next mission.";
    }

    public sealed class MissionDebriefState
    {
        private MissionDebrief context;
        public MissionDebrief Result { get; private set; }
        public bool Pending => context != null && Result == null;
        public bool Active => context != null;
        public bool Begin(MissionDebrief value, string localPlayer)
        {
            if (context != null) return context.SameAdmission(value);
            if (value == null || value.playerId != localPlayer || !value.Valid()) return false;
            context = value; return true;
        }
        public bool Accept(MissionDebrief value)
        {
            if (context == null || !context.SameAdmission(value) || !value.Valid() || value.origin != context.origin
                || value.streamId != context.streamId || value.throughSequence < context.throughSequence
                || value.finalStreamSequence != context.finalStreamSequence || value.worldSequence != context.worldSequence) return false;
            // First accepted final result is immutable, including across a transport disconnect.
            if (Result != null) return false;
            Result = value; return true;
        }
        public void Clear() { context = null; Result = null; }
    }

    [Serializable] public sealed class DebriefStatistics
    {
        public string sessionId, origin;
        public long throughSequence;
        public bool pendingTelemetry;
        public DebriefPlayerStatistics[] players;
        public MissionDebrief Select(TicketApproval admission, MissionDebrief context)
        {
            // Unity JsonUtility reads an API JSON null string as "". Only a proven zero-event
            // sealed stream may use that representation; never infer a nonempty combat source.
            var missingOrigin = string.IsNullOrEmpty(origin);
            if (context == null || admission == null || admission.sessionId != context.sessionId || admission.playerId != context.playerId
                || admission.admissionId != context.admissionId || admission.roomId != context.roomId || pendingTelemetry
                || sessionId != context.sessionId || throughSequence < context.throughSequence
                || (!missingOrigin && origin != context.origin) || players == null) return null;
            if (missingOrigin)
            {
                if (context.finalStreamSequence != 0) return null;
                foreach (var player in players)
                    if (player == null || player.ammoUsed != 0 || player.shotsHit != 0 || player.kills != 0 || player.hitsReceived != 0
                        || player.damageTaken != 0 || player.health != 100 || player.accuracyPercent != 0) return null;
            }
            DebriefPlayerStatistics found = null;
            foreach (var player in players)
                if (player != null && player.playerId == admission.playerId)
                { if (found != null) return null; found = player; }
            if (found == null || found.roomId != admission.roomId) return null;
            var result = new MissionDebrief { sessionId = sessionId, playerId = admission.playerId, admissionId = admission.admissionId,
                roomId = found.roomId, origin = context.origin, streamId = context.streamId, throughSequence = throughSequence,
                finalStreamSequence = context.finalStreamSequence, worldSequence = context.worldSequence,
                ammoUsed = found.ammoUsed, shotsHit = found.shotsHit, kills = found.kills, hitsReceived = found.hitsReceived,
                damageTaken = found.damageTaken, health = found.health, accuracyPercent = found.accuracyPercent };
            return result.Valid() ? result : null;
        }
    }
    [Serializable] public sealed class DebriefPlayerStatistics
    {
        public string playerId;
        public int roomId, health;
        public long ammoUsed, shotsHit, kills, hitsReceived, damageTaken;
        public double accuracyPercent;
    }
}
