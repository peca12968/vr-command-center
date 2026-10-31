using NUnit.Framework;
using UnityEngine;

namespace VrCommand.Unity.Tests
{
    public sealed class NativeReplicationProbeTests
    {
        [Test] public void JsonSnapshotPreservesExplicitWeatherAndIdentityInsteadOfOmittingNetworkStructs()
        {
            var original=new NativeReplicationProbe.Snapshot{request=4,localConnection=25,role="Client",phase="Paused",ready=true,
                presentation=NativeReplicationProbe.WeatherObservation.From(new WeatherState{tick=1234,phase=2,weather=3,rooms=31,night=true,lightning=true}),
                actors=new[]{new NativeReplicationProbe.Actor{id="player-25",room=5,health=60,presentationTick=1234,position=new Vector3(31,1.65f,-3)}},
                avatars=new[]{new NativeReplicationProbe.Avatar{playerId="player-25",connection=25,owner=true,accepted=true,source=1,head=new Vector3(31,1.65f,-3)}}};
            var json=JsonUtility.ToJson(original);StringAssert.Contains("\"presentation\"",json);
            var actual=JsonUtility.FromJson<NativeReplicationProbe.Snapshot>(json);
            Assert.AreEqual(1234,actual.presentation.tick);Assert.AreEqual(2,actual.presentation.phase);Assert.AreEqual(31,actual.presentation.rooms);
            Assert.AreEqual(3,actual.presentation.weather);Assert.IsTrue(actual.presentation.night&&actual.presentation.lightning);
            Assert.AreEqual("player-25",actual.actors[0].id);Assert.AreEqual(60,actual.actors[0].health);
            Assert.AreEqual(25,actual.localConnection);Assert.AreEqual(25,actual.avatars[0].connection);Assert.AreEqual(original.avatars[0].head,actual.avatars[0].head);
        }
        [Test] public void JsonReportRetainsQueueErrorClockAndIncoherentObservation()
        {
            var expected=new NativeReplicationProbe.Report{complete=true,rows=new[]{new NativeReplicationProbe.Row{tick=10,phase=1,players=25,connected=24,health=2500,coherent=false}},
                sendQueueErrors=new[]{new NativeReplicationProbe.QueueError{tick=10,phase=1,utcTicks=639290101921137393,seconds=12.5}}};
            var actual=JsonUtility.FromJson<NativeReplicationProbe.Report>(JsonUtility.ToJson(expected));
            Assert.IsFalse(actual.rows[0].coherent);Assert.AreEqual(24,actual.rows[0].connected);
            Assert.AreEqual(639290101921137393,actual.sendQueueErrors[0].utcTicks);Assert.AreEqual(12.5,actual.sendQueueErrors[0].seconds);
        }
    }
}
