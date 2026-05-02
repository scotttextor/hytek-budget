"""3D Truss V6 - Simplified-CSV view with 3-hole WEB HOLE clusters.

Renders the SIMPLIFIED CSV by default (centreline-intersection bolt pattern).
Each "BOLT HOLES" position on a Linear-truss stick becomes a 3-hole cluster:
  - 3 small dark cylinders (Ø3.8mm) at 17mm pitch
  - Pitch direction = perpendicular to that stick's own length, on the web face
  - Middle hole sits exactly on the centreline at the local position

KEY INSIGHT (Tool Station 1 of F37008):
  Each "BOLT HOLES" CSV entry = ONE rollformer tool fire = THREE physical
  Ø3.8mm holes at 17mm pitch (3xÃ˜3.8mm punch perpendicular to stick).
  This applies to BOTH original and simplified CSVs. So the count comparison
  needs to multiply BOTH counts by 3 to talk in physical-hole terms.

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
    """Return {frame: [{short, length, ops}, ...]} preserving CSV row order
    and allowing duplicate-name rows (W5 480 + W5 740 etc.)."""
    out = {}
    with open(csv_path) as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) < 14 or parts[0] != 'COMPONENT':
                continue
            full = parts[1]
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
            out.setdefault(frame_name, []).append({
                'short': short, 'length': length, 'ops': ops
            })
    return out


# ---------- CSV-row -> XML-stick assignment (1:1, handles duplicates by length) ----------

def assign_csv_rows_to_sticks(sticks, csv_rows):
    """For each CSV row, pick the best unused XML stick: same base name + length
    first; then closest length within 5mm. Returns a list of (csv_row, xml_idx)
    where xml_idx may be None if no match found.

    Critical: duplicate-name sticks (W5 480 AND W5 740) need length to disambiguate.
    """
    def stick_len(s):
        return math.hypot(s['end'][0]-s['start'][0], s['end'][2]-s['start'][2])
    used = [False] * len(sticks)
    assignments = []  # parallel to csv_rows
    # Pass 1: same base name AND length within 1mm
    for row in csv_rows:
        base = re.sub(r'\s*\(Box\d+\)\s*$', '', row['short']).strip()
        match = None
        for i, s in enumerate(sticks):
            if used[i]: continue
            if s['name'] == base and abs(stick_len(s) - row['length']) < 1.0:
                used[i] = True
                match = i
                break
        assignments.append(match)
    # Pass 2: closest length only (within 5mm) for unmatched rows
    for ri, row in enumerate(csv_rows):
        if assignments[ri] is not None: continue
        best_idx, best_diff = None, 5.0
        for i, s in enumerate(sticks):
            if used[i]: continue
            d = abs(stick_len(s) - row['length'])
            if d < best_diff:
                best_diff = d; best_idx = i
        if best_idx is not None:
            used[best_idx] = True
            assignments[ri] = best_idx
    return assignments


# ---------- Build per-frame data bundle for the JS ----------

frames_xml = parse_all_frames()
csv_orig_all = parse_csv_ops_all(CSV_ORIG)
csv_simp_all = parse_csv_ops_all(CSV_SIMP)

frame_names = sorted(frames_xml.keys())

frame_bundles = {}
global_orig_fires = 0
global_simp_fires = 0
for fname in frame_names:
    sticks = frames_xml[fname]['sticks']
    csv_orig_rows = csv_orig_all.get(fname, [])
    csv_simp_rows = csv_simp_all.get(fname, [])

    # Map each CSV row to a unique XML stick index (1:1 assignment)
    assign_orig = assign_csv_rows_to_sticks(sticks, csv_orig_rows)
    assign_simp = assign_csv_rows_to_sticks(sticks, csv_simp_rows)

    # Per XML stick: ops list. Aggregate the assigned CSV rows' ops onto each stick.
    ops_by_xml_orig = {s['name']: [] for s in sticks}
    ops_by_xml_simp = {s['name']: [] for s in sticks}
    # Build by index so duplicate-name sticks each get their own ops:
    ops_by_idx_orig = [list() for _ in sticks]
    ops_by_idx_simp = [list() for _ in sticks]
    for row, idx in zip(csv_orig_rows, assign_orig):
        if idx is not None:
            ops_by_idx_orig[idx] = row['ops']
    for row, idx in zip(csv_simp_rows, assign_simp):
        if idx is not None:
            ops_by_idx_simp[idx] = row['ops']

    # CSV-truth fire counts (regardless of mapping success)
    orig_fires_csv = sum(1 for row in csv_orig_rows for t,_ in row['ops'] if t == 'BOLT HOLES')
    simp_fires_csv = sum(1 for row in csv_simp_rows for t,_ in row['ops'] if t == 'BOLT HOLES')
    global_orig_fires += orig_fires_csv
    global_simp_fires += simp_fires_csv

    # Geometry centre/extent
    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_y = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    all_z = [c for s in sticks for c in (s['start'][2], s['end'][2])]
    cx = (min(all_x)+max(all_x))/2
    cy = (min(all_y)+max(all_y))/2
    cz = (min(all_z)+max(all_z))/2
    extent = max(max(all_x)-min(all_x), max(all_z)-min(all_z), 100.0)

    frame_bundles[fname] = {
        'sticks': sticks,
        'ops_orig_by_idx': ops_by_idx_orig,
        'ops_simp_by_idx': ops_by_idx_simp,
        'centre': [cx, cy, cz],
        'extent': extent,
        'orig_fires_csv': orig_fires_csv,
        'simp_fires_csv': simp_fires_csv,
    }

default_frame = 'TN2-1' if 'TN2-1' in frame_bundles else frame_names[0]

data = {
    'frames': frame_bundles,
    'frame_names': frame_names,
    'default_frame': default_frame,
    'global_orig_fires': global_orig_fires,
    'global_simp_fires': global_simp_fires,
}

html = '''<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Truss 3D V6</title>
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
  #stats { position: absolute; top: 12px; right: 12px; color: white; padding: 10px 14px; background: rgba(0,0,0,0.7); border-radius: 6px; font-size: 12px; min-width: 320px; line-height: 1.45; }
  #stats .big { font-size: 13px; font-family: Segoe UI, Arial, sans-serif; margin-bottom: 4px; }
  #stats .row { font-family: Consolas, "Courier New", monospace; font-size: 12px; white-space: nowrap; }
  #stats .small { font-size: 10px; color: #a8b9c7; line-height: 1.5; font-family: Segoe UI, Arial, sans-serif; }
  #stats hr { border: none; border-top: 1px solid #4a5568; margin: 6px 0; }
  .controls { position: absolute; bottom: 12px; left: 12px; color: white; padding: 10px 14px; background: rgba(0,0,0,0.65); border-radius: 6px; font-size: 12px; max-width: 900px; }
  .toggle { display: inline-block; margin: 4px 6px 4px 0; padding: 4px 10px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); border-radius: 3px; cursor: pointer; user-select: none; color: white; font-size: 11px; }
  .toggle.active { background: #16a34a; border-color: #14532d; }
  .swage-tog.active { background: #9333ea; border-color: #6b21a8; }
  .lip-tog.active   { background: #d97706; border-color: #92400e; }
  .leg-tog.active   { background: #dc2626; border-color: #7f1d1d; }
  .orig-tog.active  { background: #b91c1c; border-color: #7f1d1d; }
  .web-tog.active   { background: #065f46; border-color: #064e3b; }
  .debug-tog.active { background: #15803d; border-color: #14532d; }
  #frame-bar { position: absolute; top: 12px; left: 50%; transform: translateX(-50%); padding: 8px 14px; background: rgba(0,0,0,0.7); border-radius: 6px; color: white; font-size: 13px; }
  #frame-bar select { background: #2d3748; color: white; border: 1px solid #4a5568; border-radius: 4px; padding: 4px 8px; font-size: 13px; margin-left: 8px; }
  #frame-bar #frame-title { font-weight: bold; color: #fbbf24; margin-right: 8px; }
</style>
</head>
<body>
<div id="info">
  <h1 id="page-title">Truss 3D V6</h1>
  <p><b>Drag</b> rotate, <b>Scroll</b> zoom, <b>Right-drag</b> pan</p>
  <p><span class="web">WEB HOLES</span> = simplified 3-hole cluster (3xO3.8 @ 17mm pitch) = ONE rollformer fire on each stick at every centreline crossing</p>
  <p><span class="orig">Original BOLT HOLES</span> = FrameCAD's per-stick bolt pattern (toggle to compare; same 3-hole cluster, just at different positions)</p>
  <p><span class="swage">SWAGE</span>, <span class="lip">LIP NOTCH</span>, <span class="leg">LEG NOTCH</span>, cyan = INNER DIMPLE</p>
</div>
<div id="frame-bar">
  <span id="frame-title">TN2-1</span>
  Frame: <select id="frame-select"></select>
</div>
<div id="stats"></div>
<div class="controls">
  <span class="toggle active web-tog"  id="t-webholes">Simplified web holes</span>
  <span class="toggle orig-tog"        id="t-orig">Show original ops</span>
  <span class="toggle debug-tog"       id="t-debug">CL-crossing markers</span>
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
// Hole interior - dark, double-sided so it reads as a hole, not a bump.
const holeInteriorMat = new THREE.MeshBasicMaterial({
  color: 0x0a0a0a,
  side: THREE.DoubleSide
});
// Original-ops hole interior - dark red tint to differentiate visually
const origHoleInteriorMat = new THREE.MeshBasicMaterial({
  color: 0x3a0a0a,
  side: THREE.DoubleSide
});
// Thin black ring on the web surface for the rim of each hole
const holeRimMat = new THREE.MeshBasicMaterial({
  color: 0x000000, side: THREE.DoubleSide
});
const origHoleRimMat = new THREE.MeshBasicMaterial({
  color: 0x7f1d1d, side: THREE.DoubleSide
});
// Debug centreline-crossing dots: bright green, no shading
const clCrossingMat = new THREE.MeshBasicMaterial({ color: 0x22c55e });

// ---------- Group containers (rebuilt on every frame switch) ----------
let sticksGroup, swagesGroup, lipMarkersGroup, legMarkersGroup, dimpleGroup, labelsGroup;
let webHolesGroup, origHolesGroup, debugGroup;
let allRootGroups = [];

const NOTCH_LEN    = 12;
const LIPNOTCH_LEN = 12;
const HOLE_PITCH   = 17;     // mm between adjacent holes in the 3-hole cluster
const HOLE_DIA     = 3.8;    // physical Ø3.8mm
const HOLE_DEPTH   = 4;      // total cylinder length (sinks through web both sides)
const WEB_T        = T;      // web thickness (0.75mm)

// Build a 3-hole cluster centred on a stick local position.
//   - hole interior: short dark cylinder, axis along local X (perpendicular to web),
//     sunk INTO the web so it visually reads as a hole, not a bump
//   - rim: thin black ring (annulus) on the web surface around each hole
//   - pitch direction: local Y (across the web, flange-to-flange)
//   - both faces rendered (DoubleSide) so dark interior visible from either side
function makeWebCluster(interiorMat, rimMat, pitch, count, dia) {
  const grp = new THREE.Group();
  const r = dia / 2;
  // Hole rim slightly larger than hole; thin (10% wider radius, very thin annulus)
  const rOuter = r + 0.6;
  for (let i = 0; i < count; i++) {
    const offsetY = (i - (count-1)/2) * pitch;

    // 1) Interior cylinder - short, sits centred on the web (sinks into it).
    //    Total length HOLE_DEPTH is greater than web thickness so it pokes
    //    out both faces and the interior is visible from any angle.
    const cyl = new THREE.CylinderGeometry(r, r, HOLE_DEPTH, 20, 1, true);
    cyl.rotateZ(Math.PI / 2);  // axis -> +X
    const interior = new THREE.Mesh(cyl, interiorMat);
    interior.position.set(0, offsetY, 0);     // CENTRED on web (no proud offset)
    interior.castShadow = false;
    interior.renderOrder = 2;                  // draw after the steel
    grp.add(interior);

    // 2) End caps - dark disks at each face so head-on it looks like a black hole
    //    (the disks sit exactly at the web surfaces +T/2 and -T/2)
    const capGeom = new THREE.CircleGeometry(r * 0.95, 20);
    const capFront = new THREE.Mesh(capGeom, interiorMat);
    capFront.rotation.y = Math.PI / 2;         // face +X
    capFront.position.set(WEB_T/2 + 0.05, offsetY, 0);
    capFront.renderOrder = 3;
    grp.add(capFront);
    const capBack = new THREE.Mesh(capGeom, interiorMat);
    capBack.rotation.y = -Math.PI / 2;         // face -X
    capBack.position.set(-WEB_T/2 - 0.05, offsetY, 0);
    capBack.renderOrder = 3;
    grp.add(capBack);

    // 3) Rim ring on each face (thin annulus around hole)
    const ringGeom = new THREE.RingGeometry(r, rOuter, 24);
    const ringFront = new THREE.Mesh(ringGeom, rimMat);
    ringFront.rotation.y = Math.PI / 2;
    ringFront.position.set(WEB_T/2 + 0.06, offsetY, 0);
    ringFront.renderOrder = 4;
    grp.add(ringFront);
    const ringBack = new THREE.Mesh(ringGeom, rimMat);
    ringBack.rotation.y = -Math.PI / 2;
    ringBack.position.set(-WEB_T/2 - 0.06, offsetY, 0);
    ringBack.renderOrder = 4;
    grp.add(ringBack);
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

  // Camera + lighting positioned for this frame.
  // Reset camera every frame switch so very different frame sizes (TN2-1 ~ 4m
  // vs U1-1 ~ 12m) all fit on screen out of the gate.
  camera.position.set(centre[0] + extent*0.7, centre[1] + extent*0.5, centre[2] + extent*0.7);
  camera.far = extent * 8;
  camera.updateProjectionMatrix();
  controls.target.set(centre[0], centre[1], centre[2]);
  controls.update();

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
  debugGroup      = new THREE.Group();
  origHolesGroup.visible = false;  // off by default
  debugGroup.visible = false;      // off by default
  scene.add(sticksGroup, swagesGroup, lipMarkersGroup, legMarkersGroup,
            dimpleGroup, labelsGroup, webHolesGroup, origHolesGroup, debugGroup);
  allRootGroups = [sticksGroup, swagesGroup, lipMarkersGroup, legMarkersGroup,
                   dimpleGroup, labelsGroup, webHolesGroup, origHolesGroup, debugGroup];

  F.sticks.forEach((stick, idx) => {
    const sx = stick.start[0], sy = stick.start[1], sz = stick.start[2];
    const ex = stick.end[0],   ey = stick.end[1],   ez = stick.end[2];
    const dx = ex-sx, dy = ey-sy, dz = ez-sz;
    const L = Math.sqrt(dx*dx + dy*dy + dz*dz);

    const opsOrig = F.ops_orig_by_idx[idx] || [];
    const opsSimp = F.ops_simp_by_idx[idx] || [];
    // Use SIMPLIFIED ops as primary (they include the same SWAGE/LIP/LEG/DIMPLE
    // - just the BOLT HOLES list differs). Fall back to orig if simplified missing.
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

    // Roll so the open side faces +Y world (lips up - V5 trick)
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

    // ---------- Simplified WEB HOLES (3-hole clusters at CL crossings) ----------
    opsSimp.forEach(([tool, pos]) => {
      if (tool !== 'BOLT HOLES') return;
      const cluster = makeWebCluster(holeInteriorMat, holeRimMat, HOLE_PITCH, 3, HOLE_DIA);
      cluster.position.set(0, 0, pos);  // local: cluster centre on the centreline
      stickGroup.add(cluster);
      webHolesGroup.add(cluster);

      // Debug marker: bright green dot AT the centreline crossing the
      // simplifier identified. The 3-hole cluster's middle hole should sit
      // exactly here. If they're offset, we have a transform bug.
      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(2.2, 10, 8),
        clCrossingMat
      );
      dot.position.set(0, 0, pos);
      stickGroup.add(dot);
      debugGroup.add(dot);
    });

    // ---------- Original BOLT HOLES (3-hole clusters too - same tool fires!) ----------
    opsOrig.forEach(([tool, pos]) => {
      if (tool !== 'BOLT HOLES') return;
      const cluster = makeWebCluster(origHoleInteriorMat, origHoleRimMat, HOLE_PITCH, 3, HOLE_DIA);
      cluster.position.set(0, 0, pos);
      stickGroup.add(cluster);
      origHolesGroup.add(cluster);
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
  // Update title
  document.getElementById('frame-title').textContent = frameName;
  document.getElementById('page-title').textContent = 'Truss 3D V6 - ' + frameName;
}

// ---------- Stats panel (Option C: apples-to-apples) ----------
// Each "BOLT HOLES" CSV entry = ONE rollformer fire of the WEB HOLE tool,
// which physically punches 3 x O3.8mm holes at 17mm pitch (per F37008
// Tool Stn 1 spec). So both the original and simplified counts MUST be
// expressed identically: fires + (3 x fires) physical holes.
//
// Format:
//   Frame TN2-1
//   Members: 11
//   --
//   Original:    55 fires (165 physical O3.8mm holes)
//   Simplified:  30 fires ( 90 physical O3.8mm holes)
//   Reduction:  -45%
//   --
//   All 22 frames: 1462 -> 826 fires (-43%)
//   1 fire = 3 physical O3.8mm holes @ 17mm pitch (Tool Stn 1)
function updateStats(frameName) {
  const F = DATA.frames[frameName];
  const oFires = F.orig_fires_csv;
  const sFires = F.simp_fires_csv;
  const oHoles = oFires * 3;
  const sHoles = sFires * 3;
  const redPct = oFires > 0 ? (100 * (sFires - oFires) / oFires) : 0;
  const gO = DATA.global_orig_fires;
  const gS = DATA.global_simp_fires;
  const gOH = gO * 3;
  const gSH = gS * 3;
  const gPct = gO > 0 ? (100 * (gS - gO) / gO) : 0;

  // Use literal Unicode chars for non-ASCII (page is UTF-8).
  const OSLASH = '\\u00D8';    // diameter symbol
  const ARROW  = '\\u2192';    // right arrow
  const MINUS  = '\\u2212';    // proper minus sign (not hyphen)

  // Pad the smaller "fires" so the parenthesised holes column lines up.
  // Monospace font on stat panel keeps these aligned.
  const wF = Math.max(String(oFires).length, String(sFires).length);
  const wH = Math.max(String(oHoles).length, String(sHoles).length);
  const padL = (s, w) => String(s).padStart(w, ' ');
  // Convert leading spaces to non-breaking so HTML preserves them.
  const nbsp = (s) => s.replace(/ /g, '\\u00A0');

  let h = '<div class="big"><b>Frame ' + frameName + '</b></div>';
  h += 'Members: ' + F.sticks.length + '<br>';
  h += '<hr>';
  h += '<div class="row"><span style="color:#f87171">Original:</span>'
     + nbsp('   ' + padL(oFires, wF)) + ' fires (' + nbsp(padL(oHoles, wH))
     + ' physical ' + OSLASH + '3.8mm holes)</div>';
  h += '<div class="row"><span style="color:#34d399">Simplified:</span>'
     + nbsp(' ' + padL(sFires, wF)) + ' fires (' + nbsp(padL(sHoles, wH))
     + ' physical ' + OSLASH + '3.8mm holes)</div>';
  const redColor = redPct < 0 ? '#34d399' : (redPct > 0 ? '#fbbf24' : '#a8b9c7');
  const redStr = redPct < 0 ? (MINUS + Math.abs(redPct).toFixed(0))
                            : (redPct > 0 ? '+' + redPct.toFixed(0) : '0');
  h += '<div class="row"><b style="color:' + redColor + '">Reduction:'
     + nbsp('  ') + redStr + '%</b></div>';
  h += '<hr>';
  h += '<div class="small">';
  const gStr = gPct < 0 ? (MINUS + Math.abs(gPct).toFixed(0))
                        : (gPct > 0 ? '+' + gPct.toFixed(0) : '0');
  h += 'All ' + DATA.frame_names.length + ' frames: ' + gO + ' ' + ARROW + ' '
     + gS + ' fires (' + gStr + '%)<br>';
  h += '&nbsp;&nbsp;&nbsp;= ' + gOH + ' ' + ARROW + ' ' + gSH
     + ' physical ' + OSLASH + '3.8mm holes<br>';
  h += '<br>1 fire = 3 physical ' + OSLASH + '3.8mm holes @ 17mm pitch (F37008 Tool Stn 1)';
  h += '</div>';
  document.getElementById('stats').innerHTML = h;
}

// ---------- Toggle wiring ----------
const toggleState = {
  't-webholes':   true,
  't-orig':       false,
  't-debug':      false,
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
  debugGroup.visible      = toggleState['t-debug'];
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
['t-webholes','t-orig','t-debug','t-swages','t-lipnotches','t-legmarkers',
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
print('Wrote V6: ' + out)
print('Frames: ' + str(len(frame_names)))
print('Default: ' + default_frame)
print('Global: orig=' + str(global_orig_fires) + ' fires (' + str(global_orig_fires*3) + ' holes)')
print('        simp=' + str(global_simp_fires) + ' fires (' + str(global_simp_fires*3) + ' holes)')
gpct = (100*(global_simp_fires-global_orig_fires)/global_orig_fires) if global_orig_fires else 0
print('        reduction ' + ('%.1f' % gpct) + '%')
print('')
print('Per-frame fire counts (CSV truth):')
for n in frame_names:
    b = frame_bundles[n]
    o = b['orig_fires_csv']
    s = b['simp_fires_csv']
    p = (100*(s-o)/o) if o else 0
    print('  ' + n.ljust(8) + '  orig=' + ('%4d' % o) + '  simp=' + ('%4d' % s) +
          '  (' + ('%+.0f' % p) + '%)  -> ' + str(o*3) + ' vs ' + str(s*3) + ' holes')
