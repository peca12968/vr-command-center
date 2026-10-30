"""Original deterministic short PCM transients; no recordings or external samples."""
import argparse
import array
import hashlib
import io
import json
from pathlib import Path
import sys
import uuid
import wave

ROOT=Path(__file__).resolve().parents[1];AUDIO=ROOT/'clients/unity/Assets/VrCommand/Audio';RES=ROOT/'clients/unity/Assets/VrCommand/Resources/VrCommand'
RATE=22050;NAMESPACE=uuid.UUID('c9df36ea-864f-421a-8528-c1656bacd6ba')
PINS={'rifle-shot-v1.wav':'d3b366164342346cb99e22e88c18482b927f382782d0368b3f7285e57608a6ae','pistol-shot-v1.wav':'33723ad9023704124ccdc1d8de1c29fa4341e39fb78627df999eeb28dad453f9'}
PROFILE_PIN='92d1a05a3d6598e61f88e38b9386efd882ac5776f58e27b4f122c98fef043a2f'

def pcm(enemy):
    count=3969 if enemy else 5292;state=0x715abc91 if enemy else 0x4912fdac;low=0;phase=0;raw=[]
    for i in range(count):
        state^=(state<<13)&0xffffffff;state^=state>>17;state^=(state<<5)&0xffffffff;state&=0xffffffff
        noise=(state&65535)-32768;low+=(noise-low)//(12 if enemy else 22)
        phase=(phase+(490 if enemy else 330))%65536;triangle=32768-abs(phase-32768)*2
        value=(noise*3+low*5+triangle)//4
        value=value*(count-i)**3//count**3;value=value*min(i,48)//48;raw.append(value)
    peak=max(abs(v)for v in raw);return [v*22000//peak for v in raw]

def wav(values):
    a=array.array('h',values)
    if sys.byteorder!='little':a.byteswap()
    b=io.BytesIO()
    with wave.open(b,'wb')as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(a.tobytes())
    return b.getvalue()

def meta(path,text=False):
    guid=uuid.uuid5(NAMESPACE,path.relative_to(ROOT/'clients/unity').as_posix()).hex
    if text:return f'fileFormatVersion: 2\nguid: {guid}\nTextScriptImporter:\n  externalObjects: {{}}\n  userData:\n  assetBundleName:\n  assetBundleVariant:\n'.encode()
    return f'fileFormatVersion: 2\nguid: {guid}\nAudioImporter:\n  externalObjects: {{}}\n  serializedVersion: 7\n  forceToMono: 1\n  normalize: 0\n  preloadAudioData: 1\n  loadInBackground: 0\n  ambisonic: 0\n  userData:\n  assetBundleName:\n  assetBundleVariant:\n'.encode()

def outputs():
    out={};files={}
    for name,enemy in [('rifle-shot-v1.wav',False),('pistol-shot-v1.wav',True)]:
        values=pcm(enemy);data=wav(values);digest=hashlib.sha256(data).hexdigest()
        if name in PINS and digest!=PINS[name]:raise SystemExit('Frozen combat sound changed; publish a new sound set: '+name)
        out[AUDIO/name]=data;out[AUDIO/(name+'.meta')]=meta(AUDIO/name)
        files[name]={'sha256':digest,'sampleRate':RATE,'channels':1,'bitsPerSample':16,'frames':len(values),'peak':max(abs(v)for v in values)}
    profile={'soundSet':'combat-audio-v1','combatAudioVersion':1,'maximumAgeTicks':3,'maximumGapTicks':10,'voices':32,'minimumDistance':1,'maximumDistance':25,'rifleVolume':.3,'pistolVolume':.25,'files':files}
    profile_bytes=(json.dumps(profile,indent=2)+'\n').encode()
    if hashlib.sha256(profile_bytes).hexdigest()!=PROFILE_PIN:raise SystemExit('Frozen sound profile changed; publish a new sound set')
    out[RES/'combat-audio-v1.json']=profile_bytes;out[RES/'combat-audio-v1.json.meta']=meta(RES/'combat-audio-v1.json',True)
    provenance={'generator':'scripts/generate-combat-audio.py','source':'Original integer noise/filter/triangle-envelope synthesis; no sampled or third-party audio','soundSet':'combat-audio-v1','files':files}
    out[AUDIO/'combat-audio-provenance.json']=(json.dumps(provenance,indent=2)+'\n').encode();out[AUDIO/'combat-audio-provenance.json.meta']=meta(AUDIO/'combat-audio-provenance.json',True)
    return out,files

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',action='store_true');args=p.parse_args();out,files=outputs()
    for path,data in out.items():
        if args.check:
            current=path.read_bytes()if path.exists()else b''
            if (data.splitlines()[1]not in current.splitlines())if path.suffix=='.meta'else(current!=data):raise SystemExit('Combat audio differs: '+str(path))
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.suffix!='.meta'or not path.exists():path.write_bytes(data)
    print(json.dumps({k:v['sha256']for k,v in files.items()}))

if __name__=='__main__':main()
