using System;
using System.Linq;

namespace VrCommand.Simulation
{
    internal static class PlayerFireValidation
    {
        internal static void Packet(WorldRecordingHeader header,WorldRecordingPacket packet,WorldRecordingPacket? previous)
        {
            foreach(var player in packet.frame.players)
            {
                if(header.playerFireVersion==0)
                {
                    if(player.hasFireState || player.fireSequence!=0 || player.fireTickPlusOne!=0 || !Zero(player.fireOrigin) || !Zero(player.fireDirection))
                        throw new ArgumentException("Legacy players cannot claim unversioned fire effects.");
                    continue;
                }
                if(!player.hasFireState || player.fireOrigin==null || player.fireDirection==null)throw new ArgumentException("Missing versioned player fire state.");
                var state=new PlayerFireState(player.fireSequence,player.fireTickPlusOne,player.fireOrigin.ToVector(),player.fireDirection.ToVector());
                PlayerFirePresentation.Validate(packet.frame.tick,state);
                // Match the original authority volume, without substituting a
                // later tracked pointer for this historical accepted muzzle.
                if(state.Sequence>packet.frame.throughSequence || (state.Sequence>0 && (state.Origin.Y<.1f || state.Origin.Y>2.6f
                    || Math.Abs(state.Origin.X-ArenaWorld.RoomOrigin(player.roomId).X)>6 || Math.Abs(state.Origin.Z)>6)))
                    throw new ArgumentException("Player fire state lies outside the accepted muzzle bounds.");
                var old=previous?.frame.players.FirstOrDefault(value=>value.id==player.id);
                var sequence=old?.fireSequence??0;var tick=old?.fireTickPlusOne??0;
                var origin=old?.fireOrigin;var direction=old?.fireDirection;
                foreach(var entry in packet.events.Where(value=>value.kind=="ShotFired" && value.playerId==player.id))
                {sequence=entry.sequence;tick=entry.tick+1;origin=entry.origin;direction=entry.direction;}
                if(sequence!=player.fireSequence || tick!=player.fireTickPlusOne || !Same(origin,player.fireOrigin) || !Same(direction,player.fireDirection))
                    throw new ArgumentException("Player fire state disagrees with its accepted shot events.");
            }
        }
        private static bool Zero(RecordedVector? p)=>p==null || (p.x==0 && p.y==0 && p.z==0);
        private static bool Same(RecordedVector? a,RecordedVector b)=>a==null?Zero(b):b!=null && a.x==b.x && a.y==b.y && a.z==b.z;
    }
}
