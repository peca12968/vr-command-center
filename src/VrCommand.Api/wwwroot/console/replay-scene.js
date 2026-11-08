import {PLAYER_BODY_ASSETS,playerBodyFactory,posePlayerBody} from './player-body.js';
import { cameraGroundTarget } from './camera-ground-target.js';
import * as THREE from './vendor/three/three.module.js';
import { EnvironmentView } from './environment-view.js';
import { fieldPropFactory, supportedAssets, FIELD_ASSETS, LEGACY_ASSETS } from './field-props.js';
import { RIFLE_ASSETS, serviceRifleFactory, placeRifle } from './service-rifle.js';
import { WEAPON_ACTION_ASSETS, weaponActionsFactory, applyWeaponPose } from './weapon-actions.js';
import { COMBATANT_ASSETS, opponentFactory, poseOpponent } from './combatants.js';

import { ARMED_ASSETS, armedOpponentFactory, poseArmedOpponent } from './armed-combatants.js';

import { COMBAT_EFFECT_ASSETS, firingOpponentFactory, poseFiringOpponent } from './combat-effects.js';

import { PLAYER_FIRE_ASSETS, firingRifleFactory, applyPlayerFire } from './player-fire.js';

const point = value => new THREE.Vector3(value.x, value.y, value.z);
const roomX = id => (id - 3) * 14;
export class ReplayScene {
  constructor(canvas, onPick, onFreeMove) {
    this.canvas = canvas; this.onPick = onPick; this.onFreeMove = onFreeMove;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
    this.renderer.setClearColor(0x101a17); this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(48, 1, .05, 300);
    this.target = new THREE.Vector3(0, .8, 0); this.theta = .6; this.phi = .9; this.radius = 15;
    this.actors = new Map(); this.follow = false; this.selected = ''; this.frame = null;
    this.stage = new THREE.Group(); this.traces = new THREE.Group(); this.scene.add(this.stage, this.traces);
    this.ambient = new THREE.HemisphereLight(0xd5e3dc, 0x394637, 2.2); this.scene.add(this.ambient);
    this.sun = new THREE.DirectionalLight(0xffe4ba, 2.5); this.sun.position.set(10, 18, -8); this.scene.add(this.sun);
    this.weather = new EnvironmentView(this.scene, this.renderer, this.sun, this.ambient, canvas);
    this.marker = new THREE.Mesh(new THREE.RingGeometry(.5, .57, 32), new THREE.MeshBasicMaterial({ color: 0xe3f594, side: THREE.DoubleSide }));
    this.marker.rotation.x = -Math.PI / 2; this.marker.visible = false; this.scene.add(this.marker);
    this.observer = new ResizeObserver(() => this.resize()); this.observer.observe(canvas.parentElement);
    this.input(); this.resize();
  }
  mesh(geometry, color) { return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, roughness: .8 })); }
  clear(group) {
    const geometries = new Set(), materials = new Set();
    group.traverse(object => {
      if (object.geometry && !object.geometry.userData.serviceRifleShared && !object.geometry.userData.enemyModelShared) geometries.add(object.geometry);
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) if (material) materials.add(material);
    });
    for (const geometry of geometries) geometry.dispose(); for (const material of materials) material.dispose();
    group.clear();
  }
  load(recording) {
    const assetSet = recording.assetSet === undefined ? LEGACY_ASSETS : recording.assetSet;
    if (!supportedAssets(assetSet)) throw new Error('不支援的錄製素材版本。');
    if (![0,1].includes(recording.enemyPresentationVersion ?? 0) || assetSet === COMBATANT_ASSETS && recording.enemyPresentationVersion !== 1) throw new Error('不支援的敵軍姿態版本。');
    if (![0,1].includes(recording.weaponPresentationVersion ?? 0) || [WEAPON_ACTION_ASSETS,ARMED_ASSETS,COMBAT_EFFECT_ASSETS,PLAYER_FIRE_ASSETS,PLAYER_BODY_ASSETS].includes(assetSet) && (recording.weaponPresentationVersion !== 1 || recording.enemyPresentationVersion !== 1)) throw new Error('不支援的武器動作版本。');
    if(![0,1].includes(recording.enemyFireVersion??0) || assetSet===COMBAT_EFFECT_ASSETS && (recording.enemyFireVersion!==1 || recording.enemyPresentationVersion!==1 || recording.weaponPresentationVersion!==1))throw new Error('不支援的敵軍射擊效果版本。');
    if(![0,1].includes(recording.playerFireVersion??0)||assetSet===PLAYER_FIRE_ASSETS&&(recording.playerFireVersion!==1||recording.enemyFireVersion!==1||recording.enemyPresentationVersion!==1||recording.weaponPresentationVersion!==1))throw new Error('不支援的玩家射擊效果版本。');
    if(![0,1].includes(recording.playerPresentationVersion??0)||assetSet===PLAYER_BODY_ASSETS&&(recording.playerPresentationVersion!==1||recording.playerFireVersion!==1||recording.enemyFireVersion!==1||recording.weaponPresentationVersion!==1||recording.enemyPresentationVersion!==1))throw Error('不支援的玩家人物版本。');
    this.roomIds = [...recording.roomIds];
    this.audioRoom='all';
    this.weather.audio.reset();
    this.weather.load(recording);
    if(![0,1].includes(recording.combatAudioVersion??0)||recording.combatAudioVersion===1&&(recording.enemyFireVersion!==1||recording.playerFireVersion!==1))throw new Error('不支援的戰鬥音效版本。');
    this.weather.audio.combat.load(recording);
    this.clear(this.stage); this.clear(this.traces); this.actors.clear(); this.selected = ''; this.follow = false;
    this.playerBodies?.dispose();this.playerBodies=assetSet===PLAYER_BODY_ASSETS?playerBodyFactory():null;this.canvas.dataset.playerBodyTriangles=String(this.playerBodies?.triangles||0);
    this.rifles?.dispose(); this.rifles = [PLAYER_FIRE_ASSETS,PLAYER_BODY_ASSETS].includes(assetSet) ? firingRifleFactory() : [WEAPON_ACTION_ASSETS,ARMED_ASSETS,COMBAT_EFFECT_ASSETS,PLAYER_FIRE_ASSETS,PLAYER_BODY_ASSETS].includes(assetSet) ? weaponActionsFactory() : [RIFLE_ASSETS, COMBATANT_ASSETS].includes(assetSet) ? serviceRifleFactory() : null;
    this.opponents?.dispose(); this.opponents = [COMBAT_EFFECT_ASSETS,PLAYER_FIRE_ASSETS,PLAYER_BODY_ASSETS].includes(assetSet) ? firingOpponentFactory() : assetSet === ARMED_ASSETS ? armedOpponentFactory() : [COMBATANT_ASSETS, WEAPON_ACTION_ASSETS].includes(assetSet) ? opponentFactory() : null;
    for (const room of recording.roomIds) {
      const floor = this.mesh(new THREE.BoxGeometry(12, .2, 12), 0x344638); floor.position.set(roomX(room), -.12, 0); this.stage.add(floor);
      const grid = new THREE.GridHelper(12, 24, 0x8b9b6c, 0x4c6354); grid.position.set(roomX(room), -.005, 0); this.stage.add(grid);
      const boundary = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([[-6,-6],[6,-6],[6,6],[-6,6]].map(([x,z]) => new THREE.Vector3(roomX(room) + x, .01, z))), new THREE.LineBasicMaterial({ color: 0xc1d281 })); this.stage.add(boundary);
    }
    const createProp = [FIELD_ASSETS, RIFLE_ASSETS, COMBATANT_ASSETS, WEAPON_ACTION_ASSETS, ARMED_ASSETS, COMBAT_EFFECT_ASSETS, PLAYER_FIRE_ASSETS, PLAYER_BODY_ASSETS].includes(assetSet) && recording.props.length ? fieldPropFactory() : null;
    let propTriangles = 0;
    for (const prop of recording.props) {
      if (createProp) {
        const mesh = createProp(prop.kind); mesh.position.copy(point(prop.feet)); mesh.rotation.y = prop.yaw * Math.PI / 180;
        propTriangles += mesh.geometry.index.count / 3; this.stage.add(mesh); continue;
      }
      const half = prop.kind === 'Barrel' ? [.35, .6, .35] : [1, .45, .35];
      // These are the exact box colliders used by the simulation, not decorative geometry.
      const mesh = this.mesh(new THREE.BoxGeometry(half[0] * 2, half[1] * 2, half[2] * 2), prop.kind === 'Barrel' ? 0x6b8e91 : 0xa59a69);
      mesh.position.copy(point(prop.feet)).add(new THREE.Vector3(0, half[1], 0)); mesh.rotation.y = prop.yaw * Math.PI / 180; this.stage.add(mesh);
      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(mesh.geometry), new THREE.LineBasicMaterial({ color: 0xc9d4ba })); mesh.add(edges);
      propTriangles += mesh.geometry.index.count / 3;
    }
    this.canvas.dataset.assetSet = assetSet; this.canvas.dataset.propTriangles = String(propTriangles);
    this.canvas.dataset.rifleTriangles = String(this.rifles?.triangles || 0); this.canvas.dataset.rifleCount = '0';
    this.canvas.dataset.enemyTriangles = String(this.opponents?.triangles || 0); this.canvas.dataset.enemyPoses = '[]'; this.canvas.dataset.weaponPoses = '[]'; this.canvas.dataset.enemyFirePoses='[]'; this.canvas.dataset.playerFirePoses='[]';
    this.defaultTarget = new THREE.Vector3(recording.roomIds.reduce((sum, id) => sum + roomX(id), 0) / recording.roomIds.length, .8, 0);
    this.defaultRadius = recording.roomIds.length === 5 ? 49 : 15; this.preset('overview');
  }
  actor(key, enemy) {
    if (this.actors.has(key)) return this.actors.get(key);
    if (enemy && this.opponents) {
      const entry = this.opponents.create(); entry.group.userData.key = key; this.actors.set(key, entry); this.stage.add(entry.group); return entry;
    }
    const group = new THREE.Group(); group.userData.key = key;
    const body = this.mesh(new THREE.BoxGeometry(1, 1, 1), enemy ? 0xc26754 : 0x82bc94); group.add(body);
    const head = this.mesh(new THREE.SphereGeometry(.17, 12, 8), enemy ? 0xefad84 : 0xb7e7c6); group.add(head);
    const gun = !enemy && this.rifles ? this.rifles.create() : this.mesh(new THREE.BoxGeometry(.08, .08, .45), enemy ? 0x5e312a : 0x222e28); group.add(gun); if(gun.userData.playerFire)group.add(gun.userData.playerFire.flash);
    const left = this.mesh(new THREE.BoxGeometry(.09, .06, .18), 0xa6d9ce), right = this.mesh(new THREE.BoxGeometry(.09, .06, .18), 0xa6d9ce);
    left.visible = right.visible = false; group.add(left, right);
    const facing = this.mesh(new THREE.BoxGeometry(.06, .04, .12), 0x344f40); facing.position.z = .18; head.add(facing);
    const playerBody=!enemy&&this.playerBodies?this.playerBodies.create():null;if(playerBody)group.add(playerBody.group);
    const entry = { group, body, head, gun, left, right, enemy,playerBody }; this.actors.set(key, entry); this.stage.add(group); return entry;
  }
  show(frame, previous, events, environment, continuous = true) {
    this.frame = frame;
    const present = new Set([...frame.players.map(player => 'p:' + player.id), ...frame.enemies.map(enemy => 'e:' + enemy.id)]);
    for (const [key, actor] of this.actors) if (!present.has(key)) { this.clear(actor.group); this.stage.remove(actor.group); this.actors.delete(key); }
    for (const actor of this.actors.values()) actor.group.visible = false;
    for (const player of frame.players) {
      const actor = this.actor('p:' + player.id, false), height = player.head.y;
      actor.group.visible = true; actor.group.position.set(player.head.x, 0, player.head.z);
      actor.body.scale.set(.44, Math.max(.25, height - .3), .35); actor.body.position.set(0, Math.max(.25, height - .3) / 2, 0);
      actor.body.rotation.y = Math.atan2(player.forward.x, player.forward.z); actor.head.position.set(0, height, 0);
      actor.head.quaternion.set(0, 0, 0, 1);
      if (player.rig && player.rig.kind !== 'None') {
        const rotation = player.rig.headRotation; actor.head.quaternion.set(rotation.x, rotation.y, rotation.z, rotation.w);
        for (const side of ['left', 'right']) {
          actor[side].visible = true; actor[side].position.copy(point(player.rig[side])).sub(actor.group.position);
          const value = player.rig[side + 'Rotation']; actor[side].quaternion.set(value.x, value.y, value.z, value.w);
        }
      } else actor.left.visible = actor.right.visible = false;
      if (this.rifles) actor.right.visible = false; // Pointer origin is the muzzle, not a measured grip pose.
      actor.gun.position.copy(point(player.muzzle)).sub(actor.group.position); actor.gun.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), point(player.forward).normalize());
      if (this.rifles) placeRifle(actor.gun, player, actor.group.position);
      if (actor.gun.userData.weaponActions) { applyWeaponPose(actor.gun,player,frame.tick); if(player.rig?.kind==='Simulated')actor.left.visible=false; }
      if(actor.gun.userData.playerFire)applyPlayerFire(actor.gun,player,frame.tick);
      if(actor.playerBody){actor.body.visible=actor.head.visible=false;posePlayerBody(actor.playerBody,player,frame.tick,actor.group.position);}
      for (const mesh of [actor.body, actor.head, actor.gun, actor.left, actor.right]) { const faded = player.health === 0 || player.connected === false; mesh.material.transparent = faded; mesh.material.opacity = faded ? .25 : 1; }
    }
    for (const enemy of frame.enemies) {
      const actor = this.actor('e:' + enemy.id, true); actor.group.visible = true; actor.group.position.copy(point(enemy.feet));
      if (actor.model) {
        if(actor.fire)poseFiringOpponent(actor,enemy,frame.tick);else if(actor.armed) poseArmedOpponent(actor,enemy,frame.tick); else poseOpponent(actor, enemy, frame.tick);
        for (const mesh of [actor.body, actor.head, actor.leftLeg, actor.rightLeg]) { mesh.material.transparent = enemy.health === 0; mesh.material.opacity = enemy.health === 0 ? .18 : 1; }
        continue;
      }
      actor.body.scale.set(.5, 1.25, .4); actor.body.position.set(0, .68, 0); actor.head.position.set(0, 1.52, 0); actor.gun.position.set(.25, 1.1, -.3);
      const before = previous?.enemies.find(value => value.id === enemy.id);
      if (before && Math.hypot(enemy.feet.x - before.feet.x, enemy.feet.z - before.feet.z) > .001) actor.group.rotation.y = Math.atan2(enemy.feet.x - before.feet.x, enemy.feet.z - before.feet.z);
      for (const mesh of [actor.body, actor.head, actor.gun]) { mesh.material.transparent = enemy.health === 0; mesh.material.opacity = enemy.health === 0 ? .18 : 1; }
    }
    this.clear(this.traces);
    for (const event of events) {
      const start = point(event.origin), end = start.clone().addScaledVector(point(event.direction), event.distance);
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([start, end]), new THREE.LineBasicMaterial({ color: event.kind === 'EnemyShot' ? 0xff775f : 0xf4e795 })); this.traces.add(line);
      const hit = new THREE.Mesh(new THREE.SphereGeometry(.065, 8, 6), new THREE.MeshBasicMaterial({ color: event.hit === 'Cover' ? 0xffb454 : 0xf4ecba })); hit.position.copy(end); this.traces.add(hit);
    }
    this.canvas.dataset.playerBodyPoses=JSON.stringify([...this.actors.values()].filter(a=>a.playerBody&&a.group.visible).map(a=>{const m=a.playerBody;a.group.updateMatrixWorld(true);const end=b=>b.localToWorld(new THREE.Vector3(0,1,0)).toArray();return{id:a.group.userData.key.slice(2),visible:m.group.visible,yaw:m.bodyFrame.rotation.y*180/Math.PI,heightScale:m.bodyFrame.scale.y,stride:m.leftLeg.rotation.x*180/Math.PI,head:m.head.getWorldPosition(new THREE.Vector3()).toArray(),leftElbow:end(m.leftUpper),leftWrist:end(m.leftLower),rightElbow:end(m.rightUpper),rightWrist:end(m.rightLower),arms:m.leftUpper.visible};}));
    this.canvas.dataset.traceCount = String(events.length);
    this.canvas.dataset.rifleCount = String(this.rifles ? frame.players.length : 0);
    this.canvas.dataset.playerFirePoses=JSON.stringify([...this.actors.values()].filter(a=>!a.enemy&&a.gun.userData.playerFire).map(a=>{
      const v=a.gun.userData.playerFire;a.group.updateMatrixWorld(true);return{id:a.group.userData.key.slice(2),flash:v.flash.visible,recoil:-v.recoil.position.z,
        origin:v.flash.getWorldPosition(new THREE.Vector3()).toArray(),direction:new THREE.Vector3(0,0,1).applyQuaternion(v.flash.getWorldQuaternion(new THREE.Quaternion())).toArray(),gun:a.gun.getWorldPosition(new THREE.Vector3()).toArray()};}));
    this.canvas.dataset.enemyFirePoses=JSON.stringify([...this.actors.values()].filter(a=>a.fire&&a.group.visible).map(a=>{
      a.group.updateMatrixWorld(true);return {id:a.group.userData.key.slice(2),flash:a.flash.visible,recoil:-a.sidearm.position.z,
        origin:a.flash.getWorldPosition(new THREE.Vector3()).toArray(),direction:new THREE.Vector3(0,0,1).applyQuaternion(a.flash.getWorldQuaternion(new THREE.Quaternion())).toArray()};}));
    this.canvas.dataset.armedPoses=JSON.stringify([...this.actors.values()].filter(a=>a.armed&&a.group.visible).map(a=>{
      a.group.updateMatrixWorld(true); const v=p=>p.toArray(); const end=m=>v(m.localToWorld(new THREE.Vector3(0,1,0)));
      return {id:a.group.userData.key.slice(2),muzzle:v(a.gun.getWorldPosition(new THREE.Vector3())),forward:v(new THREE.Vector3(0,0,1).applyQuaternion(a.gun.getWorldQuaternion(new THREE.Quaternion()))),
        leftElbow:end(a.leftUpper),leftWrist:end(a.leftLower),rightElbow:end(a.rightUpper),rightWrist:end(a.rightLower)};}));
    this.canvas.dataset.enemyPoses = JSON.stringify([...this.actors.values()].filter(a => a.model && a.group.visible).map(a => ({ id: a.group.userData.key.slice(2),
      yaw: a.group.rotation.y * 180 / Math.PI, pitch: a.head.rotation.x * 180 / Math.PI, left: a.leftLeg.rotation.x * 180 / Math.PI, right: a.rightLeg.rotation.x * 180 / Math.PI })));
    this.canvas.dataset.weaponPoses=JSON.stringify([...this.actors.values()].filter(a=>!a.enemy&&a.gun.userData.weaponActions).map(a=>{
      const v=a.gun.userData.weaponActions;return {id:a.group.userData.key.slice(2),magazine:v.magazine.position.toArray(),roll:v.magazine.rotation.z*180/Math.PI,
        magazineVisible:v.magazine.visible,left:v.left.position.toArray(),leftRoll:v.left.rotation.z*180/Math.PI,hands:v.left.visible&&v.right.visible};}));
    if (!this.weather.show(frame, environment, continuous)) {
      this.ambient.intensity = frame.night ? .8 : 2.2; this.sun.intensity = frame.night ? .35 : 2.5;
      this.sun.color.setHex(0xffe4ba); this.renderer.setClearColor(0x101a17);
      this.scene.fog = frame.visibility === 'Clear' ? null : new THREE.FogExp2(frame.night ? 0x111e25 : 0x637266, frame.visibility === 'Fog' ? .035 : .015);
    }
    this.draw();
    this.weather.audio.combat.show(frame,this.camera,this.audioRoom,continuous);
    this.canvas.dataset.combatAudioPeak=String(this.weather.audio.peak());
  }
  select(key) { this.selected = key; this.draw(); }
  fitRadius(radius) { const aspect = this.canvas.parentElement.clientWidth / Math.max(1, this.canvas.parentElement.clientHeight); return radius * Math.max(1, 1.5 / Math.max(.4, aspect)); }
  setAudioRoom(room) {
    if (this.audioRoom === room) return;
    this.audioRoom = room; this.weather.audio.combat.pause();
  }
  focus(room) {
    if (room === 'all') { this.preset('overview'); return; }
    const id = Number(room); if (!this.roomIds?.includes(id)) return;
    this.follow = false; this.target.set(roomX(id), .8, 0); this.radius = Math.min(240, this.fitRadius(15)); this.draw();
  }
  view() {
    this.draw(); // Resolve a moving follow target before saving a fixed world position.
    return { target: this.target.toArray(), theta: Math.atan2(Math.sin(this.theta), Math.cos(this.theta)), phi: this.phi, radius: this.radius };
  }
  restoreView(view) {
    this.follow = false; this.target.fromArray(view.target); this.theta = view.theta; this.phi = view.phi; this.radius = view.radius; this.draw();
  }
  preset(mode, room = 'all') {
    const id = Number(room), focused = this.roomIds?.includes(id);
    if (focused) this.target.set(roomX(id), .8, 0);
    else this.target.copy(this.defaultTarget || new THREE.Vector3(0, .8, 0));
    this.follow = false; this.radius = Math.min(240, this.fitRadius(focused ? 15 : this.defaultRadius || 15));
    this.theta = mode === 'top' ? 0 : .6; this.phi = mode === 'top' ? .08 : .9; this.draw();
  }
  resize() {
    const width = this.canvas.parentElement.clientWidth, height = this.canvas.parentElement.clientHeight;
    if (!width || !height) return;
    this.renderer.setSize(width, height, false); this.camera.aspect = width / height; this.camera.updateProjectionMatrix(); this.draw();
  }
  draw() {
    const actor = this.actors.get(this.selected);
    if (this.follow && actor?.group.visible) this.target.copy(actor.group.position).add(new THREE.Vector3(0, 1, 0));
    this.marker.visible = !!actor?.group.visible;
    if (this.marker.visible) this.marker.position.copy(actor.group.position).setY(.02);
    this.camera.position.copy(this.target).add(new THREE.Vector3(this.radius * Math.sin(this.phi) * Math.sin(this.theta), this.radius * Math.cos(this.phi), -this.radius * Math.sin(this.phi) * Math.cos(this.theta)));
    this.camera.lookAt(this.target); this.renderer.render(this.scene, this.camera);
    this.canvas.dataset.triangles = String(this.renderer.info.render.triangles);
    this.canvas.dataset.camera = this.camera.position.toArray().map(x => x.toFixed(2)).join(',');
  }
  input() {
    let drag = null;
    this.canvas.addEventListener('contextmenu', event => event.preventDefault());
    this.canvas.addEventListener('pointerdown', event => { this.canvas.focus(); drag = { id: event.pointerId, x: event.clientX, y: event.clientY, firstX: event.clientX, firstY: event.clientY, pan: event.button === 2 || event.shiftKey }; this.canvas.setPointerCapture(event.pointerId); });
    this.canvas.addEventListener('pointermove', event => {
      if (!drag || drag.id !== event.pointerId) return;
      const dx = event.clientX - drag.x, dy = event.clientY - drag.y; drag.x = event.clientX; drag.y = event.clientY;
      if (drag.pan) { this.follow = false; this.onFreeMove(); this.pan(dx, dy); }
      else { this.theta -= dx * .007; this.phi = Math.max(.06, Math.min(1.5, this.phi + dy * .007)); }
      this.draw();
    });
    this.canvas.addEventListener('pointerup', event => {
      if (drag && !drag.pan && Math.hypot(event.clientX - drag.firstX, event.clientY - drag.firstY) < 5) this.pick(event);
      drag = null;
    });
    for (const name of ['pointercancel', 'lostpointercapture']) this.canvas.addEventListener(name, () => { drag = null; });
    this.canvas.addEventListener('dblclick', event => {
      if (event.button !== 0 || event.shiftKey || event.ctrlKey || event.altKey || event.metaKey || !this.frame) return;
      const bounds = this.canvas.getBoundingClientRect();
      if (!bounds.width || !bounds.height) return;
      this.draw(); // Resolve a current follow target before projecting the click.
      const cursor = new THREE.Vector2((event.clientX - bounds.left) / bounds.width * 2 - 1, 1 - (event.clientY - bounds.top) / bounds.height * 2);
      const ray = new THREE.Raycaster(); ray.setFromCamera(cursor, this.camera);
      const location = cameraGroundTarget(ray.ray.origin, ray.ray.direction, this.roomIds);
      if (!location) return;
      this.follow = false; this.target.fromArray(location.target); this.onFreeMove(); this.draw();
    });
    this.canvas.addEventListener('wheel', event => { event.preventDefault(); this.radius = Math.max(2, Math.min(240, this.radius * Math.exp(event.deltaY * .001))); this.draw(); }, { passive: false });
    this.canvas.addEventListener('keydown', event => {
      const keys = { ArrowLeft: [-15, 0], ArrowRight: [15, 0], ArrowUp: [0, -15], ArrowDown: [0, 15] };
      if (keys[event.key]) { event.preventDefault(); this.follow = false; this.onFreeMove(); this.pan(...keys[event.key]); this.draw(); }
      if (event.key === '+' || event.key === '-') { event.preventDefault(); this.radius = Math.max(2, Math.min(240, this.radius * (event.key === '+' ? .9 : 1.1))); this.draw(); }
    });
  }
  pan(dx, dy) {
    const right = new THREE.Vector3().setFromMatrixColumn(this.camera.matrixWorld, 0), forward = new THREE.Vector3().setFromMatrixColumn(this.camera.matrixWorld, 1);
    this.target.addScaledVector(right, -dx * this.radius / 600).addScaledVector(forward, dy * this.radius / 600);
  }
  pick(event) {
    const bounds = this.canvas.getBoundingClientRect(), cursor = new THREE.Vector2((event.clientX - bounds.left) / bounds.width * 2 - 1, 1 - (event.clientY - bounds.top) / bounds.height * 2);
    const ray = new THREE.Raycaster(); ray.setFromCamera(cursor, this.camera);
    const hit = ray.intersectObjects([...this.actors.values()].filter(actor => actor.group.visible).map(actor => actor.group), true)[0];
    if (hit) { let object = hit.object; while (object && !object.userData.key) object = object.parent; if (object) this.onPick(object.userData.key); }
  }
  reset() { this.playerBodies?.dispose();this.playerBodies=null;this.canvas.dataset.playerBodyPoses='[]';this.canvas.dataset.playerBodyTriangles='0';this.weather.reset(); this.frame = null; this.follow = false; this.selected = ''; this.clear(this.stage); this.clear(this.traces); this.rifles?.dispose(); this.rifles = null; this.opponents?.dispose(); this.opponents = null; this.actors.clear(); this.canvas.dataset.rifleCount = '0'; this.canvas.dataset.rifleTriangles = '0'; this.canvas.dataset.enemyTriangles = '0'; this.canvas.dataset.enemyPoses = '[]'; this.canvas.dataset.weaponPoses = '[]'; this.canvas.dataset.enemyFirePoses='[]'; this.canvas.dataset.playerFirePoses='[]'; this.marker.visible = false; this.draw(); }
}
