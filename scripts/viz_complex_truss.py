"""Realistic full-truss view with multiple web angles.

Uses frame TN2-1 (most complex frame in the 2603191 truss) which has:
- 2 horizontal chord pieces (B1, C4 collar tie)
- 2 sloped top chord pieces (T2 apex, T3 main rake)
- Vertical webs (W5, W7, W9, W10)
- Diagonal webs (W6, W8)

Each member rendered as actual 89mm-wide band so you can see the
real overlap zones at every junction.
"""
import re
import math

XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075.xml'
OUT = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/complex_truss.svg'

text = open(XML).read()

def find_frame(name):
    s = text.find(f'<frame name="{name}"')
    if s < 0: return None
    e = text.find('</frame>', s) + len('</frame>')
    return text[s:e]

frame = find_frame('TN2-1')
if not frame:
    raise SystemExit('TN2-1 not found')

# Extract sticks
sticks = []
for m in re.finditer(r'<stick name="([^"]+)" type="([^"]+)"[^>]*?(?:usage="([^"]+)")?[^>]*>\s*<start>([^<]+)</start>\s*<end>([^<]+)</end>', frame):
    name, typ, usage, s, e = m.groups()
    sx,sy,sz = [float(v) for v in s.strip().split(',')]
    ex,ey,ez = [float(v) for v in e.strip().split(',')]
    sticks.append({'name':name, 'type':typ, 'usage':usage or '', 'start':(sx,sz), 'end':(ex,ez)})

fasteners = []
for m in re.finditer(r'<fastener name="(\d+)" count="(\d+)">\s*<point>([^<]+)</point>', frame):
    code, count, pt = m.groups()
    px,py,pz = [float(v) for v in pt.strip().split(',')]
    fasteners.append({'code':code, 'count':int(count), 'pt':(px,pz)})

print(f'Frame TN2-1: {len(sticks)} sticks, {len(fasteners)} fastener points')
for s in sticks:
    dx = s["end"][0]-s["start"][0]; dy = s["end"][1]-s["start"][1]
    L = math.hypot(dx, dy)
    angle = math.degrees(math.atan2(dy, dx))
    print(f'  {s["name"]:4s} {s["type"]:6s} {s["usage"]:12s} L={L:7.1f}mm  angle={angle:+6.1f}deg')

# View extent
all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
xmin, xmax = min(all_x), max(all_x)
zmin, zmax = min(all_z), max(all_z)
pad = 350
xmin -= pad; xmax += pad; zmin -= pad; zmax += pad

panel_w_mm = (xmax - xmin)
panel_h_mm = (zmax - zmin)
gap_mm = 700
total_w_mm = panel_w_mm * 2 + gap_mm
SCALE = 1700 / total_w_mm
W = int(total_w_mm * SCALE)
H = int(panel_h_mm * SCALE) + 160

def to_px_left(x, z):
    return ((x - xmin) * SCALE, H - 100 - (z - zmin) * SCALE)
def to_px_right(x, z):
    return ((x - xmin + panel_w_mm + gap_mm) * SCALE, H - 100 - (z - zmin) * SCALE)

# --- helpers to draw a member as an 89mm-wide rectangle along its axis ---
WIDTH_MM = 89.0  # member section width

def member_polygon(stick, scale_fn):
    """Return points of a 4-vertex polygon for a member of width 89mm."""
    sx, sz = stick['start']; ex, ez = stick['end']
    dx, dz = ex-sx, ez-sz
    L = math.hypot(dx, dz)
    if L == 0: return ''
    # perpendicular unit vector (rotated 90 deg CCW)
    nx, nz = -dz/L, dx/L
    half = WIDTH_MM/2
    p1 = (sx + nx*half, sz + nz*half)
    p2 = (sx - nx*half, sz - nz*half)
    p3 = (ex - nx*half, ez - nz*half)
    p4 = (ex + nx*half, ez + nz*half)
    pts = [scale_fn(*p) for p in (p1, p2, p3, p4)]
    return ' '.join(f'{x:.1f},{y:.1f}' for x,y in pts)

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
svg.append('''<defs>
  <pattern id="chord-fill" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)">
    <rect width="6" height="6" fill="#dbeafe"/>
    <line x1="0" y1="0" x2="0" y2="6" stroke="#93c5fd" stroke-width="0.6"/>
  </pattern>
  <pattern id="web-fill" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
    <rect width="6" height="6" fill="#e2e8f0"/>
    <line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" stroke-width="0.6"/>
  </pattern>
</defs>''')
svg.append(f'<rect width="{W}" height="{H}" fill="#fafaf8"/>')

# Title
svg.append(f'<text x="20" y="36" font-size="22" font-weight="700" fill="#1a202c">Complex truss frame TN2-1 — multiple web angles</text>')
svg.append(f'<text x="20" y="60" font-size="14" fill="#4a5568">10 members, 8 different angles. Each blue band is a chord plate; each grey band is a stud web. Where bands overlap, two layers of 0.75mm steel are stacked — that\'s the connection zone.</text>')
svg.append(f'<text x="20" y="80" font-size="13" fill="#374151">Frame is part of {len(sticks)} sticks total. {len(fasteners)} centreline-crossing connection points highlighted.</text>')

left_cx = panel_w_mm * SCALE / 2
right_cx = (panel_w_mm * 1.5 + gap_mm) * SCALE
svg.append(f'<text x="{left_cx:.0f}" y="115" text-anchor="middle" font-size="15" font-weight="700" fill="#7f1d1d">CURRENT — clusters of bolts at each junction</text>')
svg.append(f'<text x="{right_cx:.0f}" y="115" text-anchor="middle" font-size="15" font-weight="700" fill="#14532d">PROPOSED — one bolt per centreline crossing</text>')

def draw_panel(scale_fn, mode):
    # Layer 1: chords (drawn first so webs sit visually on top)
    chord_polys = []
    web_polys = []
    for s in sticks:
        poly = member_polygon(s, scale_fn)
        if not poly: continue
        if s['type'] == 'Plate':
            chord_polys.append((s, poly))
        else:
            web_polys.append((s, poly))
    # Draw chords as blue bands
    for s, poly in chord_polys:
        svg.append(f'<polygon points="{poly}" fill="url(#chord-fill)" stroke="#1d4ed8" stroke-width="1.6" opacity="0.95"/>')
    # Draw webs as grey bands (slight transparency so chord shows through at overlap)
    for s, poly in web_polys:
        svg.append(f'<polygon points="{poly}" fill="url(#web-fill)" stroke="#475569" stroke-width="1.4" opacity="0.85"/>')
    # Centrelines on top (solid colour by member type)
    for s in sticks:
        x1, y1 = scale_fn(*s['start'])
        x2, y2 = scale_fn(*s['end'])
        col = '#1d4ed8' if s['type'] == 'Plate' else '#334155'
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="1" stroke-dasharray="5 3" opacity="0.7"/>')
    # Member labels
    for s in sticks:
        mx = (s['start'][0] + s['end'][0]) / 2
        mz = (s['start'][1] + s['end'][1]) / 2
        px, py = scale_fn(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="12" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="#fafaf8" stroke-width="3.5" paint-order="stroke">{s["name"]}</text>')

draw_panel(to_px_left, 'old')

# Old: clusters of bolt dots at each fastener (count=N)
for f in fasteners:
    cx, cy = to_px_left(*f['pt'])
    n = f['count']
    # cluster N dots in small triangle/cluster
    for i in range(n):
        angle = (i * 2 * math.pi / max(n, 3)) - math.pi/2
        r = 7 if n > 1 else 0
        dx = r * math.cos(angle)
        dy = r * math.sin(angle)
        svg.append(f'<circle cx="{cx+dx:.1f}" cy="{cy+dy:.1f}" r="3" fill="#dc2626" stroke="#7f1d1d" stroke-width="0.8"/>')

draw_panel(to_px_right, 'new')

# New: one bolt per fastener, with subtle highlight ring on the crossing
for f in fasteners:
    cx, cy = to_px_right(*f['pt'])
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="none" stroke="#16a34a" stroke-width="1" opacity="0.5"/>')
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.8" fill="#16a34a" stroke="#14532d" stroke-width="1.2"/>')

# Stats
left_count = sum(f['count'] for f in fasteners)
right_count = len(fasteners)
svg.append(f'<rect x="40" y="{H-58}" width="{W-80}" height="42" fill="#f1f5f9" stroke="#cbd5e0" rx="3"/>')
svg.append(f'<text x="{left_cx:.0f}" y="{H-32}" text-anchor="middle" font-size="13" fill="#7f1d1d" font-weight="700">{left_count} bolt holes total</text>')
svg.append(f'<text x="{left_cx:.0f}" y="{H-18}" text-anchor="middle" font-size="11" fill="#7f1d1d">({len(fasteners)} junctions × ~{left_count/max(len(fasteners),1):.1f} holes each)</text>')
svg.append(f'<text x="{right_cx:.0f}" y="{H-32}" text-anchor="middle" font-size="13" fill="#14532d" font-weight="700">{right_count} bolt holes total</text>')
svg.append(f'<text x="{right_cx:.0f}" y="{H-18}" text-anchor="middle" font-size="11" fill="#14532d">(1 hole per junction = {(left_count-right_count)/left_count*100:.0f}% reduction)</text>')

svg.append('</svg>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(svg))
print(f'\nWrote {OUT}')
print(f'  Left:  {left_count} holes')
print(f'  Right: {right_count} holes')
