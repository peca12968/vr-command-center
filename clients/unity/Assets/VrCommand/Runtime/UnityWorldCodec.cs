using UnityEngine;
using VrCommand.Simulation;

namespace VrCommand.Unity
{
    public sealed class UnityWorldCodec : IWorldCodec
    {
        public string Header(WorldRecordingHeader value) => JsonUtility.ToJson(value);
        public string Packet(WorldRecordingPacket value) => JsonUtility.ToJson(value);
        public WorldRecordingHeader ReadHeader(string value) => JsonUtility.FromJson<WorldRecordingHeader>(value);
        public WorldRecordingPacket ReadPacket(string value) => JsonUtility.FromJson<WorldRecordingPacket>(value);
        public WorldPublicationAck ReadAck(string value) => JsonUtility.FromJson<WorldPublicationAck>(value);
    }
}
