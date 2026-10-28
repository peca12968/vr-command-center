export const ENVIRONMENT_VERSION = 1;
const PERIOD = 140, DELAY = 40, MAX_TICK = 1728000;
export function environmentStyle(tick, weather, night, lightning, phase) {
  if (!Number.isSafeInteger(tick) || tick < 0 || tick > MAX_TICK || !['Clear', 'Rain', 'Fog', 'Storm'].includes(weather) || !['Preparing', 'Running', 'Paused', 'Ended'].includes(phase)) throw new Error('Unsupported environment presentation');
  const running = phase === 'Running', flash = running && lightning && tick >= PERIOD && tick % PERIOD < 3;
  return { tick, rain: weather === 'Storm' ? 1 : weather === 'Rain' ? .5 : 0,
    fog: weather === 'Fog' ? .035 : weather === 'Clear' ? 0 : weather === 'Storm' ? .02 : .012,
    sun: flash ? 2.5 : night ? .08 : 1.15, ambient: night ? .18 : .65,
    sky: [night ? .035 : weather === 'Clear' ? .30 : .20, night ? .05 : weather === 'Clear' ? .42 : .25, night ? .085 : weather === 'Clear' ? .52 : .30], flash, running };
}
export function rainPoint(room, index, tick) {
  if (!Number.isInteger(room) || room < 1 || room > 5 || !Number.isInteger(index) || index < 0 || index >= 128 || !Number.isSafeInteger(tick) || tick < 0 || tick > MAX_TICK) throw new Error('Invalid rain sample');
  return { x: (room - 3) * 14 + ((index * 73 + room * 17) % 997) / 997 * 12 - 6,
    z: ((index * 137 + room * 29) % 991) / 991 * 12 - 6,
    y: 6 - (((index * 37) % 1000) / 1000 * 6 + (tick % 150) * .28) % 6 };
}
export class EnvironmentCueTracker {
  constructor() { this.reset(); }
  reset() { this.previous = null; this.observed = this.sounded = -1; }
  advance(tick, weather, night, lightning, phase) {
    const sample = environmentStyle(tick, weather, night, lightning, phase), before = this.previous;
    const gap = !before || tick < before.tick || tick - before.tick > 10 || weather !== before.weather || night !== before.night || lightning !== before.lightning;
    if (gap || phase === 'Preparing' || phase === 'Ended') this.observed = this.sounded = -1;
    const cycle = Math.floor(tick / PERIOD); if (sample.flash) this.observed = cycle;
    const sound = !gap && sample.running && before.phase === 'Running' && lightning && cycle > 0 && this.observed === cycle && this.sounded !== cycle && before.tick < cycle * PERIOD + DELAY && tick >= cycle * PERIOD + DELAY;
    if (sound) this.sounded = cycle;
    this.previous = { tick, weather, night, lightning, phase }; return Boolean(sound);
  }
}
