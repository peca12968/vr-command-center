using System;
using System.Text;

namespace VrCommand.Simulation
{
    public static class ArenaConnectionProfile
    {
        private const string Prefix = "mr2.";
        private const int TicketLimit = 256;
        private const int AlignmentHashLength = 64;
        private const int TicketOffset = 6 + AlignmentHashLength + 1;
        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);

        // VR keeps the original opaque ticket bytes. MR also declares the checked room file.
        public static byte[] Encode(string ticket, int mixedRealityRoom, string? alignmentHash = null)
        {
            if (mixedRealityRoom == 0 && alignmentHash is null) return Utf8.GetBytes(ticket);
            if (mixedRealityRoom is < 1 or > 5 || !IsAlignmentHash(alignmentHash))
                throw new ArgumentException("MR connection data requires a room and checked alignment hash.");
            return Utf8.GetBytes(Prefix + (char)('0' + mixedRealityRoom) + "." + alignmentHash + "." + ticket);
        }

        public static bool TryDecode(byte[] payload, out string ticket, out int mixedRealityRoom, out string? alignmentHash)
        {
            ticket = ""; mixedRealityRoom = 0; alignmentHash = null;
            if (payload == null || payload.Length < 1 || payload.Length > TicketLimit + TicketOffset) return false;
            string value;
            try { value = Utf8.GetString(payload); }
            catch (DecoderFallbackException) { return false; }
            if (value.StartsWith(Prefix, StringComparison.Ordinal))
            {
                if (value.Length <= TicketOffset || value[4] < '1' || value[4] > '5' || value[5] != '.' || value[TicketOffset - 1] != '.') return false;
                var hash = value.Substring(6, AlignmentHashLength);
                var candidate = value.Substring(TicketOffset);
                if (!IsAlignmentHash(hash) || !IsTicket(candidate)) return false;
                mixedRealityRoom = value[4] - '0';
                alignmentHash = hash;
                ticket = candidate;
                return true;
            }
            if (!IsTicket(value)) return false;
            ticket = value;
            return true;
        }

        private static bool IsTicket(string value) => value.Length <= TicketLimit && value.StartsWith("v2.", StringComparison.Ordinal);

        public static bool IsAlignmentHash(string? value)
        {
            if (value is null || value.Length != AlignmentHashLength) return false;
            foreach (var character in value)
                if (character is not (>= '0' and <= '9') && character is not (>= 'a' and <= 'f')) return false;
            return true;
        }

        public static bool Matches(bool mixedReality, int requestedRoom, int admittedRoom, string headset,
            string? requestedHash, string? expectedHash) => mixedReality
            ? requestedRoom == admittedRoom && requestedRoom != 0 && headset == "Quest3"
                && IsAlignmentHash(expectedHash) && string.Equals(requestedHash, expectedHash, StringComparison.Ordinal)
            : requestedRoom == 0 && requestedHash is null;
    }
}
