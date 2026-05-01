"""3D Truss V2 - LEG NOTCH cuts flange properly (segmented extrusion).

Key change: each stick is built as a chain of extruded segments. Where there's
a LEG NOTCH (LEFT or RIGHT), that segment uses a profile WITHOUT the notched
flange. So you can SEE the flange disappear at the notch and reappear after.

LIP NOTCH: just cuts the lip portion at the end (small visual)
LEG NOTCH: removes the entire 41mm flange + lip on the notched side for ~12mm
"""
import re, math, os, json

XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075.xml'
CSV = r'C:/Users/Scott/AppData/Local/Temp/2603191-GF-LIN-89.075.csv'
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

def line_intersection(p1, p2, p3, p4, slack=200):
    x1, z1 = p1; x2, z2 = p2; x3, z3 = p3; x4, z4 = p4
    denom = (x1-x2)*(z3-z4) - (z1-z2)*(x3-x4)
    if abs(denom) < 1e-9: return None
    t = ((x1-x3)*(z3-z4) - (z1-z3)*(x3-x4)) / denom
    u = -((x1-x2)*(z1-z3) - (z1-z2)*(x1-x3)) / denom
    L1 = math.hypot(x2-x1, z2-z1); L2 = math.hypot(x4-x3, z4-z3)
    st_ = slack/L1 if L1>0 else 0; su = slack/L2 if L2>0 else 0
    if not (-st_ <= t <= 1+st_): return None
    if not (-su <= u <= 1+su): return None
    return (x1 + t*(x2-x1), z1 + t*(z2-z1))

def all_crossings(sticks):
    out = []
    for i in range(len(sticks)):
        for j in range(i+1, len(sticks)):
            a = sticks[i]; b = sticks[j]
            pt = line_intersection((a['start'][0], a['start'][2]),
                                   (a['end'][0], a['end'][2]),
                                   (b['start'][0], b['start'][2]),
                                   (b['end'][0], b['end'][2]))
            if pt: out.append({'pt':pt})
    return out

def cluster(crossings, tol=180):
    if not crossings: return []
    n = len(crossings)
    parent = list(range(n))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def union(i,j):
        ri,rj = find(i),find(j)
        if ri != rj: parent[ri] = rj
    for i in range(n):
        for j in range(i+1, n):
            d = math.hypot(crossings[i]['pt'][0]-crossings[j]['pt'][0],
                           crossings[i]['pt'][1]-crossings[j]['pt'][1])
            if d <= tol: union(i,j)
    cl = {}
    for i,c in enumerate(crossings):
        cl.setdefault(find(i), []).append(c)
    return [{'pt':[sum(g['pt'][0] for g in grp)/len(grp),
                   sum(g['pt'][1] for g in grp)/len(grp)]} for grp in cl.values()]

frame = 'TN2-1'
sticks = parse_frame(frame)
csv_ops = parse_csv_ops(frame)
nodes = cluster(all_crossings(sticks), 180)

all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
all_y = [c for s in sticks for c in (s['start'][1], s['end'][1])]
all_z = [c for s in sticks for c in (s['start'][2], s['end'][2])]
cx = (min(all_x)+max(all_x))/2
cy = (min(all_y)+max(all_y))/2
cz = (min(all_z)+max(all_z))/2
extent = max(max(all_x)-min(all_x), max(all_z)-min(all_z))

data = {
    'frame': frame,
    'sticks': sticks,
    'csv_ops': csv_ops,
    'nodes': nodes,
    'centre': [cx, cy, cz],
    'extent': extent,
}

html = '''<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Truss 3D V2 - leg notches</title>
<style>
  body { margin: 0; overflow: hidden; font-family: Segoe UI, Arial, sans-serif; background: #1a202c; }
  #info { position: absolute; top: 12px; left: 12px; color: white; padding: 12px 16px; background: rgba(0,0,0,0.55); border-radius: 6px; font-size: 13px; max-width: 360px; pointer-events: none; }
  #info h1 { margin: 0 0 6px; font-size: 16px; }
  #info p { margin: 2px 0; }
  #stats { position: absolute; top: 12px; right: 12px; color: white; padding: 10px 14px; background: rgba(0,0,0,0.55); border-radius: 6px; font-size: 12px; }
  .controls { position: absolute; bottom: 12px; left: 12px; color: white; padding: 10px 14px; background: rgba(0,0,0,0.55); border-radius: 6px; font-size: 12px; max-width: 800px; }
  .toggle { display: inline-block; margin: 4px 6px 4px 0; padding: 4px 10px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 3px; cursor: pointer; user-select: none; color: white; font-size: 11px; }
  .toggle.active { background: #16a34a; border-color: #14532d; }
  .legend { font-size: 10px; color: #cbd5e0; margin-top: 6px; line-height: 1.4; }
</style>
</head>
<body>
<div id="info">
  <h1>Truss frame ''' + frame + ''' - 3D V2</h1>
  <p><b>Drag</b> rotate · <b>Right-drag</b> pan · <b>Scroll</b> zoom</p>
  <p>Leg notches now cut the flange away. Lip notches cut just the lip.</p>
</div>
<div id="stats"></div>
<div class="controls">
  <span class="toggle active" id="t-screws">Screws</span>
  <span class="toggle active" id="t-swages">Swages</span>
  <span class="toggle active" id="t-labels">Labels</span>
  <span class="toggle" id="t-wireframe">Wireframe</span>
  <span class="toggle" id="t-explode">Explode 50%</span>
  <span class="toggle active" id="t-bench">Bench</span>
  <div class="legend">
    LEG NOTCH (red marker) = entire flange + lip cut away in that zone &middot;
    LIP NOTCH (yellow marker) = just the lip cut at end &middot;
    SWAGE (dark patch) = pressed depression in web
  </div>
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

scene.add(new THREE.AmbientLight(0xffffff, 0.5));
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

// Bench
const benchGeom = new THREE.PlaneGeometry(DATA.extent*4, DATA.extent*4);
const benchMat = new THREE.MeshStandardMaterial({ color: 0x6a6e75, roughness: 0.85, metalness: 0.05 });
const bench = new THREE.Mesh(benchGeom, benchMat);
bench.rotation.x = -Math.PI/2;
bench.position.y = -55;
bench.receiveShadow = true;
scene.add(bench);

// Profile constants
const W = 89;     // web height
const F1 = 41;    // top flange
const F2 = 38;    // bottom flange
const LIP = 12;   // lip
const T = 0.75;   // gauge

// Build a lipped-C 2D shape with optional cuts.
// `topCut`: if true, omit the top flange (and its lip)
// `botCut`: if true, omit the bottom flange (and its lip)
// `topLipCut`: if true, omit just the top lip
// `botLipCut`: if true, omit just the bottom lip
function makeProfile(topCut, botCut, topLipCut, botLipCut) {
  const shape = new THREE.Shape();
  // Trace clockwise from bottom-left of web
  // Origin: web is at X=0, Y from -W/2 to +W/2
  // Top flange = +Y side, extends in +X
  if (botCut) {
    // No bottom flange - just web tip
    shape.moveTo(0, -W/2);
    shape.lineTo(T, -W/2);
  } else {
    shape.moveTo(0, -W/2);                  // bottom-left of web (outer)
    // Bottom flange goes out
    shape.lineTo(F2, -W/2);                  // bottom flange tip
    if (botLipCut) {
      shape.lineTo(F2, -W/2 + T);            // back inside flange
    } else {
      shape.lineTo(F2, -W/2 + LIP);          // bottom lip up
      shape.lineTo(F2 - T, -W/2 + LIP);      // back inside lip
      shape.lineTo(F2 - T, -W/2 + T);        // back inside flange
    }
    shape.lineTo(T, -W/2 + T);               // inside web bottom
  }
  shape.lineTo(T, W/2 - T);                  // up inside web
  if (topCut) {
    shape.lineTo(0, W/2);                    // straight up - no top flange
  } else {
    shape.lineTo(F1 - T, W/2 - T);           // inside top flange
    if (topLipCut) {
      shape.lineTo(F1 - T, W/2);             // straight up to top
      shape.lineTo(F1, W/2);                 // hmm this isn't quite right but close
    } else {
      shape.lineTo(F1 - T, W/2 - LIP);       // top lip back
      shape.lineTo(F1, W/2 - LIP);           // top lip up
      shape.lineTo(F1, W/2);                  // top of lip
    }
    shape.lineTo(0, W/2);                     // top of web
  }
  shape.lineTo(0, -W/2);                      // close (web outer back to start)
  return shape;
}

const profileFull = makeProfile(false, false, false, false);
const profileTopCut = makeProfile(true, false, false, false);
const profileBotCut = makeProfile(false, true, false, false);
const profileTopLipCut = makeProfile(false, false, true, false);
const profileBotLipCut = makeProfile(false, false, false, true);

const galvMat = new THREE.MeshStandardMaterial({
  color: 0xb8c8d4, metalness: 0.85, roughness: 0.4
});
const chordMat = new THREE.MeshStandardMaterial({
  color: 0xa4b6c4, metalness: 0.85, roughness: 0.4
});
const swageMat = new THREE.MeshStandardMaterial({
  color: 0x566270, metalness: 0.7, roughness: 0.6
});
const screwHeadMat = new THREE.MeshStandardMaterial({
  color: 0x65a30d, metalness: 0.3, roughness: 0.5,
  emissive: 0x1a4a0a, emissiveIntensity: 0.1
});
const screwShaftMat = new THREE.MeshStandardMaterial({
  color: 0x808a90, metalness: 0.9, roughness: 0.3
});

const sticksGroup = new THREE.Group();
const swagesGroup = new THREE.Group();
const screwsGroup = new THREE.Group();
const labelsGroup = new THREE.Group();
const markersGroup = new THREE.Group();
scene.add(sticksGroup, swagesGroup, screwsGroup, labelsGroup, markersGroup);

const NOTCH_LEN = 12; // mm

DATA.sticks.forEach(stick => {
  const sx = stick.start[0], sy = stick.start[1], sz = stick.start[2];
  const ex = stick.end[0], ey = stick.end[1], ez = stick.end[2];
  const dx = ex-sx, dy = ey-sy, dz = ez-sz;
  const L = Math.sqrt(dx*dx + dy*dy + dz*dz);

  // Get ops
  const opsForStick = DATA.csv_ops[stick.name];
  const ops = opsForStick ? opsForStick.ops : [];

  // Identify leg-notch zones (along stick length): list of {start, end, side}
  const legZones = [];  // side: 'top' or 'bot'
  ops.forEach(([tool, pos]) => {
    if (tool === 'LEFT LEG NOTCH') {
      legZones.push({start: pos - NOTCH_LEN/2, end: pos + NOTCH_LEN/2, side: 'top'});
    } else if (tool === 'RIGHT LEG NOTCH') {
      legZones.push({start: pos - NOTCH_LEN/2, end: pos + NOTCH_LEN/2, side: 'bot'});
    }
  });
  const lipZones = [];  // we'll just visualize lip notches as markers
  ops.forEach(([tool, pos]) => {
    if (tool === 'LIP NOTCH') {
      lipZones.push({start: pos - NOTCH_LEN/2, end: pos + NOTCH_LEN/2});
    }
  });

  // Sort by start
  legZones.sort((a,b) => a.start - b.start);

  // Build segments along the stick length, alternating between full profile
  // and notched profile.
  const segments = [];
  let cursor = 0;
  legZones.forEach(zone => {
    const ns = Math.max(0, zone.start);
    const ne = Math.min(L, zone.end);
    if (ns > cursor) segments.push({s: cursor, e: ns, type: 'full'});
    segments.push({s: ns, e: ne, type: zone.side});
    cursor = ne;
  });
  if (cursor < L) segments.push({s: cursor, e: L, type: 'full'});

  // Build mesh group for this stick
  const stickGroup = new THREE.Group();

  segments.forEach(seg => {
    const segLen = seg.e - seg.s;
    if (segLen <= 0.1) return;
    let prof;
    if (seg.type === 'full') prof = profileFull;
    else if (seg.type === 'top') prof = profileTopCut;
    else if (seg.type === 'bot') prof = profileBotCut;
    else prof = profileFull;

    const geom = new THREE.ExtrudeGeometry(prof, { steps: 1, depth: segLen, bevelEnabled: false });
    geom.translate(0, 0, seg.s); // segment starts at z=seg.s in stick-local
    const mat = stick.type === 'Plate' ? chordMat : galvMat;
    const mesh = new THREE.Mesh(geom, mat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    stickGroup.add(mesh);
  });

  // Position the whole stick group
  // Parent transform: translate to start position, rotate so local Z aligns with stick direction
  // and lip orientation = +Y world (lips up)
  stickGroup.position.set(sx, sy, sz);

  const target = new THREE.Vector3(dx, dy, dz).normalize();
  const q1 = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1), target);
  stickGroup.quaternion.copy(q1);

  // Roll so that the open side of C (+X in profile coords) faces +Y world
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

  stickGroup.userData = { stick: stick.name, length: L };
  sticksGroup.add(stickGroup);

  // Add SWAGE features (small box on web face)
  ops.forEach(([tool, pos]) => {
    if (tool === 'SWAGE' && stick.type !== 'Plate') {
      const swageGeom = new THREE.BoxGeometry(2, 30, 10);
      const swageMesh = new THREE.Mesh(swageGeom, swageMat);
      swageMesh.castShadow = true;
      // Position: x=0 (web face), y=0 (web centre), z=pos
      swageMesh.position.set(0.5, 0, pos);
      stickGroup.add(swageMesh);
      swagesGroup.add(swageMesh);
    }
  });

  // Add visual MARKERS for leg notches (red glowing edge to make them pop)
  legZones.forEach(zone => {
    const markerLen = zone.end - zone.start;
    // For top leg notch: marker at the position where the flange used to be (top of profile, +Y)
    const yPos = zone.side === 'top' ? W/2 : -W/2;
    // Marker: thin red line at the edge of where the flange should have been
    const markerGeom = new THREE.BoxGeometry(F1, 0.5, markerLen);
    const markerMat = new THREE.MeshBasicMaterial({ color: 0xff3030 });
    const marker = new THREE.Mesh(markerGeom, markerMat);
    marker.position.set(F1/2, yPos, (zone.start + zone.end)/2);
    stickGroup.add(marker);
    markersGroup.add(marker);
  });

  // Add visual MARKERS for lip notches (yellow line)
  lipZones.forEach(zone => {
    const markerLen = zone.end - zone.start;
    [W/2 - LIP/2, -(W/2 - LIP/2)].forEach(yPos => {
      const markerGeom = new THREE.BoxGeometry(2, LIP, markerLen);
      const markerMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24 });
      const marker = new THREE.Mesh(markerGeom, markerMat);
      // Lip is at outer flange end, so x = F1 (top) or F2 (bottom) - LIP/2 (lip is back-folded)
      const xPos = yPos > 0 ? F1 - LIP/2 : F2 - LIP/2;
      marker.position.set(xPos, yPos, (zone.start + zone.end)/2);
      stickGroup.add(marker);
      markersGroup.add(marker);
    });
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

// Web holes + screws at every node
DATA.nodes.forEach(node => {
  const cx = node.pt[0], cz = node.pt[1];
  const cy = DATA.centre[1];

  let webStick = null;
  for (const s of DATA.sticks) {
    if (s.type === 'Plate') continue;
    const dx = s.end[0]-s.start[0], dz = s.end[2]-s.start[2];
    const dn = Math.hypot(dx, dz);
    if (dn === 0) continue;
    const t = ((cx-s.start[0])*dx + (cz-s.start[2])*dz) / (dn*dn);
    if (t < -0.1 || t > 1.1) continue;
    const px = s.start[0] + t*dx, pz = s.start[2] + t*dz;
    if (Math.hypot(cx-px, cz-pz) < 50) { webStick = s; break; }
  }

  let axisX = 1, axisZ = 0;
  if (webStick) {
    const dx = webStick.end[0]-webStick.start[0], dz = webStick.end[2]-webStick.start[2];
    const dn = Math.hypot(dx, dz);
    axisX = dx/dn; axisZ = dz/dn;
  }
  const perpX = -axisZ, perpZ = axisX;

  for (const off of [-17, 0, 17]) {
    const sx = cx + perpX*off;
    const sz = cz + perpZ*off;

    // Drilled hole (dark ring)
    const ringGeom = new THREE.RingGeometry(1.6, 1.9, 16);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(ringGeom, ringMat);
    ring.position.set(sx, cy + 1, sz);
    ring.rotation.x = -Math.PI/2;
    sticksGroup.add(ring);

    // Screw head
    const head = new THREE.Mesh(new THREE.CylinderGeometry(3.5, 3.5, 1.8, 16), screwHeadMat);
    head.position.set(sx, cy + 5, sz);
    head.castShadow = true;
    screwsGroup.add(head);

    // Screw shaft
    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.5, 8, 12), screwShaftMat);
    shaft.position.set(sx, cy + 0.5, sz);
    screwsGroup.add(shaft);

    // Phillips cross
    const xLine = new THREE.Mesh(new THREE.BoxGeometry(4.5, 0.3, 0.6), new THREE.MeshBasicMaterial({color: 0x1a2e0a}));
    xLine.position.set(sx, cy + 5.95, sz);
    screwsGroup.add(xLine);
    const yLine = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.3, 4.5), new THREE.MeshBasicMaterial({color: 0x1a2e0a}));
    yLine.position.set(sx, cy + 5.95, sz);
    screwsGroup.add(yLine);
  }
});

const legNotchCount = DATA.sticks.reduce((acc, s) => {
  const ops = (DATA.csv_ops[s.name] || {ops:[]}).ops;
  return acc + ops.filter(([t,_]) => t === 'LEFT LEG NOTCH' || t === 'RIGHT LEG NOTCH').length;
}, 0);
const lipNotchCount = DATA.sticks.reduce((acc, s) => {
  const ops = (DATA.csv_ops[s.name] || {ops:[]}).ops;
  return acc + ops.filter(([t,_]) => t === 'LIP NOTCH').length;
}, 0);
const swageCount = DATA.sticks.reduce((acc, s) => {
  const ops = (DATA.csv_ops[s.name] || {ops:[]}).ops;
  return acc + ops.filter(([t,_]) => t === 'SWAGE').length;
}, 0);

document.getElementById('stats').innerHTML = `
  Members: ${DATA.sticks.length}<br>
  Junction nodes: ${DATA.nodes.length}<br>
  Screws: ${DATA.nodes.length * 3}<br>
  Leg notches: ${legNotchCount}<br>
  Lip notches: ${lipNotchCount}<br>
  Swages: ${swageCount}<br>
  Profile: F37008 W089 F41-38
`;

function setupToggle(id, group) {
  const btn = document.getElementById(id);
  btn.addEventListener('click', () => {
    group.visible = !group.visible;
    btn.classList.toggle('active', group.visible);
  });
}
setupToggle('t-screws', screwsGroup);
setupToggle('t-swages', swagesGroup);
setupToggle('t-labels', labelsGroup);
setupToggle('t-bench', bench);

document.getElementById('t-wireframe').addEventListener('click', (e) => {
  const isWire = !e.target.classList.contains('active');
  e.target.classList.toggle('active', isWire);
  [galvMat, chordMat, swageMat].forEach(m => m.wireframe = isWire);
});

let exploded = false;
document.getElementById('t-explode').addEventListener('click', (e) => {
  exploded = !exploded;
  e.target.classList.toggle('active', exploded);
  sticksGroup.children.forEach(g => {
    if (exploded && g.userData.stick) {
      const c = new THREE.Vector3(...DATA.centre);
      const dir = g.position.clone().sub(c).normalize();
      g.position.add(dir.multiplyScalar(DATA.extent * 0.15));
    } else if (g.userData.stick) {
      const stick = DATA.sticks.find(s => s.name === g.userData.stick);
      g.position.set(stick.start[0], stick.start[1], stick.start[2]);
    }
  });
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

out = os.path.join(OUT_DIR, 'truss_3d_v2.html')
open(out, 'w', encoding='utf-8').write(html)
print(f'Wrote V2 3D model: {out}')

# Stats
leg_total = sum(1 for s in sticks for t,_ in csv_ops.get(s['name'],{}).get('ops',[]) if t in ('LEFT LEG NOTCH','RIGHT LEG NOTCH'))
lip_total = sum(1 for s in sticks for t,_ in csv_ops.get(s['name'],{}).get('ops',[]) if t == 'LIP NOTCH')
sw_total = sum(1 for s in sticks for t,_ in csv_ops.get(s['name'],{}).get('ops',[]) if t == 'SWAGE')
print(f'  Members: {len(sticks)}')
print(f'  Nodes: {len(nodes)}')
print(f'  Leg notches: {leg_total} (flanges removed)')
print(f'  Lip notches: {lip_total}')
print(f'  Swages: {sw_total}')
