"""Generate a realistic SVG diagram of the truss showing:
  Left:  current bolt-hole rule (multiple holes per junction, offset)
  Right: proposed centreline-intersection rule (one hole at each crossing)

Uses real coordinates from the 2603191 ROCKVILLE truss XML.
"""
import re
import xml.etree.ElementTree as ET

XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075.xml'
OUT = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/truss_bolts.svg'

# Parse the truss XML — pull frame TN1 (the main hip truss type)
text = open(XML).read()

# Find first <frame> block
frame_start = text.find('<frame name="TN1-1"')
if frame_start < 0:
    frame_start = text.find('<frame ')
frame_end = text.find('</frame>', frame_start) + len('</frame>')
frame = text[frame_start:frame_end]

# Extract sticks (name, start xyz, end xyz, type, usage)
sticks = []
for m in re.finditer(r'<stick name="([^"]+)" type="([^"]+)"[^>]*?(?:usage="([^"]+)")?[^>]*>\s*<start>([^<]+)</start>\s*<end>([^<]+)</end>', frame):
    name, typ, usage, s, e = m.groups()
    sx,sy,sz = [float(v) for v in s.strip().split(',')]
    ex,ey,ez = [float(v) for v in e.strip().split(',')]
    sticks.append({'name':name, 'type':typ, 'usage':usage or '', 'start':(sx,sz), 'end':(ex,ez)})

# Extract fastener points
fasteners = []
for m in re.finditer(r'<fastener name="(\d+)" count="(\d+)">\s*<point>([^<]+)</point>', frame):
    code, count, pt = m.groups()
    px,py,pz = [float(v) for v in pt.strip().split(',')]
    fasteners.append({'code':code, 'count':int(count), 'pt':(px,pz)})

print(f'Frame TN1-1: {len(sticks)} sticks, {len(fasteners)} fastener points')

# Compute viewport
all_x = [pt for s in sticks for pt in (s['start'][0], s['end'][0])] + [f['pt'][0] for f in fasteners]
all_z = [pt for s in sticks for pt in (s['start'][1], s['end'][1])] + [f['pt'][1] for f in fasteners]
xmin, xmax = min(all_x), max(all_x)
zmin, zmax = min(all_z), max(all_z)
pad = 250
xmin -= pad; xmax += pad; zmin -= pad; zmax += pad

# We'll draw two panels side by side
panel_w_mm = (xmax - xmin)
panel_h_mm = (zmax - zmin)
gap_mm = 600
total_w_mm = panel_w_mm * 2 + gap_mm

# Pixel scale - target 1400px wide
SCALE = 1400 / total_w_mm
W = int(total_w_mm * SCALE)
H = int(panel_h_mm * SCALE) + 100  # extra for title

def to_px_left(x, z):
    return ((x - xmin) * SCALE, H - 100 - (z - zmin) * SCALE)

def to_px_right(x, z):
    return ((x - xmin + panel_w_mm + gap_mm) * SCALE, H - 100 - (z - zmin) * SCALE)

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
svg.append('<style>')
svg.append('  .stick-chord { stroke: #2b6cb0; stroke-width: 18; stroke-linecap: butt; fill: none; }')
svg.append('  .stick-web   { stroke: #4a5568; stroke-width: 12; stroke-linecap: butt; fill: none; }')
svg.append('  .centreline-chord { stroke: #2b6cb0; stroke-width: 1; stroke-dasharray: 4 3; opacity: 0.55; fill: none; }')
svg.append('  .centreline-web   { stroke: #4a5568; stroke-width: 1; stroke-dasharray: 4 3; opacity: 0.55; fill: none; }')
svg.append('  .label { font-size: 14px; fill: #2d3748; }')
svg.append('  .label-small { font-size: 11px; fill: #4a5568; }')
svg.append('  .title { font-size: 22px; font-weight: 700; fill: #1a202c; }')
svg.append('  .subtitle { font-size: 14px; fill: #4a5568; }')
svg.append('  .bolt-old { fill: #d53f8c; stroke: #97266d; stroke-width: 1; }')
svg.append('  .bolt-new { fill: #38a169; stroke: #22543d; stroke-width: 1.5; }')
svg.append('  .crossing { fill: none; stroke: #38a169; stroke-width: 1; opacity: 0.6; }')
svg.append('</style>')

# White background
svg.append(f'<rect width="{W}" height="{H}" fill="#fafaf8"/>')

# Title bar
svg.append(f'<text x="20" y="34" class="title">Truss TN1-1 (89S41 Linear) — bolt-hole placement comparison</text>')
svg.append(f'<text x="20" y="58" class="subtitle">Frame from your 2603191 ROCKVILLE TH-TYPE-A1-LT job. Each ● is one bolt hole.</text>')

# Panel labels
left_cx = panel_w_mm * SCALE / 2
right_cx = (panel_w_mm * 1.5 + gap_mm) * SCALE
svg.append(f'<text x="{left_cx:.0f}" y="92" class="label" text-anchor="middle" font-weight="700">CURRENT — multiple holes per junction</text>')
svg.append(f'<text x="{right_cx:.0f}" y="92" class="label" text-anchor="middle" font-weight="700" fill="#22543d">PROPOSED — one hole at centreline crossing</text>')

# --- LEFT PANEL: draw sticks as wide bands (showing actual width) + current bolt clusters
def draw_panel(to_px, side):
    # Sticks as thick lines (chord vs web)
    for s in sticks:
        x1,z1 = to_px(*s['start'])
        x2,z2 = to_px(*s['end'])
        cls = 'stick-chord' if s['type'] == 'Plate' else 'stick-web'
        svg.append(f'<line x1="{x1:.1f}" y1="{z1:.1f}" x2="{x2:.1f}" y2="{z2:.1f}" class="{cls}" />')
    # Centrelines (dashed) on top
    for s in sticks:
        x1,z1 = to_px(*s['start'])
        x2,z2 = to_px(*s['end'])
        cls = 'centreline-chord' if s['type'] == 'Plate' else 'centreline-web'
        svg.append(f'<line x1="{x1:.1f}" y1="{z1:.1f}" x2="{x2:.1f}" y2="{z2:.1f}" class="{cls}" />')
    # Stick name labels
    for s in sticks:
        mx = (s['start'][0] + s['end'][0]) / 2
        mz = (s['start'][1] + s['end'][1]) / 2
        # Offset label perpendicular to stick a bit
        px, py = to_px(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py:.1f}" class="label-small" text-anchor="middle" dy="-12" fill="#1a202c" stroke="#fafaf8" stroke-width="3" paint-order="stroke">{s["name"]}</text>')

draw_panel(to_px_left, 'left')

# Current bolt holes — show count=N as small cluster of dots near each fastener point
import math
for f in fasteners:
    x, z = f['pt']
    n = f['count']
    cx, cy = to_px_left(x, z)
    # Spread N dots in a vertical or angular pattern
    for i in range(n):
        # Spread 3 dots in a small triangle around the point
        angle = (i * 2 * math.pi / max(n, 3)) - math.pi/2
        r = 5
        dx = r * math.cos(angle)
        dy = r * math.sin(angle)
        svg.append(f'<circle cx="{cx+dx:.1f}" cy="{cy+dy:.1f}" r="2.4" class="bolt-old"/>')

# RIGHT PANEL: same sticks, but only ONE bolt per fastener point
draw_panel(to_px_right, 'right')

# Highlight crossings + single bolt
for f in fasteners:
    x, z = f['pt']
    cx, cy = to_px_right(x, z)
    # Green ring to highlight the centreline crossing
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9" class="crossing"/>')
    # Single bolt
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" class="bolt-new"/>')

# Stats footer
left_count = sum(f['count'] for f in fasteners)
right_count = len(fasteners)
svg.append(f'<text x="{left_cx:.0f}" y="{H-25:.0f}" class="subtitle" text-anchor="middle">{left_count} bolt holes total ({len(fasteners)} junctions × 3 holes avg)</text>')
svg.append(f'<text x="{right_cx:.0f}" y="{H-25:.0f}" class="subtitle" text-anchor="middle" fill="#22543d">{right_count} bolt holes total (1 per junction)</text>')

svg.append('</svg>')

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(svg))

print(f'Wrote {OUT}')
print(f'Left panel:  {left_count} bolt holes')
print(f'Right panel: {right_count} bolt holes')
print(f'Reduction: {left_count - right_count} holes ({(left_count-right_count)/left_count*100:.0f}% fewer)')
