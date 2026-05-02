"""3D Truss V6 - Simplified-CSV view with 3-hole WEB HOLE clusters.

Renders the SIMPLIFIED CSV by default (centreline-intersection bolt pattern).
Each "BOLT HOLES" position on a Linear-truss stick becomes a 3-hole cluster:
  - 3 small dark cylinders (Ø3.8mm) at 17mm pitch
  - Pitch direction = perpendicular to that stick's own length, on the web face
  - Middle hole sits exactly on the centreline at the local position

Toggle "Show original ops" hides the simplified WEB HOLES and shows the
ORIGINAL CSV's BOLT HOLES (smaller red holes) so the user can flip between
old and new layouts.

Frame selector dropdown lets the user switch between all 22 frames in the XML.
Default to TN2-1.

Reuses V5's profile geometry, lipped-C extrusion, leg-notch segmenting, and
all toggles. Adds a stat counter showing original-vs-simplified hole counts.
"""
import re, math, os, json

XML  = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075 (1).xml'
CSV_ORIG = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.csv'
CSV_SIMP = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.simplified.csv'
OUT_DIR  = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/'

text = open(XML).read()


# ---------- XML parse: pull stick geometry per frame ----------

def parse_all_frames():
    """Return {frame_name: [stick_dicts]} for every <frame> in the XML."""
    out = {}
    for fm in re.finditer(r'<frame name="([^"]+)" type="([^"]+)"[^>]*>(.*?)</frame>', text, re.DOTALL):
        fname, ftype, body = fm.groups()
        sticks = []
        for sm in re.finditer(
            r'<stick\s+([^>]*?)>\s*<start>([^<]+)</start>\s*<end>([^<]+)</end>',
            body
        ):
            attrs, st, en = sm.groups()
            def ga(s, k):
                m = re.search(rf'\b{k}="([^"]*)"', s)
                return m.group(1) if m else ''
            name = ga(attrs, 'name')
            typ  = ga(attrs, 'type')
            sx,sy,sz = [float(v) for v in st.strip().split(',')]
            ex,ey,ez = [float(v) for v in en.strip().split(',')]
            sticks.append({
                'name': name, 'type': typ,
                'start':[sx,sy,sz], 'end':[ex,ey,ez]
            })
        if sticks:
            out[fname] = {'type': ftype, 'sticks': sticks}
    return out


# ---------- CSV parse: per frame ops, with length to enable B1->B2 mapping ----------

def parse_csv_ops_all(csv_path):
    """Return {frame: {csv_short_name: {length, ops:[(tool,pos)...]}}}."""
    out = {}
    with open(csv_path) as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) < 14 or parts[0] != 'COMPONENT':
                continue
            full = parts[1]
            # Frame name = everything up to the FIRST hyphen (e.g. TN2-1-W5 -> TN2-1)
            mfx = re.match(r'^([A-Z]+\d+(?:-\d+)?)-(.+)$', full)
            if not mfx:
                continue
            frame_name = mfx.group(1)
            short = mfx.group(2)
            try:
                length = float(parts[7])
            except ValueError:
                continue
            ops_raw = parts[13:]
            ops = []
            i = 0
            while i+1 < len(ops_raw):
                tool = ops_raw[i]
                try:
                    pos = float(ops_raw[i+1])
                    ops.append([tool, pos])
                except ValueError:
                    pass
                i += 2
            out.setdefault(frame_name, {})[short] = {'length': length, 'ops': ops}
    return out


# ---------- CSV-name -> XML-stick-name length-matching (handles B1 (Box1) -> B2) ----------

def build_csv_to_xml_map(sticks, csv_for_frame):
    """For each CSV component name in this frame, decide which XML stick it
    represents. CSV may have 'B1 (Box1)' that actually maps to XML stick 'B2'.
    Match by base name + length first, then by length only."""
    def stick_len(s):
        return math.hypot(s['end'][0]-s['start'][0], s['end'][2]-s['start'][2])
    used = [False]*len(sticks)
    mapping = {}  # csv_short -> xml_name
    items = list(csv_for_frame.items())
    # Pass 1: exact base-name AND length match
    for short, info in items:
        base = re.sub(r'\s*\(Box\d+\)\s*$', '', short).strip()
        for i, s in enumerate(sticks):
            if used[i]: continue
            if s['name'] == base and abs(stick_len(s) - info['length']) < 1.0:
                used[i] = True
                mapping[short] = s['name']
                break
    # Pass 2: closest length only (within 5mm) for unmatched CSV rows
    for short, info in items:
        if short in mapping: continue
        best_idx, best_diff = None, 5.0
        for i, s in enumerate(sticks):
            if used[i]: continue
            d = abs(stick_len(s) - info['length'])
            if d < best_diff:
                best_diff = d; best_idx = i
        if best_idx is not None:
            used[best_idx] = True
            mapping[short] = sticks[best_idx]['name']
    return mapping


# ---------- Build per-frame data bundle for the JS ----------

frames_xml = parse_all_frames()
csv_orig_all = parse_csv_ops_all(CSV_ORIG)
csv_simp_all = parse_csv_ops_all(CSV_SIMP)

frame_names = sorted(frames_xml.keys())

frame_bundles = {}
for fname in frame_names:
    sticks = frames_xml[fname]['sticks']
    csv_orig = csv_orig_all.get(fname, {})
    csv_simp = csv_simp_all.get(fname, {})

    # Map CSV rows to XML stick names
    map_orig = build_csv_to_xml_map(sticks, csv_orig)
    map_simp = build_csv_to_xml_map(sticks, csv_simp)

    # Per XML stick: ops, then split ORIGINAL bolts vs SIMPLIFIED bolts
    ops_by_xml_orig = {s['name']: [] for s in sticks}
    ops_by_xml_simp = {s['name']: [] for s in sticks}
    for short, info in csv_orig.items():
        xn = map_orig.get(short)
        if xn: ops_by_xml_orig[xn] = info['ops']
    for short, info in csv_simp.items():
        xn = map_simp.get(short)
        if xn: ops_by_xml_simp[xn] = info['ops']

    # Geometry centre/extent
    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_y = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    all_z = [c for s in sticks for c in (s['start'][2], s['end'][2])]
    cx = (min(all_x)+max(all_x))/2
    cy = (min(all_y)+max(all_y))/2
    cz = (min(all_z)+max(all_z))/2
    extent = max(max(all_x)-min(all_x), max(all_z)-min(all_z), 100.0)

    # Tool counters
    orig_bolt = sum(1 for n in ops_by_xml_orig for t,_ in ops_by_xml_orig[n] if t == 'BOLT HOLES')
    simp_bolt = sum(1 for n in ops_by_xml_simp for t,_ in ops_by_xml_simp[n] if t == 'BOLT HOLES')

    frame_bundles[fname] = {
        'sticks': sticks,
        'ops_orig': ops_by_xml_orig,
        'ops_simp': ops_by_xml_simp,
        'centre': [cx, cy, cz],
        'extent': extent,
        'orig_bolt_count': orig_bolt,
        'simp_bolt_count': simp_bolt,
    }

default_frame = 'TN2-1' if 'TN2-1' in frame_bundles else frame_names[0]

data = {
    'frames': frame_bundles,
    'frame_names': frame_names,
    'default_frame': default_frame,
}

html = '''<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Truss 3D V6 - Simplified centreline holes</title>
<style>
  body { margin: 0; overflow: hidden; font-family: Segoe UI, Arial, sans-serif; background: #1a202c; }
  #info { position: absolute; top: 12px; left: 12px; color: white; padding: 12px 16px; background: rgba(0,0,0,0.65); border-radius: 6px; font-size: 13px; max-width: 460px; pointer-events: none; }
  #info h1 { margin: 0 0 6px; font-size: 16px; }
  #info p { margin: 2px 0; }
  .swage { color: #c084fc; }
  .lip { color: #fbbf24; }
  .leg { color: #f87171; }
  .web { color: #34d399; }
  .orig { color: #f87171; }
  #stats { position: absolute; top: 12px; right: 12px; color: white; padding: 10px 14px; background: rgba(0,0,0,0.65); border-radius: 6px; font-size: 12px; min-width: 240px; }
  .controls { position: absolute; bottom: 12px; left: 12px; color: white; padding: 10px 14px; background: rgba(0,0,0,0.65); border-radius: 6px; font-size: 12px; max-width: 900px; }
  .toggle { display: inline-block; margin: 4px 6px 4px 0; padding: 4px 10px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 3px; cursor: pointer; user-select: none; color: white; font-size: 11px; }
  .toggle.active { background: #16a34a; border-color: #14532d; }
  .swage-tog.active { background: #9333ea; border-color: #6b21a8; }
  .lip-tog.active   { background: #d97706; border-color: #92400e; }
  .leg-tog.active   { background: #dc2626; border-color: #7f1d1d; }
  .orig-tog.active  { background: #b91c1c; border-color: #7f1d1d; }
  .web-tog.active   { background: #065f46; border-color: #064e3b; }
  #frame-bar { position: absolute; top: 12px; left: 50%; transform: translateX(-50%); padding: 8px 14px; background: rgba(0,0,0,0.7); border-radius: 6px; color: white; font-size: 13px; }
  #frame-bar select { background: #2d3748; color: white; border: 1px solid #4a5568; border-radius: 4px; padding: 4px 8px; font-size: 13px; margin-left: 8px; }
</style>
</head>
<body>
<div id="info">
  <h1>Truss 3D V6 - centreline-intersection bolts</h1>
  <p><b>Drag</b> rotate &middot; <b>Scroll</b> zoom &middot; <b>Right-drag</b> pan</p>
  <p><span class="web">WEB HOLES</span> = simplified 3-hole cluster (Ø3.8 @ 17mm pitch) on each stick at every centreline crossing</p>
  <p><span class="orig">Original BOLT HOLES</span> = FrameCAD's per-stick bolt pattern (toggle to compare)</p>
  <p><span class="swage">SWAGE</span> &middot; <span class="lip">LIP NOTCH</span> &middot; <span class="leg">LEG NOTCH</span> &middot; cyan = INNER DIMPLE</p>
</div>
<div id="frame-bar">
  Frame: <select id="frame-select"></select>
</div>
<div id="stats"></div>
<div class="controls">
  <span class="toggle active web-tog"  id="t-webholes">Simplified web holes</span>
  <span class="toggle orig-tog"        id="t-orig">Show original ops</span>
  <span class="toggle active swage-tog" id="t-swages">Swages</span>
  <span class="toggle active lip-tog"   id="t-lipnotches">Lip notches</span>
  <span class="toggle active leg-tog"   id="t-legmarkers">Leg notches</span>
  <span class="toggle active"           id="t-dimples">Inner dimples</span>
  <span class="toggle active"           id="t-labels">Labels</span>
  <span class="toggle"                  id="t-wireframe">Wireframe</span>
  <span class="toggle active"           id="t-bench">Bench</span>
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

// ---------- Three.js scene scaffolding ----------
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x2a2f37);

const camera = new THREE.PerspectiveCamera(50, window.innerWidth/window.innerHeight, 1, 1e7);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;

const ambient = new THREE.AmbientLight(0xffffff, 0.55);
scene.add(ambient);
const sun = new THREE.DirectionalLight(0xffffff, 0.85);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
scene.add(sun);
const fill = new THREE.DirectionalLight(0xa8c0d0, 0.3);
scene.add(fill);

const benchMat = new THREE.MeshStandardMaterial({ color: 0x6a6e75, roughness: 0.85, metalness: 0.05 });
const bench = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), benchMat);
bench.rotation.x = -Math.PI/2;
bench.receiveShadow = true;
scene.add(bench);

// ---------- Profile constants & shapes (V5-identical) ----------
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
const profileBothLipCut = makeProfile(false, false, true,  true);

const galvMat   = new THREE.MeshStandardMaterial({ color: 0xb8c8d4, metalness: 0.85, roughness: 0.4 });
const chordMat  = new THREE.MeshStandardMaterial({ color: 0xa4b6c4, metalness: 0.85, roughness: 0.4 });
const swageMat  = new THREE.MeshStandardMaterial({ color: 0x9333ea, metalness: 0.5, roughness: 0.5,
  emissive: 0x4c1d95, emissiveIntensity: 0.2 });
const legMarkerMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
const lipMarkerMat = new THREE.MeshBasicMaterial({ color: 0xfbbf24 });
const dimpleMat = new THREE.MeshStandardMaterial({
  color: 0x06b6d4, metalness: 0.5, roughness: 0.4,
  emissive: 0x0e7490, emissiveIntensity: 0.3
});
// New-rule WEB HOLES = small dark green dots on the web face
const webHoleMat = new THREE.MeshStandardMaterial({
  color: 0x111827, metalness: 0.2, roughness: 0.6,
  emissive: 0x0f766e, emissiveIntensity: 0.4
});
// Original BOLT HOLES = small red dots
const origHoleMat = new THREE.MeshStandardMaterial({
  color: 0x7f1d1d, metalness: 0.2, roughness: 0.6,
  emissive: 0xb91c1c, emissiveIntensity: 0.4
});

// ---------- Group containers (rebuilt on every frame switch) ----------
let sticksGroup, swagesGroup, lipMarkersGroup, legMarkersGroup, dimpleGroup, labelsGroup;
let webHolesGroup, origHolesGroup;
let allRootGroups = [];

const NOTCH_LEN = 12;
const LIPNOTCH_LEN = 12;
const HOLE_PITCH = 17;        // mm between adjacent holes in the 3-hole cluster
const HOLE_DIA = 3.8;         // hole Ø
const ORIG_HOLE_DIA = 2.6;    // smaller red dot for original ops

// Build a single 3-hole cluster (centred on a stick local position).
// Reused for WEB HOLES; for ORIG just one hole at the position.
function makeWebCluster(material, pitch, count, dia, depth) {
  const grp = new THREE.Group();
  const r = dia / 2;
  // We render each hole as a short cylinder whose AXIS is along world-X
  // (perpendicular to the web in profile coords, i.e. into the steel).
  // The pitch direction is along world-Y (across the web from flange to flange).
  for (let i = 0; i < count; i++) {
    const offsetY = (i - (count-1)/2) * pitch;
    const cyl = new THREE.CylinderGeometry(r, r, depth, 16);
    // Rotate so axis points along +X (the cylinder default axis is +Y).
    cyl.rotateZ(Math.PI / 2);
    const mesh = new THREE.Mesh(cyl, material);
    mesh.position.set(depth/2 + 0.05, offsetY, 0);  // sit just proud of web face
    mesh.castShadow = false;
    grp.add(mesh);
  }
  return grp;
}

// ---------- Build the scene for a given frame name ----------
function buildFrame(frameName) {
  // Tear down previous groups
  allRootGroups.forEach(g => scene.remove(g));
  allRootGroups = [];

  const F = DATA.frames[frameName];
  const centre = F.centre;
  const extent = F.extent;

  // Camera + lighting positioned for this frame
  camera.position.set(centre[0] + extent*0.7, centre[1] + extent*0.5, centre[2] + extent*0.7);
  camera.far = extent * 8;
  camera.updateProjectionMatrix();
  controls.target.set(centre[0], centre[1], centre[2]);
  sun.position.set(centre[0]+extent, centre[1]+extent*1.2, centre[2]+extent*0.8);
  sun.shadow.camera.left = -extent;
  sun.shadow.camera.right = extent;
  sun.shadow.camera.top = extent;
  sun.shadow.camera.bottom = -extent;
  sun.shadow.camera.far = extent*4;
  sun.shadow.camera.updateProjectionMatrix();
  fill.position.set(centre[0]-extent, centre[1]+extent*0.5, centre[2]);

  // Bench
  bench.geometry.dispose();
  bench.geometry = new THREE.PlaneGeometry(extent*4, extent*4);
  bench.position.set(centre[0], -55, centre[2]);

  sticksGroup     = new THREE.Group();
  swagesGroup     = new THREE.Group();
  lipMarkersGroup = new THREE.Group();
  legMarkersGroup = new THREE.Group();
  dimpleGroup     = new THREE.Group();
  labelsGroup     = new THREE.Group();
  webHolesGroup   = new THREE.Group();
  origHolesGroup  = new THREE.Group();
  origHolesGroup.visible = false;  // off by default
  scene.add(sticksGroup, swagesGroup, lipMarkersGroup, legMarkersGroup,
            dimpleGroup, labelsGroup, webHolesGroup, origHolesGroup);
  allRootGroups = [sticksGroup, swagesGroup, lipMarkersGroup, legMarkersGroup,
                   dimpleGroup, labelsGroup, webHolesGroup, origHolesGroup];

  F.sticks.forEach(stick => {
    const sx = stick.start[0], sy = stick.start[1], sz = stick.start[2];
    const ex = stick.end[0],   ey = stick.end[1],   ez = stick.end[2];
    const dx = ex-sx, dy = ey-sy, dz = ez-sz;
    const L = Math.sqrt(dx*dx + dy*dy + dz*dz);

    const opsOrig = F.ops_orig[stick.name] || [];
    const opsSimp = F.ops_simp[stick.name] || [];
    // Use SIMPLIFIED ops as primary (they include the same SWAGE/LIP/LEG/DIMPLE
    // — just the BOLT HOLES list differs). Fall back to orig if simplified missing.
    const ops = opsSimp.length ? opsSimp : opsOrig;

    // Notch zones for segmented profile
    const zones = [];
    ops.forEach(([tool, pos]) => {
      if (tool === 'LEFT LEG NOTCH')  zones.push({start: pos - NOTCH_LEN/2, end: pos + NOTCH_LEN/2, kind: 'leg-top'});
      else if (tool === 'RIGHT LEG NOTCH') zones.push({start: pos - NOTCH_LEN/2, end: pos + NOTCH_LEN/2, kind: 'leg-bot'});
      else if (tool === 'LIP NOTCH')   zones.push({start: pos - LIPNOTCH_LEN/2, end: pos + LIPNOTCH_LEN/2, kind: 'lip-both'});
    });
    zones.sort((a,b) => a.start - b.start);

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
      if      (seg.type === 'leg-top')  prof = profileTopCut;
      else if (seg.type === 'leg-bot')  prof = profileBotCut;
      else if (seg.type === 'lip-both') prof = profileBothLipCut;
      else                              prof = profileFull;
      const geom = new THREE.ExtrudeGeometry(prof, { steps: 1, depth: segLen, bevelEnabled: false });
      geom.translate(0, 0, seg.s);
      const mat = stick.type === 'Plate' ? chordMat : galvMat;
      const mesh = new THREE.Mesh(geom, mat);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      stickGroup.add(mesh);
    });

    // Place + orient stick along its world axis
    stickGroup.position.set(sx, sy, sz);
    const target = new THREE.Vector3(dx, dy, dz).normalize();
    const q1 = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0,0,1), target);
    stickGroup.quaternion.copy(q1);

    // Roll so the open side faces +Y world (lips up — V5 trick)
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

    // ---------- Per-stick ops ----------
    ops.forEach(([tool, pos]) => {
      if (tool === 'SWAGE' && stick.type !== 'Plate') {
        const swageMesh = new THREE.Mesh(new THREE.BoxGeometry(1.5, 30, 10), swageMat);
        swageMesh.castShadow = true;
        swageMesh.position.set(0.5, 0, pos);
        stickGroup.add(swageMesh);
        swagesGroup.add(swageMesh);
      }
      else if (tool === 'INNER DIMPLE') {
        const dimpleMesh = new THREE.Mesh(
          new THREE.SphereGeometry(2.55, 12, 8, 0, Math.PI*2, 0, Math.PI/2),
          dimpleMat
        );
        dimpleMesh.castShadow = true;
        dimpleMesh.position.set(1.5, 0, pos);
        dimpleMesh.rotation.x = -Math.PI/2;
        stickGroup.add(dimpleMesh);
        dimpleGroup.add(dimpleMesh);
      }
      else if (tool === 'LIP NOTCH') {
        const lipGeom = new THREE.BoxGeometry(LIP * 0.8, LIP * 1.1, LIPNOTCH_LEN * 1.05);
        const topMarker = new THREE.Mesh(lipGeom, lipMarkerMat);
        topMarker.position.set(F1 - LIP/2, W/2 - LIP/2, pos);
        stickGroup.add(topMarker);
        lipMarkersGroup.add(topMarker);
        const botMarker = new THREE.Mesh(lipGeom, lipMarkerMat);
        botMarker.position.set(F2 - LIP/2, -(W/2 - LIP/2), pos);
        stickGroup.add(botMarker);
        lipMarkersGroup.add(botMarker);
      }
      else if (tool === 'LEFT LEG NOTCH' || tool === 'RIGHT LEG NOTCH') {
        const isLeftLeg = tool === 'LEFT LEG NOTCH';
        const yPos = isLeftLeg ? W/2 + 1 : -(W/2 + 1);
        const xPos = isLeftLeg ? F1/2 : F2/2;
        const markerGeom = new THREE.BoxGeometry(isLeftLeg ? F1 : F2, 1.5, NOTCH_LEN);
        const marker = new THREE.Mesh(markerGeom, legMarkerMat);
        marker.position.set(xPos, yPos, pos);
        stickGroup.add(marker);
        legMarkersGroup.add(marker);
      }
    });

    // ---------- Simplified WEB HOLES (3-hole clusters) ----------
    // For each BOLT HOLES position in the SIMPLIFIED ops, render a 3-hole
    // cluster centred at that stick-local Z. The cluster lives in the
    // stick's local frame: pitch direction = local Y (across the web,
    // flange-to-flange), depth direction = local X (into the web).
    opsSimp.forEach(([tool, pos]) => {
      if (tool !== 'BOLT HOLES') return;
      const cluster = makeWebCluster(webHoleMat, HOLE_PITCH, 3, HOLE_DIA, 4);
      cluster.position.set(0, 0, pos);  // local: middle hole on centreline
      stickGroup.add(cluster);
      webHolesGroup.add(cluster);
    });

    // ---------- Original BOLT HOLES (single small red dot per op) ----------
    opsOrig.forEach(([tool, pos]) => {
      if (tool !== 'BOLT HOLES') return;
      const r = ORIG_HOLE_DIA / 2;
      const cyl = new THREE.CylinderGeometry(r, r, 4, 12);
      cyl.rotateZ(Math.PI / 2);
      const mesh = new THREE.Mesh(cyl, origHoleMat);
      // Single hole sits at the stick centreline at its local pos
      mesh.position.set(2.05, 0, pos);
      stickGroup.add(mesh);
      origHolesGroup.add(mesh);
    });

    // Label sprite
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

  // Re-apply current toggle visibility (don't reset state on frame switch)
  applyToggleStates();
  updateStats(frameName);
}

// ---------- Stats panel ----------
function updateStats(frameName) {
  const F = DATA.frames[frameName];
  const orig = F.orig_bolt_count;
  // Each simplified BOLT HOLES op renders 3 physical web holes in the cluster.
  const simpClusters = F.simp_bolt_count;
  const simpHoles = simpClusters * 3;
  const reduction = orig > 0 ? (100 * (orig - simpHoles) / orig) : 0;
  let h = '<b>Frame ' + frameName + '</b><br>';
  h += 'Members: ' + F.sticks.length + '<br>';
  h += '<hr style="border-color:#4a5568;margin:6px 0">';
  h += '<span style="color:#f87171">Original BOLT HOLES: ' + orig + '</span><br>';
  h += '<span style="color:#34d399">Simplified clusters:  ' + simpClusters + ' (' + simpHoles + ' holes)</span><br>';
  const sign = reduction >= 0 ? '' : '+';
  h += '<b>Reduction: ' + sign + reduction.toFixed(0) + '%</b>';
  h += '<hr style="border-color:#4a5568;margin:6px 0">';
  h += '<span style="font-size:10px;color:#a8b9c7">Profile F37008 W089 F41-38<br>Pitch ' + HOLE_PITCH + 'mm &middot; &Oslash;' + HOLE_DIA + 'mm</span>';
  document.getElementById('stats').innerHTML = h;
}

// ---------- Toggle wiring ----------
const toggleState = {
  't-webholes':   true,
  't-orig':       false,
  't-swages':     true,
  't-lipnotches': true,
  't-legmarkers': true,
  't-dimples':    true,
  't-labels':     true,
  't-bench':      true,
  't-wireframe':  false,
};

function applyToggleStates() {
  webHolesGroup.visible   = toggleState['t-webholes'];
  origHolesGroup.visible  = toggleState['t-orig'];
  swagesGroup.visible     = toggleState['t-swages'];
  lipMarkersGroup.visible = toggleState['t-lipnotches'];
  legMarkersGroup.visible = toggleState['t-legmarkers'];
  dimpleGroup.visible     = toggleState['t-dimples'];
  labelsGroup.visible     = toggleState['t-labels'];
  bench.visible           = toggleState['t-bench'];
  [galvMat, chordMat].forEach(m => m.wireframe = toggleState['t-wireframe']);
}

function bindToggle(id) {
  const btn = document.getElementById(id);
  btn.classList.toggle('active', toggleState[id]);
  btn.addEventListener('click', () => {
    toggleState[id] = !toggleState[id];
    btn.classList.toggle('active', toggleState[id]);
    applyToggleStates();
  });
}
['t-webholes','t-orig','t-swages','t-lipnotches','t-legmarkers',
 't-dimples','t-labels','t-bench','t-wireframe'].forEach(bindToggle);

// ---------- Frame selector ----------
const sel = document.getElementById('frame-select');
DATA.frame_names.forEach(n => {
  const opt = document.createElement('option');
  opt.value = n; opt.textContent = n;
  if (n === DATA.default_frame) opt.selected = true;
  sel.appendChild(opt);
});
sel.addEventListener('change', () => buildFrame(sel.value));

// ---------- Initial build ----------
buildFrame(DATA.default_frame);

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

out = os.path.join(OUT_DIR, 'truss_3d_v6.html')
open(out, 'w', encoding='utf-8').write(html)
print(f'Wrote V6: {out}')
print(f'Frames: {len(frame_names)}')
print(f'Default: {default_frame}')
print()
print('Per-frame bolt counts (orig vs simplified clusters):')
for n in frame_names:
    b = frame_bundles[n]
    orig = b['orig_bolt_count']
    simp = b['simp_bolt_count']
    holes = simp * 3
    pct = (100*(orig-holes)/orig) if orig else 0
    print(f'  {n:8s}  orig={orig:4d}  clusters={simp:3d}  holes={holes:4d}  ({pct:+.0f}%)')
