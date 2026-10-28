import * as THREE from './vendor/three/three.module.js';
import { environmentStyle, rainPoint, EnvironmentCueTracker } from './environment-style.js';
import { EnvironmentAudio } from './environment-audio.js';

export class EnvironmentView {
  constructor(scene, renderer, sun, ambient, canvas) {
    this.renderer = renderer; this.scene = scene; this.sun = sun; this.ambient = ambient; this.canvas = canvas;
    this.cues = new EnvironmentCueTracker(); this.audio = new EnvironmentAudio(canvas);
    this.geometry = new THREE.BufferGeometry(); this.positions = new Float32Array(1280 * 3);
    this.geometry.setAttribute('position', new THREE.BufferAttribute(this.positions, 3).setUsage(THREE.DynamicDrawUsage)); this.geometry.setDrawRange(0, 0);
    this.rain = new THREE.LineSegments(this.geometry, new THREE.LineBasicMaterial({ color: 0x99bbcc, transparent: true, opacity: .5, depthWrite: false }));
    this.rain.frustumCulled = false; scene.add(this.rain);
  }
  load(header) { this.version = header.environmentVersion || 0; this.rooms = [...header.roomIds]; this.latest = null; this.cues.reset(); this.audio.pause(); if (this.version !== 1) { this.audio.reset(); this.sun.position.set(10, 18, -8); } this.geometry.setDrawRange(0, 0); this.canvas.dataset.rainCount = '0'; this.canvas.dataset.environmentVersion = String(this.version); }
  show(frame, environment, continuous = true) {
    if (this.version !== 1 || !environment) { this.rain.visible = false; return false; }
    this.latest = { frame, environment }; this.continuous = continuous;
    const phase = !continuous && frame.phase === 'Running' ? 'Paused' : frame.phase;
    const style = environmentStyle(frame.tick, environment.weather, frame.night, environment.lightning, phase);
    const cue = this.cues.advance(frame.tick, environment.weather, frame.night, environment.lightning, phase);
    const sky = new THREE.Color(...style.sky); this.renderer.setClearColor(sky);
    this.scene.fog = style.fog ? new THREE.FogExp2(sky, style.fog) : null;
    this.sun.intensity = style.sun; this.ambient.intensity = style.ambient;
    this.sun.color.setRGB(frame.night && !style.flash ? .6 : 1, frame.night && !style.flash ? .72 : 1, 1);
    this.sun.position.set(frame.night ? -10 : 10, frame.night ? 12 : 18, frame.night ? 8 : -8);
    const perRoom = style.rain > .75 ? 128 : style.rain > 0 ? 64 : 0; let cursor = 0;
    for (const room of this.rooms) for (let index = 0; index < perRoom; index++) {
      const point = rainPoint(room, index, frame.tick);
      this.positions.set([point.x, point.y, point.z, point.x, Math.max(0, point.y - .32), point.z], cursor); cursor += 6;
    }
    this.geometry.attributes.position.needsUpdate = true; this.geometry.setDrawRange(0, cursor / 3); this.rain.visible = cursor > 0;
    this.rain.material.color.setRGB(frame.night ? .35 : .6, frame.night ? .48 : .72, frame.night ? .65 : .8);
    this.audio.apply(style.running ? style.rain : 0, cue);
    if (!style.running && this.audio.thunder) { this.audio.pause(); }
    this.canvas.dataset.rainCount = String(cursor / 6); this.canvas.dataset.weatherTick = String(frame.tick);
    this.canvas.dataset.weatherFlash = String(style.flash); this.canvas.dataset.weatherSun = String(style.sun); this.canvas.dataset.weatherFog = String(style.fog);
    this.canvas.dataset.weatherAudioPeak = String(this.audio.peak()); return true;
  }
  pause() {
    this.audio.pause(); this.cues.reset();
    if (this.latest) this.show(this.latest.frame, this.latest.environment, false);
  }
  reset() { this.audio.reset(); this.cues.reset(); this.latest = null; this.version = 0; this.geometry.setDrawRange(0, 0); this.rain.visible = false; this.canvas.dataset.rainCount = '0'; this.canvas.dataset.weatherFlash = 'false'; }
}
