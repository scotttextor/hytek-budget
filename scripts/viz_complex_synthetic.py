"""Generate REALLY complex synthetic trusses and run centreline-crossing on them.

Six classic+nasty truss shapes designers actually build:
  1. Long-span Pratt (15m, 11 panels = 22 webs)
  2. Howe truss (10m, web pattern reversed - lots of crossings)
  3. Scissors / vaulted ceiling (raked bottom chord)
  4. Modified Fink (multiple pitches, sub-webs)
  5. Girder truss (doubled chords, dense web pattern)
  6. Hip-end girder corner (asymmetric, multi-direction)

Each is rendered with:
  - Members to scale (89mm wide)
  - Faint centrelines
  - Mathematical centreline crossings as green dots
  - Apex/heel clusters merged within tolerance
"""
import math, os

OUT_DIR = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/'
WIDTH_MM = 89.0

def line_intersection(p1, p2, p3, p4, slack_mm=150.0):
    x1, z1 = p1; x2, z2 = p2
    x3, z3 = p3; x4, z4 = p4
    denom = (x1-x2)*(z3-z4) - (z1-z2)*(x3-x4)
    if abs(denom) < 1e-9: return None
    t = ((x1-x3)*(z3-z4) - (z1-z3)*(x3-x4)) / denom
    u = -((x1-x2)*(z1-z3) - (z1-z2)*(x1-x3)) / denom
    L1 = math.hypot(x2-x1, z2-z1)
    L2 = math.hypot(x4-x3, z4-z3)
    st = slack_mm/L1 if L1>0 else 0
    su = slack_mm/L2 if L2>0 else 0
    if not (-st <= t <= 1+st): return None
    if not (-su <= u <= 1+su): return None
    return (x1 + t*(x2-x1), z1 + t*(z2-z1))

def all_crossings(sticks, slack=150):
    out = []
    for i in range(len(sticks)):
        for j in range(i+1, len(sticks)):
            pt = line_intersection(sticks[i]['start'], sticks[i]['end'],
                                   sticks[j]['start'], sticks[j]['end'], slack)
            if pt:
                out.append({'pt':pt, 'a':sticks[i]['name'], 'b':sticks[j]['name']})
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

# ----- TRUSS GENERATORS -----

def long_pratt_truss(span=15000, height=2400, panels=11):
    """Pratt-style: vertical webs, diagonals slope toward centre."""
    sticks = []
    panel_w = span / panels
    # Bottom chord: single member
    sticks.append({'name':'B1','type':'Plate','start':(0,0),'end':(span,0)})
    # Top chord: triangular peak (gable)
    sticks.append({'name':'T_L','type':'Plate','start':(0,0),'end':(span/2, height)})
    sticks.append({'name':'T_R','type':'Plate','start':(span/2, height),'end':(span,0)})
    # Verticals at each panel point
    for k in range(1, panels):
        x = k * panel_w
        # Top chord height at this x:
        if x <= span/2:
            tz = (x / (span/2)) * height
        else:
            tz = ((span-x) / (span/2)) * height
        if tz > 100:
            sticks.append({'name':f'V{k}','type':'Stud','start':(x, 0),'end':(x, tz)})
    # Diagonals — sloping toward centre
    for k in range(1, panels):
        x_low = (k-1)*panel_w
        x_high = k*panel_w
        if k <= panels//2:
            # diagonal from bottom of (k-1) up to top-chord at x_high
            tz = (x_high/(span/2))*height if x_high <= span/2 else ((span-x_high)/(span/2))*height
            sticks.append({'name':f'D{k}','type':'Stud','start':(x_low, 0),'end':(x_high, tz)})
        else:
            tz = (x_low/(span/2))*height if x_low <= span/2 else ((span-x_low)/(span/2))*height
            sticks.append({'name':f'D{k}','type':'Stud','start':(x_high, 0),'end':(x_low, tz)})
    return sticks

def howe_truss(span=10000, height=2200, panels=8):
    """Howe: diagonals slope outward from centre."""
    sticks = []
    panel_w = span / panels
    sticks.append({'name':'B1','type':'Plate','start':(0,0),'end':(span,0)})
    sticks.append({'name':'T_L','type':'Plate','start':(0,0),'end':(span/2, height)})
    sticks.append({'name':'T_R','type':'Plate','start':(span/2, height),'end':(span,0)})
    for k in range(1, panels):
        x = k * panel_w
        tz = (x/(span/2))*height if x<=span/2 else ((span-x)/(span/2))*height
        if tz > 100:
            sticks.append({'name':f'V{k}','type':'Stud','start':(x, 0),'end':(x, tz)})
    # Howe diagonals slope outward (toward heels)
    for k in range(1, panels):
        x_l = (k-1)*panel_w; x_h = k*panel_w
        if k <= panels//2:
            # diagonal from x_h on bottom UP to x_l on top
            tz = (x_l/(span/2))*height if x_l<=span/2 else ((span-x_l)/(span/2))*height
            sticks.append({'name':f'D{k}','type':'Stud','start':(x_h, 0),'end':(x_l, tz)})
        else:
            tz = (x_h/(span/2))*height if x_h<=span/2 else ((span-x_h)/(span/2))*height
            sticks.append({'name':f'D{k}','type':'Stud','start':(x_l, 0),'end':(x_h, tz)})
    return sticks

def scissors_truss(span=9000, top_h=2700, bot_h=1100, panels=6):
    """Vaulted ceiling - bottom chord rakes upward toward middle."""
    sticks = []
    # Top chord — peaked
    sticks.append({'name':'T_L','type':'Plate','start':(0,0),'end':(span/2, top_h)})
    sticks.append({'name':'T_R','type':'Plate','start':(span/2, top_h),'end':(span,0)})
    # Bottom chord — also peaked but lower
    sticks.append({'name':'B_L','type':'Plate','start':(0,0),'end':(span/2, bot_h)})
    sticks.append({'name':'B_R','type':'Plate','start':(span/2, bot_h),'end':(span,0)})
    # Webs - verticals at panel points + diagonals
    panel_w = span / panels
    for k in range(1, panels):
        x = k * panel_w
        tz = (x/(span/2))*top_h if x<=span/2 else ((span-x)/(span/2))*top_h
        bz = (x/(span/2))*bot_h if x<=span/2 else ((span-x)/(span/2))*bot_h
        if tz - bz > 50:
            sticks.append({'name':f'V{k}','type':'Stud','start':(x, bz),'end':(x, tz)})
    # Diagonals
    for k in range(1, panels):
        x_l = (k-1)*panel_w; x_h = k*panel_w
        bz_l = (x_l/(span/2))*bot_h if x_l<=span/2 else ((span-x_l)/(span/2))*bot_h
        tz_h = (x_h/(span/2))*top_h if x_h<=span/2 else ((span-x_h)/(span/2))*top_h
        if k <= panels//2:
            sticks.append({'name':f'D{k}','type':'Stud','start':(x_l, bz_l),'end':(x_h, tz_h)})
        else:
            bz_h = (x_h/(span/2))*bot_h if x_h<=span/2 else ((span-x_h)/(span/2))*bot_h
            tz_l = (x_l/(span/2))*top_h if x_l<=span/2 else ((span-x_l)/(span/2))*top_h
            sticks.append({'name':f'D{k}','type':'Stud','start':(x_h, bz_h),'end':(x_l, tz_l)})
    return sticks

def fink_truss(span=11000, height=3000):
    """Fink — split webs into sub-webs forming W pattern."""
    sticks = []
    sticks.append({'name':'B1','type':'Plate','start':(0,0),'end':(span,0)})
    sticks.append({'name':'T_L','type':'Plate','start':(0,0),'end':(span/2, height)})
    sticks.append({'name':'T_R','type':'Plate','start':(span/2, height),'end':(span,0)})
    # Vertical at apex
    sticks.append({'name':'V_C','type':'Stud','start':(span/2, 0),'end':(span/2, height)})
    # Two main diagonals from heels to apex - quarter points
    qx_l = span/4; qx_r = 3*span/4
    qz_l = (qx_l/(span/2))*height
    qz_r = ((span-qx_r)/(span/2))*height
    # Webs forming W pattern
    sticks.append({'name':'W1','type':'Stud','start':(0, 0),'end':(qx_l, qz_l-300)})
    sticks.append({'name':'W2','type':'Stud','start':(qx_l, 0),'end':(qx_l, qz_l)})
    sticks.append({'name':'W3','type':'Stud','start':(qx_l, qz_l),'end':(span/2, 0)})
    sticks.append({'name':'W4','type':'Stud','start':(span/2, 0),'end':(qx_r, qz_r)})
    sticks.append({'name':'W5','type':'Stud','start':(qx_r, qz_r),'end':(qx_r, 0)})
    sticks.append({'name':'W6','type':'Stud','start':(qx_r, qz_r),'end':(span, 0)})
    # Sub-webs to top chord
    sticks.append({'name':'S1','type':'Stud','start':(qx_l, qz_l),'end':(qx_l + 800, (qx_l+800)/(span/2)*height)})
    sticks.append({'name':'S2','type':'Stud','start':(qx_r - 800, ((qx_r-800)<=span/2 and ((qx_r-800)/(span/2)*height) or ((span-(qx_r-800))/(span/2)*height))),'end':(qx_r, qz_r)})
    return sticks

def girder_truss(span=12000, height=2600, panels=10):
    """Girder — heavy duty, doubled chord pattern, denser webs."""
    sticks = []
    panel_w = span / panels
    sticks.append({'name':'B1','type':'Plate','start':(0,0),'end':(span,0)})
    sticks.append({'name':'B2','type':'Plate','start':(0,height/8),'end':(span,height/8)})  # second bot chord (girder)
    sticks.append({'name':'T_L','type':'Plate','start':(0,0),'end':(span/2, height)})
    sticks.append({'name':'T_R','type':'Plate','start':(span/2, height),'end':(span,0)})
    # Verticals + diagonals at each panel
    for k in range(1, panels):
        x = k * panel_w
        tz = (x/(span/2))*height if x<=span/2 else ((span-x)/(span/2))*height
        if tz > 100:
            sticks.append({'name':f'V{k}','type':'Stud','start':(x, 0),'end':(x, tz)})
    for k in range(panels):
        x_l = k*panel_w; x_h = (k+1)*panel_w
        if k+1 == panels: continue
        if k < panels//2:
            tz_h = (x_h/(span/2))*height if x_h<=span/2 else ((span-x_h)/(span/2))*height
            sticks.append({'name':f'D{k}A','type':'Stud','start':(x_l, 0),'end':(x_h, tz_h)})
            sticks.append({'name':f'D{k}B','type':'Stud','start':(x_h, 0),'end':(x_l, (x_l/(span/2))*height if x_l<=span/2 else ((span-x_l)/(span/2))*height)})
        else:
            tz_l = (x_l/(span/2))*height if x_l<=span/2 else ((span-x_l)/(span/2))*height
            sticks.append({'name':f'D{k}A','type':'Stud','start':(x_h, 0),'end':(x_l, tz_l)})
    return sticks

def attic_truss(span=10000, height=3200, room_width=4500, room_height=2400):
    """Attic / room-in-roof truss with rectangular interior space."""
    sticks = []
    sticks.append({'name':'B1','type':'Plate','start':(0,0),'end':(span,0)})
    sticks.append({'name':'T_L','type':'Plate','start':(0,0),'end':(span/2, height)})
    sticks.append({'name':'T_R','type':'Plate','start':(span/2, height),'end':(span,0)})
    # Room walls (vertical posts)
    rl = (span - room_width)/2
    rr = rl + room_width
    sticks.append({'name':'P_L','type':'Stud','start':(rl, 0),'end':(rl, room_height)})
    sticks.append({'name':'P_R','type':'Stud','start':(rr, 0),'end':(rr, room_height)})
    # Ceiling tie
    sticks.append({'name':'CT','type':'Plate','start':(rl, room_height),'end':(rr, room_height)})
    # Diagonal webs heel-to-room-corner
    sticks.append({'name':'D_L','type':'Stud','start':(0, 0),'end':(rl, room_height)})
    sticks.append({'name':'D_R','type':'Stud','start':(rr, room_height),'end':(span, 0)})
    # Apex king post + rafters from room corners to apex
    sticks.append({'name':'KP','type':'Stud','start':(span/2, room_height),'end':(span/2, height)})
    # Sub-rafters from room corner to apex
    sticks.append({'name':'SR_L','type':'Stud','start':(rl, room_height),'end':(span/2, height)})
    sticks.append({'name':'SR_R','type':'Stud','start':(span/2, height),'end':(rr, room_height)})
    return sticks

# ----- RENDERER -----

def render(sticks, frame_name, description, tol=200):
    crossings = all_crossings(sticks, slack=200)
    clustered = cluster(crossings, tol)

    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    xmin, xmax = min(all_x)-500, max(all_x)+500
    zmin, zmax = min(all_z)-500, max(all_z)+500
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
    svg.append(f'<text x="40" y="44" font-size="26" font-weight="700" fill="#1a202c">{frame_name}</text>')
    svg.append(f'<text x="40" y="72" font-size="15" fill="#4a5568">{description}</text>')
    svg.append(f'<text x="40" y="98" font-size="13" fill="#374151">{len(sticks)} members  ·  {len(crossings)} centreline crossings  →  {len(clustered)} bolts after clustering at {tol}mm</text>')

    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(f'<polygon points="{member_polygon(s)}" fill="url(#cf)" stroke="#1d4ed8" stroke-width="1.4" opacity="0.95"/>')
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(f'<polygon points="{member_polygon(s)}" fill="url(#wf)" stroke="#475569" stroke-width="1.2" opacity="0.85"/>')
    for s in sticks:
        x1,y1 = to_px(*s['start']); x2,y2 = to_px(*s['end'])
        col = '#1d4ed8' if s['type']=='Plate' else '#334155'
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="0.8" stroke-dasharray="5 3" opacity="0.5"/>')
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px,py = to_px(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="11" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="white" stroke-width="3" paint-order="stroke">{s["name"]}</text>')

    for cl in clustered:
        cx, cy = to_px(*cl['pt'])
        n = len(cl['pairs'])
        ring_r = 11 + (n-1)*2.5
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{ring_r}" fill="none" stroke="#16a34a" stroke-width="1.1" opacity="0.55"/>')
        svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4.5" fill="#16a34a" stroke="#14532d" stroke-width="1.4"/>')
        if n > 1:
            svg.append(f'<text x="{cx+ring_r+3:.1f}" y="{cy+3:.1f}" font-size="10" font-weight="700" fill="#14532d">x{n}</text>')

    svg.append('</svg>')
    return '\n'.join(svg), len(crossings), len(clustered)

# ----- BUILD ALL -----

trusses = [
    ('Long-span Pratt (15m, 11 panels)',     'Workhorse roof truss — verticals + sloping diagonals to centre',  long_pratt_truss(),  150),
    ('Howe truss (10m, 8 panels)',           'Reversed diagonals — tension verticals, compression diagonals',     howe_truss(),         150),
    ('Scissors / vaulted (9m)',              'Cathedral / vaulted ceiling — bottom chord rakes inward',           scissors_truss(),     200),
    ('Modified Fink with sub-webs (11m)',    'Double-W pattern, sub-webs to top chord — multi-pitch hipped',      fink_truss(),         200),
    ('Girder (12m, 10 panels, twin chord)',  'Heavy-duty load-carrying truss with doubled bottom chord',          girder_truss(),       180),
    ('Attic / room-in-roof (10m)',           'Living space inside the truss — room walls, ceiling tie, king post', attic_truss(),       250),
]

generated = []
for name, desc, sticks, tol in trusses:
    safe = name.split()[0].replace('/','_').replace('(','').replace(')','')
    print(f'\n{name}: {len(sticks)} members')
    svg, raw_n, fin_n = render(sticks, name, desc, tol)
    out_file = os.path.join(OUT_DIR, f'big_truss_{safe}.svg')
    open(out_file, 'w', encoding='utf-8').write(svg)
    generated.append((name, len(sticks), out_file, raw_n, fin_n))
    print(f'  {raw_n} crossings -> {fin_n} bolts (tol={tol}mm)  Wrote {os.path.basename(out_file)}')

# Build index
idx = ['<!DOCTYPE html><html><head><title>Really complex trusses</title>',
       '<style>',
       '*{box-sizing:border-box}',
       'body{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:24px;background:#f1f5f9}',
       'h1{margin:0 0 12px}',
       '.sub{color:#4a5568;margin-bottom:24px}',
       '.card{background:white;border:1px solid #cbd5e0;border-radius:6px;margin-bottom:24px;overflow:hidden}',
       '.card-head{padding:14px 18px;background:#fafaf8;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center}',
       '.card-head h2{margin:0;font-size:16px}',
       '.card-head a{color:#2563eb;text-decoration:none;padding:5px 12px;border:1px solid #93c5fd;border-radius:3px;font-size:12px}',
       '.card-head a:hover{background:#dbeafe}',
       '.stat{color:#14532d;font-weight:600;font-size:12px;margin-top:2px}',
       'iframe{border:0;width:100%;height:880px;display:block;background:white}',
       '</style></head><body>',
       '<h1>Really complex trusses with centreline-crossing bolts</h1>',
       '<p class="sub">Six classic complex truss types. Green dots are exact mathematical centreline crossings (clustered to one bolt per joint zone). x N labels mean N pair-crossings merged into one bolt.</p>']
for name, count, path, raw, final in generated:
    fname = os.path.basename(path)
    idx.append(f'<div class="card"><div class="card-head"><div><h2>{name}</h2><div class="stat">{count} members &middot; {raw} crossings &rarr; {final} bolts</div></div><a href="{fname}" target="_blank">open standalone &uarr;&rarr;</a></div><iframe src="{fname}"></iframe></div>')
idx.append('</body></html>')
idx_path = os.path.join(OUT_DIR, 'COMPLEX_TRUSSES.html')
open(idx_path, 'w', encoding='utf-8').write('\n'.join(idx))
print(f'\nWrote index: {idx_path}')
