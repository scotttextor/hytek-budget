"""3D Truss V5 - Tooling rules only (no fasteners).

Focus on getting the NON-FASTENER tools correctly rendered:
  - SWAGE: rectangular pressed depression on web (10mm long x 30mm tall, transverse)
  - LIP NOTCH: small cut into the LIP only at end of web (12mm long x 12mm tall lip)
  - LEFT LEG NOTCH: top flange + lip removed for 12mm zone (segmented profile)
  - RIGHT LEG NOTCH: bottom flange + lip removed for 12mm zone (segmented profile)
  - WEB NOTCH: rectangular cut into web edge (when present)

All from real CSV positions. No bolts, no screws, no web holes.
"""
import re, math, os, json

XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075 (1).xml'
# Source of truth — Scott's authoritative CSV on Desktop
CSV = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.csv'
OUT_DIR = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/'

text = open(XML).read()

def parse_frame(name):
    s = text.find(f'<frame name="{name}"')
    if s < 0: return None
    e = text.find('</frame>', s) + len('</frame>')
    f = text[s:e]
    sticks = []
    for m in re.finditer(r'<stick name="([^"]+)" type="([^"]+)"[^>]*>\s*<start>([^<]+)</start>\s*<end>([^<]+)</end>', f):
        nm, typ, st, en = m.groups()
        sx,sy,sz = [float(v) for v in st.strip().split(',')]
        ex,ey,ez = [float(v) for v in en.strip().split(',')]
        sticks.append({'name':nm,'type':typ,'start':[sx,sy,sz],'end':[ex,ey,ez]})
    return sticks

def parse_csv_ops(frame_name):
    out = {}
    with open(CSV) as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) < 14 or parts[0] != 'COMPONENT': continue
            full = parts[1]
            if not full.startswith(frame_name + '-'): continue
            short = full[len(frame_name)+1:]
            length = float(parts[7])
            ops_raw = parts[13:]
            ops = []
            i = 0
            while i+1 < len(ops_raw):
                tool = ops_raw[i]
                try:
                    pos = float(ops_raw[i+1])
                    ops.append([tool, pos])
                except:
                    pass
                i += 2
            out[short] = {'length':length, 'ops':ops}
    return out

frame = 'TN2-1'
sticks = parse_frame(frame)
csv_ops = parse_csv_ops(frame)

all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
all_y = [c for s in sticks for c in (s['start'][1], s['end'][1])]
all_z = [c for s in sticks for c in (s['start'][2], s['end'][2])]
cx = (min(all_x)+max(all_x))/2
cy = (min(all_y)+max(all_y))/2
cz = (min(all_z)+max(all_z))/2
extent = max(max(all_x)-min(all_x), max(all_z)-min(all_z))

# Tool inventory for stats
tool_counts = {}
for s in sticks:
    ops = csv_ops.get(s['name'], {}).get('ops', [])
    for tool, _ in ops:
        tool_counts[tool] = tool_counts.get(tool, 0) + 1

data = {
    'frame': frame,
    'sticks': sticks,
    'csv_ops': csv_ops,
    'centre': [cx, cy, cz],
    'extent': extent,
    'tool_counts': tool_counts,
}

html = '''<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Truss 3D V5 - Tooling rules</title>
<style>
  body { margin: 0; overflow: hidden; font-family: Segoe UI, Arial, sans-serif; background: #1a202c; }
  #info { position: absolute; top: 12px; left: 12px; color: white; padding: 12px 16px; background: rgba(0,0,0,0.65); border-radius: 6px; font-size: 13px; max-width: 420px; pointer-events: none; }
  #info h1 { margin: 0 0 6px; font-size: 16px; }
  #info p { margin: 2px 0; }
  .swage { color: #c084fc; }
  .lip { color: #fbbf24; }
  .leg { color: #f87171; }
  #stats { position: absolute; top: 12px; right: 12px; color: white; padding: 10px 14px; background: rgba(0,0,0,0.65); border-radius: 6px; font-size: 12px; min-width: 220px; }
  .controls { position: absolute; bottom: 12px; left: 12px; color: white; padding: 10px 14px; background: rgba(0,0,0,0.65); border-radius: 6px; font-size: 12px; max-width: 800px; }
  .toggle { display: inline-block; margin: 4px 6px 4px 0; padding: 4px 10px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 3px; cursor: pointer; user-select: none; color: white; font-size: 11px; }
  .toggle.active { background: #16a34a; border-color: #14532d; }
  .swage-tog.active { background: #9333ea; border-color: #6b21a8; }
  .lip-tog.active { background: #d97706; border-color: #92400e; }
  .leg-tog.active { background: #dc2626; border-color: #7f1d1d; }
</style>
</head>
<body>
<div id="info">
  <h1>Truss frame ''' + frame + ''' - V5 Tooling rules</h1>
  <p><b>Drag</b> rotate · <b>Scroll</b> zoom · No fasteners shown</p>
  <p><span class="swage">SWAGE</span> = pressed depression on web (~10×30mm, transverse)</p>
  <p><span class="lip">LIP NOTCH</span> = cut into lip only at end of web (~12mm)</p>
  <p><span class="leg">LEG NOTCH</span> = entire flange+lip removed for 12mm zone</p>
  <p style="color:#06b6d4">INNER DIMPLE = Ø5.1mm raised bump pressed into web</p>
</div>
<div id="stats"></div>
<div class="controls">
  <span class="toggle active swage-tog" id="t-swages">Swages</span>
  <span class="toggle active lip-tog" id="t-lipnotches">Lip notches</span>
  <span class="toggle active leg-tog" id="t-legmarkers">Leg notch markers</span>
  <span class="toggle active" id="t-dimples">Inner dimples</span>
  <span class="toggle active" id="t-labels">Labels</span>
  <span class="toggle" id="t-wireframe">Wireframe</span>
  <span class="toggle active" id="t-bench">Bench</span>
</div>

<script type="importmap">
{
  "imports": {
    "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
    "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
  }
}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const DATA = ''' + json.dumps(data) + ''';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x2a2f37);

const camera = new THREE.PerspectiveCamera(50, window.innerWidth/window.innerHeight, 1, DATA.extent*8);
camera.position.set(DATA.centre[0] + DATA.extent*0.7, DATA.centre[1] + DATA.extent*0.5, DATA.centre[2] + DATA.extent*0.7);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.target.set(...DATA.centre);

scene.add(new THREE.AmbientLight(0xffffff, 0.55));
const sun = new THREE.DirectionalLight(0xffffff, 0.85);
sun.position.set(DATA.centre[0]+DATA.extent, DATA.centre[1]+DATA.extent*1.2, DATA.centre[2]+DATA.extent*0.8);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -DATA.extent;
sun.shadow.camera.right = DATA.extent;
sun.shadow.camera.top = DATA.extent;
sun.shadow.camera.bottom = -DATA.extent;
sun.shadow.camera.far = DATA.extent*4;
scene.add(sun);
scene.add(new THREE.DirectionalLight(0xa8c0d0, 0.3).translateX(-DATA.extent).translateY(DATA.extent*0.5));

const benchGeom = new THREE.PlaneGeometry(DATA.extent*4, DATA.extent*4);
const benchMat = new THREE.MeshStandardMaterial({ color: 0x6a6e75, roughness: 0.85, metalness: 0.05 });
const bench = new THREE.Mesh(benchGeom, benchMat);
bench.rotation.x = -Math.PI/2;
bench.position.y = -55;
bench.receiveShadow = true;
scene.add(bench);

// Profile constants
const W = 89, F1 = 41, F2 = 38, LIP = 12, T = 0.75;

function makeProfile(topCut, botCut, topLipCut, botLipCut) {
  const shape = new THREE.Shape();
  if (botCut) {
    shape.moveTo(0, -W/2);
    shape.lineTo(T, -W/2);
  } else {
    shape.moveTo(0, -W/2);
    shape.lineTo(F2, -W/2);
    if (botLipCut) {
      shape.lineTo(F2, -W/2 + T);
    } else {
      shape.lineTo(F2, -W/2 + LIP);
      shape.lineTo(F2 - T, -W/2 + LIP);
      shape.lineTo(F2 - T, -W/2 + T);
    }
    shape.lineTo(T, -W/2 + T);
  }
  shape.lineTo(T, W/2 - T);
  if (topCut) {
    shape.lineTo(0, W/2);
  } else {
    shape.lineTo(F1 - T, W/2 - T);
    if (topLipCut) {
      shape.lineTo(F1 - T, W/2);
      shape.lineTo(F1, W/2);
    } else {
      shape.lineTo(F1 - T, W/2 - LIP);
      shape.lineTo(F1, W/2 - LIP);
      shape.lineTo(F1, W/2);
    }
    shape.lineTo(0, W/2);
  }
  shape.lineTo(0, -W/2);
  return shape;
}

const profileFull       = makeProfile(false, false, false, false);
const profileTopCut     = makeProfile(true,  false, false, false);
const profileBotCut     = makeProfile(false, true,  false, false);
const profileTopLipCut  = makeProfile(false, false, true,  false);
const profileBotLipCut  = makeProfile(false, false, false, true);
const profileBothLipCut = makeProfile(false, false, true,  true);

const galvMat = new THREE.MeshStandardMaterial({ color: 0xb8c8d4, metalness: 0.85, roughness: 0.4 });
const chordMat = new THREE.MeshStandardMaterial({ color: 0xa4b6c4, metalness: 0.85, roughness: 0.4 });
const swageMat = new THREE.MeshStandardMaterial({ color: 0x9333ea, metalness: 0.5, roughness: 0.5,
  emissive: 0x4c1d95, emissiveIntensity: 0.2 });
const legMarkerMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
const lipMarkerMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24 });
const dimpleMat = new THREE.MeshStandardMaterial({
  color: 0x06b6d4, metalness: 0.5, roughness: 0.4,
  emissive: 0x0e7490, emissiveIntensity: 0.3
});

const sticksGroup = new THREE.Group();
const swagesGroup = new THREE.Group();
const lipMarkersGroup = new THREE.Group();
const legMarkersGroup = new THREE.Group();
const dimpleGroup = new THREE.Group();
const labelsGroup = new THREE.Group();
scene.add(sticksGroup, swagesGroup, lipMarkersGroup, legMarkersGroup, dimpleGroup, labelsGroup);

const NOTCH_LEN = 12;
const LIPNOTCH_LEN = 12;

DATA.sticks.forEach(stick => {
  const sx = stick.start[0], sy = stick.start[1], sz = stick.start[2];
  const ex = stick.end[0], ey = stick.end[1], ez = stick.end[2];
  const dx = ex-sx, dy = ey-sy, dz = ez-sz;
  const L = Math.sqrt(dx*dx + dy*dy + dz*dz);

  const opsForStick = DATA.csv_ops[stick.name];
  const ops = opsForStick ? opsForStick.ops : [];

  // Collect notch zones (LEG = full flange cut, LIP = lip-only cut)
  const zones = [];
  ops.forEach(([tool, pos]) => {
    if (tool === 'LEFT LEG NOTCH') zones.push({start: pos - NOTCH_LEN/2, end: pos + NOTCH_LEN/2, kind: 'leg-top'});
    else if (tool === 'RIGHT LEG NOTCH') zones.push({start: pos - NOTCH_LEN/2, end: pos + NOTCH_LEN/2, kind: 'leg-bot'});
    else if (tool === 'LIP NOTCH') zones.push({start: pos - LIPNOTCH_LEN/2, end: pos + LIPNOTCH_LEN/2, kind: 'lip-both'});
  });
  zones.sort((a,b) => a.start - b.start);

  // Build segmented stick
  const segments = [];
  let cursor = 0;
  zones.forEach(z => {
    const ns = Math.max(0, z.start);
    const ne = Math.min(L, z.end);
    if (ns > cursor) segments.push({s: cursor, e: ns, type: 'full'});
    segments.push({s: ns, e: ne, type: z.kind});
    cursor = ne;
  });
  if (cursor < L) segments.push({s: cursor, e: L, type: 'full'});

  const stickGroup = new THREE.Group();
  segments.forEach(seg => {
    const segLen = seg.e - seg.s;
    if (segLen <= 0.1) return;
    let prof;
    if (seg.type === 'full') prof = profileFull;
    else if (seg.type === 'leg-top') prof = profileTopCut;
    else if (seg.type === 'leg-bot') prof = profileBotCut;
    else if (seg.type === 'lip-both') prof = profileBothLipCut;
    else prof = profileFull;
    const geom = new THREE.ExtrudeGeometry(prof, { steps: 1, depth: segLen, bevelEnabled: false });
    geom.translate(0, 0, seg.s);
    const mat = stick.type === 'Plate' ? chordMat : galvMat;
    const mesh = new THREE.Mesh(geom, mat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    stickGroup.add(mesh);
  });

  stickGroup.position.set(sx, sy, sz);
  const target = new THREE.Vector3(dx, dy, dz).normalize();
  const q1 = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1), target);
  stickGroup.quaternion.copy(q1);

  // Roll so open-side faces +Y world
  const stickAxis = target.clone();
  const openWorld = new THREE.Vector3(1,0,0).applyQuaternion(q1);
  const desired = new THREE.Vector3(0,1,0);
  const op = openWorld.clone().sub(stickAxis.clone().multiplyScalar(openWorld.dot(stickAxis))).normalize();
  const dp = desired.clone().sub(stickAxis.clone().multiplyScalar(desired.dot(stickAxis))).normalize();
  if (dp.lengthSq() > 0.01) {
    const angle = Math.acos(Math.max(-1, Math.min(1, op.dot(dp))));
    const cross = new THREE.Vector3().crossVectors(op, dp);
    const sign = cross.dot(stickAxis) > 0 ? 1 : -1;
    const roll = new THREE.Quaternion().setFromAxisAngle(stickAxis, angle * sign);
    stickGroup.quaternion.premultiply(roll);
  }

  stickGroup.userData = { stick: stick.name };
  sticksGroup.add(stickGroup);

  // SWAGE features (purple pressed rectangles)
  ops.forEach(([tool, pos]) => {
    if (tool === 'SWAGE' && stick.type !== 'Plate') {
      // Box: 10mm long along stick × 30mm tall (cross-web) × 1.5mm "deep"
      const swageGeom = new THREE.BoxGeometry(1.5, 30, 10);
      const swageMesh = new THREE.Mesh(swageGeom, swageMat);
      swageMesh.castShadow = true;
      // Sit on web face (web is at x=0 in profile coords, slightly offset toward open side)
      swageMesh.position.set(0.5, 0, pos);
      stickGroup.add(swageMesh);
      swagesGroup.add(swageMesh);
    }
  });

  // INNER DIMPLE features (cyan raised bumps on web - Ø5.1mm pressed dimples)
  ops.forEach(([tool, pos]) => {
    if (tool === 'INNER DIMPLE') {
      // Small cyan sphere/bump on the web face
      const dimpleGeom = new THREE.SphereGeometry(2.55, 12, 8, 0, Math.PI*2, 0, Math.PI/2);
      const dimpleMesh = new THREE.Mesh(dimpleGeom, dimpleMat);
      dimpleMesh.castShadow = true;
      // On web face, raised toward open side (+x in profile)
      dimpleMesh.position.set(1.5, 0, pos);
      dimpleMesh.rotation.x = -Math.PI/2;
      stickGroup.add(dimpleMesh);
      dimpleGroup.add(dimpleMesh);
    }
  });

  // LIP NOTCH visual markers (yellow boxes on the lip strips)
  ops.forEach(([tool, pos]) => {
    if (tool === 'LIP NOTCH') {
      // Top lip: at y=W/2 - LIP/2, x=F1 - LIP/2 (inside the lip strip)
      const lipGeomTop = new THREE.BoxGeometry(LIP * 0.8, LIP * 1.1, LIPNOTCH_LEN * 1.05);
      const topMarker = new THREE.Mesh(lipGeomTop, lipMarkerMat);
      topMarker.position.set(F1 - LIP/2, W/2 - LIP/2, pos);
      stickGroup.add(topMarker);
      lipMarkersGroup.add(topMarker);
      // Bottom lip
      const botMarker = new THREE.Mesh(lipGeomTop, lipMarkerMat);
      botMarker.position.set(F2 - LIP/2, -(W/2 - LIP/2), pos);
      stickGroup.add(botMarker);
      lipMarkersGroup.add(botMarker);
    }
  });

  // LEG NOTCH visual markers (red lines where flange used to be)
  ops.forEach(([tool, pos]) => {
    const isLeftLeg = tool === 'LEFT LEG NOTCH';
    const isRightLeg = tool === 'RIGHT LEG NOTCH';
    if (!(isLeftLeg || isRightLeg)) return;
    // Marker: red box at the missing-flange position
    const yPos = isLeftLeg ? W/2 + 1 : -(W/2 + 1);
    const xPos = isLeftLeg ? F1/2 : F2/2;
    const markerGeom = new THREE.BoxGeometry(isLeftLeg ? F1 : F2, 1.5, NOTCH_LEN);
    const marker = new THREE.Mesh(markerGeom, legMarkerMat);
    marker.position.set(xPos, yPos, pos);
    stickGroup.add(marker);
    legMarkersGroup.add(marker);
  });

  // Label
  const canvas = document.createElement('canvas');
  canvas.width = 256; canvas.height = 64;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = 'rgba(255,255,255,0.95)';
  ctx.fillRect(0,0,256,64);
  ctx.fillStyle = '#1a202c';
  ctx.font = 'bold 38px Segoe UI, Arial';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(stick.name, 128, 32);
  const tex = new THREE.CanvasTexture(canvas);
  const labelMat = new THREE.SpriteMaterial({ map: tex, transparent: true });
  const label = new THREE.Sprite(labelMat);
  label.position.set((sx+ex)/2, (sy+ey)/2 + 70, (sz+ez)/2);
  label.scale.set(180, 45, 1);
  labelsGroup.add(label);
});

// Stats
const tc = DATA.tool_counts;
let statsHtml = `Members: ${DATA.sticks.length}<br>`;
statsHtml += `<hr style="border-color:#4a5568;margin:6px 0">`;
statsHtml += `<b style="color:#c084fc">SWAGE: ${tc.SWAGE || 0}</b><br>`;
statsHtml += `<b style="color:#fbbf24">LIP NOTCH: ${tc['LIP NOTCH'] || 0}</b><br>`;
statsHtml += `<b style="color:#f87171">LEFT LEG NOTCH: ${tc['LEFT LEG NOTCH'] || 0}</b><br>`;
statsHtml += `<b style="color:#f87171">RIGHT LEG NOTCH: ${tc['RIGHT LEG NOTCH'] || 0}</b><br>`;
statsHtml += `<b style="color:#06b6d4">INNER DIMPLE: ${tc['INNER DIMPLE'] || 0}</b><br>`;
const otherTools = Object.keys(tc).filter(k => !['SWAGE','LIP NOTCH','LEFT LEG NOTCH','RIGHT LEG NOTCH','BOLT HOLES','INNER DIMPLE'].includes(k));
otherTools.forEach(k => { statsHtml += `${k}: ${tc[k]}<br>`; });
statsHtml += `<hr style="border-color:#4a5568;margin:6px 0">`;
statsHtml += `<span style="font-size:10px;color:#a8b9c7">Profile: F37008 W089 F41-38<br>Fasteners hidden</span>`;
document.getElementById('stats').innerHTML = statsHtml;

function setupToggle(id, group) {
  const btn = document.getElementById(id);
  btn.addEventListener('click', () => {
    group.visible = !group.visible;
    btn.classList.toggle('active', group.visible);
  });
}
setupToggle('t-swages', swagesGroup);
setupToggle('t-lipnotches', lipMarkersGroup);
setupToggle('t-legmarkers', legMarkersGroup);
setupToggle('t-dimples', dimpleGroup);
setupToggle('t-labels', labelsGroup);
setupToggle('t-bench', bench);

document.getElementById('t-wireframe').addEventListener('click', (e) => {
  const isWire = !e.target.classList.contains('active');
  e.target.classList.toggle('active', isWire);
  [galvMat, chordMat].forEach(m => m.wireframe = isWire);
});

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
</script>
</body></html>'''

out = os.path.join(OUT_DIR, 'truss_3d_v5.html')
open(out, 'w', encoding='utf-8').write(html)
print(f'Wrote V5: {out}')
print('Tool counts (TN2-1):')
for k, v in tool_counts.items():
    print(f'  {k}: {v}')
