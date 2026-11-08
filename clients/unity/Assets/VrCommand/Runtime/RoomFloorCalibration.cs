using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    public sealed class RoomFloorPlan
    {
        private readonly FloorXZ[] markers;
        public int RoomId { get; }
        private RoomFloorPlan(int roomId, FloorXZ[] markers) { RoomId = roomId; this.markers = markers; }

        [Serializable] private sealed class Point
        {
            public double x = double.NaN, z = double.NaN;
            public FloorXZ Value => new FloorXZ(x, z);
        }
        [Serializable] private sealed class Marker
        {
            public string name = "";
            public Point room = null, tracking = null;
        }
        [Serializable] private sealed class Report
        {
            public int version = 0, roomId = 0;
            public string profile = "";
            public bool withinTolerance = false;
            public Point roomOrigin = null;
            public Marker[] markers = null;
        }

        public static RoomFloorPlan Parse(string json)
        {
            var report = JsonUtility.FromJson<Report>(json);
            if (report == null || report.version != 1 || report.profile != RoomFloorFit.Profile || !report.withinTolerance
                || report.roomId < 1 || report.roomId > 5 || report.roomOrigin == null || report.markers?.Length != 3)
                throw new InvalidDataException("Use a checked room floor alignment report.");
            var origin = ArenaWorld.RoomOrigin(report.roomId);
            if (report.roomOrigin.x != origin.X || report.roomOrigin.z != origin.Z)
                throw new InvalidDataException("The room origin differs from the arena.");

            var room = new FloorXZ[3];
            var tracking = new FloorXZ[3];
            for (var i = 0; i < room.Length; i++)
            {
                var marker = report.markers[i];
                if (marker == null || marker.name != "ABC"[i].ToString() || marker.room == null || marker.tracking == null)
                    throw new InvalidDataException("Use the original A, B and C measurements.");
                room[i] = marker.room.Value;
                tracking[i] = marker.tracking.Value;
            }
            if (RoomFloorFit.Solve(room, tracking, out _) != FloorFitResult.Valid)
                throw new InvalidDataException("The exported measurements do not meet the room tolerance.");
            return new RoomFloorPlan(report.roomId, room);
        }

        internal static RoomFloorPlan Load(string directory, string expectedHash)
        {
            if (expectedHash.Length != 64) throw new InvalidDataException("Invalid room alignment hash.");
            foreach (var character in expectedHash)
                if ((character < '0' || character > '9') && (character < 'a' || character > 'f'))
                    throw new InvalidDataException("Invalid room alignment hash.");
            byte[] bytes;
            using (var input = new BinaryReader(File.OpenRead(Path.Combine(directory, "vr-room-alignment-" + expectedHash + ".json"))))
            {
                var length = input.BaseStream.Length;
                if (length < 1 || length > 16384) throw new InvalidDataException("Invalid room alignment file size.");
                bytes = input.ReadBytes((int)length);
            }
            using (var sha = SHA256.Create())
            {
                var hash = BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
                if (!string.Equals(hash, expectedHash, StringComparison.Ordinal))
                    throw new InvalidDataException("The room alignment file differs from the player configuration.");
            }
            return Parse(new UTF8Encoding(false, true).GetString(bytes).TrimStart('\uFEFF'));
        }

        internal FloorFitResult Fit(FloorXZ[] samples, out FloorTransform transform) => RoomFloorFit.Solve(markers, samples, out transform);

        public bool MatchesSpawn(Vector3 position)
        {
            for (var seat = 0; seat < 5; seat++)
            {
                var spawn = ArenaSession.Spawn(RoomId, seat);
                if ((position - new Vector3(spawn.X, 0, spawn.Z)).sqrMagnitude <= .0001f) return true;
            }
            return false;
        }
    }

    public sealed class RoomFloorCalibration
    {
        private readonly RoomFloorPlan plan;
        private readonly Transform trackingSpace;
        private readonly bool assignedRoomMatches;
        private readonly FloorXZ[] samples = new FloorXZ[3];
        private int count;
        private bool retry;
        internal int RoomId => plan.RoomId;
        public bool Ready { get; private set; }
        public string Hint { get; private set; } = "WAITING FOR FLOOR TRACKING";

        public RoomFloorCalibration(RoomFloorPlan plan, Vector3 assignedSpawn, Transform trackingSpace)
        {
            this.plan = plan;
            this.trackingSpace = trackingSpace;
            assignedRoomMatches = plan.MatchesSpawn(assignedSpawn);
        }

        public void Invalidate()
        {
            Ready = false;
            count = 0;
            retry = false;
            Hint = "FLOOR ALIGNMENT REQUIRED";
        }

        // A completed capture never releases pose or weapon input on the capture frame itself.
        public bool Update(bool measurementAllowed, bool floorReady, bool jointsTracked, bool capture, Vector3 leftController)
        {
            if (!assignedRoomMatches) { Hint = "ALIGNMENT FILE IS FOR ANOTHER ROOM"; return false; }
            if (!floorReady)
            {
                Invalidate(); Hint = "WAITING FOR FLOOR TRACKING";
                return false;
            }
            if (Ready) return jointsTracked;
            if (!measurementAllowed || !jointsTracked)
            {
                count = 0;
                Hint = measurementAllowed ? "ALIGNMENT NEEDS HEAD AND BOTH CONTROLLERS" : "PAUSE MISSION TO ALIGN ROOM";
                return false;
            }
            Hint = (retry ? "MARKERS DID NOT MATCH\n" : "") + "LEFT CONTROLLER OVER " + "ABC"[count] + "\nPRESS LEFT TRIGGER";
            if (!capture) return false;

            var point = new FloorXZ(leftController.x, leftController.z);
            if (!point.InRange(RoomFloorFit.TrackingLimit)) return false;
            samples[count++] = point;
            if (count < samples.Length) { retry = false; return false; }
            if (plan.Fit(samples, out var fit) != FloorFitResult.Valid)
            {
                Invalidate(); retry = true;
                return false;
            }

            var origin = ArenaWorld.RoomOrigin(plan.RoomId);
            trackingSpace.SetPositionAndRotation(new Vector3(origin.X + (float)fit.Translation.X, 0, origin.Z + (float)fit.Translation.Z),
                Quaternion.AngleAxis((float)fit.YawDegrees, Vector3.up));
            Ready = true;
            Hint = "";
            return false;
        }
    }
}
