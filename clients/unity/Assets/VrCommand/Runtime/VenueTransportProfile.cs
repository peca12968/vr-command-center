using System;
using Unity.Netcode.Transports.UTP;

namespace VrCommand.Unity
{
    public static class VenueTransportProfile
    {
        // UTP packet slots shared by the whole driver per update, not per peer.
        // Server fans each actor batch out to up to 25 peers. Keep headset/client
        // allocation at the upstream default; reserve bounded server burst room.
        public const int ServerPacketQueueSize=1024;
        public const int ClientPacketQueueSize=128;
        public static void Apply(UnityTransport transport,bool server)
        {
            if(transport==null)throw new ArgumentNullException(nameof(transport));
            transport.MaxPacketQueueSize=server?ServerPacketQueueSize:ClientPacketQueueSize;
        }
    }
}
