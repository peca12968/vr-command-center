using System;
using System.Linq;

namespace VrCommand.Simulation
{
    internal static class EnemyFireValidation
    {
        internal static void Packet(WorldRecordingHeader header,WorldRecordingPacket packet,WorldRecordingPacket? previous)
        {
            foreach(var enemy in packet.frame.enemies)
            {
                if(header.enemyFireVersion==0)
                {
                    if(enemy.hasFireState || enemy.fireSequence!=0 || enemy.fireTickPlusOne!=0 || !Zero(enemy.fireOrigin) || !Zero(enemy.fireDirection))
                        throw new ArgumentException("Legacy enemies cannot claim unversioned fire effects.");
                    continue;
                }
                if(!enemy.hasFireState || enemy.fireOrigin==null || enemy.fireDirection==null)throw new ArgumentException("Missing versioned enemy fire state.");
                var state=new EnemyFireState(enemy.fireSequence,enemy.fireTickPlusOne,enemy.fireOrigin.ToVector(),enemy.fireDirection.ToVector());
                EnemyFirePresentation.Validate(packet.frame.tick,state);
                if(state.Sequence>packet.frame.throughSequence || (state.Sequence>0 && (Math.Abs(state.Origin.Y-1.4f)>.001f
                    || Math.Abs(state.Origin.X-ArenaWorld.RoomOrigin(enemy.roomId).X)>6 || Math.Abs(state.Origin.Z)>6)))
                    throw new ArgumentException("Enemy fire state lies outside its recorded world.");
                var old=previous?.frame.enemies.FirstOrDefault(value=>value.id==enemy.id);
                var sequence=old?.fireSequence??0;var tick=old?.fireTickPlusOne??0;
                var origin=old?.fireOrigin;var direction=old?.fireDirection;
                foreach(var entry in packet.events.Where(value=>value.kind=="EnemyShot" && value.enemyId==enemy.id))
                {sequence=entry.sequence;tick=entry.tick+1;origin=entry.origin;direction=entry.direction;}
                if(sequence!=enemy.fireSequence || tick!=enemy.fireTickPlusOne || !Same(origin,enemy.fireOrigin) || !Same(direction,enemy.fireDirection))
                    throw new ArgumentException("Enemy fire state disagrees with its accepted shot events.");
            }
        }
        private static bool Zero(RecordedVector? p)=>p==null || (p.x==0 && p.y==0 && p.z==0);
        private static bool Same(RecordedVector? a,RecordedVector b)=>a==null?Zero(b):b!=null && a.x==b.x && a.y==b.y && a.z==b.z;
    }
}
