using System;
using NUnit.Framework;
using Unity.Collections;
using Unity.Netcode;
using Unity.Netcode.Transports.UTP;
using Unity.Networking.Transport;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class VenueTransportProfileTests
    {
        [Test] public void AppliedQueuesReachActualDriverSettingsAndLeaveClientAtUpstreamDefault()
        {
            var owner=new GameObject("Transport profile fixture",typeof(NetworkManager),typeof(UnityTransport));
            try
            {
                var transport=owner.GetComponent<UnityTransport>();
                foreach(var server in new[]{true,false})
                {
                    VenueTransportProfile.Apply(transport,server);
                    using(var settings=transport.GetDefaultNetworkSettings())
                    {
                        Assert.IsTrue(settings.TryGet<NetworkConfigParameter>(out var actual));
                        Assert.AreEqual(server?1024:UnityTransport.InitialMaxPacketQueueSize,actual.sendQueueCapacity);
                        Assert.AreEqual(actual.sendQueueCapacity,actual.receiveQueueCapacity);
                    }
                }
            }
            finally{UnityEngine.Object.DestroyImmediate(owner);}
        }
        [TestCase(30)] [TestCase(125)] public void ActualCombatActorSerializationMeasuresFragmentedFanoutAndPreservesFields(int count)
        {
            var values=new CombatActorState[count];
            using(var writer=new FastBufferWriter(65536,Allocator.Temp))
            {
                writer.WriteValueSafe((ushort)count);
                for(var i=0;i<count;i++)
                {
                    values[i]=new CombatActorState{id=new Guid(i,0,0,new byte[8]),position=new Vector3(i,1.65f,-3),
                        room=i%5+1,health=100,magazine=30,reserve=90,enemy=i>=25,connected=true,presentationTick=1234,
                        fireSequence=7,fireTickPlusOne=1230,fireDirection=Vector3.forward,presentationRunning=true};
                    writer.WriteValueSafe(values[i]);
                }
                TestContext.WriteLine("Actor field count="+count+" bytes="+writer.Length+"; excludes NGO / UTP envelopes and retransmits.");
                // NGO 29 used 141 bytes for each canonical actor in this fixture.
                Assert.Less(writer.Length, count * 85 + 2, "Active actors retain their fields in a smaller payload.");
                using(var reader=new FastBufferReader(writer.ToArray(),Allocator.Temp))
                {
                    reader.ReadValueSafe(out ushort actualCount);Assert.AreEqual(count,actualCount);
                    for(var i=0;i<count;i++){reader.ReadValueSafe(out CombatActorState actual);Assert.IsTrue(actual.Equals(values[i]));}
                }
            }
        }

        [Test] public void CompactActorDecodesIntoReusedStateWithoutRetainingOmittedFields()
        {
            var idle = new CombatActorState { id = Guid.Parse("83a52e15-d670-48b8-8bdb-0ff9d111ae65"), room = 5,
                position = new Vector3(28.123456f, 1.654321f, -2.123456f), health = 100, magazine = 30,
                reserve = 90, connected = true, presentationTick = 300000 };
            var active = idle;
            active.facing = new Vector3(BitConverter.Int32BitsToSingle(int.MinValue), 0, 0);
            active.health = int.MaxValue;
            active.presentationTick = long.MaxValue;
            active.reloadUntilTick = long.MinValue;
            active.fireSequence = long.MaxValue;
            active.fireTickPlusOne = long.MinValue;
            active.fireOrigin = new Vector3(28.234567f, .876543f, -1.765432f);
            active.fireDirection = new Vector3(.125125f, .025025f, .991816f);
            active.enemy = active.reloading = active.walking = active.presentationRunning = true;

            using var writer = new FastBufferWriter(512, Allocator.Temp);
            writer.WriteValueSafe(idle);
            Assert.LessOrEqual(writer.Length, 40);
            writer.WriteValueSafe(active);
            writer.WriteValueSafe(idle);
            using var reader = new FastBufferReader(writer.ToArray(), Allocator.Temp);
            reader.ReadValueSafe(out CombatActorState actual);
            Assert.That(actual.Equals(idle), Is.True);
            Assert.That(actual.position.Equals(idle.position), Is.True);
            reader.ReadNetworkSerializableInPlace(ref actual);
            Assert.That(actual.Equals(active), Is.True);
            Assert.That(BitConverter.SingleToInt32Bits(actual.facing.x), Is.EqualTo(int.MinValue));
            Assert.That(actual.fireOrigin.Equals(active.fireOrigin) && actual.fireDirection.Equals(active.fireDirection), Is.True);
            reader.ReadNetworkSerializableInPlace(ref actual);
            Assert.That(actual.Equals(idle), Is.True);
            Assert.That(BitConverter.SingleToInt32Bits(actual.facing.x), Is.Zero);
            Assert.That(reader.Position, Is.EqualTo(writer.Length));
        }
    }
}
