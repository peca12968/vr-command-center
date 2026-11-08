using System.Text;

namespace VrCommand.Simulation
{
    public static class ArenaConnectionProfile
    {
        private const string Prefix = "mr1.";
        private const int TicketLimit = 256;
        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);

        // VR keeps the original opaque ticket bytes. MR also declares the locally configured room.
        public static byte[] Encode(string ticket, int mixedRealityRoom)
        {
            return Utf8.GetBytes(mixedRealityRoom == 0 ? ticket : Prefix + (char)('0' + mixedRealityRoom) + "." + ticket);
        }

        public static bool TryDecode(byte[] payload, out string ticket, out int mixedRealityRoom)
        {
            ticket = ""; mixedRealityRoom = 0;
            if (payload == null || payload.Length < 1 || payload.Length > TicketLimit + 6) return false;
            string value;
            try { value = Utf8.GetString(payload); }
            catch (DecoderFallbackException) { return false; }
            if (value.StartsWith(Prefix, System.StringComparison.Ordinal))
            {
                if (value.Length < 7 || value[4] < '1' || value[4] > '5' || value[5] != '.') return false;
                mixedRealityRoom = value[4] - '0';
                value = value.Substring(6);
            }
            if (value.Length > TicketLimit || !value.StartsWith("v2.", System.StringComparison.Ordinal)) return false;
            ticket = value;
            return true;
        }

        public static bool Matches(bool mixedReality, int requestedRoom, int admittedRoom, string headset) =>
            mixedReality ? requestedRoom == admittedRoom && requestedRoom != 0 && headset == "Quest3" : requestedRoom == 0;
    }
}
