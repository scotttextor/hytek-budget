"""All bolt-placement rules side-by-side on one page.

Five options for the same complex truss frame TN2-1:
  1. CURRENT (FrameCAD): 3 bolts per junction, offset from centreline
  2. RAW: every centreline crossing = 1 bolt
  3. CLUSTERED 40mm: tight clustering
  4. CLUSTERED 80mm: medium
  5. CLUSTERED 150mm: wide (apex/heel collapse fully)
"""
import re, math
XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075.xml'
OUT = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/all_options.svg'

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

def cluster(points, tol):
    if tol <= 0:
        return [{'pt':(p[0],p[1]), 'merged_from':1} for p in points]
    n = len(points)
    parent = list(range(n))
    def find(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj: parent[ri] = rj
    for i in range(n):
        for j in range(i+1, n):
            d = math.hypot(points[i][0]-points[j][0], points[i][1]-points[j][1])
            if d <= tol: union(i,j)
    cl = {}
    for i, p in enumerate(points):
        cl.setdefault(find(i), []).append(p)
    out = []
    for c in cl.values():
        cx = sum(p[0] for p in c)/len(c); cy = sum(p[1] for p in c)/len(c)
        out.append({'pt':(cx,cy), 'merged_from':len(c)})
    return out

# Define 5 panels
options = [
    {'title':'1. CURRENT (FrameCAD rule)', 'subtitle':'3 bolts clustered near each junction, offset from crossing', 'mode':'old'},
    {'title':'2. RAW crossings (no merge)', 'subtitle':'Every centreline pair-crossing = 1 bolt', 'mode':'tol', 'tol':0},
    {'title':'3. CLUSTERED 40mm', 'subtitle':'Merge crossings within 40mm', 'mode':'tol', 'tol':40},
    {'title':'4. CLUSTERED 80mm', 'subtitle':'Merge crossings within 80mm (medium)', 'mode':'tol', 'tol':80},
    {'title':'5. CLUSTERED 150mm', 'subtitle':'Merge crossings within 150mm (apex/heel fully collapse)', 'mode':'tol', 'tol':150},
]

# Compute extents
all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
xmin, xmax = min(all_x)-300, max(all_x)+300
zmin, zmax = min(all_z)-300, max(all_z)+300
mm_w = xmax-xmin; mm_h = zmax-zmin

# Layout: 5 panels in a 3+2 grid (3 across top, 2 across bottom)
# Or simpler — 1 across top (current), 2x2 grid below for the four proposed
# Let's do 5 horizontally if width allows, else 3+2
COLS = 3
ROWS = 2
PANEL_W = 720
PANEL_H = 520
GAP_X = 30
GAP_Y = 90
HEAD = 100
TOTAL_W = COLS*PANEL_W + (COLS+1)*GAP_X
TOTAL_H = HEAD + ROWS*PANEL_H + (ROWS+1)*GAP_Y + 20

# Per-panel scale: fit truss into PANEL_W × PANEL_H (with margin)
margin = 40
sx = (PANEL_W - 2*margin) / mm_w
sy = (PANEL_H - 2*margin) / mm_h
SCALE = min(sx, sy)
draw_w = mm_w*SCALE; draw_h = mm_h*SCALE
ox = (PANEL_W - draw_w)/2; oy = (PANEL_H - draw_h)/2

def panel_origin(idx):
    col = idx % COLS
    row = idx // COLS
    x0 = GAP_X + col*(PANEL_W+GAP_X)
    y0 = HEAD + GAP_Y + row*(PANEL_H+GAP_Y)
    return x0, y0

def to_panel(x, z, x0, y0):
    return (x0 + ox + (x-xmin)*SCALE, y0 + oy + (zmax-z)*SCALE)

WIDTH_MM = 89.0
def member_polygon(stick, x0, y0):
    sx_,sz_ = stick['start']; ex_,ez_ = stick['end']
    dx, dz = ex_-sx_, ez_-sz_
    L = math.hypot(dx, dz)
    if L == 0: return ''
    nx, nz = -dz/L, dx/L
    h = WIDTH_MM/2
    pts = [(sx_+nx*h, sz_+nz*h), (sx_-nx*h, sz_-nz*h), (ex_-nx*h, ez_-nz*h), (ex_+nx*h, ez_+nz*h)]
    return ' '.join(f'{a:.1f},{b:.1f}' for a,b in (to_panel(*p, x0, y0) for p in pts))

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{TOTAL_W}" height="{TOTAL_H}" viewBox="0 0 {TOTAL_W} {TOTAL_H}" font-family="Segoe UI, Arial, sans-serif">')
svg.append('''<defs>
  <pattern id="cf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)">
    <rect width="6" height="6" fill="#dbeafe"/><line x1="0" y1="0" x2="0" y2="6" stroke="#93c5fd" stroke-width="0.6"/></pattern>
  <pattern id="wf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
    <rect width="6" height="6" fill="#e2e8f0"/><line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" stroke-width="0.6"/></pattern>
</defs>''')
svg.append(f'<rect width="{TOTAL_W}" height="{TOTAL_H}" fill="#fafaf8"/>')

# Header
svg.append(f'<text x="30" y="40" font-size="24" font-weight="700" fill="#1a202c">All bolt-placement options — same truss, 5 rules</text>')
svg.append(f'<text x="30" y="66" font-size="14" fill="#4a5568">Frame TN2-1 from your 2603191 ROCKVILLE truss. Compare bolt count and pattern, pick the rule you want.</text>')
svg.append(f'<text x="30" y="86" font-size="13" fill="#374151">10 members  ·  22 raw centreline crossings  ·  blue = chord plate, grey = web stud</text>')

for idx, opt in enumerate(options):
    x0, y0 = panel_origin(idx)
    # Panel border
    color = '#dc2626' if opt['mode']=='old' else '#16a34a'
    fill = '#fef2f2' if opt['mode']=='old' else '#f0fdf4'
    svg.append(f'<rect x="{x0}" y="{y0}" width="{PANEL_W}" height="{PANEL_H}" fill="white" stroke="#cbd5e0" stroke-width="1.2" rx="4"/>')
    # Title strip
    svg.append(f'<rect x="{x0}" y="{y0}" width="{PANEL_W}" height="50" fill="{fill}" stroke="#cbd5e0" stroke-width="1.2" rx="4"/>')
    svg.append(f'<text x="{x0+18}" y="{y0+22}" font-size="14" font-weight="700" fill="{color}">{opt["title"]}</text>')
    svg.append(f'<text x="{x0+18}" y="{y0+40}" font-size="11" fill="#4a5568">{opt["subtitle"]}</text>')

    # Draw members
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(f'<polygon points="{member_polygon(s, x0, y0)}" fill="url(#cf)" stroke="#1d4ed8" stroke-width="1.2" opacity="0.9"/>')
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(f'<polygon points="{member_polygon(s, x0, y0)}" fill="url(#wf)" stroke="#475569" stroke-width="1" opacity="0.85"/>')
    for s in sticks:
        x1,y1 = to_panel(*s['start'], x0, y0); x2,y2 = to_panel(*s['end'], x0, y0)
        col = '#1d4ed8' if s['type']=='Plate' else '#334155'
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="0.8" stroke-dasharray="4 2" opacity="0.6"/>')
    # Member labels (only key ones to avoid clutter)
    for s in sticks:
        if s['name'] in ('T2','T3','B1','C4','W5','W6','W7','W8','W9','W10'):
            mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
            px,py = to_panel(mx, mz, x0, y0)
            svg.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="10" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="#fafaf8" stroke-width="3" paint-order="stroke">{s["name"]}</text>')

    # Bolt placement
    if opt['mode'] == 'old':
        # 3 bolts per fastener point, in cluster
        for px, pz, cnt in raw_pts:
            cx, cy = to_panel(px, pz, x0, y0)
            n = cnt
            for i in range(n):
                a = (i*2*math.pi/max(n,3)) - math.pi/2
                r = 5
                svg.append(f'<circle cx="{cx + r*math.cos(a):.1f}" cy="{cy + r*math.sin(a):.1f}" r="2.4" fill="#dc2626" stroke="#7f1d1d" stroke-width="0.6"/>')
        bolt_count = sum(p[2] for p in raw_pts)
    else:
        merged = cluster([(p[0], p[1]) for p in raw_pts], opt.get('tol',0))
        for m_pt in merged:
            cx, cy = to_panel(*m_pt['pt'], x0, y0)
            n = m_pt['merged_from']
            ring = 8 + (n-1)*3
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring}" fill="none" stroke="#16a34a" stroke-width="1" opacity="0.5"/>')
            svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3.4" fill="#16a34a" stroke="#14532d" stroke-width="1.1"/>')
            if n > 1:
                svg.append(f'<text x="{cx+ring+2:.1f}" y="{cy+3:.1f}" font-size="9" font-weight="700" fill="#14532d">×{n}</text>')
        bolt_count = len(merged)

    # Footer count
    pct = ''
    if opt['mode'] == 'old':
        pct_text = f'{bolt_count} bolts (baseline)'
        text_col = '#7f1d1d'
    else:
        baseline = sum(p[2] for p in raw_pts)
        pct = f' ({(baseline-bolt_count)/baseline*100:.0f}% reduction)'
        pct_text = f'{bolt_count} bolts{pct}'
        text_col = '#14532d'
    svg.append(f'<rect x="{x0+10}" y="{y0+PANEL_H-32}" width="{PANEL_W-20}" height="22" fill="#f1f5f9" stroke="#cbd5e0" rx="3"/>')
    svg.append(f'<text x="{x0+PANEL_W/2:.0f}" y="{y0+PANEL_H-16}" text-anchor="middle" font-size="13" font-weight="700" fill="{text_col}">{pct_text}</text>')

# Bottom legend
ly = HEAD + ROWS*PANEL_H + (ROWS+1)*GAP_Y + 5
svg.append(f'<text x="30" y="{ly+10}" font-size="11" fill="#374151"><tspan font-weight="700">Reading the diagrams:</tspan> blue hatched bands = chord plates · grey hatched bands = web studs · dashed lines = centrelines · circles = bolt holes · ×N labels show how many crossings merged into one bolt.</text>')

svg.append('</svg>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(svg))
print(f'Wrote {OUT}')

# Print summary
baseline = sum(p[2] for p in raw_pts)
print(f'\nSummary for frame TN2-1:')
print(f'  CURRENT FrameCAD:   {baseline} bolts')
for opt in options[1:]:
    merged = cluster([(p[0], p[1]) for p in raw_pts], opt.get('tol',0))
    print(f'  {opt["title"]:30s}: {len(merged):3d} bolts  ({(baseline-len(merged))/baseline*100:.0f}% reduction)')
