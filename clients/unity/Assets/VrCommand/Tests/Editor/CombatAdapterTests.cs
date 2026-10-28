using System;
using NUnit.Framework;
using Unity.Collections;
using Unity.Netcode;
using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class CombatAdapterTests
    {
        [Test] public void JsonUtilityBindsTheManagementContractIncludingRosterAndGeometry()
        {
            var json = "{\"id\":\"8aaf649c-f482-40b2-9a99-ef8758c58802\",\"sequence\":2,\"state\":\"Preparing\",\"roomIds\":[3],"
                + "\"mission\":{\"id\":\"3d872c98-e108-4c46-94d0-e3f0ed3ed712\",\"definition\":{\"name\":\"Test\",\"props\":[{\"assetId\":\"barrel\",\"position\":{\"x\":0,\"y\":0,\"z\":0},\"yawDegrees\":45}]}},"
                + "\"environment\":{\"mode\":\"VR\",\"weather\":\"Clear\",\"timeOfDay\":\"Day\"},\"enemies\":{\"count\":1,\"behavior\":\"Hold\",\"autoAttack\":false},"
                + "\"players\":[{\"id\":\"6bcd2409-6172-43af-8307-88255c0959f8\",\"roomId\":3,\"seat\":0}]}";
            var adapter = new ArenaSession(); adapter.Apply(JsonUtility.FromJson<ManagementSnapshot>(json));
            Assert.AreEqual(1, adapter.World.Snapshot().Players.Length);
            Assert.IsFalse(adapter.World.Snapshot().Players[0].Connected);
            Assert.AreEqual(45, adapter.Props[0].Yaw);
        }
        [Test] public void MissingJsonFieldsCannotBecomeADefaultPlayableMission()
        {
            var adapter = new ArenaSession();
            Assert.Throws<ArgumentException>(() => adapter.Apply(JsonUtility.FromJson<ManagementSnapshot>("{}")));
        }
        [Test] public void NetcodeActorSerializationPreservesHealthWeaponAndConnectionState()
        {
            var expected = new CombatActorState { id = "6bcd2409-6172-43af-8307-88255c0959f8", position = new Vector3(2, 1.65f, -3),
                room = 3, health = 80, magazine = 27, reserve = 90, connected = true, reloading = true };
            using (var writer = new FastBufferWriter(512, Allocator.Temp))
            {
                writer.WriteValueSafe(expected);
                using (var reader = new FastBufferReader(writer.ToArray(), Allocator.Temp))
                { reader.ReadValueSafe(out CombatActorState actual); Assert.IsTrue(expected.Equals(actual)); }
            }
        }
    }
}
