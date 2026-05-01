"""Same complex truss but with apex/heel clusters merged into single bolts.

If multiple centreline crossings fall within TOL mm of each other, replace
them with one bolt at the centroid of the cluster.
"""
import re, math
XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075.xml'
OUT = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/complex_truss_clustered.svg'
TOL = 80.0   # mm — crossings within this distance get merged

text = open(XML).read()
s = text.find('<frame name="TN2-1"'); e = text.find('</frame>', s)+len('</frame>')
frame = text[s:e]

sticks = []
for m in re.finditer(r'<stick name="([^"]+)" type="([^"]+)"[^>]*>\s*<start>([^<]+)</start>\s*<end>([^<]+)</end>', frame):
    name, typ, st, en = m.groups()
    sx,sy,sz = [float(v) for v in st.strip().split(',')]
    ex,ey,ez = [float(v) for v in en.strip().split(',')]
    sticks.append({'name':name,'type':typ,'start':(sx,sz),'end':(ex,ez)})

raw_pts = []
for m in re.finditer(r'<fastener name="(\d+)" count="(\d+)">\s*<point>([^<]+)</point>', frame):
    code, count, pt = m.groups()
    px,py,pz = [float(v) for v in pt.strip().split(',')]
    raw_pts.append((px, pz, int(count)))

# Cluster points within TOL using simple union-find
n = len(raw_pts)
parent = list(range(n))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i
def union(i, j):
    ri, rj = find(i), find(j)
    if ri != rj: parent[ri] = rj

for i in range(n):
    for j in range(i+1, n):
        d = math.hypot(raw_pts[i][0]-raw_pts[j][0], raw_pts[i][1]-raw_pts[j][1])
        if d <= TOL: union(i, j)

clusters = {}
for i, pt in enumerate(raw_pts):
    r = find(i)
    clusters.setdefault(r, []).append(pt)

merged = []
for cluster in clusters.values():
    cx = sum(p[0] for p in cluster) / len(cluster)
    cy = sum(p[1] for p in cluster) / len(cluster)
    merged.append({'pt':(cx,cy), 'merged_from':len(cluster)})

print(f'Raw centreline crossings: {len(raw_pts)}')
print(f'After clustering (within {TOL}mm): {len(merged)} bolts')
print(f'Reduction: {len(raw_pts)-len(merged)} bolts removed')

# Render
all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
xmin, xmax = min(all_x)-350, max(all_x)+350
zmin, zmax = min(all_z)-350, max(all_z)+350
panel_w_mm = xmax-xmin; panel_h_mm = zmax-zmin
gap_mm = 700
SCALE = 1700 / (panel_w_mm*2 + gap_mm)
W = int((panel_w_mm*2+gap_mm)*SCALE); H = int(panel_h_mm*SCALE)+160

def to_left(x,z): return ((x-xmin)*SCALE, H-100-(z-zmin)*SCALE)
def to_right(x,z): return ((x-xmin+panel_w_mm+gap_mm)*SCALE, H-100-(z-zmin)*SCALE)

WIDTH_MM = 89.0
def member_polygon(stick, scale_fn):
    sx,sz = stick['start']; ex,ez = stick['end']
    dx, dz = ex-sx, ez-sz
    L = math.hypot(dx, dz)
    if L == 0: return ''
    nx, nz = -dz/L, dx/L
    h = WIDTH_MM/2
    pts = [(sx+nx*h, sz+nz*h), (sx-nx*h, sz-nz*h), (ex-nx*h, ez-nz*h), (ex+nx*h, ez+nz*h)]
    return ' '.join(f'{a:.1f},{b:.1f}' for a,b in (scale_fn(*p) for p in pts))

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
svg.append('''<defs>
  <pattern id="cf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)">
    <rect width="6" height="6" fill="#dbeafe"/><line x1="0" y1="0" x2="0" y2="6" stroke="#93c5fd" stroke-width="0.6"/>
  </pattern>
  <pattern id="wf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
    <rect width="6" height="6" fill="#e2e8f0"/><line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" stroke-width="0.6"/>
  </pattern>
</defs>''')
svg.append(f'<rect width="{W}" height="{H}" fill="#fafaf8"/>')
svg.append(f'<text x="20" y="34" font-size="22" font-weight="700" fill="#1a202c">Complex truss TN2-1 — clustering option</text>')
svg.append(f'<text x="20" y="58" font-size="14" fill="#4a5568">Apex/heel zones have multiple centreline crossings within a few cm. Right panel merges any crossings within {TOL:.0f}mm of each other into one bolt.</text>')

left_cx = panel_w_mm*SCALE/2
right_cx = (panel_w_mm*1.5+gap_mm)*SCALE
svg.append(f'<text x="{left_cx:.0f}" y="92" text-anchor="middle" font-size="15" font-weight="700" fill="#7f1d1d">RAW — every centreline crossing = 1 bolt</text>')
svg.append(f'<text x="{right_cx:.0f}" y="92" text-anchor="middle" font-size="15" font-weight="700" fill="#14532d">CLUSTERED — crossings within {TOL:.0f}mm merge to 1 bolt</text>')

for sf, draw_fn in [(to_left, 'left'), (to_right, 'right')]:
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(f'<polygon points="{member_polygon(s, sf)}" fill="url(#cf)" stroke="#1d4ed8" stroke-width="1.6" opacity="0.95"/>')
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(f'<polygon points="{member_polygon(s, sf)}" fill="url(#wf)" stroke="#475569" stroke-width="1.4" opacity="0.85"/>')
    for s in sticks:
        x1,y1 = sf(*s['start']); x2,y2 = sf(*s['end'])
        col = '#1d4ed8' if s['type']=='Plate' else '#334155'
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="1" stroke-dasharray="5 3" opacity="0.7"/>')
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px,py = sf(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="12" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="#fafaf8" stroke-width="3.5" paint-order="stroke">{s["name"]}</text>')

# Left: raw crossings
for px, pz, cnt in raw_pts:
    cx, cy = to_left(px, pz)
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="none" stroke="#dc2626" stroke-width="1" opacity="0.5"/>')
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.8" fill="#dc2626" stroke="#7f1d1d" stroke-width="1.2"/>')

# Right: clustered
for m_pt in merged:
    cx, cy = to_right(*m_pt['pt'])
    # bolts merged from N — show ring scaled by N
    n = m_pt['merged_from']
    ring_r = 11 + (n-1)*4
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring_r}" fill="none" stroke="#16a34a" stroke-width="1.3" opacity="0.5"/>')
    svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.2" fill="#16a34a" stroke="#14532d" stroke-width="1.4"/>')
    if n > 1:
        svg.append(f'<text x="{cx+ring_r+3:.1f}" y="{cy+4:.1f}" font-size="10" fill="#14532d" font-weight="700">{n}→1</text>')

svg.append(f'<rect x="40" y="{H-58}" width="{W-80}" height="42" fill="#f1f5f9" stroke="#cbd5e0" rx="3"/>')
svg.append(f'<text x="{left_cx:.0f}" y="{H-32}" text-anchor="middle" font-size="13" fill="#7f1d1d" font-weight="700">{len(raw_pts)} bolts</text>')
svg.append(f'<text x="{left_cx:.0f}" y="{H-18}" text-anchor="middle" font-size="11" fill="#7f1d1d">every centreline pair-crossing</text>')
svg.append(f'<text x="{right_cx:.0f}" y="{H-32}" text-anchor="middle" font-size="13" fill="#14532d" font-weight="700">{len(merged)} bolts ({(len(raw_pts)-len(merged))/len(raw_pts)*100:.0f}% fewer)</text>')
svg.append(f'<text x="{right_cx:.0f}" y="{H-18}" text-anchor="middle" font-size="11" fill="#14532d">"N→1" labels show how many crossings merged</text>')

svg.append('</svg>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(svg))
print(f'Wrote {OUT}')
