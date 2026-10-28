using System;
using NUnit.Framework;
using VrCommand.Simulation;

namespace VrCommand.Unity.Tests
{
    public sealed class WorldCodecTests
    {
        [Test] public void WorldFieldContractRoundTripsThroughUnityJson()
        {
            var player = Guid.NewGuid(); var world = new ArenaWorld(new[] { 3 }, new WorldProp[0]);
            world.AddPlayer(player, 3, new Vec3(0, 1.65f, 0));
            var packet = WorldRecordingPacket.Capture(world, 1, 0, 3, 0, 0, _ => new RecordedRig { kind = "Simulated",
                left = new RecordedVector(new Vec3(-.2f, 1.2f, 0)), right = new RecordedVector(new Vec3(.2f, 1.2f, 0)) });
            var header = WorldRecordingHeader.Create(Guid.NewGuid(), Guid.NewGuid(), "Simulation", new[] { 3 }, new WorldProp[0]);
            var codec = new UnityWorldCodec(); var restored = codec.ReadPacket(codec.Packet(packet));
            WorldRecordingValidation.Header(codec.ReadHeader(codec.Header(header))); WorldRecordingValidation.Packet(header, restored, null);
            Assert.AreEqual(player.ToString("D"), restored.frame.players[0].id); Assert.AreEqual("Simulated", restored.frame.players[0].rig.kind);
        }
        [Test] public void WorldAcknowledgmentUsesThePublishedFieldNames()
        {
            var ack = new UnityWorldCodec().ReadAck("{\"type\":\"ack\",\"info\":{\"acceptedSequence\":12,\"complete\":true,\"header\":{\"streamId\":\"d497ad54-98b7-40c0-b5a7-69800016c5bc\"}}}");
            Assert.AreEqual(12, ack.info.acceptedSequence); Assert.IsTrue(ack.info.complete);
            Assert.AreEqual("d497ad54-98b7-40c0-b5a7-69800016c5bc", ack.info.header.streamId);
        }
    }
}
