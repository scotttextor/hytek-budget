"""HYTEK U4-1 — assembled real-world view.

Draws the truss as it would look sitting on the bench fully fabricated:
  - Every member rendered as a 89mm-wide rectangle (the actual C-section depth)
  - Sticks rotated to match their real slope/orientation
  - Webs trimmed so they nestle between chord faces (not crossing through)
  - Bolt clusters drawn AT joints, perpendicular to chord
  - Box pieces drawn as parallel members with dimples
  - Overall dimensions and pitch angles called out
  - Inset showing how the C-section sits in cross-section

Output: HYTEK_U4-1_assembled.svg on Desktop.
"""
import os, math

CSV = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.simplified.csv'
DESKTOP = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop'
TRUSS = 'U4-1'
OUT = os.path.join(DESKTOP, f'HYTEK_{TRUSS}_assembled.svg')

# ---------- Parse CSV ----------
sticks = []
with open(CSV) as f:
    for line in f:
        parts = [p.strip() for p in line.strip().split(',')]
        if len(parts) < 13 or parts[0] != 'COMPONENT': continue
        name = parts[1]
        if not name.startswith(f'{TRUSS}-'): continue
        try:
            usage = parts[3]
            length = float(parts[7])
            x1, z1, x2, z2 = float(parts[8]), float(parts[9]), float(parts[10]), float(parts[11])
        except ValueError:
            continue
        ops = []
        i = 13
        while i + 1 < len(parts):
            op = parts[i]
            try: pos = float(parts[i+1])
            except ValueError: i += 2; continue
            ops.append((op, pos))
            i += 2
        sticks.append({'name': name, 'usage': usage, 'length': length,
                       'x1': x1, 'z1': z1, 'x2': x2, 'z2': z2, 'ops': ops})

def is_box(name): return '(Box' in name
def usage_of(s): return (s['usage'] or '').upper()
def is_chord(s): return 'CHORD' in usage_of(s)
def is_web(s):   return 'WEB'   in usage_of(s) and not is_box(s['name'])

chord_sticks = [s for s in sticks if is_chord(s) and not is_box(s['name'])]
web_sticks   = [s for s in sticks if is_web(s)]
box_sticks   = [s for s in sticks if is_box(s['name'])]

# ---------- Geometry ----------
PROFILE_DEPTH = 89.0  # mm — the C-section web depth, drawn as the bar width

# Page
W, H = 1700, 1100
PAD = 40
TITLE_H = 90
SUMMARY_H = 130

# Compute bounding box (with profile depth padding)
all_xs, all_zs = [], []
for s in sticks:
    all_xs.extend([s['x1'], s['x2']])
    all_zs.extend([s['z1'], s['z2']])
PAD_MM = PROFILE_DEPTH * 0.7  # extra margin for the profile thickness
minx, maxx = min(all_xs) - PAD_MM, max(all_xs) + PAD_MM
minz, maxz = min(all_zs) - PAD_MM, max(all_zs) + PAD_MM
span_x = maxx - minx
span_z = maxz - minz

# Drawing area
draw_x0 = PAD
draw_y0 = TITLE_H
draw_x1 = W - PAD - 280  # leave room for inset on right
draw_y1 = H - SUMMARY_H - PAD
avail_w = draw_x1 - draw_x0
avail_h = draw_y1 - draw_y0
scale = min(avail_w / span_x, avail_h / span_z)
draw_w_actual = span_x * scale
draw_h_actual = span_z * scale
ox = draw_x0 + (avail_w - draw_w_actual) / 2
oy = draw_y0 + (avail_h - draw_h_actual) / 2 + draw_h_actual  # flip z

def to_svg(x, z):
    return (ox + (x - minx) * scale, oy - (z - minz) * scale)

def line_intersect(p1, p2, p3, p4):
    x1,z1=p1; x2,z2=p2; x3,z3=p3; x4,z4=p4
    denom = (x1-x2)*(z3-z4) - (z1-z2)*(x3-x4)
    if abs(denom) < 1e-9: return None
    t = ((x1-x3)*(z3-z4) - (z1-z3)*(x3-x4)) / denom
    u = -((x1-x2)*(z1-z3) - (z1-z2)*(x1-x3)) / denom
    return t, u

# Trim webs to chord boundaries (where centrelines cross chord centrelines)
for w in web_sticks:
    ts = []
    for c in chord_sticks:
        r = line_intersect((w['x1'], w['z1']), (w['x2'], w['z2']),
                           (c['x1'], c['z1']), (c['x2'], c['z2']))
        if r is None: continue
        t, u = r
        if -0.05 <= t <= 1.05 and -0.05 <= u <= 1.05:
            ts.append(max(0.0, min(1.0, t)))
    if ts:
        ts.sort()
        w['t_lo'] = ts[0]
        w['t_hi'] = ts[-1]
    else:
        w['t_lo'] = 0.0
        w['t_hi'] = 1.0

def stick_corners(x1, z1, x2, z2, depth_mm):
    """Return 4 world-coord corners of the stick rectangle."""
    dx, dz = x2 - x1, z2 - z1
    L = math.hypot(dx, dz) or 1.0
    # Perpendicular unit vector (90° anticlockwise in math; let's pick +z direction)
    px, pz = -dz / L, dx / L
    h = depth_mm / 2
    return [
        (x1 + px*h, z1 + pz*h),
        (x2 + px*h, z2 + pz*h),
        (x2 - px*h, z2 - pz*h),
        (x1 - px*h, z1 - pz*h),
    ]

# ---------- SVG output ----------
svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
svg.append('''<defs>
  <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#e2e8f0"/><stop offset="100%" stop-color="#94a3b8"/>
  </linearGradient>
  <linearGradient id="boxsteel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#fef3c7"/><stop offset="100%" stop-color="#fbbf24"/>
  </linearGradient>
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="#64748b" stroke-width="0.5"/>
  </pattern>
  <marker id="arrDim" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
    <path d="M0,0 L7,3 L0,6 z" fill="#1e293b"/>
  </marker>
</defs>''')
svg.append(f'<rect width="{W}" height="{H}" fill="#f8fafc"/>')

# Header
svg.append(f'<rect x="0" y="0" width="{W}" height="{TITLE_H}" fill="#231F20"/>')
svg.append(f'<rect x="0" y="0" width="8" height="{TITLE_H}" fill="#FFCB05"/>')
svg.append(f'<text x="30" y="34" font-size="22" font-weight="800" fill="#FFCB05">HYTEK Truss {TRUSS} — assembled view</text>')
svg.append(f'<text x="30" y="56" font-size="12" fill="white" opacity="0.9">Job 2603191 ROCKVILLE  |  Plan GF-LIN-89.075  |  Profile 89×41 LC 0.75mm AZ150  |  Real geometry · steel drawn at scale 1mm = {scale:.3f}px</text>')
svg.append(f'<text x="30" y="76" font-size="11" fill="#FFCB05" opacity="0.85">Webs trimmed to nestle between chords. Bolt clusters at every centreline-crossing. Box piece shown clipped on. This is the assembly an installer sees.</text>')

# ---------- Draw chords (drawn first so webs sit on top) ----------
def draw_stick_rect(s, fill, stroke, sw=1.6, depth=PROFILE_DEPTH):
    corners = stick_corners(s['x1'], s['z1'], s['x2'], s['z2'], depth)
    pts = ' '.join(f'{to_svg(x,z)[0]:.1f},{to_svg(x,z)[1]:.1f}' for x,z in corners)
    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'

# Centreline (faint) for each chord
for c in chord_sticks:
    x1p, y1p = to_svg(c['x1'], c['z1'])
    x2p, y2p = to_svg(c['x2'], c['z2'])
    svg.append(f'<line x1="{x1p:.1f}" y1="{y1p:.1f}" x2="{x2p:.1f}" y2="{y2p:.1f}" '
               f'stroke="#1e40af" stroke-width="0.4" stroke-dasharray="3,3" opacity="0.5"/>')

# Chords as steel rectangles
for c in chord_sticks:
    svg.append(draw_stick_rect(c, 'url(#steel)', '#1e293b', 1.8))

# Webs trimmed to chord-to-chord (using t_lo/t_hi computed earlier)
for w in web_sticks:
    t_lo, t_hi = w.get('t_lo', 0.0), w.get('t_hi', 1.0)
    sx = w['x1'] + t_lo * (w['x2'] - w['x1'])
    sz = w['z1'] + t_lo * (w['z2'] - w['z1'])
    ex = w['x1'] + t_hi * (w['x2'] - w['x1'])
    ez = w['z1'] + t_hi * (w['z2'] - w['z1'])
    corners = stick_corners(sx, sz, ex, ez, PROFILE_DEPTH)
    pts = ' '.join(f'{to_svg(x,z)[0]:.1f},{to_svg(x,z)[1]:.1f}' for x,z in corners)
    svg.append(f'<polygon points="{pts}" fill="url(#steel)" stroke="#475569" stroke-width="1.2"/>')

# Box pieces — drawn alongside their parent chord, slightly offset (above the chord)
# Drawn with amber tint to distinguish from main chord
for b in box_sticks:
    # Compute offset perpendicular to box direction (toward "outside" of truss)
    # Box pieces are typically below their parent chord on the open side
    # We draw them just adjacent to the parent chord
    dx, dz = b['x2'] - b['x1'], b['z2'] - b['z1']
    L = math.hypot(dx, dz) or 1.0
    # Offset perpendicular by -PROFILE_DEPTH (outside the truss for bottom chord)
    px, pz = -dz / L, dx / L
    # Decide which side: for bottom chord box, offset DOWN (negative z)
    # For top chord box, offset UP
    parent = b['name'].split(' (Box')[0]
    parent_stick = next((s for s in sticks if s['name'] == parent and not is_box(s['name'])), None)
    if parent_stick and 'TOP' in usage_of(parent_stick).upper():
        # Top chord: box sits ABOVE
        ox_b, oz_b = px * PROFILE_DEPTH, pz * PROFILE_DEPTH
        if oz_b < 0: ox_b, oz_b = -ox_b, -oz_b  # ensure positive z direction
    else:
        # Bottom chord: box sits BELOW (or just adjacent — we'll show it overlaid offset for clarity)
        ox_b, oz_b = -px * PROFILE_DEPTH * 0.55, -pz * PROFILE_DEPTH * 0.55
    bx1, bz1 = b['x1'] + ox_b, b['z1'] + oz_b
    bx2, bz2 = b['x2'] + ox_b, b['z2'] + oz_b
    corners = stick_corners(bx1, bz1, bx2, bz2, PROFILE_DEPTH * 0.7)
    pts = ' '.join(f'{to_svg(x,z)[0]:.1f},{to_svg(x,z)[1]:.1f}' for x,z in corners)
    svg.append(f'<polygon points="{pts}" fill="url(#boxsteel)" stroke="#92400e" stroke-width="1.5"/>')

# ---------- Stick name labels ----------
for c in chord_sticks:
    midx, midz = (c['x1'] + c['x2'])/2, (c['z1'] + c['z2'])/2
    mx, my = to_svg(midx, midz)
    short = c['name'].replace(f'{TRUSS}-', '')
    svg.append(f'<text x="{mx:.1f}" y="{my + 4:.1f}" text-anchor="middle" font-size="11" font-weight="800" fill="white" stroke="#1e3a8a" stroke-width="2.5" paint-order="stroke">{short}</text>')

for w in web_sticks:
    t_lo, t_hi = w.get('t_lo', 0.0), w.get('t_hi', 1.0)
    midx = w['x1'] + (t_lo + t_hi)/2 * (w['x2'] - w['x1'])
    midz = w['z1'] + (t_lo + t_hi)/2 * (w['z2'] - w['z1'])
    mx, my = to_svg(midx, midz)
    short = w['name'].replace(f'{TRUSS}-', '')
    # Offset label perpendicular to web so it doesn't sit on top of the steel
    dx, dz = w['x2'] - w['x1'], w['z2'] - w['z1']
    L = math.hypot(dx, dz) or 1.0
    perp_x, perp_z = -dz/L, dx/L
    off_world = PROFILE_DEPTH * 0.85
    lx_world = midx + perp_x * off_world
    lz_world = midz + perp_z * off_world
    lx, ly = to_svg(lx_world, lz_world)
    svg.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" font-size="10" font-weight="700" fill="#1e293b">{short}</text>')

for b in box_sticks:
    midx, midz = (b['x1'] + b['x2'])/2, (b['z1'] + b['z2'])/2
    parent = b['name'].split(' (Box')[0]
    parent_stick = next((s for s in sticks if s['name'] == parent and not is_box(s['name'])), None)
    dx, dz = b['x2'] - b['x1'], b['z2'] - b['z1']
    L = math.hypot(dx, dz) or 1.0
    px, pz = -dz/L, dx/L
    if parent_stick and 'TOP' in usage_of(parent_stick).upper():
        off = PROFILE_DEPTH * 1.4
        if (-pz) > 0: px, pz = -px, -pz
    else:
        off = -PROFILE_DEPTH * 1.0
    lx_world = midx + px * off
    lz_world = midz + pz * off
    lx, ly = to_svg(lx_world, lz_world)
    short = b['name'].replace(f'{TRUSS}-', '')
    svg.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" font-size="9" font-style="italic" font-weight="700" fill="#92400e">{short}</text>')

# ---------- Bolt clusters at joints ----------
# Find every chord-web centreline intersection
joints = []
for c in chord_sticks:
    for w in web_sticks:
        r = line_intersect((c['x1'], c['z1']), (c['x2'], c['z2']),
                           (w['x1'], w['z1']), (w['x2'], w['z2']))
        if r is None: continue
        t, u = r
        if -0.05 <= t <= 1.05 and -0.05 <= u <= 1.05:
            ix = c['x1'] + max(0,min(1,t)) * (c['x2'] - c['x1'])
            iz = c['z1'] + max(0,min(1,t)) * (c['z2'] - c['z1'])
            joints.append({'world': (ix, iz), 'chord': c, 'web': w})

# Also consider chord-chord splices as joints
for i, c1 in enumerate(chord_sticks):
    for c2 in chord_sticks[i+1:]:
        # Check if endpoints coincide (within 50mm) — that's a splice
        for p1 in [(c1['x1'], c1['z1']), (c1['x2'], c1['z2'])]:
            for p2 in [(c2['x1'], c2['z1']), (c2['x2'], c2['z2'])]:
                if math.hypot(p1[0]-p2[0], p1[1]-p2[1]) < 50:
                    midp = ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2)
                    joints.append({'world': midp, 'chord': c1, 'web': c2})
                    break

# Deduplicate joints by world position (10mm tolerance)
unique_joints = []
for j in joints:
    jx, jz = j['world']
    found = False
    for u in unique_joints:
        ux, uz = u['world']
        if abs(ux - jx) < 10 and abs(uz - jz) < 10:
            found = True
            break
    if not found:
        unique_joints.append(j)

# Draw bolt cluster at each joint — 3 dots perpendicular to the chord
PITCH_MM = 17
for j in unique_joints:
    jx, jz = j['world']
    chord = j['chord']
    dx, dz = chord['x2'] - chord['x1'], chord['z2'] - chord['z1']
    L = math.hypot(dx, dz) or 1.0
    perp_wx, perp_wz = -dz / L, dx / L
    cx_svg, cy_svg = to_svg(jx, jz)
    # Perpendicular in screen space
    perp_px = perp_wx * scale
    perp_py = -perp_wz * scale
    # Halo ring
    svg.append(f'<circle cx="{cx_svg:.1f}" cy="{cy_svg:.1f}" r="9" fill="none" stroke="#dc2626" stroke-width="0.7" opacity="0.5"/>')
    # 3 holes at -PITCH, 0, +PITCH along the perpendicular (1 mm step = scale px)
    for k in (-1, 0, 1):
        hx = cx_svg + perp_px * k * PITCH_MM
        hy = cy_svg + perp_py * k * PITCH_MM
        svg.append(f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="1.7" fill="#dc2626" stroke="white" stroke-width="0.4"/>')

# ---------- Inner dimples on Box pieces (snap-fit indicators) ----------
# For each Box piece's INNER DIMPLE op, draw a small amber diamond
for b in box_sticks:
    for op, pos in b['ops']:
        if op != 'INNER DIMPLE': continue
        L = b['length']
        if L <= 0: continue
        t = pos / L
        bx_world = b['x1'] + t * (b['x2'] - b['x1'])
        bz_world = b['z1'] + t * (b['z2'] - b['z1'])
        # Apply same offset we used to draw the box
        dx, dz = b['x2'] - b['x1'], b['z2'] - b['z1']
        Lb = math.hypot(dx, dz) or 1.0
        px, pz = -dz / Lb, dx / Lb
        parent = b['name'].split(' (Box')[0]
        parent_stick = next((s for s in sticks if s['name'] == parent and not is_box(s['name'])), None)
        if parent_stick and 'TOP' in usage_of(parent_stick).upper():
            ox_b, oz_b = px * PROFILE_DEPTH, pz * PROFILE_DEPTH
            if oz_b < 0: ox_b, oz_b = -ox_b, -oz_b
        else:
            ox_b, oz_b = -px * PROFILE_DEPTH * 0.55, -pz * PROFILE_DEPTH * 0.55
        dx_svg, dy_svg = to_svg(bx_world + ox_b, bz_world + oz_b)
        svg.append(f'<rect x="{dx_svg-3.2:.1f}" y="{dy_svg-3.2:.1f}" width="6.4" height="6.4" '
                   f'fill="#f59e0b" stroke="#92400e" stroke-width="0.6" '
                   f'transform="rotate(45 {dx_svg:.1f} {dy_svg:.1f})"/>')

# Also draw the matching dimples on the parent chord (CL-to-CL snap points)
for c in chord_sticks:
    for op, pos in c['ops']:
        if op != 'INNER DIMPLE': continue
        L = c['length']
        if L <= 0: continue
        t = pos / L
        cx_world = c['x1'] + t * (c['x2'] - c['x1'])
        cz_world = c['z1'] + t * (c['z2'] - c['z1'])
        dx_svg, dy_svg = to_svg(cx_world, cz_world)
        svg.append(f'<rect x="{dx_svg-2.8:.1f}" y="{dy_svg-2.8:.1f}" width="5.6" height="5.6" '
                   f'fill="#f59e0b" stroke="#92400e" stroke-width="0.5" opacity="0.7" '
                   f'transform="rotate(45 {dx_svg:.1f} {dy_svg:.1f})"/>')

# ---------- Overall dimensions ----------
# Span (horizontal extent of bottom chord)
b1 = next((s for s in chord_sticks if 'BOTTOM' in usage_of(s).upper()), None)
if b1:
    span_mm = abs(b1['x2'] - b1['x1'])
    p1 = to_svg(b1['x1'], b1['z1'])
    p2 = to_svg(b1['x2'], b1['z2'])
    dim_y = max(p1[1], p2[1]) + 50
    svg.append(f'<line x1="{p1[0]:.1f}" y1="{dim_y}" x2="{p2[0]:.1f}" y2="{dim_y}" '
               f'stroke="#1e293b" stroke-width="1" marker-start="url(#arrDim)" marker-end="url(#arrDim)"/>')
    svg.append(f'<line x1="{p1[0]:.1f}" y1="{p1[1]+10}" x2="{p1[0]:.1f}" y2="{dim_y+5}" stroke="#1e293b" stroke-width="0.6" stroke-dasharray="3,2"/>')
    svg.append(f'<line x1="{p2[0]:.1f}" y1="{p2[1]+10}" x2="{p2[0]:.1f}" y2="{dim_y+5}" stroke="#1e293b" stroke-width="0.6" stroke-dasharray="3,2"/>')
    svg.append(f'<text x="{(p1[0]+p2[0])/2:.1f}" y="{dim_y - 6}" text-anchor="middle" font-size="11" font-weight="700" fill="#1e293b">SPAN {span_mm:.0f}mm</text>')

# Height (vertical extent — top chord apex to bottom chord)
top_z_max = max((max(c['z1'], c['z2']) for c in chord_sticks if 'TOP' in usage_of(c).upper()), default=0)
bot_z = b1['z1'] if b1 else 0
height_mm = top_z_max - bot_z
if b1:
    apex_x = next((c['x1'] if c['z1'] > c['z2'] else c['x2'] for c in chord_sticks if 'TOP' in usage_of(c).upper() and max(c['z1'], c['z2']) == top_z_max), b1['x1'])
    p1 = to_svg(apex_x, top_z_max)
    p2 = to_svg(apex_x, bot_z)
    dim_x = min(p1[0], p2[0]) - 50
    svg.append(f'<line x1="{dim_x}" y1="{p1[1]:.1f}" x2="{dim_x}" y2="{p2[1]:.1f}" '
               f'stroke="#1e293b" stroke-width="1" marker-start="url(#arrDim)" marker-end="url(#arrDim)"/>')
    svg.append(f'<text x="{dim_x - 8}" y="{(p1[1]+p2[1])/2}" text-anchor="end" font-size="11" font-weight="700" fill="#1e293b" transform="rotate(-90 {dim_x - 8} {(p1[1]+p2[1])/2})">HEIGHT {height_mm:.0f}mm</text>')

# Pitch — find the steepest top chord segment, compute its angle
pitch_deg = 0
steepest = None
for c in chord_sticks:
    if 'TOP' not in usage_of(c).upper(): continue
    dx = c['x2'] - c['x1']
    dz = c['z2'] - c['z1']
    if abs(dx) < 10: continue
    angle = abs(math.degrees(math.atan2(abs(dz), abs(dx))))
    if angle > pitch_deg:
        pitch_deg = angle
        steepest = c
if steepest:
    midx = (steepest['x1'] + steepest['x2'])/2
    midz = (steepest['z1'] + steepest['z2'])/2
    mx, my = to_svg(midx, midz)
    svg.append(f'<text x="{mx + 30:.1f}" y="{my - 20:.1f}" font-size="11" font-weight="700" fill="#1e3a8a">PITCH {pitch_deg:.1f}°</text>')

# ---------- INSET: cross-section ----------
inset_x = W - 280
inset_y = TITLE_H + 30
inset_w = 240
inset_h = 320
svg.append(f'<rect x="{inset_x}" y="{inset_y}" width="{inset_w}" height="{inset_h}" '
           f'fill="white" stroke="#1e293b" stroke-width="1.5" rx="4"/>')
svg.append(f'<text x="{inset_x + inset_w/2}" y="{inset_y + 22}" text-anchor="middle" font-size="13" font-weight="700" fill="#1a202c">CROSS-SECTION at a joint</text>')
svg.append(f'<text x="{inset_x + inset_w/2}" y="{inset_y + 38}" text-anchor="middle" font-size="9" fill="#475569">Web meeting chord — looking down the chord length</text>')

# Cross-section drawing
xs_cx = inset_x + inset_w/2
xs_cy = inset_y + 130

# Chord (open up)
chord_w_xs = 100
chord_h_xs = 50
svg.append(f'<rect x="{xs_cx - chord_w_xs/2}" y="{xs_cy}" width="{chord_w_xs}" height="{chord_h_xs}" fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
# Lips at top corners
svg.append(f'<rect x="{xs_cx - chord_w_xs/2}" y="{xs_cy}" width="13" height="6" fill="#94a3b8" stroke="#1e293b" stroke-width="1"/>')
svg.append(f'<rect x="{xs_cx + chord_w_xs/2 - 13}" y="{xs_cy}" width="13" height="6" fill="#94a3b8" stroke="#1e293b" stroke-width="1"/>')
svg.append(f'<text x="{xs_cx + chord_w_xs/2 + 8}" y="{xs_cy + chord_h_xs/2 + 4}" font-size="10" fill="#1e3a8a" font-weight="700">chord</text>')

# Web sitting on top (its WEB face down on chord's WEB face)
web_w_xs = 80
web_h_xs = 40
web_y = xs_cy - web_h_xs - 4
svg.append(f'<rect x="{xs_cx - web_w_xs/2}" y="{web_y}" width="{web_w_xs}" height="{web_h_xs}" fill="#94a3b8" stroke="#1e293b" stroke-width="1.5"/>')
# Web flanges going down (open side down on chord)
svg.append(f'<rect x="{xs_cx - web_w_xs/2}" y="{web_y + web_h_xs - 6}" width="10" height="6" fill="#94a3b8" stroke="#1e293b" stroke-width="1"/>')
svg.append(f'<rect x="{xs_cx + web_w_xs/2 - 10}" y="{web_y + web_h_xs - 6}" width="10" height="6" fill="#94a3b8" stroke="#1e293b" stroke-width="1"/>')
svg.append(f'<text x="{xs_cx + web_w_xs/2 + 8}" y="{web_y + web_h_xs/2}" font-size="10" fill="#475569" font-weight="700">web</text>')

# Three M3.5 screws through both
screw_y_top = web_y - 14
screw_y_bot = xs_cy + chord_h_xs + 10
for i, dx in enumerate([-15, 0, 15]):
    sx = xs_cx + dx
    # Screw shaft
    svg.append(f'<rect x="{sx - 1.5}" y="{screw_y_top + 3}" width="3" height="{screw_y_bot - screw_y_top - 3}" fill="#231F20"/>')
    # Head
    svg.append(f'<rect x="{sx - 4}" y="{screw_y_top - 6}" width="8" height="9" fill="#231F20" rx="1"/>')
    # Point
    svg.append(f'<polygon points="{sx},{screw_y_bot + 4} {sx - 1.5},{screw_y_bot} {sx + 1.5},{screw_y_bot}" fill="#231F20"/>')

svg.append(f'<text x="{xs_cx}" y="{screw_y_top - 12}" text-anchor="middle" font-size="10" fill="#231F20" font-weight="700">3 × M3.5 screws</text>')
svg.append(f'<text x="{xs_cx}" y="{screw_y_bot + 22}" text-anchor="middle" font-size="9" font-style="italic" fill="#475569">17mm pitch — one rollformer fire</text>')

# Profile dimensions
svg.append(f'<text x="{xs_cx - chord_w_xs/2 - 5}" y="{xs_cy + chord_h_xs + 16}" text-anchor="end" font-size="9" fill="#64748b">89mm web</text>')

# ---------- Footer summary ----------
footer_y = H - SUMMARY_H + 5
svg.append(f'<rect x="0" y="{footer_y}" width="{W}" height="{SUMMARY_H - 5}" fill="#1f2937"/>')
svg.append(f'<text x="{PAD}" y="{footer_y + 24}" font-size="14" font-weight="700" fill="#FFCB05">Truss assembly facts</text>')

n_joints = len(unique_joints)
n_total_holes = n_joints * 6  # 3 holes on each side per joint
n_dimples = sum(len([op for op,_ in s['ops'] if op == 'INNER DIMPLE']) for s in sticks)

facts = [
    f'• {len(chord_sticks)} chord segments  +  {len(web_sticks)} web members  +  {len(box_sticks)} Box pieces  =  {len(sticks)} sticks total',
    f'• {n_joints} chord-to-web/chord junctions  ·  {n_joints * 3} bolt-hole fires  ·  {n_total_holes} physical bolt holes',
    f'• {n_dimples} INNER DIMPLE press points  (snap-fit between Box pieces and parent chord)',
    f'• Span {span_mm:.0f}mm  ·  Height {height_mm:.0f}mm  ·  Steepest pitch {pitch_deg:.1f}°',
    f'• Profile: 89×41 lipped C, 0.75mm gauge, AZ150 zinc-aluminium coating, G550 grade steel',
]
for i, fact in enumerate(facts):
    svg.append(f'<text x="{PAD}" y="{footer_y + 46 + i*16}" font-size="11" fill="white">{fact}</text>')

svg.append('</svg>')
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(svg))
print(f'Wrote {OUT}')
print(f'Joints: {n_joints} | Bolt fires: {n_joints*3} | Physical holes: {n_total_holes} | Dimples: {n_dimples}')
print(f'Span: {span_mm:.0f}mm | Height: {height_mm:.0f}mm | Pitch: {pitch_deg:.1f}°')
