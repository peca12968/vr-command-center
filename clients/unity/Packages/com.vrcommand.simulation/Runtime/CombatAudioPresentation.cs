using System;

namespace VrCommand.Simulation
{
    // Presentation only. A cursor observes accepted fire state, never predicts
    // input or changes ammunition, hit tests, phase or the simulation clock.
    public static class CombatAudioPresentation
    {
        public const int Version=1,MaximumAge=3,MaximumGap=10,Voices=32;
        public const float MinimumDistance=1,MaximumDistance=25,RifleVolume=.3f,PistolVolume=.25f;
    }
    public sealed class CombatAudioCursor
    {
        private bool initialized,previousContinuous;
        private long previousTick,previousSequence;
        public void Reset(){initialized=previousContinuous=false;previousTick=previousSequence=0;}
        public bool Advance(long tick,string phase,long sequence,long tickPlusOne,bool continuous)
        {
            if(tick<0||tick>EnvironmentPresentation.MaximumTick||sequence<0||tickPlusOne<0||tickPlusOne>tick+1
                ||(sequence==0?tickPlusOne!=0:tickPlusOne==0)||
                (phase!="Preparing"&&phase!="Running"&&phase!="Paused"&&phase!="Ended"))throw new ArgumentException("Invalid combat audio observation.");
            var sound=initialized&&previousContinuous&&continuous&&phase=="Running"&&tick>=previousTick
                &&tick-previousTick<=CombatAudioPresentation.MaximumGap&&sequence>previousSequence
                &&tickPlusOne>0&&tick-(tickPlusOne-1)<=CombatAudioPresentation.MaximumAge;
            initialized=true;previousContinuous=continuous&&(phase=="Running"||phase=="Preparing");previousTick=tick;previousSequence=sequence;return sound;
        }
    }
}
