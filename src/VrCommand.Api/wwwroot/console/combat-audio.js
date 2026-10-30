export class CombatAudioCursor {
  reset(){this.initialized=false;this.previousContinuous=false;this.tick=0;this.sequence=0;}
  advance(tick,phase,sequence,tickPlusOne,continuous){
    if(!Number.isSafeInteger(tick)||tick<0||tick>1728000||!Number.isSafeInteger(sequence)||sequence<0||!Number.isSafeInteger(tickPlusOne)||tickPlusOne<0||tickPlusOne>tick+1
      ||(sequence===0?tickPlusOne!==0:tickPlusOne===0)||!['Preparing','Running','Paused','Ended'].includes(phase))throw new Error('Invalid combat audio observation');
    const cue=!!this.initialized&&this.previousContinuous&&continuous&&phase==='Running'&&tick>=this.tick&&tick-this.tick<=10&&sequence>this.sequence&&tickPlusOne>0&&tick-(tickPlusOne-1)<=3;
    this.initialized=true;this.previousContinuous=continuous&&(phase==='Running'||phase==='Preparing');this.tick=tick;this.sequence=sequence;return cue;
  }
}
// Shares the explicitly enabled weather AudioContext and output gain. Browser
// and Unity reconstruct short cues, not an original recorded soundtrack.
export class CombatAudio {
  constructor(host){this.host=host;this.canvas=host.canvas;this.cursors=new Map();this.voices=[];this.version=0;this.count=0;this.epoch=0;}
  load(header){this.pause();this.version=header.combatAudioVersion||0;this.cursors.clear();this.count=0;this.canvas.dataset.combatAudioCount='0';this.canvas.dataset.combatAudioVersion=String(this.version);}
  async prepare(context){
    if(this.version!==1||this.buffers)return;
    this.loading??=Promise.all(['rifle-shot-v1.wav','pistol-shot-v1.wav'].map(async name=>{
      const r=await fetch(new URL('./audio/'+name,import.meta.url),{signal:AbortSignal.timeout(10000),cache:'no-store'});
      if(!r.ok)throw new Error('Combat audio unavailable');return context.decodeAudioData(await r.arrayBuffer());
    })).then(b=>{this.buffers=b;}).catch(e=>{this.loading=null;throw e;});
    await this.loading;
  }
  show(frame,camera,room,continuous){
    if(this.version!==1)return;
    const enabled=this.host.enabled&&this.host.state==='on'&&!!this.buffers&&document.visibilityState==='visible';
    if(this.host.enabled&&this.host.state==='on'&&!this.buffers)this.prepare(this.host.context).catch(()=>{this.canvas.dataset.combatAudioError='unavailable';});
    const running=enabled&&continuous&&frame.phase==='Running';if(!running)this.stop();
    const context=this.host.context,cues=[],present=new Set(),listener=camera.position;
    if(enabled){const target=camera.getWorldDirection(camera.position.clone());const l=context.listener;
      for(const [p,v]of [['positionX',listener.x],['positionY',listener.y],['positionZ',listener.z],['forwardX',target.x],['forwardY',target.y],['forwardZ',target.z],['upX',0],['upY',1],['upZ',0]])if(l[p])l[p].value=v;
    }
    for(const [actors,enemy]of [[frame.players,false],[frame.enemies,true]])for(const actor of actors){
      const key=(enemy?'e:':'p:')+actor.id;present.add(key);let cursor=this.cursors.get(key);if(!cursor){cursor=new CombatAudioCursor();this.cursors.set(key,cursor);}
      const inRoom=room==='all'||Number(room)===actor.roomId;
      const cue=cursor.advance(frame.tick,frame.phase,actor.fireSequence,actor.fireTickPlusOne,enabled&&continuous&&inRoom);
      if(cue&&running){const p=actor.fireOrigin,d=Math.hypot(p.x-listener.x,p.y-listener.y,p.z-listener.z);if(d<25)cues.push({actor,enemy,d});}
    }
    for(const key of this.cursors.keys())if(!present.has(key))this.cursors.delete(key);
    cues.sort((a,b)=>a.d-b.d||a.actor.id.localeCompare(b.actor.id));
    for(const cue of cues.slice(0,32))this.play(cue);
  }
  play({actor,enemy}){
    while(this.voices.length>=32){const v=this.voices.shift();try{v.source.stop();}catch{}v.source.disconnect();v.panner.disconnect();v.gain.disconnect();}
    const c=this.host.context,source=c.createBufferSource(),panner=c.createPanner(),gain=c.createGain(),p=actor.fireOrigin;
    panner.panningModel='equalpower';panner.distanceModel='linear';panner.refDistance=1;panner.maxDistance=25;panner.rolloffFactor=1;
    panner.positionX.value=p.x;panner.positionY.value=p.y;panner.positionZ.value=p.z;gain.gain.value=enemy?.25:.3;
    source.buffer=this.buffers[enemy?1:0];source.connect(panner);panner.connect(gain);gain.connect(this.host.gain);const voice={source,panner,gain};this.voices.push(voice);
    source.onended=()=>{const i=this.voices.indexOf(voice);if(i>=0)this.voices.splice(i,1);source.disconnect();panner.disconnect();gain.disconnect();this.canvas.dataset.combatAudioVoices=String(this.voices.length);};source.start();
    this.count++;this.canvas.dataset.combatAudioVoices=String(this.voices.length);this.canvas.dataset.combatAudioCount=String(this.count);this.canvas.dataset.combatAudioLast=JSON.stringify({id:actor.id,sequence:actor.fireSequence,tick:actor.fireTickPlusOne-1,enemy,origin:p});
  }
  stop(){for(const v of this.voices){v.source.onended=null;try{v.source.stop();}catch{}v.source.disconnect();v.panner.disconnect();v.gain.disconnect();}this.voices=[];this.canvas.dataset.combatAudioVoices='0';}
  pause(){this.stop();for(const cursor of this.cursors.values())cursor.reset();}
  reset(){this.pause();this.epoch++;this.cursors.clear();this.count=0;this.canvas.dataset.combatAudioCount='0';this.canvas.dataset.combatAudioLast='';}
}
