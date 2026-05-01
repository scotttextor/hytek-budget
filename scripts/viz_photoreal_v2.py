"""Photoreal v2 — fixes:
  - Truss now actually renders (no broken filter chain)
  - SWAGE drawn correctly: discrete LOZENGE pressings at the real CSV positions,
    not a continuous stripe. Shape from F37008 spec.
  - WEB HOLE pattern (3 x Ø3.8mm at 17mm spacing)
  - All tool reference fits in viewport
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
    """Get per-stick operations from CSV for one frame."""
    ops_by_stick = {}
    with open(CSV) as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) < 14 or parts[0] != 'COMPONENT': continue
            name = parts[1]
            if not name.startswith(frame_name + '-'): continue
            short = name.replace(frame_name + '-', '')
            length = float(parts[7])
            ops_raw = parts[13:]
            ops = []
            i = 0
            while i + 1 < len(ops_raw):
                tool = ops_raw[i]
                try:
                    pos = float(ops_raw[i+1])
                    ops.append((tool, pos))
                except:
                    pass
                i += 2
            ops_by_stick[short] = {'length':length, 'ops':ops}
    return ops_by_stick

def line_intersection(p1, p2, p3, p4, slack_mm=200):
    x1, z1 = p1; x2, z2 = p2; x3, z3 = p3; x4, z4 = p4
    denom = (x1-x2)*(z3-z4) - (z1-z2)*(x3-x4)
    if abs(denom) < 1e-9: return None
    t = ((x1-x3)*(z3-z4) - (z1-z3)*(x3-x4)) / denom
    u = -((x1-x2)*(z1-z3) - (z1-z2)*(x1-x3)) / denom
    L1 = math.hypot(x2-x1, z2-z1); L2 = math.hypot(x4-x3, z4-z3)
    st_ = slack_mm/L1 if L1>0 else 0; su = slack_mm/L2 if L2>0 else 0
    if not (-st_ <= t <= 1+st_): return None
    if not (-su <= u <= 1+su): return None
    return (x1 + t*(x2-x1), z1 + t*(z2-z1))

def all_crossings(sticks, slack=200):
    out = []
    for i in range(len(sticks)):
        for j in range(i+1, len(sticks)):
            pt = line_intersection(sticks[i]['start'], sticks[i]['end'],
                                   sticks[j]['start'], sticks[j]['end'], slack)
            if pt:
                out.append({'pt':pt})
    return out

def cluster(crossings, tol):
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
    out = []
    for grp in cl.values():
        cx = sum(g['pt'][0] for g in grp)/len(grp)
        cy = sum(g['pt'][1] for g in grp)/len(grp)
        out.append({'pt':(cx,cy)})
    return out

WIDTH_MM = 89.0

# ================= COMMON DEFS (no broken filter chains) =================
DEFS = '''<defs>
  <linearGradient id="galv" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#eef2f6"/>
    <stop offset="25%" stop-color="#dee3e9"/>
    <stop offset="60%" stop-color="#bcc4cd"/>
    <stop offset="100%" stop-color="#8d959e"/>
  </linearGradient>
  <linearGradient id="lip-strip" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#f4f7fa"/>
    <stop offset="100%" stop-color="#a8b0b8"/>
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

  <!-- SWAGE - localized embossed lozenge pressed into web -->
  <radialGradient id="swage-press" cx="0.5" cy="0.5" r="0.6">
    <stop offset="0%" stop-color="#5a626c"/>
    <stop offset="40%" stop-color="#6a727c"/>
    <stop offset="80%" stop-color="#a8b0b8"/>
    <stop offset="100%" stop-color="#cad0d7"/>
  </radialGradient>

  <pattern id="spangle" patternUnits="userSpaceOnUse" width="60" height="60">
    <rect width="60" height="60" fill="none"/>
    <ellipse cx="12" cy="18" rx="9" ry="5" fill="white" opacity="0.04" transform="rotate(20 12 18)"/>
    <ellipse cx="42" cy="34" rx="11" ry="6" fill="white" opacity="0.03" transform="rotate(-15 42 34)"/>
    <ellipse cx="22" cy="48" rx="7" ry="4" fill="white" opacity="0.05" transform="rotate(40 22 48)"/>
  </pattern>

  <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f8f9fa"/>
    <stop offset="1" stop-color="#dde1e6"/>
  </linearGradient>
</defs>'''

def draw_member(stick, scale_fn, is_chord=False):
    """Galvanised steel member with lit edges and lip strips."""
    sx, sz = stick['start']; ex, ez = stick['end']
    dx, dz = ex-sx, ez-sz
    L = math.hypot(dx, dz)
    if L == 0: return ''
    nx, nz = -dz/L, dx/L
    h = WIDTH_MM/2
    lip = 12
    # Outer + inner-lip-edge points
    p_a = (sx+nx*h, sz+nz*h)
    p_b = (sx-nx*h, sz-nz*h)
    p_c = (ex-nx*h, ez-nz*h)
    p_d = (ex+nx*h, ez+nz*h)
    p_a_in = (sx+nx*(h-lip), sz+nz*(h-lip))
    p_d_in = (ex+nx*(h-lip), ez+nz*(h-lip))
    p_b_in = (sx-nx*(h-lip), sz-nz*(h-lip))
    p_c_in = (ex-nx*(h-lip), ez-nz*(h-lip))

    pts = lambda lst: ' '.join(f'{a:.1f},{b:.1f}' for a,b in (scale_fn(*p) for p in lst))

    out = []
    # Soft drop shadow (skip filter chain — use offset+blur via static dark polygon)
    shadow_off = 4
    sa = scale_fn(*p_a); sb = scale_fn(*p_b); sc = scale_fn(*p_c); sd = scale_fn(*p_d)
    out.append(f'<polygon points="{sa[0]+shadow_off:.1f},{sa[1]+shadow_off:.1f} {sb[0]+shadow_off:.1f},{sb[1]+shadow_off:.1f} {sc[0]+shadow_off:.1f},{sc[1]+shadow_off:.1f} {sd[0]+shadow_off:.1f},{sd[1]+shadow_off:.1f}" fill="rgba(0,0,0,0.18)" filter="url(#blur)"/>')
    # Body with steel gradient
    out.append(f'<polygon points="{pts([p_a, p_b, p_c, p_d])}" fill="url(#galv)"/>')
    # Spangle texture
    out.append(f'<polygon points="{pts([p_a, p_b, p_c, p_d])}" fill="url(#spangle)" opacity="0.7"/>')
    # Top lip strip (lit)
    out.append(f'<polygon points="{pts([p_a, p_d, p_d_in, p_a_in])}" fill="url(#lip-strip)" stroke="#5a626c" stroke-width="0.5"/>')
    # Bottom lip strip (shadowed - reverse gradient)
    out.append(f'<polygon points="{pts([p_b_in, p_c_in, p_c, p_b])}" fill="url(#lip-strip)" stroke="#5a626c" stroke-width="0.5" opacity="0.85"/>')
    # Outline
    out.append(f'<polygon points="{pts([p_a, p_b, p_c, p_d])}" fill="none" stroke="#3a3f47" stroke-width="0.9"/>')
    # Top edge highlight
    out.append(f'<polyline points="{pts([p_a, p_d])}" fill="none" stroke="white" stroke-width="0.9" opacity="0.7"/>')
    # Bottom edge shadow
    out.append(f'<polyline points="{pts([p_b, p_c])}" fill="none" stroke="#1f2329" stroke-width="0.9" opacity="0.5"/>')
    return '\n'.join(out)

def draw_swage_lozenge(stick, position_mm, scale_fn, length_mm=10, height_mm=32):
    """Discrete swage feature - lozenge pressed into the web at given position from start.
    Real F37008 swage is ~10mm long × ~32mm tall, pressed centred on web."""
    sx, sz = stick['start']; ex, ez = stick['end']
    dx, dz = ex-sx, ez-sz
    L = math.hypot(dx, dz)
    if L == 0: return ''
    # Unit vector along stick
    ax, az = dx/L, dz/L
    # Perpendicular (web direction)
    px, pz = -az, ax

    # Centre of swage
    cx = sx + ax*position_mm
    cz = sz + az*position_mm

    # 4 corners of the lozenge in stick-local coords
    half_l = length_mm/2
    half_h = height_mm/2
    corners = []
    for sign_l, sign_h in [(-1,-1), (1,-1), (1,1), (-1,1)]:
        wx = cx + ax*sign_l*half_l + px*sign_h*half_h
        wz = cz + az*sign_l*half_l + pz*sign_h*half_h
        corners.append((wx, wz))

    # Tip points (more lozenge-like)
    tip_l = (cx + ax*-half_l*1.3, cz + az*-half_l*1.3)
    tip_r = (cx + ax*half_l*1.3, cz + az*half_l*1.3)

    pts_screen = [scale_fn(*p) for p in [tip_l, (cx+ax*-half_l*0.5+px*half_h, cz+az*-half_l*0.5+pz*half_h),
                                          (cx+ax*half_l*0.5+px*half_h, cz+az*half_l*0.5+pz*half_h),
                                          tip_r,
                                          (cx+ax*half_l*0.5-px*half_h, cz+az*half_l*0.5-pz*half_h),
                                          (cx+ax*-half_l*0.5-px*half_h, cz+az*-half_l*0.5-pz*half_h)]]
    pts_str = ' '.join(f'{a:.1f},{b:.1f}' for a,b in pts_screen)

    out = []
    # Lozenge shape - dark depression pressed into web
    out.append(f'<polygon points="{pts_str}" fill="url(#swage-press)" stroke="#3a3f47" stroke-width="0.5" opacity="0.85"/>')
    # Bright catch on upper edge
    cx_screen = scale_fn(cx, cz)
    # Tiny bright highlight along top edge
    p1 = scale_fn(*tip_l)
    p2 = scale_fn(cx+ax*-half_l*0.5+px*half_h, cz+az*-half_l*0.5+pz*half_h)
    p3 = scale_fn(cx+ax*half_l*0.5+px*half_h, cz+az*half_l*0.5+pz*half_h)
    p4 = scale_fn(*tip_r)
    out.append(f'<path d="M {p1[0]:.1f},{p1[1]:.1f} L {p2[0]:.1f},{p2[1]:.1f} L {p3[0]:.1f},{p3[1]:.1f} L {p4[0]:.1f},{p4[1]:.1f}" fill="none" stroke="white" stroke-width="0.6" opacity="0.5"/>')
    return '\n'.join(out)

def draw_web_holes(cx, cy, scale, perp_x, perp_y):
    """3 x Ø3.8mm holes drilled through, looking real."""
    out = []
    radius = 1.9 * scale
    spacing = 17 * scale
    rect_w = 14*scale; rect_h = 46*scale
    ang = math.degrees(math.atan2(perp_y, perp_x)) - 90
    out.append(f'<rect x="{cx-rect_w/2:.1f}" y="{cy-rect_h/2:.1f}" width="{rect_w:.1f}" height="{rect_h:.1f}" '
               f'transform="rotate({ang:.1f} {cx:.1f} {cy:.1f})" '
               f'fill="rgba(0,0,0,0.04)" stroke="rgba(0,0,0,0.25)" stroke-width="0.6" stroke-dasharray="2 2" rx="2"/>')
    for offset in [-spacing, 0, spacing]:
        hx = cx + perp_x * offset
        hy = cy + perp_y * offset
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius+0.8:.2f}" fill="url(#hole-rim)"/>')
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius:.2f}" fill="url(#hole-deep)"/>')
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius:.2f}" fill="none" stroke="#000" stroke-width="0.4" opacity="0.6"/>')
        out.append(f'<circle cx="{hx+radius*0.3:.1f}" cy="{hy+radius*0.3:.1f}" r="{radius*0.25:.2f}" fill="white" opacity="0.55"/>')
    return '\n'.join(out)


def render_truss(frame_name='TN2-1', tol=180):
    sticks = parse_frame(frame_name)
    crossings = all_crossings(sticks)
    clustered = cluster(crossings, tol)
    csv_ops = parse_csv_ops(frame_name)

    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    xmin, xmax = min(all_x)-300, max(all_x)+300
    zmin, zmax = min(all_z)-300, max(all_z)+300
    mm_w = xmax-xmin; mm_h = zmax-zmin

    PAGE_W = 1900
    PAGE_H = 1200
    margin_top = 130
    margin_other = 40
    draw_w = PAGE_W - 2*margin_other - 280  # leave space for spec card
    draw_h = PAGE_H - margin_top - margin_other - 70
    SCALE = min(draw_w/mm_w, draw_h/mm_h)
    ox = margin_other
    oy = margin_top + (draw_h - mm_h*SCALE)/2

    def to_px(x, z): return (ox + (x-xmin)*SCALE, oy + (zmax-z)*SCALE)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append(DEFS)
    svg.append(f'<filter id="blur"><feGaussianBlur stdDeviation="3"/></filter>')
    svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="url(#bg)"/>')

    svg.append(f'<text x="40" y="44" font-size="26" font-weight="700" fill="#1a202c">Truss frame {frame_name} — photoreal galvanised steel</text>')
    svg.append(f'<text x="40" y="70" font-size="14" fill="#4a5568">F37008 W089 F41-38 (89×41 lipped C, 0.75mm AZ150). Real swage lozenges + WEB HOLE pattern.</text>')
    svg.append(f'<text x="40" y="94" font-size="13" fill="#374151">{len(sticks)} members &middot; {len(clustered)} junction nodes &middot; {len(clustered)*3} Ø3.8mm holes &middot; {sum(len([o for o in csv_ops.get(s["name"].split("-",2)[-1] if "-" in s["name"] else s["name"], {}).get("ops", []) if o[0]=="SWAGE"]) for s in sticks)} swages from CSV</text>')

    # Members - chords first, webs on top
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(draw_member(s, to_px, is_chord=True))
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(draw_member(s, to_px, is_chord=False))

    # SWAGE lozenges at real CSV positions on each web
    for s in sticks:
        if s['type'] == 'Plate': continue
        # Get short name (W5, W6 etc - csv keys are 'W5' format after stripping frame prefix)
        short_name = s['name']
        # CSV stores as 'W5' (without the frame prefix already stripped)
        ops_data = csv_ops.get(short_name, None)
        if not ops_data: continue
        for tool, pos in ops_data['ops']:
            if tool == 'SWAGE':
                svg.append(draw_swage_lozenge(s, pos, to_px))

    # Member labels
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px,py = to_px(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py+4:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="#1a202c" stroke="white" stroke-width="3.5" paint-order="stroke" opacity="0.85">{s["name"]}</text>')

    # WEB HOLES
    for cl in clustered:
        cx_mm, cy_mm = cl['pt']
        cx_px, cy_px = to_px(cx_mm, cy_mm)
        # Find web direction
        web_stick = None
        for s in sticks:
            if s['type'] != 'Plate':
                sx, sz = s['start']; ex, ez = s['end']
                d = math.hypot(ex-sx, ez-sz)
                if d == 0: continue
                t = ((cx_mm-sx)*(ex-sx) + (cy_mm-sz)*(ez-sz)) / (d*d)
                if -0.1 <= t <= 1.1:
                    px = sx + t*(ex-sx); pz = sz + t*(ez-sz)
                    if math.hypot(cx_mm-px, cy_mm-pz) < 50:
                        web_stick = s; break
        if web_stick:
            sx, sz = web_stick['start']; ex, ez = web_stick['end']
            dx, dy = ex-sx, ez-sz; L = math.hypot(dx, dy)
            ax_x = dx/L; ax_y = -dy/L
            perp_x = -ax_y; perp_y = ax_x
        else:
            perp_x, perp_y = 0, 1
        svg.append(draw_web_holes(cx_px, cy_px, SCALE, perp_x, perp_y))

    # Spec card
    cx_card = PAGE_W - 280; cy_card = 130
    svg.append(f'<rect x="{cx_card-3}" y="{cy_card+3}" width="260" height="280" fill="rgba(0,0,0,0.18)" filter="url(#blur)"/>')
    svg.append(f'<rect x="{cx_card}" y="{cy_card}" width="260" height="280" fill="white" stroke="#cbd5e0" rx="6"/>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+24}" font-size="14" font-weight="700" fill="#1a202c">F37008 W089 F41-38</text>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+42}" font-size="11" fill="#4a5568">89 × 41 lipped C section</text>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+58}" font-size="11" fill="#4a5568">0.75 mm gauge, AZ150 finish</text>')
    svg.append(f'<line x1="{cx_card+15}" y1="{cy_card+72}" x2="{cx_card+245}" y2="{cy_card+72}" stroke="#e2e8f0"/>')
    # Mini WEB HOLE diagram
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+92}" font-size="11" font-weight="700" fill="#374151">WEB HOLE (at every node)</text>')
    cx_mini = cx_card + 35; cy_mini = cy_card + 130
    for off in [-12, 0, 12]:
        svg.append(f'<circle cx="{cx_mini}" cy="{cy_mini+off}" r="2.4" fill="url(#hole-rim)"/>')
        svg.append(f'<circle cx="{cx_mini}" cy="{cy_mini+off}" r="2" fill="url(#hole-deep)"/>')
    svg.append(f'<text x="{cx_card+70}" y="{cy_card+118}" font-size="10" fill="#374151">3 × Ø3.8 mm</text>')
    svg.append(f'<text x="{cx_card+70}" y="{cy_card+132}" font-size="10" fill="#374151">17 mm pitch</text>')
    svg.append(f'<text x="{cx_card+70}" y="{cy_card+146}" font-size="10" fill="#374151">on web ℄</text>')
    svg.append(f'<line x1="{cx_card+15}" y1="{cy_card+165}" x2="{cx_card+245}" y2="{cy_card+165}" stroke="#e2e8f0"/>')
    # Mini SWAGE
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+185}" font-size="11" font-weight="700" fill="#374151">SWAGE lozenge</text>')
    swcx = cx_card + 70; swcy = cy_card + 220
    sw_pts = f'{swcx-22},{swcy} {swcx-12},{swcy-9} {swcx+12},{swcy-9} {swcx+22},{swcy} {swcx+12},{swcy+9} {swcx-12},{swcy+9}'
    svg.append(f'<polygon points="{sw_pts}" fill="url(#swage-press)" stroke="#3a3f47" stroke-width="0.5"/>')
    svg.append(f'<text x="{cx_card+105}" y="{cy_card+212}" font-size="10" fill="#374151">~10 × 32 mm</text>')
    svg.append(f'<text x="{cx_card+105}" y="{cy_card+226}" font-size="10" fill="#374151">pressed into web</text>')
    svg.append(f'<text x="{cx_card+105}" y="{cy_card+240}" font-size="10" fill="#374151">at panel points</text>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+267}" font-size="9" fill="#6b7280">Geometry from F37008 spec rev 0.</text>')

    svg.append('</svg>')
    return '\n'.join(svg)


def render_tool_reference():
    """Tool reference page that fits in viewport."""
    W, H = 1900, 1100
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append(DEFS)
    svg.append(f'<filter id="blur"><feGaussianBlur stdDeviation="3"/></filter>')
    svg.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

    svg.append(f'<text x="30" y="40" font-size="26" font-weight="700" fill="#1a202c">All FrameCAD tools — corrected SWAGE</text>')
    svg.append(f'<text x="30" y="64" font-size="14" fill="#4a5568">F37008 W089 F41-38 spec. Each tool drawn at 4px = 1mm. SWAGE now shown correctly as a lozenge pressing.</text>')

    MM = 4  # 4 px per mm — fits in 1900px width for ~470mm of stick
    stick_y_top = 130
    stick_y_bot = stick_y_top + 89*MM   # 356px
    cy = (stick_y_top + stick_y_bot) / 2
    LIP = 12 * MM

    stick_x0 = 80
    stick_len_mm = (W - 200) / MM   # ~430mm visible
    stick_x1 = stick_x0 + stick_len_mm * MM

    # Stick body
    # Drop shadow
    svg.append(f'<rect x="{stick_x0+4}" y="{stick_y_top+5}" width="{stick_len_mm*MM}" height="{89*MM}" fill="rgba(0,0,0,0.18)" filter="url(#blur)"/>')
    # Main body
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_len_mm*MM}" height="{89*MM}" fill="url(#galv)"/>')
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_len_mm*MM}" height="{89*MM}" fill="url(#spangle)" opacity="0.7"/>')
    # Lip strips
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_len_mm*MM}" height="{LIP}" fill="url(#lip-strip)" stroke="#5a626c" stroke-width="0.6"/>')
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_bot-LIP}" width="{stick_len_mm*MM}" height="{LIP}" fill="url(#lip-strip)" stroke="#5a626c" stroke-width="0.6" opacity="0.85"/>')
    # Outline
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_len_mm*MM}" height="{89*MM}" fill="none" stroke="#3a3f47" stroke-width="1"/>')
    # Top edge bright
    svg.append(f'<line x1="{stick_x0}" y1="{stick_y_top+0.5}" x2="{stick_x1}" y2="{stick_y_top+0.5}" stroke="white" stroke-width="1.2" opacity="0.7"/>')
    # Bottom edge dark
    svg.append(f'<line x1="{stick_x0}" y1="{stick_y_bot-0.5}" x2="{stick_x1}" y2="{stick_y_bot-0.5}" stroke="#1f2329" stroke-width="1.2" opacity="0.5"/>')

    # 89mm dimension
    svg.append(f'<line x1="{stick_x0-30}" y1="{stick_y_top}" x2="{stick_x0-30}" y2="{stick_y_bot}" stroke="#374151" stroke-width="1"/>')
    svg.append(f'<line x1="{stick_x0-35}" y1="{stick_y_top}" x2="{stick_x0-25}" y2="{stick_y_top}" stroke="#374151" stroke-width="1"/>')
    svg.append(f'<line x1="{stick_x0-35}" y1="{stick_y_bot}" x2="{stick_x0-25}" y2="{stick_y_bot}" stroke="#374151" stroke-width="1"/>')
    svg.append(f'<text x="{stick_x0-40}" y="{cy+5}" text-anchor="end" font-size="12" font-weight="700" fill="#374151">89 mm</text>')

    def x_at(mm): return stick_x0 + mm*MM

    # ---- 1. SWAGE — at 30mm — DISCRETE LOZENGE ----
    sw_x = x_at(30)
    # Lozenge: 10mm long (along stick) × 32mm tall
    sw_l = 10*MM; sw_h = 32*MM
    sw_pts = (
        f'{sw_x-sw_l/2*1.3},{cy} '
        f'{sw_x-sw_l/2*0.5},{cy-sw_h/2} '
        f'{sw_x+sw_l/2*0.5},{cy-sw_h/2} '
        f'{sw_x+sw_l/2*1.3},{cy} '
        f'{sw_x+sw_l/2*0.5},{cy+sw_h/2} '
        f'{sw_x-sw_l/2*0.5},{cy+sw_h/2}'
    )
    svg.append(f'<polygon points="{sw_pts}" fill="url(#swage-press)" stroke="#3a3f47" stroke-width="0.7"/>')
    # Highlight on top edge
    svg.append(f'<polyline points="{sw_x-sw_l/2*1.3},{cy} {sw_x-sw_l/2*0.5},{cy-sw_h/2} {sw_x+sw_l/2*0.5},{cy-sw_h/2} {sw_x+sw_l/2*1.3},{cy}" fill="none" stroke="white" stroke-width="0.6" opacity="0.5"/>')

    # ---- 2. WEB HOLE at 90mm ----
    wh_x = x_at(90)
    radius = 1.9 * MM
    spacing = 17 * MM
    for off in [-spacing, 0, spacing]:
        svg.append(f'<circle cx="{wh_x}" cy="{cy+off}" r="{radius+0.8:.2f}" fill="url(#hole-rim)"/>')
        svg.append(f'<circle cx="{wh_x}" cy="{cy+off}" r="{radius:.2f}" fill="url(#hole-deep)"/>')
        svg.append(f'<circle cx="{wh_x}" cy="{cy+off}" r="{radius:.2f}" fill="none" stroke="#000" stroke-width="0.4" opacity="0.6"/>')
        svg.append(f'<circle cx="{wh_x+radius*0.3:.1f}" cy="{cy+off+radius*0.3:.1f}" r="{radius*0.25:.2f}" fill="white" opacity="0.55"/>')

    # ---- 3. WEB BOLT HOLE at 160mm — Ø13.5 ----
    wbh_x = x_at(160)
    bolt_r = 6.75 * MM
    svg.append(f'<circle cx="{wbh_x}" cy="{cy}" r="{bolt_r+1:.2f}" fill="url(#hole-rim)"/>')
    svg.append(f'<circle cx="{wbh_x}" cy="{cy}" r="{bolt_r:.2f}" fill="url(#hole-deep)"/>')
    svg.append(f'<circle cx="{wbh_x}" cy="{cy}" r="{bolt_r:.2f}" fill="none" stroke="#000" stroke-width="0.5" opacity="0.6"/>')
    svg.append(f'<circle cx="{wbh_x+bolt_r*0.35:.1f}" cy="{cy+bolt_r*0.35:.1f}" r="{bolt_r*0.25:.2f}" fill="white" opacity="0.55"/>')

    # ---- 4. LIP CUT at 220mm — angled cut (V-shape) into top + bottom lip ----
    lc_x = x_at(220)
    lc_w = 12 * MM
    svg.append(f'<polygon points="{lc_x-lc_w/2},{stick_y_top} {lc_x+lc_w/2},{stick_y_top} {lc_x},{stick_y_top+LIP}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1.2"/>')
    svg.append(f'<polygon points="{lc_x-lc_w/2},{stick_y_bot} {lc_x+lc_w/2},{stick_y_bot} {lc_x},{stick_y_bot-LIP}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1.2"/>')

    # ---- 5. WEB NOTCH at 280mm ----
    wn_x = x_at(280)
    wn_w = 14*MM; wn_h = 9*MM
    svg.append(f'<rect x="{wn_x-wn_w/2}" y="{stick_y_top+LIP}" width="{wn_w}" height="{wn_h}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1.2"/>')

    # ---- 6. FLANGE CUT at 320mm — 3mm vertical strip ----
    fc_x = x_at(320)
    fc_w = 3 * MM
    svg.append(f'<rect x="{fc_x-fc_w/2}" y="{stick_y_top}" width="{fc_w}" height="{89*MM}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1"/>')

    # ---- 7. SERVICE HOLE at 390mm — Ø32mm ----
    sh_x = x_at(390)
    sh_r = 16*MM
    svg.append(f'<circle cx="{sh_x}" cy="{cy}" r="{sh_r+1.5:.2f}" fill="url(#hole-rim)"/>')
    svg.append(f'<circle cx="{sh_x}" cy="{cy}" r="{sh_r:.2f}" fill="url(#hole-deep)"/>')
    svg.append(f'<circle cx="{sh_x}" cy="{cy}" r="{sh_r:.2f}" fill="none" stroke="#000" stroke-width="0.7" opacity="0.6"/>')
    svg.append(f'<ellipse cx="{sh_x-sh_r*0.4}" cy="{cy-sh_r*0.5}" rx="{sh_r*0.45}" ry="{sh_r*0.18}" fill="white" opacity="0.3" transform="rotate(-30 {sh_x-sh_r*0.4} {cy-sh_r*0.5})"/>')

    # ---- LABELS BELOW THE STICK ----
    label_y = stick_y_bot + 50
    labels = [
        (sw_x, 'SWAGE',          'lozenge press',  '~10 × 32 mm'),
        (wh_x, 'TOOL 1 — WEB HOLE',     '3 × Ø3.8 mm',     '17 mm pitch'),
        (wbh_x, 'TOOL 1 — WEB BOLT HOLE','Ø13.5 mm',       'single hole'),
        (lc_x, 'TOOL 2 — LIP CUT',      'V-cut',          'into lip'),
        (wn_x, 'TOOL 2 — WEB NOTCH',    'rectangular',    '~14 × 9 mm'),
        (fc_x, 'TOOL 3 — FLANGE CUT',   'narrow strip',   '3 mm wide'),
        (sh_x, 'TOOL 3 — SERVICE HOLE', 'Ø32 mm',         'through web'),
    ]
    for lx, name, dim1, dim2 in labels:
        svg.append(f'<line x1="{lx}" y1="{stick_y_bot+8}" x2="{lx}" y2="{label_y-8}" stroke="#374151" stroke-width="0.6" opacity="0.4"/>')
        svg.append(f'<text x="{lx}" y="{label_y}" text-anchor="middle" font-size="11" fill="#1a202c" font-weight="700">{name}</text>')
        svg.append(f'<text x="{lx}" y="{label_y+15}" text-anchor="middle" font-size="10" fill="#4a5568">{dim1}</text>')
        svg.append(f'<text x="{lx}" y="{label_y+28}" text-anchor="middle" font-size="9" fill="#6b7280">{dim2}</text>')

    # SWAGE explanation card
    card_y = label_y + 70
    svg.append(f'<rect x="80" y="{card_y}" width="700" height="170" fill="white" stroke="#cbd5e0" rx="6"/>')
    svg.append(f'<text x="100" y="{card_y+25}" font-size="14" font-weight="700" fill="#1a202c">SWAGE — corrected from F37008 spec</text>')
    svg.append(f'<text x="100" y="{card_y+50}" font-size="12" fill="#374151">A localized lozenge-shape pressed into the web — NOT a continuous stripe.</text>')
    svg.append(f'<text x="100" y="{card_y+72}" font-size="12" fill="#374151">• Approximately 10 mm long along stick × 32 mm tall (covers ~36% of web)</text>')
    svg.append(f'<text x="100" y="{card_y+90}" font-size="12" fill="#374151">• Pressed inward 5 mm — reduces web from 89 to 86.6 mm at the swage</text>')
    svg.append(f'<text x="100" y="{card_y+108}" font-size="12" fill="#374151">• Applied at discrete positions: every ~55 mm near connection ends + at each panel point</text>')
    svg.append(f'<text x="100" y="{card_y+126}" font-size="12" fill="#374151">• In CSV: appears as "SWAGE,xx.x" entries with the position from stick start</text>')
    svg.append(f'<text x="100" y="{card_y+148}" font-size="12" fill="#374151">• Stiffens the web against buckling under axial load</text>')

    # WEB HOLE detail card
    svg.append(f'<rect x="800" y="{card_y}" width="500" height="170" fill="white" stroke="#16a34a" rx="6"/>')
    svg.append(f'<text x="820" y="{card_y+25}" font-size="14" font-weight="700" fill="#14532d">WEB HOLE replaces BOLT HOLE for connections</text>')
    svg.append(f'<text x="820" y="{card_y+50}" font-size="12" fill="#374151">3 holes Ø3.8 mm at 17 mm pitch on web centreline.</text>')
    # Mini diagram
    mcx = 1180; mcy = card_y + 100
    for off in [-22, 0, 22]:
        svg.append(f'<circle cx="{mcx}" cy="{mcy+off}" r="3.6" fill="url(#hole-rim)"/>')
        svg.append(f'<circle cx="{mcx}" cy="{mcy+off}" r="3" fill="url(#hole-deep)"/>')
    svg.append(f'<text x="820" y="{card_y+78}" font-size="12" fill="#374151">Each hole takes a 10g self-drilling screw.</text>')
    svg.append(f'<text x="820" y="{card_y+100}" font-size="12" fill="#374151">3 screws ≈ same shear as one M6 bolt</text>')
    svg.append(f'<text x="820" y="{card_y+122}" font-size="12" fill="#374151">— but spread across 34 mm of web</text>')
    svg.append(f'<text x="820" y="{card_y+144}" font-size="12" fill="#374151">for better load distribution.</text>')

    # Cross-section card
    svg.append(f'<rect x="1320" y="{card_y}" width="500" height="170" fill="white" stroke="#cbd5e0" rx="6"/>')
    svg.append(f'<text x="1340" y="{card_y+25}" font-size="14" font-weight="700" fill="#1a202c">SWAGED "C" cross-section</text>')
    svg.append(f'<text x="1340" y="{card_y+45}" font-size="11" fill="#4a5568">86.6 web · 41/38 flange · 12 lip · 5 swage</text>')
    cs_cx = 1700; cs_cy = card_y + 105
    cs_scale = 1.0
    cs_top = cs_cy - 41*cs_scale; cs_bot = cs_cy + 38*cs_scale
    svg.append(f'<path d="M {cs_cx} {cs_top} L {cs_cx} {cs_cy-3*cs_scale} Q {cs_cx-5*cs_scale*1.5} {cs_cy} {cs_cx} {cs_cy+3*cs_scale} L {cs_cx} {cs_bot}" fill="none" stroke="#3a3f47" stroke-width="2.5"/>')
    svg.append(f'<path d="M {cs_cx} {cs_top} L {cs_cx-41*cs_scale} {cs_top} L {cs_cx-41*cs_scale} {cs_top+12*cs_scale}" fill="none" stroke="#3a3f47" stroke-width="2.5"/>')
    svg.append(f'<path d="M {cs_cx} {cs_bot} L {cs_cx-38*cs_scale} {cs_bot} L {cs_cx-38*cs_scale} {cs_bot-12*cs_scale}" fill="none" stroke="#3a3f47" stroke-width="2.5"/>')
    svg.append(f'<text x="{cs_cx-50}" y="{cs_cy-30}" font-size="9" fill="#6b7280">41</text>')
    svg.append(f'<text x="{cs_cx-50}" y="{cs_cy+45}" font-size="9" fill="#6b7280">38</text>')
    svg.append(f'<text x="{cs_cx+8}" y="{cs_cy+3}" font-size="9" fill="#dc2626" font-weight="700">↑ 5 mm swage</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# === RUN ===
print('Photoreal v2 truss...')
truss_path = os.path.join(OUT_DIR, 'photoreal_truss_v2.svg')
open(truss_path, 'w', encoding='utf-8').write(render_truss('TN2-1'))
print(f'  Wrote {truss_path}')

print('Photoreal v2 tool reference...')
ref_path = os.path.join(OUT_DIR, 'photoreal_tools_v2.svg')
open(ref_path, 'w', encoding='utf-8').write(render_tool_reference())
print(f'  Wrote {ref_path}')

# Index
idx = ['<!DOCTYPE html><html><head><title>Photoreal v2</title>',
       '<style>',
       '*{box-sizing:border-box}',
       'body{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:24px;background:#1a202c;color:#e2e8f0}',
       'h1{margin:0 0 12px;color:white}',
       '.sub{color:#94a3b8;margin-bottom:24px}',
       '.card{background:white;color:#1a202c;border:1px solid #4a5568;border-radius:6px;margin-bottom:24px;overflow:hidden}',
       '.card-head{padding:14px 18px;background:#fafaf8;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center}',
       '.card-head h2{margin:0;font-size:16px}',
       '.card-head a{color:#2563eb;text-decoration:none;padding:5px 12px;border:1px solid #93c5fd;border-radius:3px;font-size:12px}',
       'iframe{border:0;width:100%;display:block;background:white}',
       '.h1{height:1250px}.h2{height:1150px}',
       '</style></head><body>',
       '<h1>Photoreal v2 — corrected SWAGE</h1>',
       '<p class="sub">Truss now actually renders. SWAGE is a localized lozenge press (not a stripe). WEB HOLE is 3 × Ø3.8mm at 17mm pitch.</p>',
       '<div class="card"><div class="card-head"><div><h2>1. Truss frame TN2-1 — photoreal galvanised</h2><div style="font-size:12px;color:#4a5568">Real SWAGE positions from CSV · WEB HOLE at every centreline crossing</div></div><a href="photoreal_truss_v2.svg" target="_blank">open standalone &uarr;</a></div><iframe src="photoreal_truss_v2.svg" class="h1"></iframe></div>',
       '<div class="card"><div class="card-head"><div><h2>2. Tool reference — corrected</h2><div style="font-size:12px;color:#4a5568">All tools at 4px = 1mm scale. SWAGE shown correctly as a lozenge.</div></div><a href="photoreal_tools_v2.svg" target="_blank">open standalone &uarr;</a></div><iframe src="photoreal_tools_v2.svg" class="h2"></iframe></div>',
       '</body></html>']
idx_path = os.path.join(OUT_DIR, 'PHOTOREAL_V2.html')
open(idx_path, 'w', encoding='utf-8').write('\n'.join(idx))
print(f'  Wrote {idx_path}')
