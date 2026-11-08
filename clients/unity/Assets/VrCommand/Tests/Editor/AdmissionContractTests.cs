using System;
using NUnit.Framework;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class AdmissionContractTests
    {
        [Test] public void TicketValidationExplicitlyRequestsTheFencedProtocol()
        {
            var json = JsonUtility.ToJson(new TicketValidationRequest { sessionId = Guid.NewGuid().ToString("D"), ticket = "opaque-v2-ticket" });
            StringAssert.Contains("\"protocolVersion\":2", json);
        }
        [Test] public void ApprovalRetainsAdmissionRevisionAndExpiry()
        {
            var result = JsonUtility.FromJson<TicketApproval>("{\"playerId\":\"f763084f-900a-4190-a14b-e13a3197bfd0\",\"admissionId\":\"a6f93528-dd40-4677-be50-8cb318bfedc5\",\"throughSequence\":17,\"expiresAtUtc\":\"2026-10-29T01:05:00+00:00\",\"roomId\":3,\"seat\":1}");
            Assert.AreEqual("a6f93528-dd40-4677-be50-8cb318bfedc5", result.admissionId); Assert.AreEqual(17, result.throughSequence);
            Assert.IsTrue(DateTimeOffset.TryParse(result.expiresAtUtc, out _)); Assert.AreEqual(1, result.seat);
        }
        [Test] public void LegacyRosterCannotSilentlyCreateAnUnfencedBinding()
        {
            var snapshot = new ManagementSnapshot { id = Guid.NewGuid().ToString("D"), sequence = 1, state = "Preparing", roomIds = new[] { 3 },
                mission = new ManagedMission { id = Guid.NewGuid().ToString("D"), definition = new ManagedDefinition { name = "Test", props = new ManagedProp[0] } },
                environment = new ManagedEnvironment { mode = "VR", weather = "Clear", timeOfDay = "Day" },
                enemies = new ManagedEnemies { count = 0, behavior = "Hold", autoAttack = false },
                players = new[] { new ManagedPlayer { id = Guid.NewGuid().ToString("D"), roomId = 3, seat = 0 } } };
            Assert.Throws<ArgumentException>(() => new ArenaSession().Apply(JsonUtility.FromJson<ManagementSnapshot>(JsonUtility.ToJson(snapshot))));
        }
        [Test] public void UnityReadsExactRoomPinsFromManagementJson()
        {
            var hash = new string('a', 64);
            var snapshot = JsonUtility.FromJson<ManagementSnapshot>("{\"roomIds\":[3],\"roomAlignment\":{\"room1\":null,\"room3\":\"" + hash + "\"}}");
            Assert.IsTrue(snapshot.roomAlignment.Covers(snapshot.roomIds));
            Assert.AreEqual(hash, snapshot.roomAlignment.ForRoom(3));
            Assert.IsFalse(snapshot.roomAlignment.Covers(new[] { 1, 2, 3, 4, 5 }));
            Assert.IsFalse(snapshot.roomAlignment.Covers(new[] { 4 }));
        }
    }
}
