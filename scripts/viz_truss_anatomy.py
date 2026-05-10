"""HYTEK Linear-truss anatomy — comprehensive visual explainer.

One large SVG covering:
  PANEL A — full truss elevation (U1-1 from real test data) with every
            machine operation colour-coded and counted
  PANEL B — zoom on a typical web-to-chord junction showing the flange/lip
            cuts that let two sticks lie flat (LIP NOTCH, LEG NOTCH, CHAMFER)
  PANEL C — zoom on an apex junction (multi-web into one chord position)
  PANEL D — zoom on a Box-piece clip-fit (dimple snap-fit mechanism)
  PANEL E — full tool legend with the role of every operation in the workflow

Everything driven by the real CSV at:
  ~/Desktop/2603191-GF-LIN-89.075.csv

Output: HYTEK_truss_anatomy_U1-1.svg on Desktop.
"""
import os, math

# Use the SIMPLIFIED CSV — bolt holes are at centreline-rule positions where
# stick centrelines actually cross. The original FrameCAD CSV has offset-based
# bolt positions that don't visually line up at the stick crossings.
CSV = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.simplified.csv'
DESKTOP = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop'
TRUSS = 'U4-1'
OUT = os.path.join(DESKTOP, f'HYTEK_truss_anatomy_{TRUSS}.svg')

# ---------- Op classification ----------
OP_COLORS = {
    'BOLT HOLES':       ('#dc2626', 'Web bolt holes',       'Ø3.8mm × 3 @ 17mm pitch — structural connection'),
    'WEB HOLES':        ('#dc2626', 'Web bolt holes',       'Ø3.8mm × 3 @ 17mm pitch — structural connection'),
    'INNER DIMPLE':     ('#f59e0b', 'Inner dimple',         'Press-formed snap-fit point for Box-piece assembly'),
    'SWAGE':            ('#94a3b8', 'Swage',                'Flange embossing — anti-buckling stiffener'),
    'LIP NOTCH':        ('#a78bfa', 'Lip notch',            'Removes lip material so adjacent sticks lie flat'),
    'LEFT LEG NOTCH':   ('#06b6d4', 'Left leg notch',       'Trims left flange heel for stick-on-stick fit'),
    'RIGHT LEG NOTCH':  ('#0ea5e9', 'Right leg notch',      'Trims right flange heel for stick-on-stick fit'),
    'TRUSS CHAMFER':    ('#ec4899', 'Truss chamfer',        'Large diagonal cut at stick end for steep angle joints'),
    'LEFT FLANGE':      ('#8b5cf6', 'Left flange (bend)',   'Programmed bend point for left flange'),
    'RIGHT FLANGE':     ('#8b5cf6', 'Right flange (bend)',  'Programmed bend point for right flange'),
    'LEFT PARTIAL FLANGE':  ('#7c3aed', 'Left partial flange', 'Partial flange — only part of the height bent'),
    'RIGHT PARTIAL FLANGE': ('#7c3aed', 'Right partial flange', 'Partial flange — only part of the height bent'),
    'SCREW HOLES':      ('#16a34a', 'Screw holes',          'Pilot holes for self-drilling screws'),
    'INNER NOTCH':      ('#84cc16', 'Inner notch',          'Web cut-out for service penetrations'),
    'INNER SERVICE':    ('#65a30d', 'Inner service hole',   'Larger hole for plumbing/electrical service'),
    'CHAMFER':          ('#ec4899', 'Chamfer',              'Diagonal corner cut'),
}

# ---------- CSV parser ----------
def parse_csv(path):
    sticks = []
    with open(path) as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) < 13 or parts[0] != 'COMPONENT': continue
            try:
                name, profile, usage = parts[1], parts[2], parts[3]
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
            sticks.append({'name': name, 'profile': profile, 'usage': usage,
                           'length': length, 'x1': x1, 'z1': z1, 'x2': x2, 'z2': z2,
                           'ops': ops})
    return sticks

all_sticks = parse_csv(CSV)
u11 = [s for s in all_sticks if s['name'].startswith(f'{TRUSS}-')]
# Compute summary for header
_n_sticks = len(u11)
_n_box = sum(1 for s in u11 if '(Box' in s['name'])
_n_web = sum(1 for s in u11 if 'WEB' in (s['usage'] or '').upper())
_max_len = max((s['length'] for s in u11), default=0)
_TRUSS_SUMMARY = f'{_n_sticks} sticks · {_n_web} webs · {_n_box} Box pieces · longest member {_max_len:.0f}mm'

# ---------- Page geometry ----------
W, H = 1700, 2400
svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')

# Defs
svg.append('''<defs>
  <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#e2e8f0"/><stop offset="100%" stop-color="#94a3b8"/>
  </linearGradient>
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="4" stroke="#64748b" stroke-width="0.4"/>
  </pattern>
  <marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
    <path d="M0,0 L7,3 L0,6 z" fill="#1f2937"/>
  </marker>
  <marker id="arrR" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
    <path d="M0,0 L7,3 L0,6 z" fill="#dc2626"/>
  </marker>
</defs>''')
svg.append(f'<rect width="{W}" height="{H}" fill="#f8fafc"/>')

# Header
svg.append(f'<rect x="0" y="0" width="{W}" height="64" fill="#231F20"/>')
svg.append(f'<rect x="0" y="0" width="8" height="64" fill="#FFCB05"/>')
svg.append(f'<text x="30" y="38" font-size="22" font-weight="800" fill="#FFCB05">HYTEK Linear Truss — full anatomy: tools, joints, flange cuts</text>')
svg.append(f'<text x="30" y="56" font-size="12" fill="white" opacity="0.85">Real example: {TRUSS} from job 2603191 ROCKVILLE TH-TYPE-A1-LT  ·  {_TRUSS_SUMMARY}  ·  3 fasteners per joint (per FrameCAD spec)</text>')

# ============ PANEL A: FULL TRUSS ELEVATION ============
PA_X, PA_Y, PA_W, PA_H = 30, 80, W - 60, 700
svg.append(f'<rect x="{PA_X}" y="{PA_Y}" width="{PA_W}" height="{PA_H}" fill="white" stroke="#cbd5e1" stroke-width="1.5" rx="6"/>')
svg.append(f'<text x="{PA_X + 20}" y="{PA_Y + 28}" font-size="16" font-weight="700" fill="#1a202c">A &#160; FULL TRUSS — every machine operation colour-coded</text>')
svg.append(f'<text x="{PA_X + 20}" y="{PA_Y + 46}" font-size="11" fill="#4a5568">All ops shown at their real machine positions on each stick. Hover-equivalent: see legend (Panel E) for what each colour means.</text>')

# Truss drawing area
TA_PAD = 60
ta_x0 = PA_X + TA_PAD
ta_x1 = PA_X + PA_W - 200  # leave room for op-count column on right
ta_y0 = PA_Y + 80
ta_y1 = PA_Y + PA_H - 60

# Bounds of U1-1 in world coords
xs = [s['x1'] for s in u11] + [s['x2'] for s in u11]
zs = [s['z1'] for s in u11] + [s['z2'] for s in u11]
minx, maxx = min(xs), max(xs)
minz, maxz = min(zs), max(zs)
span_x = max(1.0, maxx - minx)
span_z = max(1.0, maxz - minz)
scale = min((ta_x1 - ta_x0) / span_x, (ta_y1 - ta_y0) / span_z)
draw_w = span_x * scale
draw_h = span_z * scale
ox = ta_x0 + ((ta_x1 - ta_x0) - draw_w) / 2
oy = ta_y0 + ((ta_y1 - ta_y0) - draw_h) / 2 + draw_h  # flip z

def to_svg(x, z):
    return (ox + (x - minx) * scale, oy - (z - minz) * scale)

def stick_op_xz(s, pos):
    L = s['length']
    if L <= 0: return (s['x1'], s['z1'])
    t = pos / L
    return (s['x1'] + t * (s['x2'] - s['x1']),
            s['z1'] + t * (s['z2'] - s['z1']))

# Sticks (chords thicker, webs thinner)
def is_box(name): return '(Box' in name

# Main sticks first
for s in u11:
    if is_box(s['name']): continue
    x1p, y1p = to_svg(s['x1'], s['z1'])
    x2p, y2p = to_svg(s['x2'], s['z2'])
    usage = (s['usage'] or '').upper()
    if 'CHORD' in usage:
        stroke, sw = '#1e40af', 6
    else:
        stroke, sw = '#475569', 4
    svg.append(f'<line x1="{x1p:.1f}" y1="{y1p:.1f}" x2="{x2p:.1f}" y2="{y2p:.1f}" '
               f'stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>')
    # Stick name label
    midx, midy = (x1p + x2p) / 2, (y1p + y2p) / 2
    short_name = s['name'].replace(f'{TRUSS}-', '')
    if 'CHORD' in usage:
        svg.append(f'<text x="{midx}" y="{midy + 18}" text-anchor="middle" font-size="9" font-weight="700" fill="#1e3a8a">{short_name}</text>')
    else:
        svg.append(f'<text x="{midx + 6}" y="{midy + 4}" font-size="8" font-weight="700" fill="#475569">{short_name}</text>')

# Box pieces second (offset slightly)
for s in u11:
    if not is_box(s['name']): continue
    x1p, y1p = to_svg(s['x1'], s['z1'])
    x2p, y2p = to_svg(s['x2'], s['z2'])
    svg.append(f'<line x1="{x1p:.1f}" y1="{y1p - 5:.1f}" x2="{x2p:.1f}" y2="{y2p - 5:.1f}" '
               f'stroke="#fbbf24" stroke-width="3" stroke-linecap="round" stroke-dasharray="6,3"/>')
    midx, midy = (x1p + x2p) / 2, (y1p + y2p) / 2
    short = s['name'].replace(f'{TRUSS}-', '')
    svg.append(f'<text x="{midx}" y="{midy - 12}" text-anchor="middle" font-size="8" font-style="italic" fill="#92400e">{short}</text>')

# Ops as marks — non-bolt ops drawn per-stick. BOLT HOLES are grouped into
# joint-level markers below so the eye sees ONE 3-hole cluster at each
# centreline-crossing instead of two coincident dots.
op_count = {}
bolt_world_positions = []  # (xw, zw, parent_stick_dict) for grouping
for s in u11:
    for op, pos in s['ops']:
        op_count[op] = op_count.get(op, 0) + 1
        col = OP_COLORS.get(op, ('#888888', op, ''))[0]
        xw, zw = stick_op_xz(s, pos)
        xp, yp = to_svg(xw, zw)
        # Box pieces — apply same -5 offset
        if is_box(s['name']):
            yp -= 5
        if op in ('BOLT HOLES', 'WEB HOLES'):
            # Collect for joint-grouping; don't draw individually
            bolt_world_positions.append((xw, zw, s))
            continue
        if op == 'INNER DIMPLE':
            svg.append(f'<rect x="{xp-2.5:.1f}" y="{yp-2.5:.1f}" width="5" height="5" fill="{col}" stroke="white" stroke-width="0.5" transform="rotate(45 {xp:.1f} {yp:.1f})"/>')
        elif op == 'TRUSS CHAMFER' or op == 'CHAMFER':
            svg.append(f'<polygon points="{xp},{yp-4} {xp+3.5},{yp+2} {xp-3.5},{yp+2}" fill="{col}" opacity="0.9"/>')
        elif 'NOTCH' in op:
            svg.append(f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="1.5" fill="{col}" opacity="0.85"/>')
        elif op == 'SWAGE':
            svg.append(f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="1.0" fill="{col}" opacity="0.55"/>')
        elif 'FLANGE' in op:
            svg.append(f'<rect x="{xp-1.8:.1f}" y="{yp-1.8:.1f}" width="3.6" height="3.6" fill="{col}" opacity="0.85"/>')
        else:
            svg.append(f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="1.4" fill="{col}" opacity="0.8"/>')

# ---- Joint-level bolt-hole markers (the centreline rule, visualised) ----
# Group BOLT HOLES across sticks by world position (2mm tolerance). Each unique
# group = one centreline-crossing = one joint. Draw a single 3-hole cluster
# centred on the joint, with the cluster oriented perpendicular to the chord
# (or whichever stick passes nearest horizontally) so it reads as "3 punches".
GROUP_TOL = 2.0  # mm
joint_groups = []  # list of {world: (x,z), sticks: [s,...]}
for xw, zw, s in bolt_world_positions:
    matched = None
    for g in joint_groups:
        gx, gz = g['world']
        if abs(gx - xw) < GROUP_TOL and abs(gz - zw) < GROUP_TOL:
            matched = g
            break
    if matched:
        # Use mean of points for refined position
        n = len(matched['sticks']) + 1
        gx, gz = matched['world']
        matched['world'] = ((gx * (n-1) + xw) / n, (gz * (n-1) + zw) / n)
        matched['sticks'].append(s)
    else:
        joint_groups.append({'world': (xw, zw), 'sticks': [s]})

# Render each joint as a 3-hole cluster centred on the CL crossing
PITCH_PX = 17 * scale  # 17mm pitch in screen space
for g in joint_groups:
    gx, gz = g['world']
    cx, cy = to_svg(gx, gz)
    sticks = g['sticks']
    # Choose orientation perpendicular to the FIRST chord stick in the group
    # (chords are usually the longer/more horizontal; webs are short).
    chord_sticks = [s for s in sticks if 'CHORD' in (s['usage'] or '').upper()]
    ref_stick = chord_sticks[0] if chord_sticks else sticks[0]
    sx1, sz1 = ref_stick['x1'], ref_stick['z1']
    sx2, sz2 = ref_stick['x2'], ref_stick['z2']
    sdx, sdz = (sx2 - sx1), (sz2 - sz1)
    L = math.hypot(sdx, sdz) or 1.0
    # Perpendicular direction in WORLD space
    perp_wx, perp_wz = -sdz / L, sdx / L
    # Map to screen-space perpendicular (z is flipped on screen)
    perp_px = perp_wx * scale
    perp_py = -perp_wz * scale
    # Halo ring marking the joint
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="6.5" fill="none" stroke="#dc2626" stroke-width="0.7" opacity="0.45"/>')
    # 3 punches: -PITCH, 0, +PITCH along perpendicular
    for k in (-1, 0, 1):
        hx = cx + perp_px * k * 17
        hy = cy + perp_py * k * 17
        svg.append(f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="1.6" fill="#dc2626" stroke="white" stroke-width="0.4"/>')

op_count['BOLT HOLES (joints)'] = len(joint_groups)

# Op-count column on right of panel A
oc_x = ta_x1 + 30
oc_y = PA_Y + 100
svg.append(f'<text x="{oc_x}" y="{oc_y - 14}" font-size="12" font-weight="700" fill="#1a202c">Op count on this truss</text>')
total_ops = sum(op_count.values())
for i, (op, cnt) in enumerate(sorted(op_count.items(), key=lambda x: -x[1])):
    col = OP_COLORS.get(op, ('#888888', op, ''))[0]
    pretty = OP_COLORS.get(op, (col, op, ''))[1]
    svg.append(f'<rect x="{oc_x}" y="{oc_y + i*22}" width="14" height="14" fill="{col}" rx="2"/>')
    svg.append(f'<text x="{oc_x + 22}" y="{oc_y + i*22 + 12}" font-size="11" fill="#1a202c">{pretty}</text>')
    svg.append(f'<text x="{oc_x + 165}" y="{oc_y + i*22 + 12}" text-anchor="end" font-size="11" font-weight="700" fill="#1a202c">{cnt}</text>')
svg.append(f'<line x1="{oc_x}" y1="{oc_y + len(op_count)*22 + 4}" x2="{oc_x + 165}" y2="{oc_y + len(op_count)*22 + 4}" stroke="#94a3b8" stroke-width="1"/>')
svg.append(f'<text x="{oc_x}" y="{oc_y + len(op_count)*22 + 22}" font-size="11" font-weight="700" fill="#1a202c">TOTAL</text>')
svg.append(f'<text x="{oc_x + 165}" y="{oc_y + len(op_count)*22 + 22}" text-anchor="end" font-size="11" font-weight="700" fill="#dc2626">{total_ops} ops</text>')

# Truss axis labels
svg.append(f'<text x="{ox + draw_w/2}" y="{ta_y1 + 30}" text-anchor="middle" font-size="11" font-weight="700" fill="#475569">5509mm bottom chord — top chord splices into segments</text>')

# ============ PANEL B: WEB-TO-CHORD JUNCTION ZOOM ============
PB_X, PB_Y, PB_W, PB_H = 30, 800, 820, 720
svg.append(f'<rect x="{PB_X}" y="{PB_Y}" width="{PB_W}" height="{PB_H}" fill="white" stroke="#cbd5e1" stroke-width="1.5" rx="6"/>')
svg.append(f'<text x="{PB_X + 20}" y="{PB_Y + 28}" font-size="16" font-weight="700" fill="#1a202c">B &#160; WEB-TO-CHORD JUNCTION — how the flange cuts let it lie flat</text>')
svg.append(f'<text x="{PB_X + 20}" y="{PB_Y + 46}" font-size="11" fill="#4a5568">Detail through W11 meeting B1 at 45°. Without the cuts the lip and flange of W11 would collide with B1 and the joint wouldn\'t lie flat.</text>')

# === Side-by-side: BEFORE cuts vs AFTER cuts ===
SIDE_W = (PB_W - 80) / 2

# Helper: draw a C-section in profile (face view)
def c_section_profile(cx, cy, web_h, lflg, rflg, lip, fill='url(#steel)', label=None, label_dy=-20):
    """C-section seen from the open side. cx,cy = back of web midpoint."""
    out = []
    # Web (vertical line)
    out.append(f'<line x1="{cx}" y1="{cy - web_h/2}" x2="{cx}" y2="{cy + web_h/2}" stroke="#1e293b" stroke-width="3"/>')
    # Top flange (right-hand looking from open side)
    out.append(f'<line x1="{cx}" y1="{cy - web_h/2}" x2="{cx + rflg}" y2="{cy - web_h/2}" stroke="#1e293b" stroke-width="3"/>')
    out.append(f'<line x1="{cx + rflg}" y1="{cy - web_h/2}" x2="{cx + rflg}" y2="{cy - web_h/2 + lip}" stroke="#1e293b" stroke-width="3"/>')
    # Bottom flange
    out.append(f'<line x1="{cx}" y1="{cy + web_h/2}" x2="{cx + lflg}" y2="{cy + web_h/2}" stroke="#1e293b" stroke-width="3"/>')
    out.append(f'<line x1="{cx + lflg}" y1="{cy + web_h/2}" x2="{cx + lflg}" y2="{cy + web_h/2 - lip}" stroke="#1e293b" stroke-width="3"/>')
    if label:
        out.append(f'<text x="{cx + max(lflg,rflg)/2}" y="{cy + web_h/2 + label_dy + 30}" text-anchor="middle" font-size="10" font-weight="700" fill="#1a202c">{label}</text>')
    return out

# === BEFORE panel ===
b_x = PB_X + 20
b_y = PB_Y + 80
b_w = SIDE_W
b_h = PB_H - 110
svg.append(f'<rect x="{b_x}" y="{b_y}" width="{b_w}" height="{b_h}" fill="#fef2f2" stroke="#dc2626" stroke-width="1.2" rx="4"/>')
svg.append(f'<text x="{b_x + b_w/2}" y="{b_y + 24}" text-anchor="middle" font-size="13" font-weight="700" fill="#7f1d1d">WITHOUT flange cuts (BAD)</text>')
svg.append(f'<text x="{b_x + b_w/2}" y="{b_y + 42}" text-anchor="middle" font-size="10" fill="#7f1d1d">Web\'s lip + flange-heel collide with chord — sits proud, 6-8mm gap</text>')

# Drawing inside: chord horizontal, web meeting at angle, gap shown
b_cx = b_x + b_w/2
b_cy = b_y + b_h/2 + 40

# Chord drawn as a long horizontal C-section (open side facing up)
CHORD_LEN = 320
WEB_LEN = 200
SCALE_C = 1.4  # 1mm = 1.4px for cross-section
WEB_DEPTH = 89 * SCALE_C
LFLG = 38 * SCALE_C
RFLG = 41 * SCALE_C
LIP = 11 * SCALE_C

# Chord (horizontal, viewed from above — we see web back + flanges going up + lips coming back inward)
# Draw as a rectangle with notches at the lips
chord_y = b_cy + 40
svg.append(f'<rect x="{b_cx - CHORD_LEN/2}" y="{chord_y}" width="{CHORD_LEN}" height="{LFLG}" '
           f'fill="url(#steel)" stroke="#1e293b" stroke-width="2"/>')
# Lips (small inward returns at top)
svg.append(f'<rect x="{b_cx - CHORD_LEN/2}" y="{chord_y}" width="{CHORD_LEN}" height="{LIP}" '
           f'fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
svg.append(f'<text x="{b_cx + CHORD_LEN/2 + 8}" y="{chord_y + LFLG/2 + 4}" font-size="11" font-weight="700" fill="#1e40af">CHORD B1</text>')

# Web member coming down at 45° — full C-section profile UNCUT
# Web's centreline arrives at chord at b_cx, b_cy
web_angle = -math.radians(45)
web_dx = math.cos(web_angle) * WEB_LEN
web_dy = math.sin(web_angle) * WEB_LEN
# Web as a rectangle — width = web depth, length = WEB_LEN
# Compute corners by rotating
def rot(px, py, ang, ox, oy):
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = px - ox, py - oy
    return (ox + c*dx - s*dy, oy + s*dx + c*dy)

# In its own frame, web is a rectangle from (0, -WEB_DEPTH/2) to (WEB_LEN, +WEB_DEPTH/2)
# Its end (cut end) sits AT the chord centreline (b_cx, b_cy = chord_y at top of flange)
# Without notch: extend the web all the way INTO the chord — this is the "would collide" state
web_end_x, web_end_y = b_cx, b_cy  # this is where the centreline of web meets chord

# Web rectangle corners (uncut)
corners = []
for px, py in [(0, -WEB_DEPTH/2), (WEB_LEN, -WEB_DEPTH/2), (WEB_LEN, WEB_DEPTH/2), (0, WEB_DEPTH/2)]:
    rx = web_end_x + math.cos(web_angle) * px - math.sin(web_angle) * py
    ry = web_end_y + math.sin(web_angle) * px + math.cos(web_angle) * py
    corners.append((rx, ry))
points = ' '.join(f'{x:.1f},{y:.1f}' for x, y in corners)
svg.append(f'<polygon points="{points}" fill="url(#steel)" stroke="#dc2626" stroke-width="2.5" stroke-dasharray="4,3"/>')
svg.append(f'<text x="{web_end_x + math.cos(web_angle)*WEB_LEN*0.6 + 12}" y="{web_end_y + math.sin(web_angle)*WEB_LEN*0.6}" font-size="11" font-weight="700" fill="#475569">WEB W11 (uncut)</text>')

# Highlight the COLLISION zone (where the web's lip would go through the chord's lip)
collision_cx = b_cx
collision_cy = chord_y + LFLG/2
svg.append(f'<circle cx="{collision_cx}" cy="{collision_cy}" r="32" fill="none" stroke="#dc2626" stroke-width="3" stroke-dasharray="5,3"/>')
svg.append(f'<text x="{collision_cx + 38}" y="{collision_cy - 8}" font-size="11" font-weight="700" fill="#7f1d1d">collision zone</text>')
svg.append(f'<text x="{collision_cx + 38}" y="{collision_cy + 6}" font-size="9" fill="#7f1d1d">web lip + flange</text>')
svg.append(f'<text x="{collision_cx + 38}" y="{collision_cy + 18}" font-size="9" fill="#7f1d1d">would intersect chord lip</text>')

# Notes (inside before-panel, bottom)
notes_y = b_y + b_h - 80
svg.append(f'<text x="{b_x + 14}" y="{notes_y}" font-size="11" font-weight="700" fill="#7f1d1d">Result without cuts:</text>')
svg.append(f'<text x="{b_x + 14}" y="{notes_y + 16}" font-size="10" fill="#7f1d1d">• Web sits proud of chord by 6-8mm</text>')
svg.append(f'<text x="{b_x + 14}" y="{notes_y + 30}" font-size="10" fill="#7f1d1d">• Bolt holes don\'t align in same plane</text>')
svg.append(f'<text x="{b_x + 14}" y="{notes_y + 44}" font-size="10" fill="#7f1d1d">• Joint is loose, screws over-stress</text>')
svg.append(f'<text x="{b_x + 14}" y="{notes_y + 58}" font-size="10" fill="#7f1d1d">• On-site fix = angle grinder = bad</text>')

# === AFTER panel ===
a_x = b_x + b_w + 40
a_y = b_y
a_w = b_w
a_h = b_h
svg.append(f'<rect x="{a_x}" y="{a_y}" width="{a_w}" height="{a_h}" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.2" rx="4"/>')
svg.append(f'<text x="{a_x + a_w/2}" y="{a_y + 24}" text-anchor="middle" font-size="13" font-weight="700" fill="#14532d">WITH flange cuts (GOOD)</text>')
svg.append(f'<text x="{a_x + a_w/2}" y="{a_y + 42}" text-anchor="middle" font-size="10" fill="#14532d">LIP NOTCH + LEG NOTCH at web end clear the chord — joint lies flat in one plane</text>')

a_cx = a_x + a_w/2
a_cy = a_y + a_h/2 + 40

# Same chord
chord_y_a = a_cy + 40
svg.append(f'<rect x="{a_cx - CHORD_LEN/2}" y="{chord_y_a}" width="{CHORD_LEN}" height="{LFLG}" '
           f'fill="url(#steel)" stroke="#1e293b" stroke-width="2"/>')
svg.append(f'<rect x="{a_cx - CHORD_LEN/2}" y="{chord_y_a}" width="{CHORD_LEN}" height="{LIP}" '
           f'fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
svg.append(f'<text x="{a_cx + CHORD_LEN/2 + 8}" y="{chord_y_a + LFLG/2 + 4}" font-size="11" font-weight="700" fill="#1e40af">CHORD B1</text>')

# Web with cuts — chamfered end + lip notches
web_end_x_a, web_end_y_a = a_cx, a_cy

# After cuts, the web's footprint at the joint is REDUCED:
# - The leading lip is notched away (LIP NOTCH) — so the inside corner is open
# - The flange-heel is trimmed back (LEG NOTCH) on each side
# - The cut end has a chamfer matching the angle (TRUSS CHAMFER)
# Effective web footprint: the centreline still hits the chord, but the corners are shaped to clear

# Draw the cut web as a polygon: flat top (web back), notched bottom near the cut
web_pts_local = [
    (0, -WEB_DEPTH/2),                  # cut end, web back
    (WEB_LEN, -WEB_DEPTH/2),            # far end, web back
    (WEB_LEN, WEB_DEPTH/2),             # far end, open side
    (28, WEB_DEPTH/2),                  # comes back to where notch starts
    (24, WEB_DEPTH/2 - LIP*0.7),        # lip notch corner
    (10, WEB_DEPTH/2 - LIP*0.7),        # lip notch back
    (0, WEB_DEPTH/2 - LIP*1.2),         # chamfer — angled cut at the very end
]
corners_a = []
for px, py in web_pts_local:
    rx = web_end_x_a + math.cos(web_angle) * px - math.sin(web_angle) * py
    ry = web_end_y_a + math.sin(web_angle) * px + math.cos(web_angle) * py
    corners_a.append((rx, ry))
points_a = ' '.join(f'{x:.1f},{y:.1f}' for x, y in corners_a)
svg.append(f'<polygon points="{points_a}" fill="url(#steel)" stroke="#16a34a" stroke-width="2.5"/>')

# Annotate the cut features
# Lip notch arrow
ln_local = (15, WEB_DEPTH/2 - LIP*0.7)
ln_x = web_end_x_a + math.cos(web_angle) * ln_local[0] - math.sin(web_angle) * ln_local[1]
ln_y = web_end_y_a + math.sin(web_angle) * ln_local[0] + math.cos(web_angle) * ln_local[1]
ann_x = a_x + 28
svg.append(f'<line x1="{ann_x + 100}" y1="{a_y + 90}" x2="{ln_x:.1f}" y2="{ln_y:.1f}" stroke="#a78bfa" stroke-width="1.5" marker-end="url(#arr)"/>')
svg.append(f'<text x="{ann_x}" y="{a_y + 90}" font-size="11" font-weight="700" fill="#5b21b6">LIP NOTCH</text>')
svg.append(f'<text x="{ann_x}" y="{a_y + 104}" font-size="9" fill="#5b21b6">cuts away the 11mm lip return</text>')

# Truss chamfer arrow
tc_local = (5, WEB_DEPTH/2 - LIP*0.95)
tc_x = web_end_x_a + math.cos(web_angle) * tc_local[0] - math.sin(web_angle) * tc_local[1]
tc_y = web_end_y_a + math.sin(web_angle) * tc_local[0] + math.cos(web_angle) * tc_local[1]
svg.append(f'<line x1="{ann_x + 100}" y1="{a_y + 130}" x2="{tc_x:.1f}" y2="{tc_y:.1f}" stroke="#ec4899" stroke-width="1.5" marker-end="url(#arr)"/>')
svg.append(f'<text x="{ann_x}" y="{a_y + 130}" font-size="11" font-weight="700" fill="#9d174d">TRUSS CHAMFER</text>')
svg.append(f'<text x="{ann_x}" y="{a_y + 144}" font-size="9" fill="#9d174d">angled end cut matches slope</text>')

# Leg notch arrow (other side)
gn_x = web_end_x_a + math.cos(web_angle) * 35 - math.sin(web_angle) * (-WEB_DEPTH/2 + 5)
gn_y = web_end_y_a + math.sin(web_angle) * 35 + math.cos(web_angle) * (-WEB_DEPTH/2 + 5)
svg.append(f'<line x1="{a_x + a_w - 30}" y1="{a_y + 130}" x2="{gn_x:.1f}" y2="{gn_y:.1f}" stroke="#06b6d4" stroke-width="1.5" marker-end="url(#arr)"/>')
svg.append(f'<text x="{a_x + a_w - 130}" y="{a_y + 124}" font-size="11" font-weight="700" fill="#155e75">LEG NOTCH</text>')
svg.append(f'<text x="{a_x + a_w - 175}" y="{a_y + 138}" font-size="9" fill="#155e75">trims flange-heel back</text>')

# Web label
mid_web_x = web_end_x_a + math.cos(web_angle) * WEB_LEN * 0.6
mid_web_y = web_end_y_a + math.sin(web_angle) * WEB_LEN * 0.6
svg.append(f'<text x="{mid_web_x + 14}" y="{mid_web_y - 2}" font-size="11" font-weight="700" fill="#475569">WEB W11 (notched)</text>')

# Bolt holes through both
bolt_cx = a_cx
bolt_cy = chord_y_a + LIP + 4
PITCH_BOLT = 17 * SCALE_C
for dx in [-PITCH_BOLT, 0, PITCH_BOLT]:
    # On the web side (perpendicular to web axis)
    bx = bolt_cx + math.cos(web_angle - math.pi/2) * dx * 0.5
    by = bolt_cy + math.sin(web_angle - math.pi/2) * dx * 0.5
    svg.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="3.5" fill="#231F20" stroke="#FFCB05" stroke-width="0.8"/>')
svg.append(f'<text x="{bolt_cx + 38}" y="{bolt_cy - 10}" font-size="10" font-weight="700" fill="#231F20">3 × Ø3.8mm</text>')

# Notes after-panel bottom
notes_ya = a_y + a_h - 80
svg.append(f'<text x="{a_x + 14}" y="{notes_ya}" font-size="11" font-weight="700" fill="#14532d">Result with cuts:</text>')
svg.append(f'<text x="{a_x + 14}" y="{notes_ya + 16}" font-size="10" fill="#14532d">• Web sits flat against chord (no gap)</text>')
svg.append(f'<text x="{a_x + 14}" y="{notes_ya + 30}" font-size="10" fill="#14532d">• Three bolts pass cleanly through</text>')
svg.append(f'<text x="{a_x + 14}" y="{notes_ya + 44}" font-size="10" fill="#14532d">• Joint loads in pure shear (designed for)</text>')
svg.append(f'<text x="{a_x + 14}" y="{notes_ya + 58}" font-size="10" fill="#14532d">• No site fitting — assembled in seconds</text>')

# ============ PANEL C: BOX CLIP-FIT ============
PC_X, PC_Y, PC_W, PC_H = 870, 800, 800, 720
svg.append(f'<rect x="{PC_X}" y="{PC_Y}" width="{PC_W}" height="{PC_H}" fill="white" stroke="#cbd5e1" stroke-width="1.5" rx="6"/>')
svg.append(f'<text x="{PC_X + 20}" y="{PC_Y + 28}" font-size="16" font-weight="700" fill="#1a202c">C &#160; BOX-PIECE CLIP-FIT — how dimples lock the assembly</text>')
svg.append(f'<text x="{PC_X + 20}" y="{PC_Y + 46}" font-size="11" fill="#4a5568">B1 (Box1) clips onto main chord B1 at world position 589mm. Inward dimples on chord lock into outward dimples on Box.</text>')

# 3D-ish exploded view
ec_x = PC_X + PC_W/2
ec_y = PC_Y + 100

# Main chord (open up)
mc_y = ec_y + 200
mc_len = 600
mc_x = ec_x - mc_len/2
svg.append(f'<rect x="{mc_x}" y="{mc_y}" width="{mc_len}" height="60" fill="url(#steel)" stroke="#1e293b" stroke-width="2"/>')
# Lips at top edges
svg.append(f'<rect x="{mc_x}" y="{mc_y}" width="{mc_len}" height="8" fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
svg.append(f'<text x="{mc_x + mc_len + 10}" y="{mc_y + 35}" font-size="11" font-weight="700" fill="#1e40af">MAIN CHORD B1</text>')
svg.append(f'<text x="{mc_x + mc_len + 10}" y="{mc_y + 50}" font-size="9" fill="#64748b">(open side facing up)</text>')

# Inner dimples on chord (inward press = circles with dot)
chord_dimples = [80, 220, 360, 500]  # mm-ish positions in drawing space
for dx in chord_dimples:
    dim_x = mc_x + dx
    dim_y = mc_y + 35
    svg.append(f'<rect x="{dim_x-5}" y="{dim_y-5}" width="10" height="10" fill="#f59e0b" stroke="#92400e" stroke-width="1" transform="rotate(45 {dim_x} {dim_y})"/>')

# Box piece (above, exploded view)
box_y = ec_y - 30
box_len = mc_len * 0.8
box_x = ec_x - box_len/2
svg.append(f'<rect x="{box_x}" y="{box_y}" width="{box_len}" height="60" fill="url(#steel)" stroke="#1e293b" stroke-width="2"/>')
# Lips at bottom edges (Box flips upside down compared to chord — open side faces DOWN)
svg.append(f'<rect x="{box_x}" y="{box_y + 52}" width="{box_len}" height="8" fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
svg.append(f'<text x="{box_x + box_len + 10}" y="{box_y + 25}" font-size="11" font-weight="700" fill="#92400e">BOX PIECE B1(Box1)</text>')
svg.append(f'<text x="{box_x + box_len + 10}" y="{box_y + 40}" font-size="9" fill="#64748b">(open side facing down)</text>')

# Box dimples (outward press)
box_dimples_local = [50, 190, 330, 470]
for dx in box_dimples_local:
    dim_x = box_x + dx
    dim_y = box_y + 35
    svg.append(f'<rect x="{dim_x-5}" y="{dim_y-5}" width="10" height="10" fill="#f59e0b" stroke="#92400e" stroke-width="1" transform="rotate(45 {dim_x} {dim_y})"/>')

# Arrows showing alignment
for i, (cd, bd) in enumerate(zip(chord_dimples, box_dimples_local)):
    chord_dim_x = mc_x + cd
    box_dim_x = box_x + bd
    # Both should be at same world X if box is at offset 30 — visually they line up
    # Draw vertical arrow from box dimple down to chord dimple
    svg.append(f'<line x1="{box_dim_x}" y1="{box_y + 50}" x2="{chord_dim_x}" y2="{mc_y - 4}" '
               f'stroke="#16a34a" stroke-width="1" stroke-dasharray="3,2" marker-end="url(#arr)"/>')

# CL-to-CL annotation
svg.append(f'<text x="{ec_x}" y="{(box_y + mc_y) / 2 + 20}" text-anchor="middle" font-size="11" font-weight="700" fill="#16a34a">CL-to-CL alignment — every dimple matches</text>')
svg.append(f'<text x="{ec_x}" y="{(box_y + mc_y) / 2 + 36}" text-anchor="middle" font-size="9" font-style="italic" fill="#16a34a">(15mm from each end · max 900mm gap)</text>')

# Below: cross-section showing how the dimples lock
xs_y = mc_y + 130
xs_w = 380
xs_x = ec_x - xs_w/2
svg.append(f'<rect x="{xs_x}" y="{xs_y}" width="{xs_w}" height="180" fill="#fefce8" stroke="#a16207" stroke-width="1" rx="4"/>')
svg.append(f'<text x="{ec_x}" y="{xs_y + 22}" text-anchor="middle" font-size="12" font-weight="700" fill="#713f12">Cross-section: how the snap-fit works</text>')

# Cross-section — chord (bottom) + box (top), both with their dimples
xc_cx = ec_x
xc_cy = xs_y + 110
# Chord lower-half C (cup shape — opens upward)
svg.append(f'<rect x="{xc_cx - 80}" y="{xc_cy}" width="160" height="40" fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
# Lips bent inward at top
svg.append(f'<rect x="{xc_cx - 80}" y="{xc_cy}" width="20" height="8" fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
svg.append(f'<rect x="{xc_cx + 60}" y="{xc_cy}" width="20" height="8" fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
# Inward dimples on chord lips (poking into the channel)
svg.append(f'<polygon points="{xc_cx-70},{xc_cy+8} {xc_cx-66},{xc_cy+14} {xc_cx-74},{xc_cy+14}" fill="#f59e0b" stroke="#92400e" stroke-width="0.8"/>')
svg.append(f'<polygon points="{xc_cx+70},{xc_cy+8} {xc_cx+66},{xc_cy+14} {xc_cx+74},{xc_cy+14}" fill="#f59e0b" stroke="#92400e" stroke-width="0.8"/>')

# Box upper-half (cup shape opens DOWNWARD — flipped C)
box_top_y = xc_cy - 50
svg.append(f'<rect x="{xc_cx - 80}" y="{box_top_y}" width="160" height="40" fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
svg.append(f'<rect x="{xc_cx - 80}" y="{box_top_y + 32}" width="20" height="8" fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
svg.append(f'<rect x="{xc_cx + 60}" y="{box_top_y + 32}" width="20" height="8" fill="#cbd5e1" stroke="#1e293b" stroke-width="1.5"/>')
# Outward dimples on box lips (sticking out of the channel down)
svg.append(f'<polygon points="{xc_cx-70},{box_top_y+32} {xc_cx-66},{box_top_y+26} {xc_cx-74},{box_top_y+26}" fill="#f59e0b" stroke="#92400e" stroke-width="0.8"/>')
svg.append(f'<polygon points="{xc_cx+70},{box_top_y+32} {xc_cx+66},{box_top_y+26} {xc_cx+74},{box_top_y+26}" fill="#f59e0b" stroke="#92400e" stroke-width="0.8"/>')

# Annotations
svg.append(f'<text x="{xc_cx + 100}" y="{box_top_y + 24}" font-size="10" fill="#92400e">Box (upper C, open down)</text>')
svg.append(f'<text x="{xc_cx + 100}" y="{xc_cy + 28}" font-size="10" fill="#92400e">Chord (lower C, open up)</text>')
svg.append(f'<text x="{xc_cx - 220}" y="{(xc_cy + box_top_y)/2 + 8}" font-size="10" font-weight="700" fill="#a16207">Dimples interlock</text>')
svg.append(f'<text x="{xc_cx - 220}" y="{(xc_cy + box_top_y)/2 + 22}" font-size="9" fill="#a16207">friction-fit, no bolts</text>')

# ============ PANEL E: TOOL LEGEND (full) ============
PE_X, PE_Y, PE_W, PE_H = 30, 1540, W - 60, 540
svg.append(f'<rect x="{PE_X}" y="{PE_Y}" width="{PE_W}" height="{PE_H}" fill="white" stroke="#cbd5e1" stroke-width="1.5" rx="6"/>')
svg.append(f'<text x="{PE_X + 20}" y="{PE_Y + 28}" font-size="16" font-weight="700" fill="#1a202c">D &#160; TOOL LEGEND — every operation explained</text>')
svg.append(f'<text x="{PE_X + 20}" y="{PE_Y + 46}" font-size="11" fill="#4a5568">Each row: tool name · what the F300i does · what it\'s for · whether the simplifier touches it.</text>')

# Tools grouped by category
tool_groups = [
    ('STRUCTURAL CONNECTION', [
        ('BOLT HOLES', '3 × Ø3.8mm punches at 17mm pitch perpendicular to stick length', 'Web-to-chord screw connection — three M3.5 screws per joint',  'REWRITTEN by simplifier (centreline rule)'),
        ('SCREW HOLES', 'Single small pilot hole', 'Self-drilling screws into the C-section', 'Preserved exactly'),
    ]),
    ('FLANGE CUTS — let sticks lie flat', [
        ('LIP NOTCH',         'Cuts away the 11mm lip return at specified position', 'Clears the chord\'s lip when web meets chord at angle', 'Preserved exactly'),
        ('LEFT LEG NOTCH',    'Trims left flange height back to web', 'Clears the chord\'s flange-heel for stick-on-stick fit', 'Preserved exactly'),
        ('RIGHT LEG NOTCH',   'Trims right flange height back to web', 'Clears the chord\'s flange-heel for stick-on-stick fit', 'Preserved exactly'),
        ('TRUSS CHAMFER',     'Large diagonal cut at stick end', 'Used at very steep angles where lip notch alone is insufficient', 'Preserved exactly'),
    ]),
    ('FLANGE FORMING — bends and partials', [
        ('LEFT FLANGE',       'Programmed bend at the rollformer\'s flange station', 'Forms the left flange at the specified position', 'Preserved exactly'),
        ('RIGHT FLANGE',      'Programmed bend at the rollformer\'s flange station', 'Forms the right flange at the specified position', 'Preserved exactly'),
        ('LEFT PARTIAL FLANGE',  'Partial bend — only part of the flange height', 'Used where a full flange would interfere with another stick', 'Preserved exactly'),
        ('RIGHT PARTIAL FLANGE', 'Partial bend — only part of the flange height', 'Used where a full flange would interfere with another stick', 'Preserved exactly'),
    ]),
    ('BOX-PIECE ASSEMBLY', [
        ('INNER DIMPLE',      'Press-formed dimple — outward on Box, inward on chord', 'Snap-fit alignment when Box clips onto main chord', 'REWRITTEN by simplifier (15mm/900mm rule)'),
    ]),
    ('STIFFENING &amp; SERVICES', [
        ('SWAGE',             'Linear flange embossing along part of the stick', 'Anti-buckling stiffener on slender sticks', 'Preserved exactly'),
        ('INNER NOTCH',       'Web cut-out', 'Allows service penetrations (small holes)', 'Preserved exactly'),
        ('INNER SERVICE',     'Larger web cut-out', 'Plumbing or electrical services pass through', 'Preserved exactly'),
    ]),
]

ly = PE_Y + 70
COL_W = (PE_W - 40) / 2
col1_x = PE_X + 20
col2_x = PE_X + 20 + COL_W
ly1 = ly
ly2 = ly
side_toggle = 0

for group_name, ops in tool_groups:
    # Group header
    if side_toggle == 0:
        gx, gy = col1_x, ly1
    else:
        gx, gy = col2_x, ly2
    svg.append(f'<text x="{gx}" y="{gy + 12}" font-size="12" font-weight="700" fill="#1a202c">{group_name}</text>')
    if side_toggle == 0: ly1 += 22
    else: ly2 += 22
    for op_name, what, why, simp in ops:
        if side_toggle == 0:
            cy = ly1
        else:
            cy = ly2
        col = OP_COLORS.get(op_name, ('#888', op_name, ''))[0]
        svg.append(f'<rect x="{gx}" y="{cy}" width="14" height="14" fill="{col}" rx="2"/>')
        svg.append(f'<text x="{gx + 22}" y="{cy + 11}" font-size="11" font-weight="700" fill="#1a202c">{op_name}</text>')
        svg.append(f'<text x="{gx + 22}" y="{cy + 25}" font-size="9" fill="#374151">{what}</text>')
        svg.append(f'<text x="{gx + 22}" y="{cy + 38}" font-size="9" font-style="italic" fill="#64748b">→ {why}</text>')
        simp_col = '#dc2626' if 'REWRITTEN' in simp else '#16a34a'
        svg.append(f'<text x="{gx + 22}" y="{cy + 50}" font-size="9" font-weight="700" fill="{simp_col}">{simp}</text>')
        if side_toggle == 0: ly1 += 60
        else: ly2 += 60
    if side_toggle == 0: ly1 += 12
    else: ly2 += 12
    side_toggle = 1 - side_toggle

# Footer
svg.append(f'<text x="{W/2}" y="{H - 20}" text-anchor="middle" font-size="10" fill="#64748b">'
           'Simplifier rewrites BOLT HOLES + INNER DIMPLE only. All physical-fit ops (notches, chamfers, swages, flange bends) preserved byte-identical.'
           '</text>')

svg.append('</svg>')

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(svg))
print(f'Wrote {OUT}')
print(f'Page size: {W}x{H} px')
