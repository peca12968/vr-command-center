export class EnvironmentAudio {
  constructor(canvas) { this.canvas = canvas; this.enabled = false; this.epoch = 0; this.state = 'off'; this.level = 0; }
  status(value) { this.state = value; this.canvas.dataset.weatherAudio = value; }
  async toggle() {
    if (this.enabled) { this.reset(); return; }
    const current = ++this.epoch; this.enabled = true; this.status('loading');
    try {
      this.context ??= new AudioContext(); await this.context.resume();
      if (current !== this.epoch) return;
      this.gain ??= this.context.createGain(); this.gain.gain.value = .45;
      if (!this.analyser) { this.analyser = this.context.createAnalyser(); this.analyser.fftSize = 256; this.gain.connect(this.analyser); this.analyser.connect(this.context.destination); }
      this.buffers ??= await Promise.all(['rain-loop.wav', 'thunder.wav'].map(async name => {
        const response = await fetch(new URL('./audio/' + name, import.meta.url), { signal: AbortSignal.timeout(10000), cache: 'no-store' });
        if (!response.ok) throw new Error('Weather audio is unavailable'); return this.context.decodeAudioData(await response.arrayBuffer());
      }));
      if (current !== this.epoch) return;
      this.status('on'); this.apply(this.level, false);
    } catch { if (current === this.epoch) { this.enabled = false; this.stop(); this.status('error'); } }
  }
  stop() {
    for (const name of ['rain', 'thunder']) if (this[name]) { try { this[name].stop(); } catch { } this[name].disconnect(); this[name] = null; }
    this.rainGain?.disconnect(); this.rainGain = null;
  }
  apply(level, cue) {
    this.level = level;
    if (!this.enabled || this.state !== 'on') return;
    if (level > 0 && !this.rain) { this.rain = this.context.createBufferSource(); this.rain.buffer = this.buffers[0]; this.rain.loop = true; this.rainGain = this.context.createGain(); this.rain.connect(this.rainGain); this.rainGain.connect(this.gain); this.rain.start(); }
    if (this.rain) {
      this.rainGain.gain.value = level * .35;
      if (level === 0) { this.rain.stop(); this.rain.disconnect(); this.rainGain.disconnect(); this.rain = null; this.rainGain = null; }
    }
    if (cue) {
      if (this.thunder) { try { this.thunder.stop(); } catch { } this.thunder.disconnect(); }
      this.thunder = this.context.createBufferSource(); this.thunder.buffer = this.buffers[1]; this.thunder.connect(this.gain); this.thunder.start();
      this.canvas.dataset.thunderCount = String(Number(this.canvas.dataset.thunderCount || 0) + 1);
    }
  }
  pause() { this.level = 0; this.stop(); }
  peak() { if (!this.analyser) return 0; const values = new Float32Array(this.analyser.fftSize); this.analyser.getFloatTimeDomainData(values); return Math.max(...values.map(Math.abs)); }
  reset() {
    this.epoch++; this.enabled = false; this.level = 0; this.stop(); this.rainGain?.disconnect(); this.rainGain = null;
    this.status('off'); this.context?.suspend().catch(() => {}); this.canvas.dataset.thunderCount = '0'; this.canvas.dataset.weatherAudioPeak = '0';
  }
}
