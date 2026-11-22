import * as THREE from 'three';

const W = 720, H = 1280;
const DUR = 70;
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.useLegacyLights = true;
renderer.outputColorSpace = THREE.SRGBColorSpace;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x05050a);
scene.fog = new THREE.FogExp2(0x05050a, 0.018);
const cam = new THREE.PerspectiveCamera(70, W / H, 0.05, 90);
scene.add(cam);

// ---------- materiais toon + contorno ----------
const grad = new THREE.DataTexture(new Uint8Array([70, 150, 255]), 3, 1, THREE.RedFormat);
grad.minFilter = grad.magFilter = THREE.NearestFilter; grad.needsUpdate = true;
const toon = (c) => new THREE.MeshToonMaterial({ color: c, gradientMap: grad });
const outMat = new THREE.MeshBasicMaterial({ color: 0x0c0a10, side: THREE.BackSide });
function outlined(mesh, th = 0.03) {
  mesh.geometry.computeBoundingBox();
  const s = new THREE.Vector3(); mesh.geometry.boundingBox.getSize(s);
  const o = new THREE.Mesh(mesh.geometry, outMat);
  o.scale.set(1 + 2 * th / Math.max(s.x, 0.05), 1 + 2 * th / Math.max(s.y, 0.05), 1 + 2 * th / Math.max(s.z, 0.05));
  mesh.add(o);
  return mesh;
}
function box(w, h, d, color, x, y, z, parent = scene, outline = true, th = 0.03) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), toon(color));
  m.position.set(x, y, z);
  if (outline) outlined(m, th);
  parent.add(m); return m;
}
function basicBox(w, h, d, color, x, y, z, parent = scene) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshBasicMaterial({ color }));
  m.position.set(x, y, z); parent.add(m); return m;
}

// ---------- luzes ----------
const hemi = new THREE.HemisphereLight(0xffffff, 0x8a8aa0, 1.0); scene.add(hemi);
const aisleLights = [];
for (const z of [-4, -10, -16]) {
  const l = new THREE.PointLight(0xffffff, 1.0, 14, 1); l.position.set(-1.75, 3.0, z); scene.add(l); aisleLights.push(l);
}
const emerg = [];
for (const z of [-3, -11, -19]) {
  const l = new THREE.PointLight(0xff2a18, 0, 9, 1); l.position.set(-1.75, 2.9, z); scene.add(l); emerg.push(l);
}
const street = new THREE.PointLight(0xffa020, 0, 30, 1); street.position.set(-0.6, 3.1, 3.2); scene.add(street);
const backBulb = new THREE.PointLight(0xffe0a8, 0.0, 12, 1); backBulb.position.set(-2.6, 2.8, -26); scene.add(backBulb);
const alarmLight = new THREE.PointLight(0xff1010, 0, 14, 1); alarmLight.position.set(-2.6, 2.6, -26); scene.add(alarmLight);

// ---------- loja ----------
const checker = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d'); g.fillStyle = '#c9ccd8'; g.fillRect(0, 0, 64, 64);
  g.fillStyle = '#9aa0b8'; g.fillRect(0, 0, 32, 32); g.fillRect(32, 32, 32, 32);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(10, 30);
  t.colorSpace = THREE.SRGBColorSpace; return t;
})();
const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 40), new THREE.MeshToonMaterial({ map: checker, gradientMap: grad }));
floor.rotation.x = -Math.PI / 2; floor.position.set(0, 0, -16); scene.add(floor);
box(14, 0.2, 40, 0x4a4a58, 0, 3.3, -16, scene, false);            // teto
box(0.3, 3.4, 40, 0xe8dcc4, -7, 1.7, -16, scene, false);          // parede esq
box(0.3, 3.4, 40, 0xe8dcc4, 7, 1.7, -16, scene, false);           // parede dir
// parede do fundo com abertura em x=-1.75
box(5.25, 3.4, 0.3, 0xe8dcc4, -4.375, 1.7, -22, scene, false);
box(8.25, 3.4, 0.3, 0xe8dcc4, 2.875, 1.7, -22, scene, false);
box(2.0, 1.0, 0.3, 0xe8dcc4, -1.75, 2.9, -22, scene, false);
// frente: vidro + molduras
const glass = new THREE.Mesh(new THREE.PlaneGeometry(14, 3.2), new THREE.MeshBasicMaterial({ color: 0x9ab8d0, transparent: true, opacity: 0.07 }));
glass.position.set(0, 1.7, 0); scene.add(glass);
for (const x of [-6.5, -3.5, -0.2, 3.5, 6.5]) box(0.18, 3.3, 0.18, 0x202028, x, 1.7, 0, scene, false);
box(14, 0.2, 0.2, 0x202028, 0, 3.2, 0, scene, false);
box(14, 0.2, 0.2, 0x202028, 0, 0.1, 0, scene, false);
// porta da frente (barra + tranca)
const doorBar = box(1.6, 0.1, 0.1, 0x777788, -0.2, 1.0, -0.12, scene, true, 0.02);
const lockObj = box(0.16, 0.22, 0.12, 0xc8c8d0, -0.2, 1.0, -0.12, scene, true, 0.02);
// balcão do caixa
box(2.2, 1.0, 0.8, 0x2f8f6f, 4.6, 0.5, -2.0);
box(0.5, 0.35, 0.4, 0x333340, 4.6, 1.2, -2.0);
// luminárias
const panels = [];
for (const z of [-3, -7, -11, -15, -19]) for (const x of [-1.75, 1.75]) {
  const p = basicBox(1.4, 0.06, 0.4, 0xffffff, x, 3.18, z); panels.push(p);
}
// gôndolas
const palette = [0xf2c230, 0xe84855, 0x4cc38a, 0xf4f4f4, 0x3b82f6, 0xff8a3d];
const prodGeo = new THREE.BoxGeometry(0.17, 0.26, 0.12);
const gondolaX = [-3.5, 0, 3.5];
const prods = [];
for (const gx of gondolaX) {
  box(0.1, 1.9, 18, 0xdfe3ee, gx, 0.95, -12);
  for (let lv = 0; lv < 4; lv++) {
    const y = 0.35 + lv * 0.45;
    box(0.95, 0.05, 18, lv % 2 ? 0x4a7fd8 : 0xd8584a, gx, y, -12, scene, true, 0.015);
    for (const s of [-1, 1]) for (let z = -3.2; z > -20.8; z -= 0.22)
      prods.push([gx + s * (0.2 + Math.random() * 0.15), y + 0.16, z, palette[(Math.random() * 6) | 0]]);
  }
}
// prateleiras nas paredes
for (const sx of [-6.5, 6.5]) {
  box(0.1, 1.9, 18, 0xdfe3ee, sx, 0.95, -12, scene, false);
  for (let lv = 0; lv < 4; lv++) {
    const y = 0.35 + lv * 0.45;
    box(0.6, 0.05, 18, 0x4a7fd8, sx - Math.sign(sx) * 0.3, y, -12, scene, false);
    for (let z = -3.2; z > -20.8; z -= 0.22) prods.push([sx - Math.sign(sx) * (0.2 + Math.random() * 0.2), y + 0.16, z, palette[(Math.random() * 6) | 0]]);
  }
}
{
  const im = new THREE.InstancedMesh(prodGeo, toon(0xffffff), prods.length);
  const m4 = new THREE.Matrix4(), col = new THREE.Color();
  prods.forEach((p, i) => { m4.makeTranslation(p[0], p[1], p[2]); im.setMatrixAt(i, m4); im.setColorAt(i, col.setHex(p[3])); });
  scene.add(im);
}
// placa de saída verde
const exitSign = basicBox(0.6, 0.2, 0.05, 0x22ff77, -1.75, 3.0, -21.8);
// sala dos fundos
box(8, 0.2, 8, 0x4a4a58, -2, 3.3, -26, scene, false);
box(8, 0.1, 8, 0x555060, -2, 0.0, -26, scene, false);
box(0.3, 3.4, 8, 0xd8ccb4, -6, 1.7, -26, scene, false);
box(0.3, 3.4, 8, 0xd8ccb4, 2, 1.7, -26, scene, false);
box(8, 3.4, 0.3, 0xd8ccb4, -2, 1.7, -30, scene, false);
const crateCols = [0xb07a3a, 0x8d6330, 0xc48a45];
for (const [x, z, s] of [[-5.3, -29, 1.0], [-4.2, -29.2, 0.8], [-5.2, -27.2, 0.7], [0.9, -29, 1.1], [1.0, -27.5, 0.8], [-0.2, -29.3, 0.7], [0.8, -24.2, 0.9]])
  box(s, s, s, crateCols[(Math.random() * 3) | 0], x, s / 2, z);
box(0.2, 2.6, 3, 0x555a70, -5.8, 1.3, -25, scene, true);
box(1.2, 0.3, 0.1, 0xdd3333, -2.6, 2.9, -29.8, scene, false);   // luz giratória base
// rua lá fora
const ground = new THREE.Mesh(new THREE.PlaneGeometry(60, 50), new THREE.MeshToonMaterial({ color: 0x1a1c26, gradientMap: grad }));
ground.rotation.x = -Math.PI / 2; ground.position.set(0, -0.01, 25); scene.add(ground);
box(60, 0.15, 1.2, 0x555560, 0, 0.07, 2.5, scene, false);
for (let i = -5; i < 6; i++) basicBox(1.4, 0.02, 0.2, 0x8a8470, i * 3, 0.02, 12);
for (const [x, z, w, h] of [[-12, 20, 6, 9], [-4, 24, 5, 12], [6, 22, 7, 8], [14, 20, 6, 11], [0, 30, 10, 14]])
  box(w, h, 4, 0x15161f, x, h / 2, z, scene, false);
box(0.18, 3.0, 0.18, 0x222228, -0.6, 1.5, 3.2);
const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.34, 12, 12), new THREE.MeshBasicMaterial({ color: 0xffb030 }));
lamp.position.set(-0.6, 3.05, 3.2); scene.add(lamp);
box(0.9, 0.08, 0.5, 0x222228, -0.6, 3.3, 3.2, scene, false);
const halo = new THREE.Mesh(new THREE.SphereGeometry(1.0, 12, 12), new THREE.MeshBasicMaterial({ color: 0xffa020, transparent: true, opacity: 0.18 }));
halo.position.copy(lamp.position); scene.add(halo);

// ---------- personagens ----------
function makeChar(shirt, hair, opts = {}) {
  const g = new THREE.Group(); const skin = opts.skin ?? 0xf0bd94;
  const tor = new THREE.Mesh(new THREE.BoxGeometry(0.52, 0.72, 0.3), toon(shirt)); tor.position.y = 1.15; outlined(tor, 0.025); g.add(tor);
  if (opts.apron) { const a = box(0.4, 0.55, 0.05, 0xd84a4a, 0, 1.05, 0.17, g, true, 0.015); }
  if (opts.tie) { box(0.08, 0.5, 0.03, 0xc02a3a, 0, 1.15, 0.17, g, false); }
  const legs = [];
  for (const sx of [-0.14, 0.14]) {
    const p = new THREE.Group(); p.position.set(sx, 0.78, 0);
    const l = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.78, 0.22), toon(0x2a2d44)); l.position.y = -0.39; outlined(l, 0.02); p.add(l);
    const shoe = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.1, 0.32), toon(0x15151c)); shoe.position.set(0, -0.76, 0.05); p.add(shoe);
    g.add(p); legs.push(p);
  }
  const arms = [];
  for (const sx of [-0.35, 0.35]) {
    const p = new THREE.Group(); p.position.set(sx, 1.46, 0);
    const a = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.62, 0.14), toon(shirt)); a.position.y = -0.3; outlined(a, 0.02); p.add(a);
    const h = new THREE.Mesh(new THREE.SphereGeometry(0.09, 10, 10), toon(skin)); h.position.y = -0.66; outlined(h, 0.015); p.add(h);
    g.add(p); arms.push(p);
  }
  const head = new THREE.Group(); head.position.y = 1.78; g.add(head);
  const hs = new THREE.Mesh(new THREE.SphereGeometry(0.25, 20, 16), toon(skin)); outlined(hs, 0.03); head.add(hs);
  const hr = new THREE.Mesh(new THREE.SphereGeometry(0.27, 20, 12, 0, Math.PI * 2, 0, Math.PI * 0.48), toon(hair)); hr.position.y = 0.04; hr.rotation.x = -0.25; outlined(hr, 0.02); head.add(hr);
  const eyes = [], pupils = [];
  for (const sx of [-0.1, 0.1]) {
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.065, 12, 10), new THREE.MeshBasicMaterial({ color: 0xffffff })); e.position.set(sx, 0.03, 0.2); head.add(e); eyes.push(e);
    const ep = new THREE.Mesh(new THREE.SphereGeometry(0.032, 10, 8), new THREE.MeshBasicMaterial({ color: 0x111111 })); ep.position.set(sx, 0.03, 0.255); head.add(ep); pupils.push(ep);
  }
  const brows = [];
  for (const sx of [-0.1, 0.1]) { const b = basicBox(0.1, 0.025, 0.02, 0x111111, sx, 0.12, 0.23, head); brows.push(b); }
  const mouth = basicBox(0.1, 0.03, 0.02, 0x2a1015, 0, -0.1, 0.23, head);
  g.userData = { arms, legs, head, brows, mouth, pupils, mood: 'calm' };
  scene.add(g); return g;
}
function setMood(c, mood, talk = 0) {
  const u = c.userData;
  const s = mood === 'tense' ? 1 : mood === 'shock' ? -1 : 0;
  u.brows[0].rotation.z = -0.4 * s * (mood === 'tense' ? 1 : -1) * (mood === 'tense' ? 1 : 1);
  u.brows[1].rotation.z = 0.4 * s * (mood === 'tense' ? 1 : -1) * (mood === 'tense' ? 1 : 1);
  u.brows.forEach(b => b.position.y = mood === 'shock' ? 0.17 : 0.12);
  u.pupils.forEach(p => p.scale.setScalar(mood === 'calm' ? 1 : 0.6));
  const open = mood === 'shock' ? 0.09 : talk;
  u.mouth.scale.set(mood === 'shock' ? 0.7 : 1, 1 + open * 28, 1);
}
const manager = makeChar(0x1e2233, 0x1b1b1e, { tie: true });
const colleague = makeChar(0x3c9a66, 0x6a3b22, { apron: false });
const vulto = (() => {
  const g = new THREE.Group();
  const b = new THREE.Mesh(new THREE.CapsuleGeometry(0.28, 1.6, 4, 10), new THREE.MeshBasicMaterial({ color: 0x030306 })); b.position.y = 1.1; g.add(b);
  const hd = new THREE.Mesh(new THREE.SphereGeometry(0.26, 12, 10), new THREE.MeshBasicMaterial({ color: 0x030306 })); hd.position.y = 2.2; g.add(hd);
  for (const sx of [-0.09, 0.09]) { const e = new THREE.Mesh(new THREE.SphereGeometry(0.035, 8, 8), new THREE.MeshBasicMaterial({ color: 0xff2020 })); e.position.set(sx, 2.23, 0.23); g.add(e); }
  g.position.set(-1.75, 0, -3.2); g.visible = false; scene.add(g); return g;
})();

// ---------- mãos POV + celular ----------
const hands = new THREE.Group(); cam.add(hands);
const handL = new THREE.Group(), handR = new THREE.Group(); hands.add(handL, handR);
for (const [grp, sx] of [[handL, -1], [handR, 1]]) {
  const sl = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.11, 0.5), toon(0x2a3a66)); sl.position.set(0, 0, 0.1); outlined(sl, 0.012); grp.add(sl);
  const fist = new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 10), toon(0xf0bd94)); fist.position.set(0, 0, -0.17); outlined(fist, 0.012); grp.add(fist);
}
const can = (() => {
  const g = new THREE.Group();
  const c = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.14, 14), toon(0xe04545)); outlined(c, 0.008); g.add(c);
  const s = new THREE.Mesh(new THREE.CylinderGeometry(0.052, 0.052, 0.05, 14), toon(0xf6f6f6)); g.add(s);
  return g;
})();
handL.add(can); can.position.set(0.0, 0.05, -0.22);
const phoneCv = document.createElement('canvas'); phoneCv.width = 256; phoneCv.height = 512;
const phoneTex = new THREE.CanvasTexture(phoneCv); phoneTex.colorSpace = THREE.SRGBColorSpace;
let phoneState = -1;
function drawPhone(state) {
  if (state === phoneState) return; phoneState = state;
  const g = phoneCv.getContext('2d');
  g.fillStyle = '#16213c'; g.fillRect(0, 0, 256, 512);
  g.fillStyle = '#fff'; g.font = 'bold 30px sans-serif'; g.fillText('02:03', 84, 60);
  if (state >= 1) {
    g.fillStyle = '#f2f2f6'; g.fillRect(12, 90, 232, 70);
    g.fillStyle = '#111'; g.font = 'bold 18px sans-serif'; g.fillText('Desconhecido', 24, 120);
    g.fillStyle = '#c31f2f'; g.font = '16px sans-serif'; g.fillText('Nova foto recebida', 24, 146);
  }
  if (state >= 2) {
    g.fillStyle = '#0b0b12'; g.fillRect(12, 190, 232, 280);
    g.fillStyle = '#2a2638'; g.beginPath(); g.moveTo(60, 470); g.lineTo(100, 270); g.lineTo(156, 270); g.lineTo(196, 470); g.fill();
    g.fillStyle = '#040407'; g.beginPath(); g.arc(128, 250, 34, 0, 7); g.fill();
    g.fillStyle = '#ff2020'; g.fillRect(114, 246, 9, 9); g.fillRect(134, 246, 9, 9);
    g.fillStyle = '#e8e8f0'; g.font = '14px monospace'; g.fillText('LOJA - CORREDOR 3', 22, 212);
  }
  phoneTex.needsUpdate = true;
}
drawPhone(0);
const phone = new THREE.Group(); cam.add(phone);
const pBody = new THREE.Mesh(new THREE.BoxGeometry(0.17, 0.34, 0.015), toon(0x0f0f14)); outlined(pBody, 0.01); phone.add(pBody);
const pScreen = new THREE.Mesh(new THREE.PlaneGeometry(0.15, 0.31), new THREE.MeshBasicMaterial({ map: phoneTex })); pScreen.position.z = 0.009; phone.add(pScreen);
phone.visible = false;

// ---------- utilidades de movimento ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const sm = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const lerp = (a, b, k) => a + (b - a) * k;
function aim(p, t) { const dx = t[0] - p[0], dy = t[1] - p[1], dz = t[2] - p[2]; return [Math.atan2(-dx, -dz), Math.atan2(dy, Math.hypot(dx, dz))]; }
function wrapNear(a, ref) { while (a - ref > Math.PI) a -= 2 * Math.PI; while (a - ref < -Math.PI) a += 2 * Math.PI; return a; }
function kf(t, p, tg, fov = 65, roll = 0) { const [yaw, pitch] = aim(p, tg); return { t, p, yaw, pitch, fov, roll }; }
const KEYS = [
  // cena 1 – grua descendo + dolly pelo corredor + arco ao redor do colega
  kf(0.0, [-1.75, 3.0, -2.0], [-1.75, 1.2, -9], 78),
  kf(2.6, [-1.75, 1.65, -3.8], [-1.75, 1.4, -9], 68),
  kf(7.0, [-1.75, 1.6, -4.6], [-1.75, 1.4, -9], 64),
  kf(12.4, [-1.2, 1.55, -5.0], [-1.75, 1.5, -9.2], 56),
  kf(13.8, [-1.2, 1.55, -5.0], [-1.75, 1.5, -9.2], 56),
  // cena 2 – whip pan 180° + push-in com zoom na luz estranha
  kf(15.5, [-2.4, 1.6, -8.4], [-0.6, 1.8, 3], 72),
  kf(19.0, [-2.4, 1.55, -7.9], [-0.6, 2.4, 3.2], 62),
  kf(25.4, [-2.4, 1.5, -6.8], [-0.6, 2.9, 3.2], 42, 0.04),
  // cena 3 – whip para a porta, close baixo com dutch angle
  kf(26.6, [-2.4, 1.5, -6.2], [-0.3, 1.4, 0], 66),
  kf(29.0, [-2.2, 1.4, -3.6], [-0.3, 1.1, -0.3], 58),
  kf(31.0, [-2.0, 0.9, -3.0], [-0.3, 1.6, -0.5], 48, 0.17),
  kf(35.0, [-2.0, 1.25, -3.3], [-0.3, 1.7, -0.5], 40, 0.1),
];
const FOLLOW_START = 35.3;

function poseAt(t) {
  const last = KEYS[KEYS.length - 1];
  let k;
  if (t <= KEYS[0].t) k = KEYS[0];
  else if (t >= last.t) k = last;
  else {
    let i = 0; while (KEYS[i + 1].t < t) i++;
    const a = KEYS[i], b = KEYS[i + 1], u = sm((t - a.t) / (b.t - a.t));
    const by = wrapNear(b.yaw, a.yaw);
    k = { p: [lerp(a.p[0], b.p[0], u), lerp(a.p[1], b.p[1], u), lerp(a.p[2], b.p[2], u)], yaw: lerp(a.yaw, by, u), pitch: lerp(a.pitch, b.pitch, u), fov: lerp(a.fov, b.fov, u), roll: lerp(a.roll, b.roll, u) };
  }
  return { p: k.p.slice(), yaw: k.yaw, pitch: k.pitch, fov: k.fov, roll: k.roll };
}

// trajetória do gerente (waypoints: t, x, z)
function path(pts, t) {
  if (t <= pts[0][0]) return [pts[0][1], pts[0][2], 0, 0];
  for (let i = 0; i < pts.length - 1; i++) {
    const a = pts[i], b = pts[i + 1];
    if (t <= b[0]) { const u = (t - a[0]) / (b[0] - a[0]); return [lerp(a[1], b[1], u), lerp(a[2], b[2], u), b[1] - a[1], b[2] - a[2]]; }
  }
  const l = pts[pts.length - 1]; return [l[1], l[2], 0, 0];
}
const MGR = [[25.5, -1.6, -14], [27.2, -1.6, -3.0], [28.2, -0.4, -0.9], [35.4, -0.35, -0.8], [36.6, -1.75, -3.0], [40.6, -1.75, -21.5]];
const COL = [[36.0, -1.0, -4.8], [36.4, -1.0, -4.8], [40.6, -1.6, -20.5]];

// ---------- legendas ----------
const LINES = [
  [1.0, 6.0, "TURNO DA NOITE. <span class=k>2H</span> DA MANHÃ."],
  [7.0, 11.5, "FALTA POUCO PRA <span class=k>ACABAR</span>..."],
  [13.5, 18.0, "AS LUZES <span class=k>APAGARAM</span>."],
  [19.0, 24.5, "AQUELA <span class=k>LUZ</span> NÃO É NORMAL."],
  [26.0, 31.0, "O GERENTE <span class=k>TRANCOU</span> A PORTA."],
  [32.0, 39.5, "NÃO OLHEM PRA <span class=k>RUA</span>!"],
  [41.0, 46.0, "O <span class=k>ALARME</span> DISPAROU SOZINHO."],
  [47.0, 52.5, "UMA FOTO. DE <span class=k>DENTRO</span> DA LOJA."],
  [53.0, 57.5, "“<span class=k>IGNORA</span>. FICA QUIETO.”"],
  [59.0, 64.0, "E <span class=k>AGORA</span>?"],
];
const subEl = document.getElementById('sub'), endEl = document.getElementById('end'), fadeEl = document.getElementById('fade'), clkEl = document.getElementById('clk'), recEl = document.getElementById('rec');
const cA = document.getElementById('cA'), cB = document.getElementById('cB');
const CUTS = [12.5, 25.5, 40.5, 58.5];

// ---------- frame ----------
const rnd = (n) => { const s = Math.sin(n * 127.1) * 43758.5453; return s - Math.floor(s); };
function setLights(t) {
  let main = 1, emer = 0;
  if (t >= 13.5 && t < 15.0) main = rnd(Math.floor(t * 14)) > 0.55 ? 0.9 : 0.05;
  else if (t >= 15.0) main = 0;
  if (t >= 14.6) emer = 1;
  const inBack = t >= 40.5 && t < 58.5;
  hemi.intensity = main ? 1.0 * main : 0.16;
  hemi.color.setHex(main ? 0xffffff : 0x6070a0); hemi.groundColor.setHex(main ? 0x8a8aa0 : 0x20202c);
  aisleLights.forEach(l => l.intensity = main * 1.0);
  panels.forEach(p => p.material.color.setHex(main > 0.5 ? 0xffffff : main > 0 ? 0x666670 : 0x1c1c22));
  emerg.forEach((l, i) => l.intensity = emer * (0.8 + 0.4 * Math.sin(t * 3 + i)));
  street.intensity = t >= 14.6 ? 2.2 + 0.6 * Math.sin(t * 4) : 0.0;
  lamp.material.color.setHex(t >= 14.6 ? 0xffb030 : 0x665030);
  halo.visible = t >= 14.6; halo.scale.setScalar(1 + 0.2 * Math.sin(t * 4));
  backBulb.intensity = t >= 15 ? 0.7 : 0.0;
  const alarmOn = inBack && t >= 41 && t < 47.5 || (t >= 58.5);
  const ph = (Math.sin(t * 9) > 0) ? 1 : 0.15;
  alarmLight.intensity = alarmOn ? 3.0 * ph : (inBack ? 0.4 : 0);
  alarmLight.position.set(-2.6 + Math.cos(t * 6) * 1.4, 2.6, -26 + Math.sin(t * 6) * 1.4);
  scene.background.setHex(0x05050a);
  exitSign.visible = t >= 14.6;
}
function animateChars(t) {
  const u = manager.userData, c = colleague.userData;
  // gerente
  manager.visible = t >= 25.5;
  if (manager.visible) {
    const [x, z, dx, dz] = path(MGR, t);
    manager.position.set(x, 0, z);
    const moving = Math.hypot(dx, dz) > 0.001 && !(t > 28.4 && t < 35.4);
    if (moving) manager.rotation.y = Math.atan2(dx, dz);
    else if (t >= 28.4 && t < 31.5) manager.rotation.y = 0;
    if (t >= 31.5 && t < 35.4) manager.rotation.y = Math.PI + 0.25 * Math.sin(t * 0.9); // vira para a câmera
    const run = moving ? Math.sin(t * 14) : 0;
    u.legs[0].rotation.x = run * 0.9; u.legs[1].rotation.x = -run * 0.9;
    u.arms[0].rotation.x = -run * 0.9; u.arms[1].rotation.x = run * 0.9;
    if (t >= 28.4 && t < 31) { u.arms[1].rotation.x = -1.4 + 0.2 * Math.sin(t * 20); u.arms[0].rotation.x = 0; }
    if (t >= 31.5 && t < 35.4) { u.arms[0].rotation.x = -0.9 + 0.3 * Math.sin(t * 5); u.arms[1].rotation.x = -0.9; }
    setMood(manager, 'tense', (t >= 31.5 && t < 35.4) ? Math.abs(Math.sin(t * 14)) * 0.5 : 0);
    manager.position.y = moving ? Math.abs(Math.sin(t * 14)) * 0.05 : 0;
  }
  // colega
  if (t < 15.3) { // repondo prateleira
    colleague.position.set(-1.35, 0, -9.0); colleague.rotation.y = Math.PI * -0.5 + 0.3;
    c.arms[0].rotation.x = -1.2 + Math.sin(t * 2.4) * 0.25; c.arms[1].rotation.x = 0.1;
    c.legs.forEach(l => l.rotation.x = 0);
    c.head.rotation.y = 0.3 * Math.sin(t * 0.9);
    setMood(colleague, 'calm', (t > 7 && t < 11.5) ? Math.abs(Math.sin(t * 10)) * 0.2 : 0);
  } else if (t < 36.0) { // paralisado olhando a rua
    colleague.position.set(-1.0, 0, -4.8); colleague.rotation.y = Math.PI;
    c.arms.forEach(a => a.rotation.x = 0); c.legs.forEach(l => l.rotation.x = 0); c.head.rotation.y = 0;
    colleague.scale.setScalar(1 + 0.004 * Math.sin(t * 2));
    setMood(colleague, 'shock');
  } else if (t < 40.6) { // corre atrás
    const [x, z, dx, dz] = path(COL, t);
    colleague.position.set(x, 0, z); colleague.rotation.y = Math.atan2(dx, dz) || 0;
    const run = Math.sin(t * 14 + 1);
    c.legs[0].rotation.x = run * 0.9; c.legs[1].rotation.x = -run * 0.9;
    c.arms[0].rotation.x = -run * 0.9; c.arms[1].rotation.x = run * 0.9;
    colleague.position.y = Math.abs(run) * 0.05; setMood(colleague, 'shock');
  } else if (t < 58.5) { // agachado nos fundos
    colleague.position.set(-1.9, 0, -26.1); colleague.rotation.y = Math.PI * -0.6;
    colleague.position.y = -0.35; c.legs.forEach(l => l.rotation.x = -1.0);
    c.arms.forEach(a => a.rotation.x = -0.6); setMood(colleague, 'shock');
  } else { colleague.visible = false; }
  colleague.visible = t < 58.5;
  if (t >= 40.6 && t < 58.5) {
    manager.position.set(-3.3, -0.3, -26.3); manager.rotation.y = Math.PI * 0.45;
    u.legs.forEach(l => l.rotation.x = -1.0); u.arms[0].rotation.x = -0.4; u.arms[1].rotation.x = -1.5; // dedo nos lábios
    setMood(manager, 'tense', (t >= 53 && t < 57.5) ? Math.abs(Math.sin(t * 9)) * 0.35 : 0);
    manager.visible = true;
  }
  if (t >= 58.5) manager.visible = false;
  // vulto
  vulto.visible = t >= 59.8 && (t < 62 ? Math.sin(t * 25) > -0.2 : true);
  vulto.position.set(-1.75, 0, -3.0 + (t > 62 ? -0.6 * (t - 62) : 0));
}

function cameraFor(t) {
  let P;
  if (t < FOLLOW_START) {
    if (t < 40.5) P = poseAt(t);
  }
  if (t >= FOLLOW_START && t < 40.5) {
    const [mx, mz] = path(MGR, t);
    const pos = [mx + 0.55, 1.55 + 0.1 * Math.sin(t * 9), Math.min(mz + 3.4, -0.8)];
    const [yaw, pitch] = aim(pos, [mx, 1.45, mz]);
    const base = poseAt(FOLLOW_START - 0.01);
    const u = sm((t - FOLLOW_START) / 0.9);
    const ty = wrapNear(yaw, base.yaw);
    P = { p: [lerp(base.p[0], pos[0], u), lerp(base.p[1], pos[1], u), lerp(base.p[2], pos[2], u)], yaw: lerp(base.yaw, ty, u), pitch: lerp(base.pitch, pitch, u), fov: lerp(base.fov, 74, u), roll: lerp(base.roll, 0.06 * Math.sin(t * 5), u) };
  }
  if (t >= 40.5 && t < 58.5) {
    const C = [-2.6, 1.15, -26.2];
    if (t < 47) {
      const ang = 0.5 + 0.34 * (t - 40.5);
      const r = lerp(3.3, 2.5, sm((t - 40.5) / 6.5));
      const pos = [C[0] + Math.cos(ang) * r, lerp(2.3, 1.35, sm((t - 40.5) / 4)), C[2] + Math.sin(ang) * r];
      const [yaw, pitch] = aim(pos, C);
      P = { p: pos, yaw, pitch, fov: 62, roll: 0.07 };
    } else if (t < 52.8) {
      const ang = 0.5 + 0.34 * 6.5 + 0.05 * (t - 47);
      const pos = [C[0] + Math.cos(ang) * 2.4, 1.45, C[2] + Math.sin(ang) * 2.4];
      const [yaw, pitch] = aim(pos, [C[0], 1.0, C[2]]);
      P = { p: pos, yaw, pitch: pitch - 0.05 * sm((t - 47.5) / 2), fov: lerp(62, 48, sm((t - 47) / 5)), roll: 0 };
    } else {
      const k = sm((t - 52.8) / 5.5);
      const pos = [lerp(-1.1, -2.15, k), lerp(1.5, 1.62, k), lerp(-24.7, -25.55, k)];
      const [yaw, pitch] = aim(pos, [-3.3, 1.62, -26.3]);
      P = { p: pos, yaw, pitch, fov: lerp(52, 34, k), roll: -0.05 * k };
    }
  }
  if (t >= 58.5) {
    const k = clamp((t - 58.5) / 6.0), e = k * k * (0.4 + 0.6 * k);
    const pos = [-1.75, lerp(1.25, 1.5, k), lerp(-24.2, -9.5, e)];
    const [yaw, pitch] = aim(pos, [-1.75, 1.45, 0]);
    P = { p: pos, yaw, pitch, fov: lerp(56, 92, e), roll: 0 };
  }
  // handheld
  const amp = (t >= 35.3 && t < 40.5) ? 2.6 : (t >= 58.5 ? 1.6 : 1.0);
  const sh = (f, ph) => Math.sin(t * f + ph);
  P.p[0] += 0.012 * amp * sh(7.3, 0); P.p[1] += 0.016 * amp * sh(5.1, 1.7) + 0.01 * Math.sin(t * 2.2);
  P.yaw += 0.006 * amp * sh(3.7, 2); P.pitch += 0.006 * amp * sh(4.3, 0.5); P.roll += 0.004 * amp * sh(2.9, 3);
  return P;
}

window.renderAt = (t) => {
  setLights(t); animateChars(t);
  const P = cameraFor(t);
  cam.position.set(...P.p);
  cam.rotation.order = 'YXZ'; cam.rotation.set(P.pitch, P.yaw, P.roll);
  cam.fov = P.fov; cam.updateProjectionMatrix();
  // mãos POV
  const bob = Math.sin(t * 2.2) * 0.012;
  const showHands = t < 25.4 || (t >= 40.5 && t < 52.8) || t >= 58.5;
  hands.visible = showHands && !(t >= 35.3 && t < 40.5);
  handL.position.set(-0.2, -0.27 + bob, -0.38); handR.position.set(0.2, -0.27 + bob, -0.38);
  handL.rotation.set(0.15, 0.12, 0); handR.rotation.set(0.15, -0.12, 0);
  can.visible = t < 15;
  if (t < 12.4) { handL.position.y += 0.06 * Math.sin(t * 1.6); handL.rotation.x = 0.35 * Math.sin(t * 1.6); }
  // celular
  const phoneUp = t >= 46.6 && t < 52.8;
  phone.visible = phoneUp;
  if (phoneUp) {
    const up = sm((t - 46.6) / 1.2);
    const vib = (t > 46.9 && t < 48.1) ? Math.sin(t * 90) * 0.004 : 0;
    phone.position.set(0.0 + vib, lerp(-0.42, -0.08, up), lerp(-0.6, lerp(-0.45, -0.3, sm((t - 49) / 3.5)), up));
    phone.rotation.set(0.1, 0, 0);
    drawPhone(t >= 49.2 ? 2 : t >= 47.8 ? 1 : 0);
    handR.visible = false; handL.position.x = -0.12;
  } else { handR.visible = true; }
  renderer.render(scene, cam);

  // overlay
  let html = ''; for (const [a, b, s] of LINES) if (t >= a && t <= b + 0.4) html = s;
  subEl.innerHTML = html; subEl.style.display = (t >= 64.5) ? 'none' : 'block';
  const mm = Math.floor(t / 60); clkEl.textContent = `02:0${3 + mm} AM`;
  recEl.firstChild.style.opacity = (Math.floor(t * 1.5) % 2 === 0) ? 1 : 0.15;
  let f = 0; for (const c of CUTS) { const d = Math.abs(t - c); if (d < 0.14) f = Math.max(f, 1 - d / 0.14); }
  if (t > DUR - 0.3) f = Math.max(f, (t - (DUR - 0.3)) / 0.3);
  if (t < 0.25) f = Math.max(f, 1 - t / 0.25);
  fadeEl.style.opacity = f;
  if (t >= 64.5) {
    endEl.style.display = 'block';
    const v = t - 64.5;
    cA.style.transform = `translateX(${(1 - sm(v / 0.4)) * 900}px)`;
    cB.style.transform = `translateX(${(1 - sm((v - 0.3) / 0.4)) * 900}px)`;
  } else endEl.style.display = 'none';
  return true;
};
window.ready = true;
