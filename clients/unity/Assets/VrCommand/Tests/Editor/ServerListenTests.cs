using System;
using NUnit.Framework;
using UnityEngine;
using Unity.Netcode.Transports.UTP;

namespace VrCommand.Unity.Tests
{
    public sealed class ServerListenTests
    {
        [Test] public void MissingListenFieldRetainsTheOriginalWildcardServerBinding()
        {
            var config = JsonUtility.FromJson<LaunchConfiguration>("{\"role\":\"Server\",\"address\":\"127.0.0.1\"}");
            Assert.AreEqual("0.0.0.0", config.ServerListenAddress);
        }
        [Test] public void ExplicitBindingIsPassedToTheRealTransportWithoutChangingAdvertisedAddress()
        {
            var node = new GameObject("Listen test", typeof(UnityTransport));
            try
            {
                foreach (var role in new[] { "Server", "Host" })
                {
                    var config = new LaunchConfiguration { role = role, address = "192.168.1.100", listenAddress = "127.0.0.1" };
                    var transport = node.GetComponent<UnityTransport>(); transport.SetConnectionData(config.address, config.port, config.ServerListenAddress);
                    Assert.AreEqual("127.0.0.1", transport.ConnectionData.ServerListenAddress);
                    Assert.AreEqual("192.168.1.100", transport.ConnectionData.Address);
                }
            }
            finally { UnityEngine.Object.DestroyImmediate(node); }
        }
        [Test] public void ExplicitListenRejectsUrlsMulticastAndAmbiguousAddressForms()
        {
            foreach (var value in new[] { "127.1", "127.0.0.01", " 127.0.0.1", "::1", "tcp://127.0.0.1", "224.0.0.1", "255.255.255.255" })
                Assert.Throws<InvalidOperationException>(() => { _ = new LaunchConfiguration { listenAddress = value }.ServerListenAddress; });
        }
    }
}
