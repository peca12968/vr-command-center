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
                    values[i]=new CombatActorState{id=new Guid(i,0,0,new byte[8]).ToString("D"),position=new Vector3(i,1.65f,-3),
                        room=i%5+1,health=100,magazine=30,reserve=90,enemy=i>=25,connected=true,presentationTick=1234,
                        fireSequence=7,fireTickPlusOne=1230,fireDirection=Vector3.forward,presentationRunning=true};
                    writer.WriteValueSafe(values[i]);
                }
                TestContext.WriteLine("Actor field count="+count+" bytes="+writer.Length+"; excludes NGO / UTP envelopes and retransmits.");
                Assert.Greater(writer.Length,1400,"Even the field payload requires multiple network packets per peer.");
                using(var reader=new FastBufferReader(writer.ToArray(),Allocator.Temp))
                {
                    reader.ReadValueSafe(out ushort actualCount);Assert.AreEqual(count,actualCount);
                    for(var i=0;i<count;i++){reader.ReadValueSafe(out CombatActorState actual);Assert.IsTrue(actual.Equals(values[i]));}
                }
            }
        }
    }
}
