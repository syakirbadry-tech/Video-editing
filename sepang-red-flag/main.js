// "Red Flag at Sepang" — 50 s cinematic explainer.
// Everything is a pure function of time t so frames can be rendered deterministically.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const W = 1920, H = 1080;
const V3 = THREE.Vector3, UP = new V3(0, 1, 0);

// ---------------------------------------------------------------- utils
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;
const seg = (t, a, b) => clamp((t - a) / (b - a));
const eio = k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
const eoe = k => k >= 1 ? 1 : 1 - Math.pow(2, -10 * k);
const eie = k => k <= 0 ? 0 : Math.pow(2, 10 * k - 10);
const eob = k => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };
const sst = k => k * k * (3 - 2 * k);
const fract = x => x - Math.floor(x);
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let r = Math.imul(seed ^ seed >>> 15, 1 | seed); r = r + Math.imul(r ^ r >>> 7, 61 | r) ^ r; return ((r ^ r >>> 14) >>> 0) / 4294967296; }; }
// numeric integral of f over [t0,t1] -> lookup function
function integral(f, t0, t1, dt = 1 / 240) {
  const n = Math.ceil((t1 - t0) / dt), acc = new Float64Array(n + 1);
  for (let i = 1; i <= n; i++) acc[i] = acc[i - 1] + f(t0 + (i - .5) * dt) * dt;
  return t => { const x = clamp((t - t0) / dt, 0, n), i = Math.floor(x), k = x - i; return i >= n ? acc[n] : lerp(acc[i], acc[i + 1], k); };
}
// Catmull-Rom over numeric keyframes [[time,[...vals]],...]
function keys(t, K) {
  if (t <= K[0][0]) return K[0][1].slice();
  if (t >= K[K.length - 1][0]) return K[K.length - 1][1].slice();
  let i = 0; while (t > K[i + 1][0]) i++;
  const k = (t - K[i][0]) / (K[i + 1][0] - K[i][0]);
  const p0 = K[Math.max(0, i - 1)][1], p1 = K[i][1], p2 = K[i + 1][1], p3 = K[Math.min(K.length - 1, i + 2)][1];
  return p1.map((_, j) => {
    const a = p0[j], b = p1[j], c = p2[j], d = p3[j];
    return .5 * ((2 * b) + (-a + c) * k + (2 * a - 5 * b + 4 * c - d) * k * k + (-a + 3 * b - 3 * c + d) * k * k * k);
  });
}

// ---------------------------------------------------------------- renderer
const glc = document.createElement('canvas'); glc.width = W; glc.height = H;
const renderer = new THREE.WebGLRenderer({ canvas: glc, antialias: false, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x0a0e16, 0.001);
scene.background = new THREE.Color(0x0a0e16);
const camera = new THREE.PerspectiveCamera(40, W / H, 0.03, 40000);
const rt = new THREE.WebGLRenderTarget(W, H, { type: THREE.HalfFloatType, samples: 4 });
const composer = new EffectComposer(renderer, rt);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W / 2, H / 2), 0.7, 0.55, 0.82);
composer.addPass(bloom);
composer.addPass(new OutputPass());

const ENV = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), .04).texture;
const hemi = new THREE.HemisphereLight(0x9fb3c8, 0x15181c, 1.0); scene.add(hemi);
const sun = new THREE.DirectionalLight(0xc8d6ff, 1.0); sun.position.set(300, 800, 200); scene.add(sun);
const rim = new THREE.SpotLight(0xffffff, 0, 0, .5, .6, 0); scene.add(rim); scene.add(rim.target);

function spriteTex() {
  const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d');
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.35, 'rgba(255,255,255,.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64); return new THREE.CanvasTexture(c);
}
const SPRITE = spriteTex();

// ---------------------------------------------------------------- track (stylised Sepang, mirrored so T1 is a right-hander)
const RAW = [[-0.95, .35], [0, .35], [.95, .35], [1.22, .3], [1.25, .08], [1.05, 0], [.3, 0], [-.6, 0], [-1.05, 0], [-1.3, -.08], [-1.32, -.28], [-1.15, -.4], [-1.25, -.6], [-1.1, -.88], [-.7, -.98], [-.3, -.9], [0, -1], [.25, -.85], [.5, -.95], [.8, -.8], [1.05, -.95], [1.45, -.9], [1.65, -.6], [1.6, -.35], [1.7, .1], [1.75, .45], [1.6, .75], [1.25, .8], [1, .95], [.95, .75], [.6, .7], [.2, .85], [-.2, .7], [-.55, .8], [-.95, .75], [-1.15, .6], [-1.1, .42]];
let tp = RAW.map(([x, y]) => new V3(-x, 0, -y));
const scale = 5543 / new THREE.CatmullRomCurve3(tp, true, 'centripetal').getLength();
tp = tp.map(p => p.multiplyScalar(scale));
const curve = new THREE.CatmullRomCurve3(tp, true, 'centripetal'); curve.arcLengthDivisions = 6000;
const L = curve.getLength();
const NS = 2400, P = [], TN = [], RT = [];
for (let i = 0; i <= NS; i++) {
  const u = (i % NS) / NS; P.push(curve.getPointAt(u)); const tn = curve.getTangentAt(u); TN.push(tn);
  RT.push(new V3().crossVectors(tn, UP).normalize());
}
function frameAt(s) {
  const x = ((s / L) % 1 + 1) % 1 * NS, i = Math.floor(x), k = x - i, j = i + 1;
  return { p: P[i].clone().lerp(P[j], k), f: TN[i].clone().lerp(TN[j], k).normalize(), r: RT[i].clone().lerp(RT[j], k).normalize() };
}
function sNear(x, z) { let b = 0, bd = 1e18; for (let i = 0; i < NS; i++) { const d = (P[i].x - x) ** 2 + (P[i].z - z) ** 2; if (d < bd) { bd = d; b = i; } } return b / NS * L; }
const curv = i => { const a = TN[(i - 6 + NS) % NS], b = TN[(i + 6) % NS]; return Math.acos(clamp(a.dot(b), -1, 1)); };

function ribbon(o0, o1, y, colorFn, mat) {
  const pos = [], col = [], idx = [];
  for (let i = 0; i <= NS; i++) {
    const p = P[i], r = RT[i]; pos.push(p.x + r.x * o0, y, p.z + r.z * o0, p.x + r.x * o1, y, p.z + r.z * o1);
    const c = colorFn ? colorFn(i) : [1, 1, 1]; col.push(...c, ...c);
    if (i < NS) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.setIndex(idx); g.computeVertexNormals();
  return new THREE.Mesh(g, mat);
}
const world = new THREE.Group(); scene.add(world);
const ground = new THREE.Mesh(new THREE.PlaneGeometry(40000, 40000), new THREE.MeshStandardMaterial({ color: 0x0b100d, roughness: .85, metalness: 0 }));
ground.rotation.x = -Math.PI / 2; ground.position.y = -.25; scene.add(ground);
const grid = new THREE.GridHelper(9000, 90, 0x1d4458, 0x0f2230); grid.position.y = -.2; grid.material.transparent = true; grid.material.opacity = .5; world.add(grid);
const trackG = new THREE.Group(); world.add(trackG);
const asphalt = new THREE.MeshStandardMaterial({ color: 0x1c1f25, roughness: .12, metalness: .3, envMapIntensity: .9, side: THREE.DoubleSide });
trackG.add(ribbon(-7, 7, 0, null, asphalt));
const edgeMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(.9, .95, 1.05), side: THREE.DoubleSide });
const vc = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .4, side: THREE.DoubleSide });
for (const s of [-1, 1]) {
  trackG.add(ribbon(s * 6.4, s * 7, .02, null, edgeMat));
  trackG.add(ribbon(s * 7, s * 8.6, .015, i => curv(i) > .1 ? ((i >> 1) & 1 ? [.8, .05, .05] : [.9, .9, .9]) : [.05, .08, .06], vc));
}
const rlineMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(.25, 1.6, 2.6), toneMapped: false, transparent: true, side: THREE.DoubleSide, fog: false });
const rline = ribbon(-4, 4, .6, null, rlineMat); world.add(rline);
const glowMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(4, .3, .2), toneMapped: false, side: THREE.DoubleSide, fog: false });
// stands between the two straights + pit building
const standMat = new THREE.MeshStandardMaterial({ color: 0x2a3038, roughness: .7, metalness: .2 });
const lampMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 2.0, 1.7), toneMapped: false });
{
  const st = new THREE.Mesh(new THREE.BoxGeometry(1.7 * scale, 18, 30), standMat); st.position.set(0, 9, -.175 * scale); trackG.add(st);
  const roof = new THREE.Mesh(new THREE.BoxGeometry(1.7 * scale, 1, 40), standMat); roof.position.set(0, 26, -.175 * scale); trackG.add(roof);
  for (const z of [-.175 * scale + 19, -.175 * scale - 19]) { const l = new THREE.Mesh(new THREE.BoxGeometry(1.7 * scale, .5, .5), lampMat); l.position.set(0, 25.5, z); trackG.add(l); }
  const pit = new THREE.Mesh(new THREE.BoxGeometry(1.2 * scale, 11, 22), standMat); pit.position.set(-.1 * scale, 5.5, 40); trackG.add(pit);
  const pl = new THREE.Mesh(new THREE.BoxGeometry(1.2 * scale, .4, .4), lampMat); pl.position.set(-.1 * scale, 9, 28.8); trackG.add(pl);
  // pit wall
  const pw = new THREE.Mesh(new THREE.BoxGeometry(1.4 * scale, 1.1, .6), new THREE.MeshStandardMaterial({ color: 0x8a9099, roughness: .5 })); pw.position.set(0, .55, 13); trackG.add(pw);
}
// palm-ish tree blobs around the circuit for scale
{
  const r = rng(7), g = new THREE.ConeGeometry(4, 14, 6), m = new THREE.MeshStandardMaterial({ color: 0x0d1f12, roughness: 1 });
  const inst = new THREE.InstancedMesh(g, m, 700), M = new THREE.Matrix4();
  for (let i = 0; i < 700; i++) {
    let x, z, ok = false;
    for (let tries = 0; tries < 20 && !ok; tries++) { x = (r() * 4.6 - 2.3) * scale; z = (r() * 2.8 - 1.4) * scale; const s = sNear(x, z); const fp = frameAt(s).p; ok = Math.hypot(fp.x - x, fp.z - z) > 45; }
    const sc = .7 + r() * .8; M.compose(new V3(x, 6 * sc, z), new THREE.Quaternion(), new V3(sc, sc, sc)); inst.setMatrixAt(i, M);
  }
  trackG.add(inst);
}

// ---------------------------------------------------------------- cars
function makeCar(body, accent, helmet = 0xffd400) {
  const g = new THREE.Group();
  const mB = new THREE.MeshStandardMaterial({ color: body, roughness: .28, metalness: .55 });
  const mA = new THREE.MeshStandardMaterial({ color: accent, roughness: .35, metalness: .3 });
  const mC = new THREE.MeshStandardMaterial({ color: 0x101115, roughness: .55, metalness: .3 });
  const B = (w, h, l, m, x, y, z) => { const me = new THREE.Mesh(new THREE.BoxGeometry(w, h, l), m); me.position.set(x, y, z); g.add(me); return me; };
  B(1.6, .06, 3.9, mC, 0, .1, -.1); B(.78, .5, 2.4, mB, 0, .42, .15); B(.34, .22, 1.5, mB, 0, .32, 2.05).rotation.x = .08;
  B(1.9, .05, .4, mA, 0, .12, 2.85); B(1.7, .04, .25, mA, 0, .2, 2.68);
  B(.5, .42, 1.7, mB, .62, .36, -.25); B(.5, .42, 1.7, mB, -.62, .36, -.25); B(.55, .5, 1.6, mB, 0, .62, -1.25);
  B(.28, .32, .5, mC, 0, .95, -.35); B(.98, .06, .32, mA, 0, 1.0, -2.3); B(.98, .05, .22, mA, 0, 1.1, -2.2);
  B(.04, .55, .6, mC, .5, .85, -2.3); B(.04, .55, .6, mC, -.5, .85, -2.3); B(.12, .3, .1, mC, 0, .75, -2.3);
  const wg = new THREE.CylinderGeometry(.36, .36, .38, 20); wg.rotateZ(Math.PI / 2);
  const mT = new THREE.MeshStandardMaterial({ color: 0x0b0b0d, roughness: .75 });
  const ringG = new THREE.TorusGeometry(.29, .025, 6, 24); ringG.rotateY(Math.PI / 2);
  const mRing = new THREE.MeshBasicMaterial({ color: 0x2a7bff });
  const wheels = [];
  for (const [x, z] of [[.82, 1.75], [-.82, 1.75], [.8, -1.65], [-.8, -1.65]]) {
    const w = new THREE.Group(); w.position.set(x, .36, z); w.add(new THREE.Mesh(wg, mT));
    const ring = new THREE.Mesh(ringG, mRing); ring.position.x = Math.sign(x) * .2; w.add(ring);
    const spoke = new THREE.Mesh(new THREE.BoxGeometry(.4, .5, .05), mC); w.add(spoke); g.add(w); wheels.push(w);
  }
  const halo = new THREE.Mesh(new THREE.TorusGeometry(.32, .035, 8, 20, Math.PI), mC); halo.rotation.x = Math.PI / 2; halo.position.set(0, .82, -.1); g.add(halo);
  B(.05, .2, .05, mC, 0, .74, .2);
  const hm = new THREE.Mesh(new THREE.SphereGeometry(.15, 16, 12), new THREE.MeshStandardMaterial({ color: helmet, roughness: .3 })); hm.position.set(0, .78, -.15); g.add(hm);
  const light = new THREE.MeshBasicMaterial({ color: 0xff0000, toneMapped: false });
  const lm = new THREE.Mesh(new THREE.BoxGeometry(.16, .09, .03), light); lm.position.set(0, .62, -2.42); g.add(lm);
  const sh = new THREE.Mesh(new THREE.PlaneGeometry(2.3, 5.8), new THREE.MeshBasicMaterial({ color: 0, transparent: true, opacity: .55, depthWrite: false }));
  sh.rotation.x = -Math.PI / 2; sh.position.y = .03; g.add(sh);
  g.userData = { wheels, light, lightPhase: Math.random() * 10 };
  return g;
}
function makeSC() {
  const g = new THREE.Group();
  const m = new THREE.MeshStandardMaterial({ color: 0xd8dade, roughness: .25, metalness: .7 });
  const d = new THREE.MeshStandardMaterial({ color: 0x0a0b0e, roughness: .2, metalness: .6 });
  const b1 = new THREE.Mesh(new THREE.BoxGeometry(1.95, .7, 4.6), m); b1.position.y = .6; g.add(b1);
  const b2 = new THREE.Mesh(new THREE.BoxGeometry(1.6, .5, 2.0), d); b2.position.set(0, 1.15, -.3); g.add(b2);
  const wg = new THREE.CylinderGeometry(.36, .36, .3, 18); wg.rotateZ(Math.PI / 2);
  const wheels = [];
  for (const [x, z] of [[.9, 1.45], [-.9, 1.45], [.9, -1.45], [-.9, -1.45]]) { const w = new THREE.Group(); w.position.set(x, .36, z); w.add(new THREE.Mesh(wg, d)); g.add(w); wheels.push(w); }
  const la = new THREE.MeshBasicMaterial({ color: 0xffa000, toneMapped: false }), lb = la.clone();
  const l1 = new THREE.Mesh(new THREE.BoxGeometry(.5, .1, .2), la); l1.position.set(-.3, 1.45, -.2); g.add(l1);
  const l2 = new THREE.Mesh(new THREE.BoxGeometry(.5, .1, .2), lb); l2.position.set(.3, 1.45, -.2); g.add(l2);
  const light = new THREE.MeshBasicMaterial({ color: 0xff0000, toneMapped: false });
  g.userData = { wheels, light, la, lb, sc: true };
  return g;
}
const carsG = new THREE.Group(); world.add(carsG);
// formation-lap cars (scene 3)
const sGrid = sNear(-.72 * scale, 0);
const FCARS = [
  ['VER', 0x16206a, 0xe8002d, 0, -2.6], ['HAM', 0xd10a0a, 0xf5f5f5, -9, 2.6], ['ANT', 0xbfc6cc, 0x00c8b4, -18, -2.6],
  ['RUS', 0xbfc6cc, 0x00c8b4, -27, 2.6], ['LEC', 0xd10a0a, 0xf5f5f5, -36, -2.6], ['NOR', 0xff7a00, 0x15151a, -45, 2.6],
  ['PIA', 0xff7a00, 0x15151a, -54, -2.6], ['ALO', 0x075e45, 0xc8f000, -63, 2.6]];
const finals = [112, 111, 101, 100, 90, 89, 79, 78];
const formation = FCARS.map(([code, b, a, s0, lat], i) => {
  const D = 2.0, tf = i === 0 ? 15.6 : i === 1 ? 16.0 : 11 + (finals[i] - s0 - 20) / 20;
  const dist = t => { if (t < tf) return s0 + 20 * (t - 11); const u = clamp((t - tf) / D); return s0 + 20 * (tf - 11) + 20 * D * (u - u * u * u + u * u * u * u / 2); };
  const speed = t => t < tf ? 20 : 20 * (1 - sst(clamp((t - tf) / D)));
  const latf = t => lat + .7 * Math.sin(t * 2.1 + i * 1.7) * speed(t) / 20 * (i > 1 ? 1 : .4);
  const obj = makeCar(b, a, i === 0 ? 0x1a3cff : 0xffd400); carsG.add(obj);
  return { code, obj, dist: t => sGrid + dist(t), speed, lat: latf };
});
// race restart cars (scene 7) on the back straight
const sBack = sNear(.95 * scale, -.35 * scale);
const sc = makeSC(); carsG.add(sc);
const RCARS = [['SC', 70, 0], ['VER', 52, 0], ['HAM', 40, .8], ['ANT', 28, -.6], ['RUS', 16, .5], ['LEC', 4, -.4], ['NOR', -8, .6], ['PIA', -20, -.5]];
const race = RCARS.map(([code, s0, lat], i) => {
  const obj = i === 0 ? sc : makeCar(FCARS.find(c => c[0] === code)[1], FCARS.find(c => c[0] === code)[2]); if (i) carsG.add(obj);
  return { code, obj, dist: t => sBack + s0 + 34 * (t - 45), speed: () => 34, lat: t => lat + .5 * Math.sin(t * 1.6 + i) };
});
const ALL = [...formation, ...race];
function pose(c, t) { const fr = frameAt(c.dist(t)); fr.p.addScaledVector(fr.r, c.lat(t)); return fr; }
function placeCar(c, t) {
  const fr = pose(c, t); const o = c.obj; o.visible = true; o.position.copy(fr.p); o.lookAt(fr.p.clone().add(fr.f));
  const ang = (c.dist(t) - c.dist(10)) / .36; o.userData.wheels.forEach(w => w.rotation.x = ang);
  const blink = (fract(t * 4 + o.userData.lightPhase) < .5) ? 1 : .08;
  o.userData.light.color.setRGB(6 * blink, .15 * blink, .1 * blink);
  if (o.userData.sc) { const k = fract(t * 3) < .5; o.userData.la.color.setRGB(k ? 6 : .2, k ? 3 : .1, 0); o.userData.lb.color.setRGB(k ? .2 : 6, k ? .1 : 3, 0); }
  return fr;
}

// spray: stateless particles emitted from each car's past positions
const SPR_N = 170, sprayG = new THREE.BufferGeometry();
const sprPos = new Float32Array(SPR_N * 8 * 3), sprCol = new Float32Array(SPR_N * 8 * 3);
sprayG.setAttribute('position', new THREE.BufferAttribute(sprPos, 3)); sprayG.setAttribute('color', new THREE.BufferAttribute(sprCol, 3));
const spray = new THREE.Points(sprayG, new THREE.PointsMaterial({ size: .55, map: SPRITE, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true }));
spray.frustumCulled = false; scene.add(spray);
const sprR = rng(99), SPRR = Array.from({ length: SPR_N * 8 * 4 }, sprR);
function updateSpray(cars, t, amount) {
  let n = 0;
  cars.slice(0, 8).forEach((c, ci) => {
    for (let k = 0; k < SPR_N; k++, n++) {
      const r = SPRR.slice((n) * 4, n * 4 + 4), life = .9 + r[3] * .5;
      const age = fract(k / SPR_N + t / life) * life, te = t - age;
      const fr = pose(c, te), v = c.speed(te) / 20;
      const side = (k & 1) ? 1 : -1;
      const p = fr.p.clone().addScaledVector(fr.r, side * .8).addScaledVector(fr.f, -1.9);
      p.addScaledVector(fr.f, -age * (3 + 5 * r[0]) * v).addScaledVector(fr.r, side * age * (1.5 + 3 * r[1]) * v);
      p.y = .3 + age * (2.5 + 3 * r[2]) - 2.2 * age * age;
      sprPos.set([p.x, Math.max(.1, p.y), p.z], n * 3);
      const a = (1 - age / life) * Math.min(1, age * 8) * v * amount * .5;
      sprCol.set([.42 * a, .46 * a, .54 * a], n * 3);
    }
  });
  for (; n < SPR_N * 8; n++) sprCol.set([0, 0, 0], n * 3);
  sprayG.attributes.position.needsUpdate = true; sprayG.attributes.color.needsUpdate = true;
}

// rain: world-anchored streaks wrapped around a box in front of the camera
const RN = 7000, rainG = new THREE.BufferGeometry(), rainPos = new Float32Array(RN * 6);
rainG.setAttribute('position', new THREE.BufferAttribute(rainPos, 3));
const rainMat = new THREE.LineBasicMaterial({ color: 0xaec4e0, transparent: true, opacity: .35, fog: false, depthWrite: false });
const rain = new THREE.LineSegments(rainG, rainMat); rain.frustumCulled = false; scene.add(rain);
const rr = rng(3), RB = Array.from({ length: RN * 3 }, rr);
function updateRain(t, inten, box = 60, len = 1.3) {
  const dir = new V3(); camera.getWorldDirection(dir);
  const c = camera.position.clone().addScaledVector(dir, box * .45);
  const n = Math.floor(RN * inten), wrap = (v, cc) => v - Math.floor((v - cc) / box + .5) * box;
  for (let i = 0; i < n; i++) {
    const x = wrap(RB[i * 3] * box * 7, c.x), z = wrap(RB[i * 3 + 2] * box * 7, c.z);
    const y = wrap(RB[i * 3 + 1] * box * 9 - t * 26, c.y);
    rainPos.set([x, y, z, x + .12 * len, y + len, z + .05 * len], i * 6);
  }
  rainG.setDrawRange(0, n * 2); rainG.attributes.position.needsUpdate = true; rain.visible = n > 0;
}

// ---------------------------------------------------------------- power unit (scene 4/5)
const pu = new THREE.Group(); scene.add(pu);
const puLabels = {};
{
  const metal = new THREE.MeshStandardMaterial({ color: 0x48505e, roughness: .32, metalness: .85 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x1b1f27, roughness: .45, metalness: .7 });
  const edgeMat = new THREE.LineBasicMaterial({ color: 0x3fd6ff, transparent: true, opacity: .28 });
  const add = (geo, m, x, y, z, rz = 0, rx = 0) => {
    const me = new THREE.Mesh(geo, m); me.position.set(x, y, z); me.rotation.z = rz; me.rotation.x = rx; pu.add(me);
    const e = new THREE.LineSegments(new THREE.EdgesGeometry(geo, 25), edgeMat); e.position.copy(me.position); e.rotation.copy(me.rotation); pu.add(e); return me;
  };
  add(new THREE.BoxGeometry(.9, .45, .75), metal, 0, 0, 0);
  for (const s of [-1, 1]) {
    add(new THREE.BoxGeometry(.3, .16, .8), metal, s * .32, .32, 0, -s * .55);
    for (let k = 0; k < 3; k++) add(new THREE.CylinderGeometry(.035, .035, .12, 10), dark, s * .4, .42, -.24 + k * .24, -s * .55);
  }
  add(new THREE.BoxGeometry(.6, .12, .7), dark, 0, -.28, 0);
  add(new THREE.BoxGeometry(.36, .3, .55), metal, 0, -.06, -.66);
  const ax = new THREE.CylinderGeometry(.035, .035, 1.7, 12); ax.rotateZ(Math.PI / 2); add(ax, dark, 0, -.1, -.75);
  for (const s of [-1, 1]) {
    const wg = new THREE.CylinderGeometry(.33, .33, .3, 32); wg.rotateZ(Math.PI / 2); add(wg, new THREE.MeshStandardMaterial({ color: 0x0c0c0f, roughness: .8 }), s * .98, -.1, -.75);
  }
  // turbo on a shaft along z, sitting in the V
  const tg = new THREE.CylinderGeometry(.11, .11, .1, 24); tg.rotateX(Math.PI / 2);
  add(tg, metal, 0, .45, .2); add(tg, metal, 0, .45, -.32);
  const sh = new THREE.CylinderGeometry(.02, .02, .55, 8); sh.rotateX(Math.PI / 2); add(sh, dark, 0, .45, -.06);
  const blades = new THREE.Group(); blades.position.set(0, .45, .26); pu.add(blades);
  const bm = new THREE.MeshStandardMaterial({ color: 0xb8c4d4, metalness: .9, roughness: .2 });
  for (let k = 0; k < 9; k++) { const b = new THREE.Mesh(new THREE.BoxGeometry(.015, .1, .03), bm); b.position.set(Math.sin(k / 9 * 6.283) * .05, Math.cos(k / 9 * 6.283) * .05, 0); b.rotation.z = -k / 9 * 6.283; b.rotation.y = .5; blades.add(b); }
  const blades2 = blades.clone(); blades2.position.z = -.38; pu.add(blades2);
  pu.userData.blades = [blades, blades2];
  const mguhMat = new THREE.MeshStandardMaterial({ color: 0xffa000, emissive: 0xff7a00, emissiveIntensity: 1.2, transparent: true, roughness: .4 });
  const mgh = new THREE.CylinderGeometry(.075, .075, .16, 20); mgh.rotateX(Math.PI / 2);
  const mguh = new THREE.Mesh(mgh, mguhMat); mguh.position.set(0, .45, -.06); pu.add(mguh); pu.userData.mguh = mguh;
  const kg = new THREE.CylinderGeometry(.13, .13, .28, 28); kg.rotateZ(Math.PI / 2);
  const mguKMat = new THREE.MeshStandardMaterial({ color: 0x2c3442, emissive: 0x00a8ff, emissiveIntensity: 0, roughness: .35, metalness: .7 });
  add(kg, mguKMat, .58, -.12, .28); pu.userData.mguKMat = mguKMat;
  const esMat = new THREE.MeshStandardMaterial({ color: 0x15202c, emissive: 0x0090ff, emissiveIntensity: .2, roughness: .4, metalness: .5 });
  add(new THREE.BoxGeometry(.75, .12, .42), esMat, 0, -.48, .08); pu.userData.esMat = esMat;
  for (let k = 0; k < 6; k++) add(new THREE.BoxGeometry(.1, .125, .38), dark, -.3 + k * .12, -.48, .08);
  const fl = new THREE.Mesh(new THREE.CircleGeometry(4, 64), new THREE.MeshStandardMaterial({ color: 0x0b0f16, roughness: .3, metalness: .6 }));
  fl.rotation.x = -Math.PI / 2; fl.position.y = -.82; pu.add(fl);
  const pg = new THREE.GridHelper(8, 40, 0x1d5068, 0x10283a); pg.position.y = -.81; pu.add(pg);
  Object.assign(puLabels, {
    ICE: new V3(-.32, .5, .32), TURBO: new V3(0, .58, -.32), MGUH: new V3(0, .55, -.06), MGUK: new V3(.62, .04, .3), ES: new V3(-.3, -.42, .3), WHEEL: new V3(.98, .25, -.75)
  });
}
const CR = a => new THREE.CatmullRomCurve3(a.map(v => new V3(...v)));
const FLOWS = [
  { k: 'batt', c: CR([[.2, -.42, .26], [.42, -.38, .34], [.56, -.27, .32], [.58, -.14, .28]]), n: 220 },
  { k: 'k', c: CR([[.48, -.12, .16], [.3, -.1, -.15], [.08, -.08, -.45], [0, -.07, -.62]]), n: 220 },
  { k: 'wl', c: CR([[0, -.1, -.75], [-.45, -.1, -.75], [-.86, -.1, -.75]]), n: 120 },
  { k: 'wr', c: CR([[0, -.1, -.75], [.45, -.1, -.75], [.86, -.1, -.75]]), n: 120 },
  { k: 'ice', c: CR([[0, .32, .3], [0, .12, .2], [0, -.12, .0], [0, -.08, -.55]]), n: 220 },
  { k: 'exh', c: CR([[.36, .4, .36], [.26, .52, .05], [.06, .5, -.28], [0, .45, -.38]]), n: 120 },
];
const FN = FLOWS.reduce((a, f) => a + f.n, 0);
const flowG = new THREE.BufferGeometry(), flPos = new Float32Array(FN * 3), flCol = new Float32Array(FN * 3);
flowG.setAttribute('position', new THREE.BufferAttribute(flPos, 3)); flowG.setAttribute('color', new THREE.BufferAttribute(flCol, 3));
const flowPts = new THREE.Points(flowG, new THREE.PointsMaterial({ size: .035, map: SPRITE, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }));
flowPts.frustumCulled = false; pu.add(flowPts);
const flR = rng(11), FLR = Array.from({ length: FN * 4 }, flR);
// physical story of the failure as functions of time
const st = {
  ice: t => 1 - .78 * eio(seg(t, 24.3, 26.3)),
  turbo: t => 1 - .82 * eio(seg(t, 24.3, 27)),
  battRaw: t => (.25 + .75 * eio(seg(t, 25.4, 27.2))) * (1 - .286 * eio(seg(t, 28.7, 30.2))),
  block: t => eio(seg(t, 32.9, 33.7)),
};
st.batt = t => st.battRaw(t) * (1 - st.block(t));
st.k = t => st.batt(t);
st.wheel = t => clamp(.5 * st.ice(t) * (1 - st.block(t) * .8) + .6 * st.k(t), 0, 1);
const flowInt = {
  batt: integral(t => .1 + .9 * st.batt(t), 18, 52), k: integral(t => .1 + .9 * st.k(t), 18, 52), wl: integral(t => .1 + .9 * st.wheel(t), 18, 52),
  wr: integral(t => .1 + .9 * st.wheel(t), 18, 52), ice: integral(t => .1 + .9 * st.ice(t), 18, 52), exh: integral(t => .1 + .9 * st.ice(t), 18, 52),
};
const turboAng = integral(t => 70 * st.turbo(t), 18, 52);
function updatePU(t) {
  pu.userData.blades.forEach(b => b.rotation.z = turboAng(t));
  const h = pu.userData.mguh, d = seg(t, 22.6, 23.5);
  h.visible = d < 1; h.material.opacity = 1 - d; h.scale.setScalar(1 + d * .8);
  h.material.emissiveIntensity = 1.2 + 2.5 * Math.max(0, Math.sin(t * 14)) * seg(t, 21.6, 22.0);
  const blk = st.block(t), pulse = .5 + .5 * Math.sin(t * 12);
  pu.userData.mguKMat.emissive.setRGB(lerp(0, 1, blk), lerp(.66, .05, blk), lerp(1, .05, blk));
  pu.userData.mguKMat.emissiveIntensity = st.k(t) * .45 + blk * (.25 + .35 * pulse);
  pu.userData.esMat.emissiveIntensity = .15 + st.batt(t) * .9;
  let n = 0;
  for (const f of FLOWS) {
    const amt = f.k === 'batt' || f.k === 'k' ? Math.max(st[f.k](t), blk * .55) : f.k === 'wl' || f.k === 'wr' ? st.wheel(t) : st[f.k] ? st[f.k](t) : st.ice(t);
    const ph = flowInt[f.k](t) * (f.k === 'exh' ? .6 : .45);
    for (let i = 0; i < f.n; i++, n++) {
      const r = FLR.slice(n * 4, n * 4 + 4); const u = fract(r[0] + ph);
      const p = f.c.getPointAt(u);
      const j = .012 * (1 + 1.5 * r[3]);
      p.x += Math.sin(t * 3 + r[1] * 30) * j; p.y += Math.cos(t * 2.6 + r[2] * 30) * j; p.z += Math.sin(t * 2.2 + r[3] * 30) * j;
      flPos.set([p.x, p.y, p.z], n * 3);
      const on = (i / f.n) < amt ? 1 : 0;
      let c;
      if (f.k === 'ice' || f.k === 'exh') c = [1.6, .75, .15];
      else if (f.k === 'wl' || f.k === 'wr') c = [lerp(.3, 1.6, st.ice(t) * .4), 1.2, 1.6];
      else c = [lerp(.25, 2.4, blk), lerp(1.3, .12, blk), lerp(2.2, .1, blk)];
      const b = on * (.6 + .4 * r[2]);
      flCol.set([c[0] * b, c[1] * b, c[2] * b], n * 3);
    }
  }
  flowG.attributes.position.needsUpdate = true; flowG.attributes.color.needsUpdate = true;
}
// MGU-H dissolve sparks
const SPK = 260, spkG = new THREE.BufferGeometry(), spkPos = new Float32Array(SPK * 3), spkCol = new Float32Array(SPK * 3);
spkG.setAttribute('position', new THREE.BufferAttribute(spkPos, 3)); spkG.setAttribute('color', new THREE.BufferAttribute(spkCol, 3));
const sparks = new THREE.Points(spkG, new THREE.PointsMaterial({ size: .02, map: SPRITE, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }));
sparks.frustumCulled = false; pu.add(sparks);
const spR = rng(5), SPRK = Array.from({ length: SPK * 4 }, spR);
function updateSparks(t) {
  const a = seg(t, 22.6, 24.2);
  for (let i = 0; i < SPK; i++) {
    const r = SPRK.slice(i * 4, i * 4 + 4); const th = r[0] * 6.283, ph = Math.acos(2 * r[1] - 1), sp = .25 + r[2] * .5;
    const d = eoe(a) * sp; spkPos.set([Math.sin(ph) * Math.cos(th) * d, .45 + Math.cos(ph) * d * .7 + a * .1, -.06 + Math.sin(ph) * Math.sin(th) * d], i * 3);
    const b = a > 0 && a < 1 ? (1 - a) * 2 : 0; spkCol.set([1.8 * b, .8 * b, .1 * b], i * 3);
  }
  spkG.attributes.position.needsUpdate = true; spkG.attributes.color.needsUpdate = true;
}

// ---------------------------------------------------------------- red flag cloth (scene 6)
const flagG = new THREE.Group(); scene.add(flagG);
const flagGeo = new THREE.PlaneGeometry(3, 2, 48, 32); flagGeo.translate(1.5, 0, 0);
const flagBase = flagGeo.attributes.position.array.slice();
const flag = new THREE.Mesh(flagGeo, new THREE.MeshStandardMaterial({ color: 0xd4061c, roughness: .5, metalness: .05, side: THREE.DoubleSide, emissive: 0x2a0004, envMapIntensity: .35 }));
flag.position.set(.05, 4.1, 0); flagG.add(flag);
const pole = new THREE.Mesh(new THREE.CylinderGeometry(.045, .05, 6, 16), new THREE.MeshStandardMaterial({ color: 0xc0c4cc, metalness: .9, roughness: .25 }));
pole.position.set(0, 2.2, 0); flagG.add(pole);
const marshal = new THREE.Mesh(new THREE.BoxGeometry(14, 1.1, .6), new THREE.MeshStandardMaterial({ color: 0x3a3f47, roughness: .6, envMapIntensity: .3 })); marshal.position.set(0, .3, 1.6); flagG.add(marshal);
const fence = new THREE.GridHelper(30, 60, 0x445566, 0x2a3440); fence.rotation.x = Math.PI / 2; fence.position.set(0, 3, -3); flagG.add(fence);
function updateFlag(t) {
  const a = flagGeo.attributes.position.array;
  for (let i = 0; i < a.length; i += 3) {
    const x = flagBase[i], y = flagBase[i + 1], k = Math.pow(x / 3, 1.1);
    a[i] = x - .12 * k * (1 + Math.sin(t * 3.1 + y));
    a[i + 1] = y - .1 * k * (1.2 + Math.sin(t * 2.3));
    a[i + 2] = k * (.32 * Math.sin(x * 2.1 - t * 7.5 + y * .5) + .09 * Math.sin(x * 5.3 - t * 12.5 + y * 2.2));
  }
  flagGeo.attributes.position.needsUpdate = true; flagGeo.computeVertexNormals();
}

// ---------------------------------------------------------------- lightning
const STRIKES = [.15, 3.35, 10.3, 18.7, 41.05];
function lightning(t) {
  let v = 0;
  for (const s of STRIKES) { const d = t - s; if (d >= 0 && d < .7) v += Math.exp(-d * 16) + (d > .13 ? .7 * Math.exp(-(d - .13) * 20) : 0); }
  return v;
}

// ---------------------------------------------------------------- 3D scene direction
function cam(p, l, fov, shake = 0, t = 0) {
  camera.position.set(...p);
  camera.position.x += shake * (Math.sin(t * 1.7) * .6 + Math.sin(t * 4.3) * .25);
  camera.position.y += shake * (Math.sin(t * 2.3 + 1) * .5 + Math.sin(t * 5.1) * .2);
  camera.up.set(0, 1, 0); camera.lookAt(...l); camera.fov = fov; camera.updateProjectionMatrix();
}
const STATE = { scrim: 0 };
function setFog(color, dens) { scene.fog.color.set(color); scene.fog.density = dens; scene.background.set(color); }

function direct(t) {
  world.visible = false; ground.visible = false; trackG.visible = true; carsG.visible = false; pu.visible = false; flagG.visible = false;
  grid.visible = false; rline.visible = false; spray.visible = false; rim.intensity = 0;
  ALL.forEach(c => c.obj.visible = false);
  scene.environment = null; edgeMat.color.setScalar(t < 12 ? 1 : .32);
  const lt = lightning(t);
  hemi.intensity = 1.0 + lt * 2.5; sun.intensity = 1.0 + lt * 2;
  hemi.color.set(0x9fb3c8); sun.color.set(0xc8d6ff);
  let rainI = 0, rainBox = 60, rainLen = 1.3;
  const cx = 0, cz = -.1 * scale;

  if (t < 12) { // ---- aerial / map
    world.visible = true; ground.visible = true; grid.visible = true; rline.visible = true;
    setFog(0x0a0e16, t < 6 ? .00011 : .00008);
    hemi.intensity = .55 + lt * 3; sun.intensity = .5 + lt * 2.5;
    const draw = eio(seg(t, .6, 6.2)); rline.geometry.setDrawRange(0, Math.floor(draw * NS) * 6);
    rlineMat.opacity = t < 9.4 ? 1 : 1 - seg(t, 9.4, 11.4) * .9;
    grid.material.opacity = .5 * (1 - seg(t, 9.6, 11.5));
    if (t < 6) {
      const k = eio(seg(t, 0, 6)), a = .35 + k * .8, r = lerp(2100, 1150, k), h = lerp(1650, 520, k);
      cam([cx + Math.sin(a) * r, h, cz + Math.cos(a) * r], [cx + lerp(-.2 * scale, -.5 * scale, k), 0, cz + lerp(.05 * scale, .15 * scale, k)], 40);
      rainI = .5; rainBox = 160; rainLen = 6;
    } else {
      const k = seg(t, 6, 9.6), d = eio(seg(t, 9.6, 12));
      // top-down map drifting, then a fluid dive towards the main straight
      const mcx = -.21 * scale - 1150 + k * 80, mcz = .02 * scale - 60, top = [mcx, 3900 - k * 250, mcz + 1], topL = [mcx, 0, mcz];
      const grd = frameAt(sGrid + 160).p;
      const low = [grd.x + 60, 40, grd.z + 70], lowL = [grd.x - 120, 0, grd.z];
      if (d <= 0) { camera.up.set(0, 0, -1); camera.position.set(...top); camera.lookAt(...topL); camera.fov = 38; camera.updateProjectionMatrix(); }
      else {
        const e = d; const p = top.map((v, i) => lerp(v, low[i], e)); p[1] = lerp(top[1], low[1], eio(e) * .5 + e * .5);
        const lk = topL.map((v, i) => lerp(v, lowL[i], e));
        camera.up.set(0, 1, 0).lerp(new V3(0, 0, -1), 1 - eoe(e * 1.3)).normalize();
        camera.position.set(...p); camera.lookAt(...lk); camera.fov = lerp(38, 46, e); camera.updateProjectionMatrix();
        setFog(new THREE.Color(0x0a0e16).lerp(new THREE.Color(0x1b2331), e), lerp(.00008, .006, eie(e)));
      }
      rainI = lerp(.35, 1, seg(t, 9, 11.5)); rainBox = lerp(220, 70, d); rainLen = lerp(8, 1.6, d);
    }
  } else if (t < 20) { // ---- formation lap
    world.visible = true; ground.visible = true; carsG.visible = true; spray.visible = true;
    setFog(0x1d2633, .011); scene.environment = ENV;
    hemi.intensity = 1.6 + lt * 3; hemi.color.set(0xa8bccf); sun.intensity = 1.6 + lt * 2;
    formation.forEach(c => placeCar(c, t));
    updateSpray(formation, t, 1);
    const v = pose(formation[0], t), h = pose(formation[1], t);
    if (t < 14.6) {
      const k = seg(t, 12, 14.6);
      const p = v.p.clone().addScaledVector(v.r, 9.5 - k * 2).addScaledVector(v.f, 5 - k * 9).add(new V3(0, 1.1 + k * .5, 0));
      const l = v.p.clone().addScaledVector(v.f, .5).add(new V3(0, .5, 0));
      cam(p.toArray(), l.toArray(), lerp(30, 34, k), .05, t);
    } else if (t < 17.3) {
      const k = seg(t, 14.6, 17.3); const end = frameAt(formation[0].dist(20) + 26 - k * 6);
      const p = end.p.clone().addScaledVector(end.r, 1.2).add(new V3(0, .9 + k * .5, 0));
      const mid = v.p.clone().lerp(h.p, .5).add(new V3(0, .7, 0));
      cam(p.toArray(), mid.toArray(), lerp(26, 34, eio(k)), .04, t);
    } else {
      const k = eio(seg(t, 17.3, 20)); const a = lerp(-.4, 1.25, k), r = lerp(9, 6.2, k);
      const c0 = v.p.clone().add(new V3(0, .5, 0));
      const off = v.f.clone().multiplyScalar(Math.cos(a) * r).addScaledVector(v.r, -Math.sin(a) * r);
      cam([c0.x + off.x, c0.y + lerp(1.6, 3.4, k), c0.z + off.z], [c0.x, c0.y, c0.z], 36, .03, t);
    }
    rainI = 1; rainBox = 50; rainLen = 1.3;
  } else if (t < 41) { // ---- power unit lab + root cause
    pu.visible = true; setFog(0x05070c, .05);
    hemi.intensity = .55; hemi.color.set(0x8fa6c4); sun.intensity = 1.6;
    rim.intensity = 30; rim.position.set(-2, 3, -2.5); rim.target.position.set(0, 0, 0); rim.color.set(0x4fc3ff);
    updatePU(t); updateSparks(t);
    if (t < 36) {
      const K = [
        [20, [2.7, 1.35, 2.5, 0, .05, 0, 34]], [22.5, [1.55, .95, 1.95, 0, .3, -.05, 34]], [24.2, [1.1, 1.25, 2.4, 0, .3, -.1, 34]],
        [26.2, [-1.7, 1.2, 2.3, -.1, .2, -.15, 36]], [28.2, [-.4, .1, 2.15, .2, -.28, .1, 36]], [30.2, [1.75, -.12, 1.3, .35, -.25, .15, 36]],
        [32.2, [2.0, .3, 1.25, .3, -.15, .1, 34]], [34.2, [1.75, .25, 1.0, .3, -.15, .12, 33]], [36, [1.65, .25, .92, .3, -.14, .12, 32]]];
      const v = keys(t, K); cam(v.slice(0, 3), v.slice(3, 6), v[6], .008, t);
    } else {
      const k = eio(seg(t, 36, 41)); const a = lerp(.9, 1.9, k);
      cam([Math.sin(a) * lerp(2.6, 4.2, k), lerp(.6, 1.9, k), Math.cos(a) * lerp(2.6, 4.2, k)], [0, 0, -.1], 36, .01, t);
    }
  } else if (t < 45) { // ---- red flag
    flagG.visible = true; setFog(0x0b0607, .03); scene.environment = ENV;
    hemi.intensity = .35 + lt * 2; hemi.color.set(0xb0a0a8); sun.intensity = .7 + lt * 1.5; sun.position.set(-4, 10, 8);
    rim.intensity = 1.6; rim.color.set(0xffb0a0); rim.position.set(-3, 8, 6); rim.target.position.set(1.5, 4, 0);
    updateFlag(t);
    const k = eio(seg(t, 41, 45)); const a = lerp(-.75, -.2, k), r = lerp(9.5, 6.2, k);
    cam([Math.sin(a) * r + 1.5, lerp(1.4, 3.4, k), Math.cos(a) * r], [lerp(3.4, 3.0, k), lerp(3.3, 3.9, k), 0], 38, .03, t);
    rainI = .9; rainBox = 30; rainLen = 1.1;
  } else { // ---- restart behind the safety car
    world.visible = true; ground.visible = true; carsG.visible = true; spray.visible = true;
    setFog(0x232c38, .0065); scene.environment = ENV; hemi.intensity = 1.5; hemi.color.set(0xb4c4d6);
    race.forEach(c => placeCar(c, t)); updateSpray(race, t, 1.25);
    const k = eio(seg(t, 45, 50)); const lead = pose(race[1], t);
    const camS = race[7].dist(45) - 20 + lerp(0, 150, seg(t, 45, 50));
    const fr = frameAt(camS); const p = fr.p.clone().addScaledVector(fr.r, lerp(-9, -34, k)).add(new V3(0, lerp(1.2, 30, k), 0));
    cam(p.toArray(), lead.p.clone().add(new V3(0, 1, 0)).toArray(), lerp(34, 44, k), .05, t);
    rainI = .55; rainBox = 60; rainLen = 1.4;
  }
  rainMat.opacity = .32 + lt * .3;
  updateRain(t, rainI, rainBox, rainLen);
}

// ---------------------------------------------------------------- 2D overlay: kinetic type & morphing shapes
const out = document.getElementById('out'), ctx = out.getContext('2d');
let T = 0;
const RED = '#ff1e2d', CYAN = '#3fd6ff', AMBER = '#ffb020', WHITE = '#f4f6fa', DIM = 'rgba(220,230,245,.6)';
const F = (s, w = 900, fam = 'Inter Display') => `${w} ${s}px "${fam}"`;

function rise(s, x, y, o) {
  const size = o.size ?? 80, a = o.a, b = o.b ?? 1e9, stg = o.stagger ?? .022, d = o.dur ?? .65, track = o.track ?? 0;
  ctx.save(); ctx.font = F(size, o.weight ?? 900, o.fam); ctx.textBaseline = 'alphabetic';
  const chars = [...s], cw = chars.map(c => ctx.measureText(c).width + track * size), tot = cw.reduce((p, c) => p + c, 0) - track * size;
  let x0 = o.align === 'center' ? x - tot / 2 : o.align === 'right' ? x - tot : x;
  ctx.beginPath(); ctx.rect(x0 - size, y - size * 1.02, tot + size * 2, size * 1.32); ctx.clip();
  ctx.fillStyle = o.color ?? WHITE; if (o.glow) { ctx.shadowColor = o.glow; ctx.shadowBlur = o.glowR ?? 30; }
  chars.forEach((c, i) => {
    const p = eoe(clamp((T - a - i * stg) / d)), q = eie(clamp((T - b - i * stg * .5) / (d * .7)));
    ctx.globalAlpha = (o.alpha ?? 1) * Math.min(1, p * 1.4) * (1 - q);
    if (ctx.globalAlpha > .004) ctx.fillText(c, x0, y + (1 - p) * size * 1.15 - q * size * 1.15);
    x0 += cw[i];
  });
  ctx.restore(); return tot;
}
function slam(s, x, y, o) {
  const size = o.size ?? 200, a = o.a, b = o.b ?? 1e9, p = clamp((T - a) / (o.dur ?? .5)), e = eoe(p), q = eio(clamp((T - b) / .35));
  if (p <= 0 || q >= 1) return;
  ctx.save(); ctx.font = F(size, o.weight ?? 900, o.fam); ctx.textAlign = o.align ?? 'center'; ctx.textBaseline = 'middle';
  ctx.letterSpacing = `${lerp(o.track0 ?? .3, o.track ?? 0, e) * size}px`;
  const sc = lerp(o.from ?? 1.9, 1, e) * (1 + q * .25);
  for (let g = 3; g >= 0; g--) {
    ctx.save(); ctx.translate(x, y); const s2 = sc * (1 + g * .07 * (1 - e)); ctx.scale(s2, s2);
    ctx.globalAlpha = (g ? .22 * (1 - e) : 1) * e * (1 - q); ctx.fillStyle = o.color ?? WHITE;
    if (!g && o.glow) { ctx.shadowColor = o.glow; ctx.shadowBlur = 40; }
    ctx.fillText(s, 0, 0); ctx.restore();
  }
  ctx.restore();
}
function typeOn(s, x, y, o) {
  const a = o.a, b = o.b ?? 1e9, d = o.dur ?? s.length * .028;
  const n = Math.floor(s.length * clamp((T - a) / d)); const q = clamp((T - b) / .25);
  if (T < a || q >= 1) return;
  ctx.save(); ctx.font = F(o.size ?? 24, o.weight ?? 600, o.fam ?? 'Inter'); ctx.letterSpacing = `${(o.track ?? .12) * (o.size ?? 24)}px`;
  ctx.fillStyle = o.color ?? DIM; ctx.globalAlpha = 1 - q; ctx.textAlign = o.align ?? 'left';
  const str = s.slice(0, n) + ((n < s.length || fract(T * 2) < .5) && T - a < d + .6 ? '▍' : '');
  ctx.fillText(str, x, y); ctx.restore();
}
function fadeTxt(s, x, y, o) {
  const a = o.a, b = o.b ?? 1e9, p = eoe(clamp((T - a) / .6)), q = clamp((T - b) / .3);
  if (p <= 0 || q >= 1) return;
  ctx.save(); ctx.font = F(o.size ?? 30, o.weight ?? 500, o.fam ?? 'Inter'); ctx.letterSpacing = `${(o.track ?? 0) * (o.size ?? 30)}px`;
  ctx.fillStyle = o.color ?? WHITE; ctx.globalAlpha = p * (1 - q); ctx.textAlign = o.align ?? 'left';
  ctx.fillText(s, x + (1 - p) * (o.dx ?? 0), y + (1 - p) * (o.dy ?? 14)); ctx.restore();
}
function rule(x, y, w, a, b = 1e9, col = RED, h = 3) {
  const p = eoe(clamp((T - a) / .7)), q = eie(clamp((T - b) / .4)); if (p <= 0 || q >= 1) return;
  ctx.fillStyle = col; ctx.fillRect(x + w * q, y, w * (p - q), h);
}
function counter(v0, v1, x, y, a, d, o) {
  const k = eio(clamp((T - a) / d)), v = lerp(v0, v1, k);
  ctx.save(); ctx.font = F(o.size ?? 60, o.weight ?? 800, o.fam); ctx.fillStyle = o.color ?? WHITE; ctx.textAlign = o.align ?? 'left';
  ctx.globalAlpha = o.alpha ?? 1; ctx.fillText((o.fmt ?? (n => n.toFixed(0)))(v), x, y); ctx.restore();
}

// --- morphing shapes
const MN = 220;
function resample(poly, N = MN) {
  const pts = poly.map(p => [p[0], p[1]]); pts.push(pts[0]);
  const d = [0]; for (let i = 1; i < pts.length; i++) d.push(d[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  const tot = d[d.length - 1], o = []; let j = 0;
  for (let i = 0; i < N; i++) { const s = i / N * tot; while (d[j + 1] < s) j++; const k = (s - d[j]) / (d[j + 1] - d[j] || 1); o.push([lerp(pts[j][0], pts[j + 1][0], k), lerp(pts[j][1], pts[j + 1][1], k)]); }
  let area = 0; for (let i = 0; i < N; i++) { const p = o[i], q = o[(i + 1) % N]; area += p[0] * q[1] - q[0] * p[1]; }
  return area < 0 ? o.reverse() : o;
}
const circ = n => Array.from({ length: n }, (_, i) => [Math.cos(i / n * 6.283 - 1.5708), Math.sin(i / n * 6.283 - 1.5708)]);
const SH = {
  circle: resample(circ(64)),
  island: resample([[0, -1], [.22, -.86], [.3, -.5], [.36, -.18], [.28, .2], [.2, .55], [.06, 1], [-.08, .72], [-.2, .32], [-.3, -.1], [-.26, -.5], [-.15, -.86]]),
  track: (() => { const pts = []; for (let i = 0; i < NS; i += 6) pts.push([P[i].x, P[i].z]); let mx = 0; const cxx = pts.reduce((a, p) => a + p[0], 0) / pts.length, czz = pts.reduce((a, p) => a + p[1], 0) / pts.length; pts.forEach(p => { p[0] -= cxx; p[1] -= czz; mx = Math.max(mx, Math.abs(p[0]), Math.abs(p[1])); }); return resample(pts.map(p => [p[0] / mx, p[1] / mx])); })(),
  rect: resample([[-1, -1], [1, -1], [1, 1], [-1, 1]]),
  oct: resample(Array.from({ length: 8 }, (_, i) => [Math.cos(i / 8 * 6.283 + .3927), Math.sin(i / 8 * 6.283 + .3927)])),
  flag: resample([[-1, -.66], [1, -.66], [1, .66], [-1, .66]]),
};
const alignCache = {};
function morphPts(A, B, k, keyName) {
  let off = alignCache[keyName];
  if (off === undefined) { let best = 1e18; for (let o = 0; o < MN; o += 2) { let s = 0; for (let i = 0; i < MN; i += 4) { const a = SH[A][i], b = SH[B][(i + o) % MN]; s += (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2; } if (s < best) { best = s; off = o; } } alignCache[keyName] = off; }
  return SH[A].map((a, i) => { const b = SH[B][(i + off) % MN]; return [lerp(a[0], b[0], k), lerp(a[1], b[1], k)]; });
}
function drawPoly(pts, cx, cy, sx, sy, o) {
  ctx.save(); ctx.beginPath();
  pts.forEach((p, i) => { const x = cx + p[0] * sx, y = cy + p[1] * sy; i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.closePath();
  if (o.fill) { ctx.globalAlpha = o.fillA ?? .15; ctx.fillStyle = o.fill; ctx.fill(); }
  ctx.globalAlpha = o.alpha ?? 1; ctx.strokeStyle = o.stroke ?? CYAN; ctx.lineWidth = o.lw ?? 3; ctx.lineJoin = 'round';
  if (o.glow) { ctx.shadowColor = o.glow; ctx.shadowBlur = 24; }
  ctx.stroke(); ctx.restore();
}
function proj(v) { const p = v.clone().project(camera); return { x: (p.x + 1) / 2 * W, y: (1 - p.y) / 2 * H, ok: p.z < 1 }; }
function tag(v, label, sub, a, b, col = WHITE, dx = 70, dy = -90) {
  const p = proj(v); if (!p.ok) return; const k = eoe(clamp((T - a) / .5)), q = clamp((T - b) / .3); if (k <= 0 || q >= 1) return;
  ctx.save(); ctx.globalAlpha = k * (1 - q); ctx.strokeStyle = col; ctx.lineWidth = 2;
  const ex = p.x + dx * k, ey = p.y + dy * k;
  ctx.beginPath(); ctx.arc(p.x, p.y, 5, 0, 6.283); ctx.fillStyle = col; ctx.fill();
  ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(ex, ey); ctx.lineTo(ex + Math.sign(dx || 1) * 26, ey); ctx.stroke();
  ctx.font = F(30, 800); ctx.textAlign = dx < 0 ? 'right' : 'left'; ctx.fillText(label, ex + Math.sign(dx || 1) * 34, ey + 10);
  if (sub) { ctx.font = F(16, 600, 'Inter'); ctx.letterSpacing = '2px'; ctx.globalAlpha *= .75; ctx.fillText(sub, ex + Math.sign(dx || 1) * 34, ey + 34); }
  ctx.restore();
}
function panel(x, y, w, h, a, b, col = 'rgba(8,12,20,.62)') {
  const k = eoe(clamp((T - a) / .5)), q = clamp((T - b) / .3); if (k <= 0 || q >= 1) return 0;
  ctx.save(); ctx.globalAlpha = (1 - q); ctx.fillStyle = col; ctx.fillRect(x, y, w * k, h);
  ctx.fillStyle = CYAN; ctx.fillRect(x, y, 3, h * k); ctx.restore(); return k * (1 - q);
}
function bar(x, y, w, h, v, col, label, val, alpha = 1) {
  ctx.save(); ctx.globalAlpha = alpha; ctx.fillStyle = 'rgba(255,255,255,.08)'; ctx.fillRect(x, y, w, h);
  ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = 16; ctx.fillRect(x, y, w * clamp(v), h); ctx.shadowBlur = 0;
  ctx.font = F(15, 700, 'Inter'); ctx.letterSpacing = '2.5px'; ctx.fillStyle = DIM; ctx.fillText(label, x, y - 10);
  if (val) { ctx.textAlign = 'right'; ctx.fillStyle = WHITE; ctx.fillText(val, x + w, y - 10); }
  ctx.restore();
}
function gauge(cx, cy, r, v, col, label, val, alpha) {
  ctx.save(); ctx.globalAlpha = alpha; ctx.lineCap = 'round';
  const a0 = Math.PI * .75, a1 = Math.PI * 2.25;
  ctx.strokeStyle = 'rgba(255,255,255,.1)'; ctx.lineWidth = 10; ctx.beginPath(); ctx.arc(cx, cy, r, a0, a1); ctx.stroke();
  ctx.strokeStyle = col; ctx.shadowColor = col; ctx.shadowBlur = 18; ctx.beginPath(); ctx.arc(cx, cy, r, a0, lerp(a0, a1, clamp(v))); ctx.stroke();
  ctx.shadowBlur = 0; ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(255,255,255,.35)';
  for (let i = 0; i <= 10; i++) { const a = lerp(a0, a1, i / 10); ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * (r - 22), cy + Math.sin(a) * (r - 22)); ctx.lineTo(cx + Math.cos(a) * (r - 14), cy + Math.sin(a) * (r - 14)); ctx.stroke(); }
  const na = lerp(a0, a1, clamp(v)); ctx.strokeStyle = WHITE; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(na) * (r - 28), cy + Math.sin(na) * (r - 28)); ctx.stroke();
  ctx.font = F(16, 700, 'Inter'); ctx.letterSpacing = '3px'; ctx.textAlign = 'center'; ctx.fillStyle = DIM; ctx.fillText(label, cx, cy + r * .62);
  ctx.font = F(34, 800); ctx.letterSpacing = '0px'; ctx.fillStyle = WHITE; ctx.fillText(val, cx, cy + r * .38);
  ctx.restore();
}

// film finishing layers
const vig = (() => { const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d'); const gr = g.createRadialGradient(W / 2, H / 2, H * .35, W / 2, H / 2, H * 1.05); gr.addColorStop(0, 'rgba(0,0,0,0)'); gr.addColorStop(1, 'rgba(0,0,0,.75)'); g.fillStyle = gr; g.fillRect(0, 0, W, H); return c; })();
const grains = [0, 1, 2, 3].map(s => { const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'); const id = g.createImageData(256, 256); const r = rng(s + 20); for (let i = 0; i < id.data.length; i += 4) { const v = r() * 255; id.data[i] = id.data[i + 1] = id.data[i + 2] = v; id.data[i + 3] = 255; } g.putImageData(id, 0, 0); return ctx.createPattern(c, 'repeat'); });
const CUTS = [6, 12, 20, 36, 41, 45];
const CHAPTERS = [[0, '01', 'THE RACE'], [6, '02', 'NEW VENUE'], [12, '03', 'FORMATION LAP'], [20, '04', 'POWER UNIT'], [36, '05', 'ROOT CAUSE'], [41, '06', 'RED FLAG'], [45, '07', 'RESTART']];

function overlay(t) {
  const bar_h = 62 * eoe(seg(t, 0, 1.2));
  ctx.drawImage(vig, 0, 0);
  if (t >= 20 && t < 36.2) { const g = ctx.createLinearGradient(0, 0, 1000, 0); g.addColorStop(0, 'rgba(3,5,10,.82)'); g.addColorStop(.6, 'rgba(3,5,10,.45)'); g.addColorStop(1, 'rgba(3,5,10,0)'); ctx.save(); ctx.globalAlpha = eoe(seg(t, 20, 20.6)) * (1 - seg(t, 35.9, 36.2)); ctx.fillStyle = g; ctx.fillRect(0, 0, 1000, H); ctx.restore(); }
  // ---------------- scene 1: title
  if (t < 6.2) {
    typeOn('04 OCT 2026  ·  SEPANG INTERNATIONAL CIRCUIT  ·  5.543 KM', 140, 360, { a: .5, b: 5.6, size: 20, color: CYAN });
    rise('BAHRAIN GP', 132, 510, { a: .8, b: 5.55, size: 168, track: -.02 });
    rise('IN MALAYSIA', 140, 600, { a: 1.25, b: 5.6, size: 72, weight: 300, color: DIM, track: .06 });
    rule(140, 640, 520, 1.6, 5.5);
    rise('WHY WAS IT', 140, 730, { a: 3.0, b: 5.65, size: 54, weight: 800 });
    rise('RED-FLAGGED?', 140, 800, { a: 3.25, b: 5.7, size: 66, weight: 900, color: RED, glow: 'rgba(255,30,45,.6)' });
  }
  // ---------------- scene 2: relocation morph + monsoon
  if (t >= 6 && t < 12.2) {
    const k = eio(seg(t, 6.8, 8.6)), app = eoe(seg(t, 6, 6.8)), out = eie(seg(t, 9.2, 9.8));
    const cx = 470, cy = 560, R = 250 * app * (1 - out * .4);
    if (out < 1) {
      ctx.save(); ctx.globalAlpha = 1 - out;
      const A = k < .5 ? 'circle' : 'island', B = k < .5 ? 'island' : 'track', kk = k < .5 ? k * 2 : (k - .5) * 2;
      const sh = morphPts(A, B, eio(kk), A + B);
      const sx = R * (A === 'circle' && kk < 1 ? lerp(.25, .9, eio(kk)) : 1), sy = R * (A === 'circle' ? lerp(.25, .9, eio(kk)) : 1) * (B === 'track' ? lerp(.9, .62, eio(kk)) : .9);
      drawPoly(sh, cx, cy, A === 'circle' ? sx : R, sy, { stroke: k > .5 ? CYAN : AMBER, lw: 4, glow: k > .5 ? CYAN : AMBER, fill: k > .5 ? CYAN : AMBER, fillA: .08 });
      ctx.restore();
      const lat = lerp(26.03, 2.76, k), lon = lerp(50.51, 101.74, k);
      ctx.save(); ctx.globalAlpha = (1 - out) * app; ctx.font = F(20, 600, 'Inter'); ctx.letterSpacing = '3px'; ctx.fillStyle = DIM; ctx.textAlign = 'center';
      ctx.fillText(`${lat.toFixed(2)}°N   ${lon.toFixed(2)}°E`, cx, cy + 300);
      ctx.font = F(44, 900); ctx.letterSpacing = '6px'; ctx.fillStyle = k > .5 ? CYAN : AMBER; ctx.fillText(k > .5 ? 'SEPANG' : 'SAKHIR', cx, cy - 290);
      ctx.restore();
    }
    rise('RELOCATED', 820, 262, { a: 6.3, b: 9.1, size: 116, track: .02 });
    fadeTxt('The 2026 Bahrain Grand Prix moved from Sakhir', 826, 318, { a: 6.9, b: 9.1, size: 28, color: DIM });
    fadeTxt('to Sepang, Malaysia — raced on 4 October.', 826, 356, { a: 7.1, b: 9.1, size: 28, color: DIM });
    rise('THEN THE', 140, 470, { a: 9.7, b: 11.65, size: 70, weight: 300, color: DIM });
    rise('MONSOON HIT', 140, 590, { a: 9.95, b: 11.7, size: 140 });
    typeOn('HEAVY RAIN DELAYS THE START  ·  FULL WET TYRES', 146, 660, { a: 10.5, b: 11.7, size: 20, color: CYAN });
  }
  // ---------------- scene 3: formation lap
  if (t >= 12 && t < 20.2) {
    rise('FORMATION LAP', 120, 230, { a: 12.2, b: 14.4, size: 100 });
    typeOn('LAP 0  ·  NO RACING YET  ·  CARS WARM TYRES & BRAKES', 126, 280, { a: 12.6, b: 14.4, size: 20, color: CYAN });
    const v = pose(formation[0], t), h = pose(formation[1], t);
    const vl = proj(v.p).x < proj(h.p).x ? -1 : 1;
    tag(v.p.clone().add(new V3(0, 1.3, 0)), 'VER', 'P1 · POLE', 14.9, 17.25, WHITE, vl * 130, -120);
    tag(h.p.clone().add(new V3(0, 1.3, 0)), 'HAM', 'P2', 15.1, 17.25, WHITE, -vl * 130, -120);
    rise('FRONT ROW', 1180, 230, { a: 15.8, b: 17.2, size: 64, weight: 300, color: DIM, align: 'left' });
    rise('LOSES DRIVE', 1180, 310, { a: 16.0, b: 17.25, size: 84, color: RED });
    // telemetry
    const pk = panel(110, 640, 640, 330, 17.35, 19.9);
    if (pk > 0) {
      ctx.save(); ctx.globalAlpha = pk;
      ctx.font = F(16, 700, 'Inter'); ctx.letterSpacing = '3px'; ctx.fillStyle = CYAN; ctx.fillText('TELEMETRY  ·  CAR 1', 140, 676);
      const thr = tt => tt < 15.2 ? .35 + .06 * Math.sin(tt * 5) : tt < 15.6 ? lerp(.38, 1, seg(tt, 15.2, 15.6)) : 1 - .55 * Math.pow(Math.max(0, Math.sin((tt - 16.6) * 4.5)), 6) * (tt > 16.6);
      const drv = tt => tt < 15.55 ? thr(tt) * .9 : thr(tt) * .9 * (1 - eio(seg(tt, 15.55, 15.85)));
      const spd = tt => formation[0].speed(tt) / 20 * .75;
      const gx = 140, gy = 700, gw = 400, gh = 220, t0 = T - 5;
      ctx.strokeStyle = 'rgba(255,255,255,.08)'; ctx.lineWidth = 1;
      for (let i = 0; i <= 4; i++) { ctx.beginPath(); ctx.moveTo(gx, gy + gh * i / 4); ctx.lineTo(gx + gw, gy + gh * i / 4); ctx.stroke(); }
      const plot = (f, col, w) => { ctx.strokeStyle = col; ctx.lineWidth = w; ctx.shadowColor = col; ctx.shadowBlur = 10; ctx.beginPath(); for (let i = 0; i <= 120; i++) { const tt = t0 + 5 * i / 120; const x = gx + gw * i / 120, y = gy + gh * (1 - f(tt)); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); } ctx.stroke(); ctx.shadowBlur = 0; };
      plot(spd, 'rgba(200,210,225,.6)', 2); plot(thr, WHITE, 3); plot(drv, RED, 3);
      ctx.font = F(14, 700, 'Inter'); ctx.letterSpacing = '2px';
      [['THROTTLE', WHITE, 0], ['WHEEL TORQUE', RED, 125], ['SPEED', 'rgba(200,210,225,.8)', 290]].forEach(([l, c, dx]) => { ctx.fillStyle = c; ctx.fillText(l, gx + dx, gy + gh + 30); });
      ctx.textAlign = 'right'; ctx.font = F(15, 700, 'Inter'); ctx.fillStyle = DIM; ctx.fillText('THROTTLE', 720, 724); ctx.fillText('TORQUE', 720, 814); ctx.fillText('SPEED', 720, 904);
      ctx.font = F(50, 900); ctx.letterSpacing = '0px';
      ctx.fillStyle = WHITE; ctx.fillText(`${Math.round(thr(T) * 100)}%`, 720, 774);
      ctx.fillStyle = RED; ctx.fillText(`${Math.round(drv(T) * 100)}%`, 720, 864);
      ctx.fillStyle = WHITE; ctx.fillText(`${Math.round(formation[0].speed(T) * 3.6)}`, 720, 954);
      ctx.restore();
    }
    rise('FOOT DOWN.', 1180, 700, { a: 17.6, b: 19.75, size: 92 });
    rise('NOTHING.', 1180, 810, { a: 18.15, b: 19.8, size: 92, color: RED, glow: 'rgba(255,30,45,.5)' });
    fadeTxt('Several cars lost drive on the formation laps', 1186, 870, { a: 18.5, b: 19.8, size: 26, color: DIM });
  }
  // ---------------- scene 4: power unit
  if (t >= 20 && t < 36.2) {
    const L1 = 20.2, L2 = 24.2, L3 = 28.2, L4 = 32.2, E1 = 23.9, E2 = 27.9, E3 = 31.9, E4 = 35.85;
    // labels on the 3D model
    tag(puLabels.ICE, 'V6 ICE', '1.6 L TURBO', 20.7, 23.9, WHITE, -60, 150);
    tag(puLabels.MGUK, 'MGU-K', 'MOTOR / GENERATOR', 21.0, 23.9, CYAN, 90, 60);
    tag(puLabels.ES, 'ENERGY STORE', 'BATTERY', 21.2, 23.9, CYAN, -90, 70);
    tag(puLabels.MGUH, 'MGU-H', T > 22.6 ? 'REMOVED FOR 2026' : 'TURBO GENERATOR', 21.6, 23.9, AMBER, 90, -110);
    tag(puLabels.TURBO, 'TURBO', null, 24.4, 27.85, AMBER, -90, -60);
    tag(puLabels.MGUK, 'MGU-K', null, 28.4, 35.8, T > 33 ? RED : CYAN, 90, -60);
    // step text
    const tx = 120;
    typeOn('TECH FILE  ·  2026 HYBRID POWER UNIT', tx + 4, 210, { a: L1, b: E1, size: 18, color: CYAN });
    rise('NO MGU-H', tx, 320, { a: L1 + .2, b: E1, size: 110 });
    fadeTxt('The 2026 rules removed the motor that', tx + 4, 380, { a: L1 + .8, b: E1, size: 28, color: DIM });
    fadeTxt('kept the turbo spinning at low speed.', tx + 4, 418, { a: L1 + 1.0, b: E1, size: 28, color: DIM });
    if (T > 22.6 && T < E1 + .3) { ctx.save(); ctx.globalAlpha = 1 - seg(T, E1, E1 + .3); ctx.fillStyle = AMBER; ctx.fillRect(tx, 278, 520 * eoe(seg(T, 22.6, 23.1)), 8); ctx.restore(); }

    typeOn('STEP 01', tx + 4, 210, { a: L2, b: E2, size: 18, color: AMBER });
    rise('SLOW CAR,', tx, 300, { a: L2 + .1, b: E2, size: 84 });
    rise('LAZY TURBO', tx, 395, { a: L2 + .3, b: E2, size: 84, color: AMBER });
    fadeTxt('Formation-lap speed → little exhaust energy', tx + 4, 455, { a: L2 + .9, b: E2, size: 27, color: DIM });
    fadeTxt('→ turbo spools down → engine torque falls', tx + 4, 492, { a: L2 + 1.3, b: E2, size: 27, color: DIM });
    fadeTxt('→ torque demand handed to the battery', tx + 4, 529, { a: L2 + 1.9, b: E2, size: 27, color: CYAN });
    if (T > L2 && T < E2 + .3) {
      const al = eoe(seg(T, L2 + .4, L2 + 1)) * (1 - seg(T, E2, E2 + .3));
      gauge(1560, 330, 120, st.turbo(T) * .92, AMBER, 'TURBO SPEED', `${Math.round(st.turbo(T) * 100)}%`, al);
      bar(1440, 560, 360, 14, st.ice(T), AMBER, 'ENGINE TORQUE', `${Math.round(st.ice(T) * 100)}%`, al);
      bar(1440, 640, 360, 14, st.batt(T), CYAN, 'BATTERY SHARE', `${Math.round(st.batt(T) * 100)}%`, al);
    }

    typeOn('STEP 02', tx + 4, 210, { a: L3, b: E3, size: 18, color: CYAN });
    rise('WET MODE', tx, 300, { a: L3 + .1, b: E3, size: 96 });
    fadeTxt('Rain settings cap battery deployment', tx + 4, 360, { a: L3 + .6, b: E3, size: 28, color: DIM });
    if (T > L3 && T < E3 + .3) {
      const al = eoe(seg(T, L3 + .5, L3 + 1)) * (1 - seg(T, E3, E3 + .3)), kw = lerp(350, 250, eio(seg(T, 28.7, 30.2)));
      ctx.save(); ctx.globalAlpha = al;
      ctx.font = F(230, 900); ctx.fillStyle = WHITE; ctx.letterSpacing = '-6px'; ctx.fillText(`${Math.round(kw)}`, tx - 8, 600);
      ctx.font = F(70, 300); ctx.fillStyle = CYAN; ctx.letterSpacing = '0px'; ctx.fillText('kW', tx + 470, 600);
      ctx.fillStyle = 'rgba(255,255,255,.1)'; ctx.fillRect(tx, 650, 600, 22);
      ctx.fillStyle = CYAN; ctx.shadowColor = CYAN; ctx.shadowBlur = 20; ctx.fillRect(tx, 650, 600 * kw / 350, 22); ctx.shadowBlur = 0;
      ctx.fillStyle = RED; ctx.fillRect(tx + 600 * 250 / 350 - 1, 640, 3, 42);
      ctx.font = F(16, 700, 'Inter'); ctx.letterSpacing = '2px'; ctx.fillStyle = DIM; ctx.fillText('DRY 350 kW', tx + 480, 710); ctx.fillStyle = RED; ctx.fillText('WET CAP 250 kW', tx + 330, 740);
      ctx.restore();
    }

    typeOn('STEP 03', tx + 4, 210, { a: L4, b: E4, size: 18, color: RED });
    rise('ENERGY LIMIT', tx, 300, { a: L4 + .1, b: E4, size: 92 });
    rise('LOCK-OUT', tx, 395, { a: L4 + .3, b: E4, size: 92, color: RED, glow: 'rgba(255,30,45,.5)' });
    fadeTxt('Sepang\'s sector energy limit was reached and', tx + 4, 455, { a: L4 + .8, b: E4, size: 27, color: DIM });
    fadeTxt('the software fell into a state that stopped', tx + 4, 492, { a: L4 + 1.0, b: E4, size: 27, color: DIM });
    fadeTxt('the battery redeploying any power.', tx + 4, 529, { a: L4 + 1.2, b: E4, size: 27, color: DIM });
    // logic chain
    if (T > L4 + .9 && T < E4 + .3) {
      const al = 1 - seg(T, E4, E4 + .3), nodes = ['THROTTLE', 'TORQUE MAP', 'ENERGY LIMIT', 'MGU-K'];
      ctx.save(); ctx.globalAlpha = al;
      nodes.forEach((n, i) => {
        const k = eob(clamp((T - L4 - .9 - i * .28) / .45)); if (k <= 0) return;
        const x = tx + i * 205, y = 610, bad = i >= 2 && T > 33.2;
        ctx.save(); ctx.translate(x + 85, y + 34); ctx.scale(k, k);
        ctx.fillStyle = bad ? 'rgba(255,30,45,.18)' : 'rgba(63,214,255,.08)'; ctx.strokeStyle = bad ? RED : CYAN; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.roundRect(-85, -34, 170, 68, 10); ctx.fill(); ctx.stroke();
        ctx.font = F(17, 800, 'Inter'); ctx.letterSpacing = '1.5px'; ctx.textAlign = 'center'; ctx.fillStyle = WHITE; ctx.fillText(n, 0, 6);
        ctx.restore();
        if (i < 3) { const ak = clamp((T - L4 - 1.2 - i * .28) / .3); ctx.strokeStyle = i >= 1 && T > 33.2 ? RED : CYAN; ctx.lineWidth = 3; ctx.beginPath(); ctx.moveTo(x + 172, y + 34); ctx.lineTo(x + 172 + 30 * ak, y + 34); ctx.stroke(); }
      });
      if (T > 33.2) {
        const k = eob(clamp((T - 33.2) / .4)); ctx.save(); ctx.translate(tx + 2 * 205 + 85, 610 - 26); ctx.scale(k, k);
        ctx.strokeStyle = RED; ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(-18, -18); ctx.lineTo(18, 18); ctx.moveTo(18, -18); ctx.lineTo(-18, 18); ctx.stroke(); ctx.restore();
        ctx.font = F(26, 900); ctx.fillStyle = RED; ctx.letterSpacing = '3px'; ctx.globalAlpha = al * eoe(seg(T, 33.5, 34)); ctx.fillText('DEPLOY 0 kW  →  THROTTLE IGNORED', tx, 740);
      }
      ctx.restore();
    }
  }
  // ---------------- scene 5: root cause
  if (t >= 36 && t < 41.2) {
    ctx.save(); ctx.globalAlpha = .55 * eoe(seg(t, 36, 36.6)); ctx.fillStyle = '#04060b'; ctx.fillRect(0, 0, W, H); ctx.restore();
    typeOn('ROOT CAUSE  ·  FIA STATEMENT', 964, 200, { a: 36.1, b: 40.8, size: 20, color: CYAN, align: 'center' });
    rise('A PERFECT STORM', 960, 290, { a: 36.2, b: 38.75, size: 88, align: 'center' });
    const tiles = [['01', 'LOW ENGINE', 'SPEED'], ['02', 'LOW-GRIP', 'WET TRACK'], ['03', 'WET ENERGY', 'SETTINGS'], ['04', 'SEPANG\'S SECTOR', 'CONFIGURATION']];
    const m = eio(seg(t, 38.8, 39.6));
    tiles.forEach((tl, i) => {
      const k = eob(clamp((t - 36.5 - i * .22) / .55)); if (k <= 0) return;
      const tx0 = 240 + i * 370, ty0 = 520, w = 330, h = 220;
      const cx = lerp(tx0 + w / 2, 960, m), cy = lerp(ty0, 600, m) + (1 - k) * 200;
      const pts = morphPts('rect', 'oct', m, 'rectoct');
      drawPoly(pts, cx, cy, lerp(w / 2, 150, m) * k, lerp(h / 2, 150, m) * k, { stroke: m > .5 ? RED : CYAN, lw: 3, fill: m > .5 ? RED : CYAN, fillA: lerp(.06, .2, m), glow: m > .5 ? RED : null, alpha: Math.min(1, k) });
      const ta = Math.min(1, k) * (1 - seg(t, 38.6, 38.9));
      if (ta > 0) {
        ctx.save(); ctx.globalAlpha = ta; ctx.textAlign = 'left';
        ctx.font = F(44, 900); ctx.fillStyle = CYAN; ctx.fillText(tl[0], tx0 + 26, cy - 40);
        ctx.font = F(28, 800); ctx.fillStyle = WHITE; ctx.fillText(tl[1], tx0 + 26, cy + 22); ctx.fillText(tl[2], tx0 + 26, cy + 58);
        ctx.restore();
      }
    });
    if (t > 39.2) {
      slam('UNTESTED', 960, 585, { a: 39.3, b: 40.85, size: 54, color: WHITE, from: 1.6 });
      fadeTxt('COMBINATION', 960, 640, { a: 39.5, b: 40.85, size: 24, weight: 800, track: .25, align: 'center', color: '#ffd0d4' });
      fadeTxt('No team had raced the 2026 cars in real wet conditions — this case had never been seen.', 960, 850, { a: 39.7, b: 40.85, size: 27, align: 'center', color: DIM });
    }
  }
  // ---------------- scene 6: red flag
  if (t >= 41 && t < 45.2) {
    const pulse = .5 + .5 * Math.sin(t * 9);
    ctx.save(); ctx.globalAlpha = .18 * eoe(seg(t, 41, 41.3)) * (1 - seg(t, 44.8, 45)); ctx.strokeStyle = RED; ctx.lineWidth = 18 + 10 * pulse; ctx.strokeRect(0, 0, W, H); ctx.restore();
    slam('RED FLAG', 1390, 330, { a: 41.15, b: 44.75, size: 190, color: RED, glow: 'rgba(255,20,40,.8)', from: 2.4, track0: .4, track: .02 });
    fadeTxt('Cars losing drive on a soaked track at crawling', 1420, 455, { a: 41.7, b: 42.95, size: 30, align: 'center', color: WHITE });
    fadeTxt('speed are a hazard → session suspended.', 1420, 497, { a: 41.85, b: 42.95, size: 30, align: 'center', color: WHITE });
    typeOn('THE FIX', 1424, 455, { a: 43.0, b: 44.8, size: 20, color: CYAN, align: 'center' });
    fadeTxt('FIA sends new control software to every team,', 1420, 505, { a: 43.15, b: 44.8, size: 30, align: 'center', color: WHITE });
    fadeTxt('removing the energy limit in the affected sectors.', 1420, 547, { a: 43.35, b: 44.8, size: 30, align: 'center', color: WHITE });
  }
  // ---------------- scene 7: restart & result
  if (t >= 45) {
    typeOn('RESTART  ·  SAFETY CAR LEADS THE FIELD AWAY', 140, 220, { a: 45.15, b: 47.6, size: 20, color: AMBER });
    rise('RACE ON', 132, 330, { a: 45.3, b: 47.6, size: 120 });
    const pod = [['P1', 'VERSTAPPEN', 'WIN'], ['P2', 'ANTONELLI', ''], ['P3', 'HAMILTON', 'FROM 18TH']];
    pod.forEach(([p, n, s], i) => {
      const a = 45.9 + i * .25;
      rise(p, 140, 450 + i * 70, { a, b: 47.65, size: 44, color: i ? DIM : RED });
      rise(n, 220, 450 + i * 70, { a: a + .05, b: 47.65, size: 44 });
      if (s) fadeTxt(s, 540, 448 + i * 70, { a: a + .3, b: 47.65, size: 16, weight: 700, track: .2, color: CYAN });
    });
    rise('A SOFTWARE BUG STOPPED IT.', 960, 500, { a: 47.8, b: 49.35, size: 76, align: 'center' });
    rise('A SOFTWARE FIX RESTARTED IT.', 960, 600, { a: 48.15, b: 49.4, size: 76, align: 'center', color: CYAN });
  }

  // ---------------- chrome: chapter tag, flashes, grade
  const ci = CHAPTERS.filter(c => t >= c[0]).length - 1, ch = CHAPTERS[ci], ck = eoe(seg(t, ch[0] + .15, ch[0] + .7));
  if (t < 49.4) {
    ctx.save(); ctx.font = F(15, 800, 'Inter'); ctx.letterSpacing = '4px'; ctx.textAlign = 'right'; ctx.globalAlpha = ck * .9;
    ctx.fillStyle = RED; ctx.fillText(ch[1], W - 120 - ctx.measureText(ch[2]).width - 18, 112); ctx.fillStyle = WHITE; ctx.fillText(ch[2], W - 120, 112);
    ctx.fillStyle = 'rgba(255,255,255,.25)'; ctx.fillRect(W - 420, 124, 300, 1); ctx.fillStyle = RED; ctx.fillRect(W - 420, 124, 300 * ((ci + 1) / 7) * ck, 2);
    ctx.textAlign = 'left'; ctx.fillStyle = DIM; ctx.globalAlpha = .8 * eoe(seg(t, .3, 1)); ctx.fillText('SEPANG  ·  RED FLAG FILE', 120, 112);
    ctx.restore();
  }
  // light leak flash on cuts
  for (const c of CUTS) { const d = t - c; if (d > -.04 && d < .35) { ctx.save(); ctx.globalAlpha = .55 * Math.exp(-Math.max(0, d) * 12); ctx.fillStyle = c === 41 ? '#ff2030' : '#dfeaff'; ctx.fillRect(0, 0, W, H); ctx.restore(); } }
  const lt = lightning(t); if (lt > 0) { ctx.save(); ctx.globalAlpha = Math.min(.35, lt * .22); ctx.fillStyle = '#e8f0ff'; ctx.fillRect(0, 0, W, H); ctx.restore(); }
  // grain
  ctx.save(); ctx.globalCompositeOperation = 'overlay'; ctx.globalAlpha = .12; const gp = grains[Math.floor(t * 30) % 4];
  const r = rng(Math.floor(t * 30)); ctx.translate(-r() * 256, -r() * 256); ctx.fillStyle = gp; ctx.fillRect(0, 0, W + 256, H + 256); ctx.restore();
  // letterbox
  ctx.fillStyle = '#000'; ctx.fillRect(0, 0, W, bar_h); ctx.fillRect(0, H - bar_h, W, bar_h);
  // fade in/out
  const fade = Math.max(1 - seg(t, 0, .5), seg(t, 49.35, 50));
  if (fade > 0) { ctx.fillStyle = `rgba(0,0,0,${fade})`; ctx.fillRect(0, 0, W, H); }
}

// ---------------------------------------------------------------- frame entry
window.frame = async (t, q = .92) => {
  T = t; direct(t);
  composer.render();
  ctx.clearRect(0, 0, W, H); ctx.drawImage(glc, 0, 0);
  overlay(t);
  return out.toDataURL('image/jpeg', q);
};
await document.fonts.load('900 100px "Inter Display"'); await document.fonts.load('300 100px "Inter Display"');
await document.fonts.load('800 30px "Inter"'); await document.fonts.load('600 30px "Inter"'); await document.fonts.load('500 30px "Inter"');
window.READY = true;
