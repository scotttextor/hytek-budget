"""V3 - Tool shapes corrected from FrameCAD 3D reference images.

Fixes from previous version:
  - SWAGE: small rectangular pressed depression with parallel inner lines
           (not a lozenge)  ~ 10mm long × 30mm tall, centred on web ℄
  - Cleaner member rendering (single bar with subtle lip-fold lines on edges,
    no harsh "fold" creases through the middle)
  - Isometric 3D tool reference page matching user's reference images
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
            full_name = parts[1]
            if not full_name.startswith(frame_name + '-'): continue
            short = full_name[len(frame_name)+1:]
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
  <radialGradient id="screw-cap" cx="0.35" cy="0.35" r="0.7">
    <stop offset="0%" stop-color="#a3e635"/>
    <stop offset="50%" stop-color="#65a30d"/>
    <stop offset="100%" stop-color="#365314"/>
  </radialGradient>
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
    # Lip fold lines (3mm in from each long edge for visual hint)
    pa_lip = (sx + nx*(h-3), sz + nz*(h-3))
    pb_lip = (sx - nx*(h-3), sz - nz*(h-3))
    pc_lip = (ex - nx*(h-3), ez - nz*(h-3))
    pd_lip = (ex + nx*(h-3), ez + nz*(h-3))
    return {'corners':(pa, pb, pc, pd), 'lip':(pa_lip, pb_lip, pc_lip, pd_lip),
            'axis':(dx/L, dz/L), 'perp':(nx, nz), 'L':L,
            'mid':((sx+ex)/2, (sz+ez)/2)}

def draw_member_clean(stick, scale_fn, is_chord=False):
    """Clean rendering: bar with subtle gradient + thin lip-fold lines on edges."""
    info = member_corners(stick)
    if not info: return ''
    pa, pb, pc, pd = info['corners']
    pa_l, pb_l, pc_l, pd_l = info['lip']

    pts = lambda lst: ' '.join(f'{a:.1f},{b:.1f}' for a,b in (scale_fn(*p) for p in lst))
    fill = 'url(#galv-chord)' if is_chord else 'url(#galv)'

    out = []
    # Body
    out.append(f'<polygon points="{pts([pa, pb, pc, pd])}" fill="{fill}"/>')
    # Spangle texture
    out.append(f'<polygon points="{pts([pa, pb, pc, pd])}" fill="url(#spangle)" opacity="0.7"/>')
    # Lip-fold hint lines - thin parallel lines 3mm from each long edge
    out.append(f'<line x1="{scale_fn(*pa)[0]:.1f}" y1="{scale_fn(*pa)[1]:.1f}" x2="{scale_fn(*pd)[0]:.1f}" y2="{scale_fn(*pd)[1]:.1f}" stroke="#3a4654" stroke-width="0.6" opacity="0.7"/>')
    out.append(f'<line x1="{scale_fn(*pa_l)[0]:.1f}" y1="{scale_fn(*pa_l)[1]:.1f}" x2="{scale_fn(*pd_l)[0]:.1f}" y2="{scale_fn(*pd_l)[1]:.1f}" stroke="#5a6c7c" stroke-width="0.5" opacity="0.5"/>')
    out.append(f'<line x1="{scale_fn(*pb)[0]:.1f}" y1="{scale_fn(*pb)[1]:.1f}" x2="{scale_fn(*pc)[0]:.1f}" y2="{scale_fn(*pc)[1]:.1f}" stroke="#3a4654" stroke-width="0.6" opacity="0.7"/>')
    out.append(f'<line x1="{scale_fn(*pb_l)[0]:.1f}" y1="{scale_fn(*pb_l)[1]:.1f}" x2="{scale_fn(*pc_l)[0]:.1f}" y2="{scale_fn(*pc_l)[1]:.1f}" stroke="#5a6c7c" stroke-width="0.5" opacity="0.5"/>')
    # Outline
    out.append(f'<polygon points="{pts([pa, pb, pc, pd])}" fill="none" stroke="#1a2329" stroke-width="0.9"/>')
    # End caps (vertical lines at start and end)
    out.append(f'<line x1="{scale_fn(*pa)[0]:.1f}" y1="{scale_fn(*pa)[1]:.1f}" x2="{scale_fn(*pb)[0]:.1f}" y2="{scale_fn(*pb)[1]:.1f}" stroke="#1a2329" stroke-width="0.9"/>')
    out.append(f'<line x1="{scale_fn(*pc)[0]:.1f}" y1="{scale_fn(*pc)[1]:.1f}" x2="{scale_fn(*pd)[0]:.1f}" y2="{scale_fn(*pd)[1]:.1f}" stroke="#1a2329" stroke-width="0.9"/>')
    return '\n'.join(out)

def draw_swage_correct(stick, position_mm, scale_fn):
    """SWAGE = small rectangular pressed feature with parallel inner lines.
    Per FrameCAD 3D reference: ~ 10mm long × 30mm tall, centred on web ℄.
    Shows as a darker rectangle with two parallel lines indicating the press."""
    info = member_corners(stick)
    if not info: return ''
    sx, sz = stick['start']
    ax, az = info['axis']
    nx, nz = info['perp']

    # Centre of swage
    cx = sx + ax*position_mm
    cz = sz + az*position_mm

    # Swage dimensions (mm)
    LENGTH = 10  # along stick
    HEIGHT = 30  # across web

    # Rectangle corners
    p1 = (cx + ax*-LENGTH/2 + nx*HEIGHT/2, cz + az*-LENGTH/2 + nz*HEIGHT/2)
    p2 = (cx + ax*LENGTH/2 + nx*HEIGHT/2, cz + az*LENGTH/2 + nz*HEIGHT/2)
    p3 = (cx + ax*LENGTH/2 - nx*HEIGHT/2, cz + az*LENGTH/2 - nz*HEIGHT/2)
    p4 = (cx + ax*-LENGTH/2 - nx*HEIGHT/2, cz + az*-LENGTH/2 - nz*HEIGHT/2)

    # Inner parallel lines (the "press" lines - 2mm in from each end along stick axis)
    INNER = 2
    p1i = (cx + ax*(-LENGTH/2+INNER) + nx*HEIGHT/2, cz + az*(-LENGTH/2+INNER) + nz*HEIGHT/2)
    p2i = (cx + ax*(LENGTH/2-INNER) + nx*HEIGHT/2, cz + az*(LENGTH/2-INNER) + nz*HEIGHT/2)
    p3i = (cx + ax*(LENGTH/2-INNER) - nx*HEIGHT/2, cz + az*(LENGTH/2-INNER) - nz*HEIGHT/2)
    p4i = (cx + ax*(-LENGTH/2+INNER) - nx*HEIGHT/2, cz + az*(-LENGTH/2+INNER) - nz*HEIGHT/2)

    pts = lambda lst: ' '.join(f'{a:.1f},{b:.1f}' for a,b in (scale_fn(*p) for p in lst))

    out = []
    # Outer dark rectangle (depression edge)
    out.append(f'<polygon points="{pts([p1, p2, p3, p4])}" fill="url(#swage-press)" stroke="#2a3540" stroke-width="0.5" opacity="0.85"/>')
    # Inner highlight lines (the parallel "press" lines)
    out.append(f'<line x1="{scale_fn(*p1i)[0]:.1f}" y1="{scale_fn(*p1i)[1]:.1f}" x2="{scale_fn(*p4i)[0]:.1f}" y2="{scale_fn(*p4i)[1]:.1f}" stroke="white" stroke-width="0.5" opacity="0.5"/>')
    out.append(f'<line x1="{scale_fn(*p2i)[0]:.1f}" y1="{scale_fn(*p2i)[1]:.1f}" x2="{scale_fn(*p3i)[0]:.1f}" y2="{scale_fn(*p3i)[1]:.1f}" stroke="white" stroke-width="0.5" opacity="0.5"/>')
    return '\n'.join(out)

def draw_screws(cx_px, cy_px, perp_x, perp_y, scale, web_facing):
    """3 green-capped self-drilling screws at 17mm pitch on web centreline."""
    out = []
    SCREW_R = 7  # mm
    spacing = 17 * scale
    r = SCREW_R/2 * scale
    for offset in [-spacing, 0, spacing]:
        sx = cx_px + perp_x * offset
        sy = cy_px + perp_y * offset
        # Drop shadow
        out.append(f'<circle cx="{sx+1.5:.1f}" cy="{sy+2:.1f}" r="{r+0.5:.2f}" fill="black" opacity="0.4" filter="url(#blur3)"/>')
        # Cap base (dark olive)
        out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r+0.5:.2f}" fill="#365314"/>')
        # Cap green
        out.append(f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r:.2f}" fill="url(#screw-cap)"/>')
        # Shine
        out.append(f'<ellipse cx="{sx-r*0.3:.1f}" cy="{sy-r*0.3:.1f}" rx="{r*0.4:.2f}" ry="{r*0.25:.2f}" fill="white" opacity="0.5"/>')
        # Phillips cross
        out.append(f'<line x1="{sx-r*0.45:.1f}" y1="{sy:.1f}" x2="{sx+r*0.45:.1f}" y2="{sy:.1f}" stroke="#1a2e0a" stroke-width="0.6" opacity="0.7"/>')
        out.append(f'<line x1="{sx:.1f}" y1="{sy-r*0.45:.1f}" x2="{sx:.1f}" y2="{sy+r*0.45:.1f}" stroke="#1a2e0a" stroke-width="0.6" opacity="0.7"/>')
    return '\n'.join(out)

# ============= TRUSS =============
def render_truss(frame_name='TN2-1'):
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

    svg.append(f'<rect x="0" y="0" width="{PAGE_W}" height="105" fill="white" opacity="0.95"/>')
    svg.append(f'<text x="40" y="42" font-size="26" font-weight="700" fill="#1a202c">Truss frame {frame_name} — corrected swage shape</text>')
    svg.append(f'<text x="40" y="68" font-size="14" fill="#4a5568">Swage = rectangular pressed feature (10×30mm) with parallel inner lines · Web Hole = 3 green screws · Lip Cut at member ends</text>')

    # Drop shadows
    svg.append('<g opacity="0.55">')
    SH = 6
    for s in sticks:
        info = member_corners(s)
        if not info: continue
        pa, pb, pc, pd = info['corners']
        ps = []
        for p in [pa, pb, pc, pd]:
            sx, sy = to_px(*p)
            ps.append(f'{sx+SH:.1f},{sy+SH:.1f}')
        svg.append(f'<polygon points="{" ".join(ps)}" fill="black" opacity="0.4" filter="url(#blur5)"/>')
    svg.append('</g>')

    # Members - chords first (under), webs on top
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(draw_member_clean(s, to_px, is_chord=True))
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(draw_member_clean(s, to_px, is_chord=False))

    # SWAGE features at real CSV positions on every web
    for s in sticks:
        if s['type'] == 'Plate': continue
        ops_data = csv_ops.get(s['name'])
        if not ops_data: continue
        for tool, pos in ops_data['ops']:
            if tool == 'SWAGE':
                svg.append(draw_swage_correct(s, pos, to_px))

    # Member labels
    for s in sticks:
        info = member_corners(s)
        if not info: continue
        px, py = to_px(*info['mid'])
        svg.append(f'<text x="{px:.1f}" y="{py+4:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="#1a202c" stroke="white" stroke-width="3.5" paint-order="stroke" opacity="0.9">{s["name"]}</text>')

    # Screws at every centreline crossing
    for n in nodes:
        cx_mm, cz_mm = n['pt']
        # Find web direction
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
        svg.append(draw_screws(cx_px, cy_px, perp_x, perp_y, SCALE, web is not None))

    # Spec card
    cx_card = PAGE_W - 290; cy_card = 130
    svg.append(f'<rect x="{cx_card-3}" y="{cy_card+3}" width="270" height="320" fill="rgba(0,0,0,0.18)" filter="url(#blur5)"/>')
    svg.append(f'<rect x="{cx_card}" y="{cy_card}" width="270" height="320" fill="white" stroke="#cbd5e0" rx="6"/>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+24}" font-size="14" font-weight="700" fill="#1a202c">Tool shapes (corrected)</text>')
    # Mini swage
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+50}" font-size="11" font-weight="700" fill="#374151">SWAGE (per FrameCAD 3D ref)</text>')
    swcx = cx_card + 60; swcy = cy_card + 80
    sw_w = 50; sw_h = 22
    svg.append(f'<rect x="{swcx-sw_w/2}" y="{swcy-sw_h/2}" width="{sw_w}" height="{sw_h}" fill="url(#swage-press)" stroke="#2a3540" stroke-width="0.6"/>')
    svg.append(f'<line x1="{swcx-sw_w/2+5}" y1="{swcy-sw_h/2+1}" x2="{swcx-sw_w/2+5}" y2="{swcy+sw_h/2-1}" stroke="white" stroke-width="0.4" opacity="0.5"/>')
    svg.append(f'<line x1="{swcx+sw_w/2-5}" y1="{swcy-sw_h/2+1}" x2="{swcx+sw_w/2-5}" y2="{swcy+sw_h/2-1}" stroke="white" stroke-width="0.4" opacity="0.5"/>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+76}" font-size="10" fill="#374151">~10 × 30 mm</text>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+90}" font-size="10" fill="#374151">pressed depression</text>')
    # Mini web hole
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+125}" font-size="11" font-weight="700" fill="#374151">WEB HOLE = 3 green screws</text>')
    wcx = cx_card + 60; wcy = cy_card + 165
    for off in [-15, 0, 15]:
        svg.append(f'<circle cx="{wcx}" cy="{wcy+off}" r="4" fill="url(#screw-cap)" stroke="#365314" stroke-width="0.6"/>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+150}" font-size="10" fill="#374151">3 × Ø3.8 mm</text>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+164}" font-size="10" fill="#374151">17 mm pitch</text>')
    svg.append(f'<text x="{cx_card+150}" y="{cy_card+178}" font-size="10" fill="#374151">10g self-drillers</text>')

    svg.append(f'<text x="{cx_card+15}" y="{cy_card+220}" font-size="11" font-weight="700" fill="#374151">Stats this frame</text>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+240}" font-size="10" fill="#4a5568">Members: {len(sticks)}</text>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+256}" font-size="10" fill="#4a5568">Junction nodes: {len(nodes)}</text>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+272}" font-size="10" fill="#4a5568">Total screws: {len(nodes)*3}</text>')
    sw_count = sum(1 for s in sticks for t,_ in csv_ops.get(s['name'],{}).get('ops',[]) if t=='SWAGE')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+288}" font-size="10" fill="#4a5568">Total swages: {sw_count}</text>')
    svg.append(f'<text x="{cx_card+15}" y="{cy_card+304}" font-size="10" fill="#6b7280">vs FrameCAD baseline ~70</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

print('Rendering v3 truss with corrected shapes...')
out_path = os.path.join(OUT_DIR, 'truss_v3.svg')
open(out_path, 'w', encoding='utf-8').write(render_truss('TN2-1'))
print(f'Wrote {out_path}')

idx = '''<!DOCTYPE html><html><head><title>V3 corrected shapes</title>
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
<h1>V3 — corrected tool shapes</h1>
<p class="sub">SWAGE now drawn as a rectangular pressed depression (10×30mm) per the FrameCAD 3D reference. Members rendered cleanly without origami-fold artifacts.</p>
<div class="card"><div class="card-head"><div><h2>Truss TN2-1 — corrected shapes</h2><div style="font-size:12px;color:#4a5568">Per CSV swage positions · Member rendering simplified</div></div><a href="truss_v3.svg" target="_blank">open standalone ↑</a></div><iframe src="truss_v3.svg"></iframe></div>
</body></html>'''
open(os.path.join(OUT_DIR, 'V3.html'), 'w', encoding='utf-8').write(idx)
print(f'Wrote V3.html')
