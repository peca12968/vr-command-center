using System.Collections;
using NUnit.Framework;
using Unity.Collections;
using Unity.Networking.Transport;
using UnityEngine;
using UnityEngine.TestTools;

namespace VrCommand.Unity.Tests
{
    public sealed class TransportRecoveryTests
    {
        [UnityTest] public IEnumerator AbruptClientLossDoesNotExhaustWindowsReceiveBuffers()
        {
            if (Application.platform != RuntimePlatform.WindowsEditor) Assert.Ignore("Windows Baselib UDP regression.");
            var settings = new NetworkSettings(Allocator.Persistent);
            settings.WithNetworkConfigParameters(disconnectTimeoutMS: 700, heartbeatTimeoutMS: 30, connectTimeoutMS: 50,
                maxConnectAttempts: 40, receiveQueueCapacity: 8, sendQueueCapacity: 32);
            var server = NetworkDriver.Create(settings); var client = NetworkDriver.Create(settings); var replacement = default(NetworkDriver);
            try
            {
                Assert.AreEqual(0, server.Bind(NetworkEndpoint.LoopbackIpv4.WithPort(0))); Assert.AreEqual(0, server.Listen());
                var endpoint = server.GetLocalEndpoint(); client.Connect(endpoint);
                var accepted = default(NetworkConnection); var deadline = Time.realtimeSinceStartupAsDouble + 5;
                while (!accepted.IsCreated && Time.realtimeSinceStartupAsDouble < deadline)
                {
                    server.ScheduleUpdate().Complete(); client.ScheduleUpdate().Complete(); accepted = server.Accept();
                    while (server.PopEvent(out _, out _) != NetworkEvent.Type.Empty) { }
                    while (client.PopEvent(out _, out _) != NetworkEvent.Type.Empty) { }
                    yield return null;
                }
                Assert.IsTrue(accepted.IsCreated, "Initial raw UDP connection failed.");
                client.Dispose(); client = default; // No Disconnect / graceful flush: reproduce process loss.
                deadline = Time.realtimeSinceStartupAsDouble + 2;
                while (Time.realtimeSinceStartupAsDouble < deadline)
                {
                    if (server.GetConnectionState(accepted) == NetworkConnection.State.Connected && server.BeginSend(accepted, out var writer) == 0)
                    { writer.WriteByte(1); server.EndSend(writer); }
                    server.ScheduleUpdate().Complete();
                    while (server.PopEvent(out _, out _) != NetworkEvent.Type.Empty) { }
                    yield return null;
                }
                replacement = NetworkDriver.Create(settings); replacement.Connect(endpoint);
                var next = default(NetworkConnection); deadline = Time.realtimeSinceStartupAsDouble + 5;
                while (!next.IsCreated && Time.realtimeSinceStartupAsDouble < deadline)
                {
                    server.ScheduleUpdate().Complete(); replacement.ScheduleUpdate().Complete(); next = server.Accept();
                    while (server.PopEvent(out _, out _) != NetworkEvent.Type.Empty) { }
                    while (replacement.PopEvent(out _, out _) != NetworkEvent.Type.Empty) { }
                    yield return null;
                }
                Assert.IsTrue(next.IsCreated, "Host stopped receiving after failed receive completions; new raw UDP client was not accepted.");
            }
            finally
            {
                if (replacement.IsCreated) replacement.Dispose(); if (client.IsCreated) client.Dispose(); server.Dispose(); settings.Dispose();
            }
        }
    }
}
