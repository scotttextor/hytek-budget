"""V4 - WEB HOLE drilled correctly + LIP NOTCH added.

Fixes:
  - WEB HOLE: 3 actual drilled Ø3.8mm holes at 17mm pitch (along web centreline).
    Green screw cap is OPTIONAL on top of the holes.
  - LIP NOTCH: drawn at every CSV LIP NOTCH position - small rectangular cut
    at the lip edge per F37008 reference (looks like Web Tab in your reference).
  - Pulls every op straight from CSV so positions are guaranteed correct.
"""
import re, math, os

XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075.xml'
CSV = r'C:/Users/Scott/AppData/Local/Temp/2603191-GF-LIN-89.075.csv'
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

def parse_csv_ops(frame_name):
    out = {}
    with open(CSV) as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) < 14 or parts[0] != 'COMPONENT': continue
            full = parts[1]
            if not full.startswith(frame_name + '-'): continue
            short = full[len(frame_name)+1:]
            length = float(parts[7])
            ops_raw = parts[13:]
            ops = []
            i = 0
            while i+1 < len(ops_raw):
                tool = ops_raw[i]
                try:
                    pos = float(ops_raw[i+1])
                    ops.append((tool, pos))
                except:
                    pass
                i += 2
            out[short] = {'length':length, 'ops':ops}
    return out

def line_intersection(p1, p2, p3, p4, slack=200):
    x1, z1 = p1; x2, z2 = p2; x3, z3 = p3; x4, z4 = p4
    denom = (x1-x2)*(z3-z4) - (z1-z2)*(x3-x4)
    if abs(denom) < 1e-9: return None
    t = ((x1-x3)*(z3-z4) - (z1-z3)*(x3-x4)) / denom
    u = -((x1-x2)*(z1-z3) - (z1-z2)*(x1-x3)) / denom
    L1 = math.hypot(x2-x1, z2-z1); L2 = math.hypot(x4-x3, z4-z3)
    st_ = slack/L1 if L1>0 else 0; su = slack/L2 if L2>0 else 0
    if not (-st_ <= t <= 1+st_): return None
    if not (-su <= u <= 1+su): return None
    return (x1 + t*(x2-x1), z1 + t*(z2-z1))

def all_crossings(sticks):
    out = []
    for i in range(len(sticks)):
        for j in range(i+1, len(sticks)):
            pt = line_intersection(sticks[i]['start'], sticks[i]['end'],
                                   sticks[j]['start'], sticks[j]['end'])
            if pt: out.append({'pt':pt})
    return out

def cluster(crossings, tol=180):
    if not crossings: return []
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
    return [{'pt':(sum(g['pt'][0] for g in grp)/len(grp),
                   sum(g['pt'][1] for g in grp)/len(grp))} for grp in cl.values()]

WIDTH_MM = 89.0
LIP_MM = 12.0

DEFS = '''<defs>
  <linearGradient id="galv" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#dde6ed"/>
    <stop offset="50%" stop-color="#a8b9c7"/>
    <stop offset="100%" stop-color="#7a8b9a"/>
  </linearGradient>
  <linearGradient id="galv-chord" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#cfd9e2"/>
    <stop offset="50%" stop-color="#9eaebd"/>
    <stop offset="100%" stop-color="#6e8090"/>
  </linearGradient>
  <linearGradient id="swage-press" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#7a8b9a"/>
    <stop offset="20%" stop-color="#566270"/>
    <stop offset="80%" stop-color="#566270"/>
    <stop offset="100%" stop-color="#7a8b9a"/>
  </linearGradient>
  <radialGradient id="hole-deep" cx="0.4" cy="0.4" r="0.6">
    <stop offset="0%" stop-color="#0a0a0a"/>
    <stop offset="70%" stop-color="#3a3a3a"/>
    <stop offset="100%" stop-color="#5a5a5a"/>
  </radialGradient>
  <radialGradient id="hole-rim" cx="0.5" cy="0.5" r="0.5">
    <stop offset="80%" stop-color="white" stop-opacity="0"/>
    <stop offset="95%" stop-color="white" stop-opacity="0.55"/>
    <stop offset="100%" stop-color="white" stop-opacity="0"/>
  </radialGradient>
  <pattern id="lip-cut-hatch" patternUnits="userSpaceOnUse" width="3" height="3" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="3" stroke="#dc2626" stroke-width="0.6"/>
  </pattern>
  <pattern id="spangle" patternUnits="userSpaceOnUse" width="50" height="50">
    <ellipse cx="10" cy="15" rx="6" ry="3" fill="white" opacity="0.05" transform="rotate(20 10 15)"/>
    <ellipse cx="35" cy="30" rx="8" ry="4" fill="white" opacity="0.04" transform="rotate(-15 35 30)"/>
    <ellipse cx="20" cy="42" rx="5" ry="2.5" fill="white" opacity="0.06" transform="rotate(40 20 42)"/>
  </pattern>
  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#a8a8a8"/>
    <stop offset="1" stop-color="#7a7a7a"/>
  </linearGradient>
  <filter id="blur3"><feGaussianBlur stdDeviation="3"/></filter>
  <filter id="blur5"><feGaussianBlur stdDeviation="5"/></filter>
</defs>'''

def member_corners(stick):
    sx, sz = stick['start']; ex, ez = stick['end']
    dx, dz = ex-sx, ez-sz
    L = math.hypot(dx, dz)
    if L == 0: return None
    nx, nz = -dz/L, dx/L
    h = WIDTH_MM/2
    pa = (sx + nx*h, sz + nz*h)
    pb = (sx - nx*h, sz - nz*h)
    pc = (ex - nx*h, ez - nz*h)
    pd = (ex + nx*h, ez + nz*h)
    pa_l = (sx + nx*(h-3), sz + nz*(h-3))
    pb_l = (sx - nx*(h-3), sz - nz*(h-3))
    pc_l = (ex - nx*(h-3), ez - nz*(h-3))
    pd_l = (ex + nx*(h-3), ez + nz*(h-3))
    return {'corners':(pa, pb, pc, pd), 'lip':(pa_l, pb_l, pc_l, pd_l),
            'axis':(dx/L, dz/L), 'perp':(nx, nz), 'L':L,
            'mid':((sx+ex)/2, (sz+ez)/2)}

def draw_member(stick, scale_fn, is_chord=False):
    info = member_corners(stick)
    if not info: return ''
    pa, pb, pc, pd = info['corners']
    pa_l, pb_l, pc_l, pd_l = info['lip']
    pts = lambda lst: ' '.join(f'{a:.1f},{b:.1f}' for a,b in (scale_fn(*p) for p in lst))
    fill = 'url(#galv-chord)' if is_chord else 'url(#galv)'
    out = []
    out.append(f'<polygon points="{pts([pa, pb, pc, pd])}" fill="{fill}"/>')
    out.append(f'<polygon points="{pts([pa, pb, pc, pd])}" fill="url(#spangle)" opacity="0.7"/>')
    # Lip-fold thin lines along edges
    for line_pair in [(pa, pd, pa_l, pd_l), (pb, pc, pb_l, pc_l)]:
        e1, e2, in1, in2 = line_pair
        out.append(f'<line x1="{scale_fn(*e1)[0]:.1f}" y1="{scale_fn(*e1)[1]:.1f}" x2="{scale_fn(*e2)[0]:.1f}" y2="{scale_fn(*e2)[1]:.1f}" stroke="#3a4654" stroke-width="0.6" opacity="0.7"/>')
        out.append(f'<line x1="{scale_fn(*in1)[0]:.1f}" y1="{scale_fn(*in1)[1]:.1f}" x2="{scale_fn(*in2)[0]:.1f}" y2="{scale_fn(*in2)[1]:.1f}" stroke="#5a6c7c" stroke-width="0.5" opacity="0.5"/>')
    out.append(f'<polygon points="{pts([pa, pb, pc, pd])}" fill="none" stroke="#1a2329" stroke-width="0.9"/>')
    return '\n'.join(out)

def draw_swage(stick, position_mm, scale_fn):
    """SWAGE = rectangular pressed depression 10mm long × 30mm tall."""
    info = member_corners(stick)
    if not info: return ''
    sx, sz = stick['start']
    ax, az = info['axis']; nx, nz = info['perp']
    cx = sx + ax*position_mm; cz = sz + az*position_mm
    LEN, HGT, INSET = 10, 30, 2

    def at(la, ha): return (cx + ax*la + nx*ha, cz + az*la + nz*ha)
    p1 = at(-LEN/2, HGT/2); p2 = at(LEN/2, HGT/2); p3 = at(LEN/2, -HGT/2); p4 = at(-LEN/2, -HGT/2)
    p1i = at(-LEN/2+INSET, HGT/2); p2i = at(LEN/2-INSET, HGT/2)
    p4i = at(-LEN/2+INSET, -HGT/2); p3i = at(LEN/2-INSET, -HGT/2)

    pts = lambda lst: ' '.join(f'{a:.1f},{b:.1f}' for a,b in (scale_fn(*p) for p in lst))
    out = []
    out.append(f'<polygon points="{pts([p1, p2, p3, p4])}" fill="url(#swage-press)" stroke="#2a3540" stroke-width="0.5" opacity="0.85"/>')
    # Inner parallel highlight lines (the "press" indicator)
    out.append(f'<line x1="{scale_fn(*p1i)[0]:.1f}" y1="{scale_fn(*p1i)[1]:.1f}" x2="{scale_fn(*p4i)[0]:.1f}" y2="{scale_fn(*p4i)[1]:.1f}" stroke="white" stroke-width="0.5" opacity="0.5"/>')
    out.append(f'<line x1="{scale_fn(*p2i)[0]:.1f}" y1="{scale_fn(*p2i)[1]:.1f}" x2="{scale_fn(*p3i)[0]:.1f}" y2="{scale_fn(*p3i)[1]:.1f}" stroke="white" stroke-width="0.5" opacity="0.5"/>')
    return '\n'.join(out)

def draw_lip_notch(stick, position_mm, scale_fn):
    """LIP NOTCH = small rectangular cut at BOTH lip edges (top + bottom) at given position.
    Per F37008: ~12mm long along stick × cuts the full 12mm lip depth."""
    info = member_corners(stick)
    if not info: return ''
    sx, sz = stick['start']
    ax, az = info['axis']; nx, nz = info['perp']
    cx = sx + ax*position_mm; cz = sz + az*position_mm
    LEN = 12  # along stick
    h = WIDTH_MM/2  # half web

    def at(la, ha): return (cx + ax*la + nx*ha, cz + az*la + nz*ha)

    pts = lambda lst: ' '.join(f'{a:.1f},{b:.1f}' for a,b in (scale_fn(*p) for p in lst))
    out = []
    # Top lip cut (perp = +nx,+nz side)
    p1 = at(-LEN/2, h); p2 = at(LEN/2, h); p3 = at(LEN/2, h-LIP_MM); p4 = at(-LEN/2, h-LIP_MM)
    out.append(f'<polygon points="{pts([p1, p2, p3, p4])}" fill="url(#bg)" stroke="#dc2626" stroke-width="1"/>')
    out.append(f'<polygon points="{pts([p1, p2, p3, p4])}" fill="url(#lip-cut-hatch)" opacity="0.7"/>')
    # Bottom lip cut (perp = -nx,-nz side)
    p5 = at(-LEN/2, -h); p6 = at(LEN/2, -h); p7 = at(LEN/2, -(h-LIP_MM)); p8 = at(-LEN/2, -(h-LIP_MM))
    out.append(f'<polygon points="{pts([p5, p6, p7, p8])}" fill="url(#bg)" stroke="#dc2626" stroke-width="1"/>')
    out.append(f'<polygon points="{pts([p5, p6, p7, p8])}" fill="url(#lip-cut-hatch)" opacity="0.7"/>')
    return '\n'.join(out)

def draw_web_hole_pattern(cx_px, cy_px, perp_x, perp_y, scale, show_screws=True):
    """3 actual drilled holes Ø3.8mm at 17mm pitch ON the web centreline.
    Optionally show green screw caps on top."""
    out = []
    HOLE_DIA = 3.8  # mm
    PITCH = 17  # mm
    radius = HOLE_DIA/2 * scale
    spacing = PITCH * scale
    for offset in [-spacing, 0, spacing]:
        hx = cx_px + perp_x * offset
        hy = cy_px + perp_y * offset
        # Outer bevel
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius+0.6:.2f}" fill="url(#hole-rim)"/>')
        # Drilled hole interior
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius:.2f}" fill="url(#hole-deep)"/>')
        # Hole rim
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius:.2f}" fill="none" stroke="#000" stroke-width="0.4" opacity="0.6"/>')
        # Catch light bottom-right
        out.append(f'<circle cx="{hx+radius*0.3:.1f}" cy="{hy+radius*0.3:.1f}" r="{radius*0.25:.2f}" fill="white" opacity="0.55"/>')

        if show_screws:
            # Green screw cap on top of hole
            screw_r = radius * 1.8  # cap is bigger than hole
            out.append(f'<circle cx="{hx+1:.1f}" cy="{hy+1.5:.1f}" r="{screw_r+0.4:.2f}" fill="black" opacity="0.4" filter="url(#blur3)"/>')
            out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{screw_r+0.3:.2f}" fill="#365314"/>')
            out.append(f'<defs><radialGradient id="cap-grad-{int(hx)}-{int(hy)}" cx="0.35" cy="0.35" r="0.7"><stop offset="0%" stop-color="#a3e635"/><stop offset="50%" stop-color="#65a30d"/><stop offset="100%" stop-color="#365314"/></radialGradient></defs>')
            out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{screw_r:.2f}" fill="url(#cap-grad-{int(hx)}-{int(hy)})"/>')
            out.append(f'<ellipse cx="{hx-screw_r*0.3:.1f}" cy="{hy-screw_r*0.3:.1f}" rx="{screw_r*0.4:.2f}" ry="{screw_r*0.25:.2f}" fill="white" opacity="0.5"/>')
            # Phillips
            out.append(f'<line x1="{hx-screw_r*0.4:.1f}" y1="{hy:.1f}" x2="{hx+screw_r*0.4:.1f}" y2="{hy:.1f}" stroke="#1a2e0a" stroke-width="0.5" opacity="0.7"/>')
            out.append(f'<line x1="{hx:.1f}" y1="{hy-screw_r*0.4:.1f}" x2="{hx:.1f}" y2="{hy+screw_r*0.4:.1f}" stroke="#1a2e0a" stroke-width="0.5" opacity="0.7"/>')
    return '\n'.join(out)

def render_truss(frame_name='TN2-1', show_screws=True):
    sticks = parse_frame(frame_name)
    crossings = all_crossings(sticks)
    nodes = cluster(crossings, 180)
    csv_ops = parse_csv_ops(frame_name)

    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    xmin, xmax = min(all_x)-300, max(all_x)+300
    zmin, zmax = min(all_z)-300, max(all_z)+300
    mm_w = xmax-xmin; mm_h = zmax-zmin

    PAGE_W, PAGE_H = 1900, 1180
    margin_top = 130; margin = 40
    draw_w = PAGE_W - 2*margin
    draw_h = PAGE_H - margin_top - margin - 90
    SCALE = min(draw_w/mm_w, draw_h/mm_h)
    ox = margin + (draw_w - mm_w*SCALE)/2
    oy = margin_top + (draw_h - mm_h*SCALE)/2
    def to_px(x, z): return (ox + (x-xmin)*SCALE, oy + (zmax-z)*SCALE)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append(DEFS)
    svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="url(#bg)"/>')

    # Header
    svg.append(f'<rect x="0" y="0" width="{PAGE_W}" height="105" fill="white" opacity="0.95"/>')
    svg.append(f'<text x="40" y="42" font-size="26" font-weight="700" fill="#1a202c">Truss frame {frame_name} — V4 (correct holes + lip notches)</text>')
    svg.append(f'<text x="40" y="68" font-size="14" fill="#4a5568">3 × Ø3.8mm drilled holes per F37008 spec · LIP NOTCHES at every CSV position · SWAGE rectangles on web</text>')

    # Drop shadows
    svg.append('<g opacity="0.55">')
    SH = 6
    for s in sticks:
        info = member_corners(s)
        if not info: continue
        pa, pb, pc, pd = info['corners']
        ps = []
        for p in [pa, pb, pc, pd]:
            sx, sy = to_px(*p); ps.append(f'{sx+SH:.1f},{sy+SH:.1f}')
        svg.append(f'<polygon points="{" ".join(ps)}" fill="black" opacity="0.4" filter="url(#blur5)"/>')
    svg.append('</g>')

    # Members
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(draw_member(s, to_px, is_chord=True))
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(draw_member(s, to_px, is_chord=False))

    # Now draw OPS - swages, lip notches - on top of members
    for s in sticks:
        ops_data = csv_ops.get(s['name'])
        if not ops_data: continue
        for tool, pos in ops_data['ops']:
            if tool == 'SWAGE' and s['type'] != 'Plate':
                svg.append(draw_swage(s, pos, to_px))
            elif tool == 'LIP NOTCH':
                svg.append(draw_lip_notch(s, pos, to_px))

    # Member labels
    for s in sticks:
        info = member_corners(s)
        if not info: continue
        px, py = to_px(*info['mid'])
        svg.append(f'<text x="{px:.1f}" y="{py+4:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="#1a202c" stroke="white" stroke-width="3.5" paint-order="stroke" opacity="0.9">{s["name"]}</text>')

    # WEB HOLE patterns at every centreline crossing
    for n in nodes:
        cx_mm, cz_mm = n['pt']
        web = None
        for s in sticks:
            if s['type'] != 'Plate':
                sx, sz = s['start']; ex, ez = s['end']
                d = math.hypot(ex-sx, ez-sz)
                if d == 0: continue
                t = ((cx_mm-sx)*(ex-sx) + (cz_mm-sz)*(ez-sz)) / (d*d)
                if -0.1 <= t <= 1.1:
                    px = sx + t*(ex-sx); pz = sz + t*(ez-sz)
                    if math.hypot(cx_mm-px, cz_mm-pz) < 50:
                        web = s; break
        if web:
            sx, sz = web['start']; ex, ez = web['end']
            dx, dy = ex-sx, ez-sz; L = math.hypot(dx, dy)
            ax_x = dx/L; ax_y = -dy/L
            perp_x = -ax_y; perp_y = ax_x
        else:
            perp_x, perp_y = 0, 1
        cx_px, cy_px = to_px(cx_mm, cz_mm)
        svg.append(draw_web_hole_pattern(cx_px, cy_px, perp_x, perp_y, SCALE, show_screws))

    # Spec card
    cx_card = PAGE_W - 290; cy_card = 130
    svg.append(f'<rect x="{cx_card-3}" y="{cy_card+3}" width="270" height="380" fill="rgba(0,0,0,0.18)" filter="url(#blur5)"/>')
    svg.append(f'<rect x="{cx_card}" y="{cy_card}" width="270" height="380" fill="white" stroke="#cbd5e0" rx="6"/>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+24}" font-size="14" font-weight="700" fill="#1a202c">Tools shown</text>')

    # WEB HOLE pattern
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+50}" font-size="11" font-weight="700" fill="#374151">WEB HOLE — drilled</text>')
    wcx = cx_card + 60; wcy = cy_card + 95
    for off in [-15, 0, 15]:
        svg.append(f'<circle cx="{wcx}" cy="{wcy+off}" r="4" fill="url(#hole-rim)"/>')
        svg.append(f'<circle cx="{wcx}" cy="{wcy+off}" r="3.4" fill="url(#hole-deep)"/>')
        svg.append(f'<circle cx="{wcx}" cy="{wcy+off}" r="3.4" fill="none" stroke="#000" stroke-width="0.4"/>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+80}" font-size="10" fill="#374151">3 × Ø3.8 mm</text>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+94}" font-size="10" fill="#374151">17 mm pitch</text>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+108}" font-size="10" fill="#374151">on web ℄</text>')

    # SWAGE
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+150}" font-size="11" font-weight="700" fill="#374151">SWAGE</text>')
    swcx = cx_card + 60; swcy = cy_card + 180
    sw_w = 50; sw_h = 22
    svg.append(f'<rect x="{swcx-sw_w/2}" y="{swcy-sw_h/2}" width="{sw_w}" height="{sw_h}" fill="url(#swage-press)" stroke="#2a3540" stroke-width="0.6"/>')
    svg.append(f'<line x1="{swcx-sw_w/2+5}" y1="{swcy-sw_h/2+1}" x2="{swcx-sw_w/2+5}" y2="{swcy+sw_h/2-1}" stroke="white" stroke-width="0.4" opacity="0.5"/>')
    svg.append(f'<line x1="{swcx+sw_w/2-5}" y1="{swcy-sw_h/2+1}" x2="{swcx+sw_w/2-5}" y2="{swcy+sw_h/2-1}" stroke="white" stroke-width="0.4" opacity="0.5"/>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+178}" font-size="10" fill="#374151">10 × 30 mm</text>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+192}" font-size="10" fill="#374151">pressed</text>')

    # LIP NOTCH
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+230}" font-size="11" font-weight="700" fill="#374151">LIP NOTCH</text>')
    lncx = cx_card + 60; lncy = cy_card + 265
    svg.append(f'<rect x="{lncx-25}" y="{lncy-22}" width="50" height="10" fill="url(#bg)" stroke="#dc2626" stroke-width="0.7"/>')
    svg.append(f'<rect x="{lncx-25}" y="{lncy-22}" width="50" height="10" fill="url(#lip-cut-hatch)" opacity="0.7"/>')
    svg.append(f'<rect x="{lncx-25}" y="{lncy-12}" width="50" height="24" fill="#cccccc" stroke="#666" stroke-width="0.5" opacity="0.4"/>')
    svg.append(f'<rect x="{lncx-25}" y="{lncy+12}" width="50" height="10" fill="url(#bg)" stroke="#dc2626" stroke-width="0.7"/>')
    svg.append(f'<rect x="{lncx-25}" y="{lncy+12}" width="50" height="10" fill="url(#lip-cut-hatch)" opacity="0.7"/>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+260}" font-size="10" fill="#374151">12 mm long</text>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+274}" font-size="10" fill="#374151">cuts both lips</text>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+288}" font-size="10" fill="#374151">at end of web</text>')

    # Stats
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+325}" font-size="11" font-weight="700" fill="#374151">Frame stats</text>')
    sw_count = sum(1 for s in sticks for t,_ in csv_ops.get(s['name'],{}).get('ops',[]) if t=='SWAGE')
    ln_count = sum(1 for s in sticks for t,_ in csv_ops.get(s['name'],{}).get('ops',[]) if t=='LIP NOTCH')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+345}" font-size="10" fill="#4a5568">Members: {len(sticks)} | Nodes: {len(nodes)}</text>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+361}" font-size="10" fill="#4a5568">Web holes: {len(nodes)*3} (3/node)</text>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+377}" font-size="10" fill="#4a5568">Swages: {sw_count} | Lip notches: {ln_count}</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# Render WITH screws and WITHOUT (just holes)
print('V4 truss WITH green screw caps...')
out1 = os.path.join(OUT_DIR, 'truss_v4_screws.svg')
open(out1, 'w', encoding='utf-8').write(render_truss('TN2-1', show_screws=True))
print(f'Wrote {out1}')

print('V4 truss WITHOUT screws (showing pure drilled holes)...')
out2 = os.path.join(OUT_DIR, 'truss_v4_holes.svg')
open(out2, 'w', encoding='utf-8').write(render_truss('TN2-1', show_screws=False))
print(f'Wrote {out2}')

idx = '''<!DOCTYPE html><html><head><title>V4</title>
<style>
*{box-sizing:border-box}
body{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:24px;background:#1a202c;color:#e2e8f0}
h1{margin:0 0 12px;color:white}
.sub{color:#94a3b8;margin-bottom:24px}
.card{background:white;color:#1a202c;border:1px solid #4a5568;border-radius:6px;margin-bottom:24px;overflow:hidden}
.card-head{padding:14px 18px;background:#fafaf8;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center}
.card-head h2{margin:0;font-size:16px}
.card-head a{color:#2563eb;text-decoration:none;padding:5px 12px;border:1px solid #93c5fd;border-radius:3px;font-size:12px}
iframe{border:0;width:100%;height:1240px;display:block;background:white}
</style></head><body>
<h1>V4 — correct WEB HOLE + LIP NOTCH</h1>
<p class="sub">3 × Ø3.8mm drilled holes per F37008. Lip notch at every CSV LIP NOTCH position (red hatched cuts at lip edges). SWAGE rectangles on web body.</p>
<div class="card"><div class="card-head"><div><h2>1. With green screw caps over the holes</h2><div style="font-size:12px;color:#4a5568">Assembled view - shows what you see on the bench</div></div><a href="truss_v4_screws.svg" target="_blank">open standalone ↑</a></div><iframe src="truss_v4_screws.svg"></iframe></div>
<div class="card"><div class="card-head"><div><h2>2. Pure drilled holes (no screws)</h2><div style="font-size:12px;color:#4a5568">Pre-assembly view - shows the steel coming off the rollformer</div></div><a href="truss_v4_holes.svg" target="_blank">open standalone ↑</a></div><iframe src="truss_v4_holes.svg"></iframe></div>
</body></html>'''
open(os.path.join(OUT_DIR, 'V4.html'), 'w', encoding='utf-8').write(idx)
print('Wrote V4.html')
