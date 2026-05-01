"""Compute and visualise EXACT centreline crossings.

For every pair of members in a truss frame:
  1. Treat each member as an infinite line through its endpoints
  2. Solve for the intersection point of the two lines
  3. Check both intersection points lie on (or very near) both segments
  4. Collect the crossing

Then optionally cluster crossings within TOL mm and place 1 bolt per cluster.

This produces structural-node-equivalent bolt positions —
exactly what the user marked by hand.
"""
import re, math, os

XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075.xml'
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
        sticks.append({'name':nm,'type':typ,'start':(sx,sz),'end':(ex,ez)})
    return sticks

def line_intersection(p1, p2, p3, p4, slack_mm=120.0):
    """Intersect segments (p1->p2) with (p3->p4). Return point if they cross
    (or extended endpoints meet within slack_mm of either segment).
    Returns (x, z) or None.
    """
    x1, z1 = p1; x2, z2 = p2
    x3, z3 = p3; x4, z4 = p4
    denom = (x1-x2)*(z3-z4) - (z1-z2)*(x3-x4)
    if abs(denom) < 1e-9:
        return None  # parallel
    t = ((x1-x3)*(z3-z4) - (z1-z3)*(x3-x4)) / denom
    u = -((x1-x2)*(z1-z3) - (z1-z2)*(x1-x3)) / denom
    # Allow extension by slack (in segment-fraction terms)
    L1 = math.hypot(x2-x1, z2-z1)
    L2 = math.hypot(x4-x3, z4-z3)
    slack_t = slack_mm / L1 if L1 > 0 else 0
    slack_u = slack_mm / L2 if L2 > 0 else 0
    if not (-slack_t <= t <= 1+slack_t): return None
    if not (-slack_u <= u <= 1+slack_u): return None
    ix = x1 + t*(x2-x1)
    iz = z1 + t*(z2-z1)
    return (ix, iz)

def all_centreline_crossings(sticks, slack_mm=120.0):
    """Find every pairwise centreline crossing."""
    out = []
    n = len(sticks)
    for i in range(n):
        for j in range(i+1, n):
            a = sticks[i]; b = sticks[j]
            pt = line_intersection(a['start'], a['end'], b['start'], b['end'], slack_mm=slack_mm)
            if pt:
                out.append({'pt':pt, 'a':a['name'], 'b':b['name']})
    return out

def cluster(crossings, tol):
    if tol <= 0:
        return [{'pt':c['pt'], 'pairs':[(c['a'],c['b'])]} for c in crossings]
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
    out = []
    for grp in cl.values():
        cx = sum(g['pt'][0] for g in grp)/len(grp)
        cy = sum(g['pt'][1] for g in grp)/len(grp)
        pairs = [(g['a'],g['b']) for g in grp]
        out.append({'pt':(cx,cy), 'pairs':pairs})
    return out

WIDTH_MM = 89.0

def render(sticks, frame_name, description, crossings, tol=150):
    if not sticks:
        return None
    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    xmin, xmax = min(all_x)-300, max(all_x)+300
    zmin, zmax = min(all_z)-300, max(all_z)+300
    mm_w = xmax-xmin; mm_h = zmax-zmin

    PAGE_W = 1700
    PAGE_H = 1100
    margin_top = 130
    margin_other = 40
    draw_area_w = PAGE_W - 2*margin_other
    draw_area_h = PAGE_H - margin_top - margin_other - 70

    SCALE = min(draw_area_w/mm_w, draw_area_h/mm_h)
    draw_w = mm_w*SCALE; draw_h = mm_h*SCALE
    ox = margin_other + (draw_area_w - draw_w)/2
    oy = margin_top + (draw_area_h - draw_h)/2

    def to_px(x, z):
        return (ox + (x-xmin)*SCALE, oy + (zmax-z)*SCALE)

    def member_polygon(stick):
        sx_,sz_ = stick['start']; ex_,ez_ = stick['end']
        dx, dz = ex_-sx_, ez_-sz_
        L = math.hypot(dx, dz)
        if L == 0: return ''
        nx, nz = -dz/L, dx/L
        h = WIDTH_MM/2
        pts = [(sx_+nx*h, sz_+nz*h), (sx_-nx*h, sz_-nz*h), (ex_-nx*h, ez_-nz*h), (ex_+nx*h, ez_+nz*h)]
        return ' '.join(f'{a:.1f},{b:.1f}' for a,b in (to_px(*p) for p in pts))

    clustered = cluster(crossings, tol)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append('''<defs>
      <pattern id="cf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)">
        <rect width="6" height="6" fill="#dbeafe"/><line x1="0" y1="0" x2="0" y2="6" stroke="#93c5fd" stroke-width="0.6"/>
      </pattern>
      <pattern id="wf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
        <rect width="6" height="6" fill="#e2e8f0"/><line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" stroke-width="0.6"/>
      </pattern>
    </defs>''')
    svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="white"/>')
    svg.append(f'<text x="40" y="44" font-size="26" font-weight="700" fill="#1a202c">Frame {frame_name} — exact centreline crossings (clustered {tol:.0f}mm)</text>')
    svg.append(f'<text x="40" y="72" font-size="15" fill="#4a5568">{description}</text>')
    svg.append(f'<text x="40" y="98" font-size="13" fill="#374151">{len(crossings)} raw centreline crossings → {len(clustered)} bolts after merging close ones (apex/heel zones collapse to single bolts).</text>')

    # Members
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(f'<polygon points="{member_polygon(s)}" fill="url(#cf)" stroke="#1d4ed8" stroke-width="1.6" opacity="0.95"/>')
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(f'<polygon points="{member_polygon(s)}" fill="url(#wf)" stroke="#475569" stroke-width="1.4" opacity="0.85"/>')
    for s in sticks:
        x1,y1 = to_px(*s['start']); x2,y2 = to_px(*s['end'])
        col = '#1d4ed8' if s['type']=='Plate' else '#334155'
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="1" stroke-dasharray="5 3" opacity="0.55"/>')
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px,py = to_px(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="14" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="white" stroke-width="3.5" paint-order="stroke">{s["name"]}</text>')

    # Bolt dots (clustered)
    for cl in clustered:
        cx, cy = to_px(*cl['pt'])
        n = len(cl['pairs'])
        ring_r = 12 + (n-1)*3
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring_r}" fill="none" stroke="#16a34a" stroke-width="1.2" opacity="0.55"/>')
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#16a34a" stroke="#14532d" stroke-width="1.6"/>')
        if n > 1:
            label = f'×{n}'
            svg.append(f'<text x="{cx+ring_r+4:.1f}" y="{cy+4:.1f}" font-size="11" font-weight="700" fill="#14532d">{label}</text>')

    # Footer
    fy = PAGE_H - 35
    svg.append(f'<rect x="40" y="{fy-12}" width="{PAGE_W-80}" height="38" fill="#f0fdf4" stroke="#16a34a" rx="3"/>')
    pair_summary = ', '.join(f'{a}∩{b}' for a,b in clustered[0]['pairs']) if clustered else ''
    svg.append(f'<text x="60" y="{fy+8}" font-size="13" fill="#14532d">Each green dot = exact centreline intersection. ×N labels show how many member-pair-crossings merged at that node.</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# Run for all 4 frames
frames_to_render = [
    ('TN1-1', 'Small hip truss — 8 members.'),
    ('TN2-1', 'Complex main truss with collar tie — 10 members.'),
    ('TN1-3', 'Mid-position hip truss.'),
    ('TN2-3', 'Mid-position complex truss with collar tie.'),
]

generated = []
for name, desc in frames_to_render:
    sticks = parse_frame(name)
    if not sticks:
        print(f'Frame {name} not found, skipping')
        continue
    crossings = all_centreline_crossings(sticks, slack_mm=150.0)
    print(f'\n{name}: {len(sticks)} members, {len(crossings)} pairwise centreline crossings')
    for c in crossings:
        print(f'  {c["a"]:5s} x {c["b"]:5s} = ({c["pt"][0]:.1f}, {c["pt"][1]:.1f})')
    svg = render(sticks, name, desc, crossings, tol=150)
    out_file = os.path.join(OUT_DIR, f'truss_math_{name}.svg')
    open(out_file, 'w', encoding='utf-8').write(svg)
    generated.append((name, len(sticks), out_file, len(crossings), len(cluster(crossings, 150))))
    print(f'  Wrote {out_file}')

# Build index
print()
idx = ['<!DOCTYPE html><html><head><title>Centreline-crossing trusses</title>',
       '<style>',
       '* {box-sizing:border-box}',
       'body {font-family: Segoe UI, Arial, sans-serif; margin:0; padding:24px; background:#f1f5f9}',
       'h1 {margin: 0 0 12px}',
       '.sub {color:#4a5568; margin-bottom:24px}',
       '.card {background:white; border:1px solid #cbd5e0; border-radius:6px; margin-bottom:24px; overflow:hidden}',
       '.card-head {padding:14px 18px; background:#fafaf8; border-bottom:1px solid #e2e8f0; display:flex; justify-content:space-between; align-items:center}',
       '.card-head h2 {margin:0; font-size:16px}',
       '.card-head a {color:#2563eb; text-decoration:none; padding:5px 12px; border:1px solid #93c5fd; border-radius:3px; font-size:12px}',
       '.card-head a:hover {background:#dbeafe}',
       '.stat {color:#14532d; font-weight:600; font-size:12px}',
       'iframe {border:0; width:100%; height:880px; display:block; background:white}',
       '</style></head><body>',
       '<h1>Mathematical centreline crossings — TN-series frames</h1>',
       '<p class="sub">Green dots are computed: for every pair of member centrelines that physically meet, place one bolt at their intersection. ×N indicates how many pairs merged at apex/heel clusters.</p>']
for name, count, path, raw, final in generated:
    fname = os.path.basename(path)
    idx.append(f'<div class="card"><div class="card-head"><div><h2>{name}</h2><div class="stat">{count} members · {raw} pairwise crossings → {final} bolts</div></div><a href="{fname}" target="_blank">open standalone ↗</a></div><iframe src="{fname}"></iframe></div>')
idx.append('</body></html>')
idx_path = os.path.join(OUT_DIR, 'CENTRELINE_TRUSSES.html')
open(idx_path, 'w', encoding='utf-8').write('\n'.join(idx))
print(f'\nWrote index: {idx_path}')
