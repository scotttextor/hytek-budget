"""Photorealistic FrameCAD truss + tool detail.

Galvanised-steel finish, real drop shadows, lit-from-above lighting,
holes drawn as drilled-through (with inner shadow), swages as proper
embossed depressions, lip-notch cuts with raw-cut edge highlights.

Tooling geometry from F37008 W089 F41-38 spec.
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
                out.append({'pt':pt, 'a':sticks[i]['name'], 'b':sticks[j]['name']})
    return out

def cluster(crossings, tol):
    if tol <= 0:
        return [{'pt':c['pt']} for c in crossings]
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
        out.append({'pt':(cx,cy), 'count':len(grp)})
    return out

WIDTH_MM = 89.0

# ============= REAL-LOOKING SVG DEFINITIONS =============

DEFS = '''<defs>
  <!-- Galvanised steel surface (cool silver with subtle horizontal sheen) -->
  <linearGradient id="galv" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#e8edf2"/>
    <stop offset="20%" stop-color="#d8dee5"/>
    <stop offset="50%" stop-color="#c5ccd4"/>
    <stop offset="80%" stop-color="#a8b0b8"/>
    <stop offset="100%" stop-color="#8d959e"/>
  </linearGradient>
  <!-- Galv chord (slightly bluer to differentiate) -->
  <linearGradient id="galv-chord" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#e2e8f0"/>
    <stop offset="50%" stop-color="#c2cbd6"/>
    <stop offset="100%" stop-color="#8a93a0"/>
  </linearGradient>
  <!-- Bright spangle highlight -->
  <radialGradient id="spangle" cx="0.3" cy="0.3" r="0.7">
    <stop offset="0%" stop-color="white" stop-opacity="0.7"/>
    <stop offset="40%" stop-color="white" stop-opacity="0.15"/>
    <stop offset="100%" stop-color="white" stop-opacity="0"/>
  </radialGradient>
  <!-- Lip strip (slightly brighter — top edge catches light) -->
  <linearGradient id="lip-top" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#f4f6f8"/>
    <stop offset="60%" stop-color="#d6dde4"/>
    <stop offset="100%" stop-color="#a8b0b8"/>
  </linearGradient>
  <linearGradient id="lip-bot" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#a8b0b8"/>
    <stop offset="40%" stop-color="#d6dde4"/>
    <stop offset="100%" stop-color="#f4f6f8"/>
  </linearGradient>
  <!-- Drilled hole — looks like a hole punched through, dark interior -->
  <radialGradient id="hole" cx="0.4" cy="0.35" r="0.6">
    <stop offset="0%" stop-color="#1a1a1a"/>
    <stop offset="60%" stop-color="#404040"/>
    <stop offset="100%" stop-color="#5a5a5a"/>
  </radialGradient>
  <!-- Hole bevel (bright catch on near edge) -->
  <radialGradient id="hole-bevel" cx="0.5" cy="0.5" r="0.5">
    <stop offset="80%" stop-color="white" stop-opacity="0"/>
    <stop offset="95%" stop-color="white" stop-opacity="0.5"/>
    <stop offset="100%" stop-color="white" stop-opacity="0"/>
  </radialGradient>
  <!-- Swage depression - darker inside -->
  <linearGradient id="swage" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#9aa0a8"/>
    <stop offset="50%" stop-color="#5a6068"/>
    <stop offset="100%" stop-color="#9aa0a8"/>
  </linearGradient>
  <!-- Cut edge (bright — exposed steel from cutting) -->
  <linearGradient id="cut-edge" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#fef9e7"/>
    <stop offset="100%" stop-color="#d6dde4"/>
  </linearGradient>
  <!-- Drop shadow filter -->
  <filter id="ds" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
    <feOffset dx="3" dy="5"/>
    <feComponentTransfer><feFuncA type="linear" slope="0.35"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <filter id="ds-light" x="-10%" y="-10%" width="120%" height="120%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="1.5"/>
    <feOffset dx="1.5" dy="2"/>
    <feComponentTransfer><feFuncA type="linear" slope="0.25"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <!-- Soft inset for swage -->
  <filter id="emboss" x="-10%" y="-10%" width="120%" height="120%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="0.5"/>
    <feOffset dx="0" dy="1"/>
    <feComponentTransfer><feFuncA type="linear" slope="0.4"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <!-- Spangle pattern (zinc galv crystals) -->
  <pattern id="spangle-pat" patternUnits="userSpaceOnUse" width="40" height="40">
    <rect width="40" height="40" fill="none"/>
    <circle cx="8" cy="12" r="6" fill="white" opacity="0.04"/>
    <circle cx="28" cy="22" r="8" fill="white" opacity="0.03"/>
    <circle cx="15" cy="32" r="5" fill="white" opacity="0.05"/>
    <circle cx="34" cy="6" r="4" fill="white" opacity="0.04"/>
  </pattern>
</defs>'''

def draw_realistic_member(stick, scale_fn, is_chord=False, scale_factor=1.0):
    """Draw a member as galvanised steel with lip strips, lighting, and shadow."""
    sx_,sz_ = stick['start']; ex_,ez_ = stick['end']
    dx, dz = ex_-sx_, ez_-sz_
    L = math.hypot(dx, dz)
    if L == 0: return ''
    nx, nz = -dz/L, dx/L
    h = WIDTH_MM/2
    # Outer corners
    p_tl = (sx_+nx*h, sz_+nz*h)
    p_bl = (sx_-nx*h, sz_-nz*h)
    p_tr = (ex_-nx*h, ez_-nz*h)
    p_br = (ex_+nx*h, ez_+nz*h)
    # Lip strip width on each side (~12mm shown as edge band)
    lip_w = 12
    p_tl_in = (sx_+nx*(h-lip_w), sz_+nz*(h-lip_w))
    p_tr_in = (ex_-nx*(h-lip_w), ez_-nz*(h-lip_w))
    p_bl_in = (sx_-nx*(h-lip_w), sz_-nz*(h-lip_w))
    p_br_in = (ex_+nx*(h-lip_w), ez_+nz*(h-lip_w))

    pts = lambda lst: ' '.join(f'{a:.1f},{b:.1f}' for a,b in (scale_fn(*p) for p in lst))

    fill = 'url(#galv-chord)' if is_chord else 'url(#galv)'

    out = []
    # Main body
    out.append(f'<polygon points="{pts([p_tl, p_bl, p_br, p_tr])}" fill="{fill}" filter="url(#ds-light)"/>')
    # Spangle overlay (subtle texture)
    out.append(f'<polygon points="{pts([p_tl, p_bl, p_br, p_tr])}" fill="url(#spangle-pat)" opacity="0.6"/>')
    # Top lip strip (catches light)
    out.append(f'<polygon points="{pts([p_tl, p_tr, p_tr_in, p_tl_in])}" fill="url(#lip-top)" stroke="#5a626c" stroke-width="0.6"/>')
    # Bottom lip strip
    out.append(f'<polygon points="{pts([p_bl_in, p_br_in, p_br, p_bl])}" fill="url(#lip-bot)" stroke="#5a626c" stroke-width="0.6"/>')
    # Member outline
    out.append(f'<polygon points="{pts([p_tl, p_bl, p_br, p_tr])}" fill="none" stroke="#444" stroke-width="0.9"/>')
    # Highlight along top edge (light from above)
    out.append(f'<polyline points="{pts([p_tl, p_tr])}" fill="none" stroke="white" stroke-width="0.9" opacity="0.7"/>')
    # Shadow line along bottom edge
    out.append(f'<polyline points="{pts([p_bl, p_br])}" fill="none" stroke="#3a3f47" stroke-width="0.9" opacity="0.6"/>')
    return '\n'.join(out)

def draw_realistic_swage(stick, scale_fn):
    """Continuous embossed swage along the centreline of a web."""
    sx_,sz_ = stick['start']; ex_,ez_ = stick['end']
    p1 = scale_fn(sx_, sz_); p2 = scale_fn(ex_, ez_)
    dx = p2[0]-p1[0]; dy = p2[1]-p1[1]
    L = math.hypot(dx, dy)
    if L == 0: return ''
    angle = math.degrees(math.atan2(dy, dx))
    # Swage band: ~5mm tall, drawn as a gradient lens stretching the length of the stick
    SWAGE_H = 8  # px
    cx = (p1[0]+p2[0])/2; cy = (p1[1]+p2[1])/2
    return (
        f'<g transform="translate({cx:.1f},{cy:.1f}) rotate({angle:.1f})">'
        f'<rect x="{-L/2+8}" y="{-SWAGE_H/2}" width="{L-16}" height="{SWAGE_H}" fill="url(#swage)" rx="{SWAGE_H/2}"/>'
        f'<line x1="{-L/2+8}" y1="{-SWAGE_H/2+1}" x2="{L/2-8}" y2="{-SWAGE_H/2+1}" stroke="white" stroke-width="0.5" opacity="0.6"/>'
        f'<line x1="{-L/2+8}" y1="{SWAGE_H/2-1}" x2="{L/2-8}" y2="{SWAGE_H/2-1}" stroke="black" stroke-width="0.5" opacity="0.4"/>'
        f'</g>'
    )

def draw_realistic_web_hole(cx, cy, scale, perp_x, perp_y, ax_x, ax_y):
    """3 x Ø3.8mm holes - drilled through, looking real."""
    out = []
    radius = 1.9 * scale
    spacing = 17 * scale
    # Boundary outline (light dashed - shows the connection zone but very subtle)
    rect_w = 14*scale; rect_h = 46*scale
    ang = math.degrees(math.atan2(perp_y, perp_x)) - 90
    out.append(f'<rect x="{cx - rect_w/2:.1f}" y="{cy - rect_h/2:.1f}" width="{rect_w:.1f}" height="{rect_h:.1f}" '
               f'transform="rotate({ang:.1f} {cx:.1f} {cy:.1f})" '
               f'fill="rgba(0,0,0,0.04)" stroke="rgba(0,0,0,0.2)" stroke-width="0.5" stroke-dasharray="2 2" rx="2"/>')
    for offset in [-spacing, 0, spacing]:
        hx = cx + perp_x * offset
        hy = cy + perp_y * offset
        # Outer bevel
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius+0.7:.2f}" fill="url(#hole-bevel)"/>')
        # Hole interior (dark)
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius:.2f}" fill="url(#hole)"/>')
        # Tiny rim shadow (top-left of hole)
        out.append(f'<path d="M {hx-radius*0.7:.1f} {hy-radius*0.4:.1f} A {radius:.2f} {radius:.2f} 0 0 1 {hx-radius*0.4:.1f} {hy-radius*0.7:.1f}" '
                   f'fill="none" stroke="#1a1a1a" stroke-width="0.4" opacity="0.7"/>')
        # Bright catch light on bottom-right
        out.append(f'<circle cx="{hx + radius*0.3:.1f}" cy="{hy + radius*0.3:.1f}" r="{radius*0.3:.2f}" fill="white" opacity="0.5"/>')
    return '\n'.join(out)

# ============= TRUSS RENDER =============

def render_truss(frame_name='TN2-1', tol=180):
    sticks = parse_frame(frame_name)
    crossings = all_crossings(sticks)
    clustered = cluster(crossings, tol)

    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    xmin, xmax = min(all_x)-300, max(all_x)+300
    zmin, zmax = min(all_z)-300, max(all_z)+300
    mm_w = xmax-xmin; mm_h = zmax-zmin

    PAGE_W = 1900
    PAGE_H = 1150
    margin_top = 130
    margin_other = 40
    draw_w = PAGE_W - 2*margin_other
    draw_h = PAGE_H - margin_top - margin_other - 70
    SCALE = min(draw_w/mm_w, draw_h/mm_h)
    ox = margin_other + (draw_w - mm_w*SCALE)/2
    oy = margin_top + (draw_h - mm_h*SCALE)/2

    def to_px(x, z): return (ox + (x-xmin)*SCALE, oy + (zmax-z)*SCALE)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append(DEFS)
    # Background — soft workshop floor gradient
    svg.append(f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f8f9fa"/><stop offset="1" stop-color="#dde1e6"/></linearGradient></defs>')
    svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="url(#bg)"/>')

    # Title
    svg.append(f'<text x="40" y="44" font-size="26" font-weight="700" fill="#1a202c">Truss frame {frame_name} — photoreal galvanised steel</text>')
    svg.append(f'<text x="40" y="70" font-size="14" fill="#4a5568">Profile F37008 W089 F41-38 (89×41 lipped C, 0.75mm AZ150). 3 × Ø3.8mm WEB HOLEs at every centreline crossing.</text>')
    svg.append(f'<text x="40" y="94" font-size="13" fill="#374151">{len(sticks)} members &middot; {len(clustered)} junction nodes &middot; {len(clustered)*3} Ø3.8mm holes total &middot; SWAGE on every web</text>')

    # Soft floor shadow group around all members
    svg.append('<g filter="url(#ds)">')

    # Chord plates first (they sit underneath)
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(draw_realistic_member(s, to_px, is_chord=True))

    # Webs on top
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(draw_realistic_member(s, to_px, is_chord=False))

    svg.append('</g>')

    # SWAGES — only on webs
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(draw_realistic_swage(s, to_px))

    # Member labels (subtle — only show, don't dominate)
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px,py = to_px(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py+4:.1f}" font-size="12" font-weight="700" text-anchor="middle" fill="#1a202c" opacity="0.7" stroke="white" stroke-width="3" paint-order="stroke">{s["name"]}</text>')

    # WEB HOLES at every crossing
    for cl in clustered:
        cx_mm, cy_mm = cl['pt']
        cx_px, cy_px = to_px(cx_mm, cy_mm)
        # Find perp direction from web member
        web_stick = None
        for s in sticks:
            if s['type'] != 'Plate':
                sx, sz = s['start']; ex, ez = s['end']
                d = math.hypot(ex-sx, ez-sz)
                if d == 0: continue
                t = ((cx_mm-sx)*(ex-sx) + (cy_mm-sz)*(ez-sz)) / (d*d)
                if -0.1 <= t <= 1.1:
                    px = sx + t*(ex-sx); pz = sz + t*(ez-sz)
                    dist = math.hypot(cx_mm-px, cy_mm-pz)
                    if dist < 50:
                        web_stick = s; break
        if web_stick:
            sx, sz = web_stick['start']; ex, ez = web_stick['end']
            dx, dy = ex-sx, ez-sz
            L = math.hypot(dx, dy)
            ax_x = dx/L; ax_y = -dy/L
            perp_x = -ax_y; perp_y = ax_x
        else:
            ax_x, ax_y = 1, 0
            perp_x, perp_y = 0, 1

        svg.append(draw_realistic_web_hole(cx_px, cy_px, SCALE, perp_x, perp_y, ax_x, ax_y))

    # Annotation - profile spec card
    card_x = PAGE_W - 290; card_y = 130
    svg.append(f'<g filter="url(#ds-light)"><rect x="{card_x}" y="{card_y}" width="260" height="200" fill="white" stroke="#cbd5e0" rx="6"/></g>')
    svg.append(f'<text x="{card_x+15}" y="{card_y+22}" font-size="13" font-weight="700" fill="#1a202c">F37008 W089 F41-38</text>')
    svg.append(f'<text x="{card_x+15}" y="{card_y+38}" font-size="10" fill="#4a5568">89 × 41 lipped C section</text>')
    svg.append(f'<line x1="{card_x+15}" y1="{card_y+50}" x2="{card_x+245}" y2="{card_y+50}" stroke="#e2e8f0"/>')
    # Mini hole diagram
    svg.append(f'<text x="{card_x+15}" y="{card_y+68}" font-size="11" fill="#374151" font-weight="600">WEB HOLE pattern at every node:</text>')
    cx_mini = card_x + 50; cy_mini = card_y + 110
    for off in [-17*0.6, 0, 17*0.6]:
        svg.append(f'<circle cx="{cx_mini}" cy="{cy_mini+off}" r="{1.9*0.6:.2f}" fill="url(#hole)"/>')
        svg.append(f'<circle cx="{cx_mini}" cy="{cy_mini+off}" r="{1.9*0.6+0.3:.2f}" fill="url(#hole-bevel)"/>')
    svg.append(f'<text x="{card_x+90}" y="{card_y+95}" font-size="10" fill="#374151">3 × Ø3.8mm</text>')
    svg.append(f'<text x="{card_x+90}" y="{card_y+110}" font-size="10" fill="#374151">17 mm pitch</text>')
    svg.append(f'<text x="{card_x+90}" y="{card_y+125}" font-size="10" fill="#374151">on web ℄</text>')
    svg.append(f'<text x="{card_x+15}" y="{card_y+155}" font-size="10" fill="#6b7280">Each hole takes a 10g</text>')
    svg.append(f'<text x="{card_x+15}" y="{card_y+170}" font-size="10" fill="#6b7280">self-drilling screw → 3×</text>')
    svg.append(f'<text x="{card_x+15}" y="{card_y+185}" font-size="10" fill="#6b7280">capacity of one M6 bolt</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# ============= TOOL REFERENCE PAGE =============

def render_tool_reference():
    """Lifelike reference of all tools applied to one stick."""
    W, H = 1900, 1150
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append(DEFS)
    svg.append(f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f8f9fa"/><stop offset="1" stop-color="#dde1e6"/></linearGradient></defs>')
    svg.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

    svg.append(f'<text x="30" y="40" font-size="26" font-weight="700" fill="#1a202c">Real FrameCAD tools — every operation drawn at scale</text>')
    svg.append(f'<text x="30" y="64" font-size="14" fill="#4a5568">Profile F37008 W089 F41-38, all 9 tool stations applied. Galvanised steel finish, lit from above.</text>')

    # Single big stick showing all tools - 5 px per mm scale
    MM = 5
    stick_y_top = 130
    stick_y_bot = stick_y_top + 89*MM
    cy = (stick_y_top + stick_y_bot) / 2
    stick_x0 = 80
    stick_x1 = W - 80
    stick_len_px = stick_x1 - stick_x0
    LIP = 12 * MM

    # ===== Build the stick body with realistic shading =====
    svg.append('<g filter="url(#ds)">')
    # Main body
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_len_px}" height="{89*MM}" fill="url(#galv)"/>')
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_len_px}" height="{89*MM}" fill="url(#spangle-pat)" opacity="0.7"/>')
    # Top lip
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_len_px}" height="{LIP}" fill="url(#lip-top)" stroke="#5a626c" stroke-width="0.7"/>')
    # Bottom lip
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_bot-LIP}" width="{stick_len_px}" height="{LIP}" fill="url(#lip-bot)" stroke="#5a626c" stroke-width="0.7"/>')
    # Main outline
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_len_px}" height="{89*MM}" fill="none" stroke="#444" stroke-width="1"/>')
    # Top edge highlight
    svg.append(f'<line x1="{stick_x0}" y1="{stick_y_top+0.5}" x2="{stick_x1}" y2="{stick_y_top+0.5}" stroke="white" stroke-width="1.2" opacity="0.7"/>')
    # Bottom edge shadow
    svg.append(f'<line x1="{stick_x0}" y1="{stick_y_bot-0.5}" x2="{stick_x1}" y2="{stick_y_bot-0.5}" stroke="#2c2f36" stroke-width="1.2" opacity="0.5"/>')
    svg.append('</g>')

    # ===== SWAGE (continuous along the stick) =====
    svg.append(f'<g filter="url(#emboss)">')
    swage_h = 7 * MM
    svg.append(f'<rect x="{stick_x0+5}" y="{cy-swage_h/2}" width="{stick_len_px-10}" height="{swage_h}" fill="url(#swage)" rx="{swage_h/2}"/>')
    svg.append(f'<line x1="{stick_x0+5}" y1="{cy-swage_h/2+1}" x2="{stick_x1-5}" y2="{cy-swage_h/2+1}" stroke="white" stroke-width="0.6" opacity="0.5"/>')
    svg.append(f'<line x1="{stick_x0+5}" y1="{cy+swage_h/2-1}" x2="{stick_x1-5}" y2="{cy+swage_h/2-1}" stroke="black" stroke-width="0.4" opacity="0.5"/>')
    svg.append('</g>')

    def x_at(mm): return stick_x0 + mm*MM

    # 1. WEB HOLE at 80mm
    wh_x = x_at(80)
    spacing = 17 * MM
    rad = 1.9 * MM
    for off in [-spacing, 0, spacing]:
        # outer bevel
        svg.append(f'<circle cx="{wh_x}" cy="{cy+off}" r="{rad+0.8:.2f}" fill="url(#hole-bevel)"/>')
        # hole
        svg.append(f'<circle cx="{wh_x}" cy="{cy+off}" r="{rad:.2f}" fill="url(#hole)"/>')
        # rim shadow
        svg.append(f'<circle cx="{wh_x}" cy="{cy+off}" r="{rad:.2f}" fill="none" stroke="#000" stroke-width="0.4" opacity="0.6"/>')
        # catch light
        svg.append(f'<circle cx="{wh_x+rad*0.35:.1f}" cy="{cy+off+rad*0.35:.1f}" r="{rad*0.25:.2f}" fill="white" opacity="0.55"/>')

    # 2. WEB BOLT HOLE at 220mm — Ø13.5mm
    wbh_x = x_at(220)
    bolt_r = 6.75 * MM
    svg.append(f'<circle cx="{wbh_x}" cy="{cy}" r="{bolt_r+1:.2f}" fill="url(#hole-bevel)"/>')
    svg.append(f'<circle cx="{wbh_x}" cy="{cy}" r="{bolt_r:.2f}" fill="url(#hole)"/>')
    svg.append(f'<circle cx="{wbh_x}" cy="{cy}" r="{bolt_r:.2f}" fill="none" stroke="#000" stroke-width="0.5" opacity="0.6"/>')
    svg.append(f'<circle cx="{wbh_x+bolt_r*0.35:.1f}" cy="{cy+bolt_r*0.35:.1f}" r="{bolt_r*0.25:.2f}" fill="white" opacity="0.55"/>')

    # 3. LIP CUT at 360mm — angled cut, shows raw cut edge
    lc_x = x_at(360)
    lc_w = 12 * MM
    # Top — triangular cutout (shows the missing material as background through hole)
    svg.append(f'<polygon points="{lc_x-lc_w/2},{stick_y_top} {lc_x+lc_w/2},{stick_y_top} {lc_x},{stick_y_top+LIP}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1.2"/>')
    # Highlight cut edges
    svg.append(f'<line x1="{lc_x-lc_w/2}" y1="{stick_y_top}" x2="{lc_x},{stick_y_top+LIP}" stroke="white" stroke-width="0.6" opacity="0.7"/>'.replace(',',' '))
    svg.append(f'<line x1="{lc_x},{stick_y_top+LIP}" x2="{lc_x+lc_w/2}" y2="{stick_y_top}" stroke="#444" stroke-width="0.5"/>'.replace(',',' '))
    # Bottom mirror
    svg.append(f'<polygon points="{lc_x-lc_w/2},{stick_y_bot} {lc_x+lc_w/2},{stick_y_bot} {lc_x},{stick_y_bot-LIP}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1.2"/>')

    # 4. WEB NOTCH at 480mm — rectangular bite into web edge
    wn_x = x_at(480)
    wn_w = 14*MM; wn_h = 9*MM
    svg.append(f'<rect x="{wn_x-wn_w/2}" y="{stick_y_top+LIP}" width="{wn_w}" height="{wn_h}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1.2"/>')
    # Cut-edge highlight
    svg.append(f'<line x1="{wn_x-wn_w/2}" y1="{stick_y_top+LIP+wn_h}" x2="{wn_x+wn_w/2}" y2="{stick_y_top+LIP+wn_h}" stroke="white" stroke-width="0.6" opacity="0.7"/>')

    # 5. FLANGE CUT at 600mm — 3mm vertical strip removed
    fc_x = x_at(600)
    fc_w = 3 * MM
    svg.append(f'<rect x="{fc_x-fc_w/2}" y="{stick_y_top}" width="{fc_w}" height="{89*MM}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1"/>')
    svg.append(f'<line x1="{fc_x-fc_w/2}" y1="{stick_y_top}" x2="{fc_x-fc_w/2}" y2="{stick_y_bot}" stroke="white" stroke-width="0.5" opacity="0.6"/>')

    # 6. SERVICE HOLE at 770mm — Ø32mm
    sh_x = x_at(770)
    sh_r = 16*MM
    svg.append(f'<circle cx="{sh_x}" cy="{cy}" r="{sh_r+1.5:.2f}" fill="url(#hole-bevel)"/>')
    svg.append(f'<circle cx="{sh_x}" cy="{cy}" r="{sh_r:.2f}" fill="url(#hole)"/>')
    svg.append(f'<circle cx="{sh_x}" cy="{cy}" r="{sh_r:.2f}" fill="none" stroke="#000" stroke-width="0.7" opacity="0.6"/>')
    svg.append(f'<ellipse cx="{sh_x-sh_r*0.4}" cy="{cy-sh_r*0.5}" rx="{sh_r*0.45}" ry="{sh_r*0.18}" fill="white" opacity="0.3" transform="rotate(-30 {sh_x-sh_r*0.4} {cy-sh_r*0.5})"/>')

    # 7. MULTI TOOL at 980mm — 4 dimples + 4 flange holes
    mt_x = x_at(980)
    for dx in [-30, -10, 10, 30]:
        # Dimple (Ø5.1mm) — embossed bump (light dome)
        cdx = mt_x + dx*MM
        cdy = cy - 7*MM
        svg.append(f'<circle cx="{cdx}" cy="{cdy}" r="{2.55*MM:.2f}" fill="url(#galv)" stroke="#5a626c" stroke-width="0.8"/>')
        svg.append(f'<circle cx="{cdx-1}" cy="{cdy-1.5}" r="{2.55*MM*0.5:.2f}" fill="white" opacity="0.6"/>')
        # Flange holes (top and bottom lips)
        for ly in [stick_y_top + LIP/2, stick_y_bot - LIP/2]:
            svg.append(f'<circle cx="{cdx}" cy="{ly}" r="{1.9*MM+0.5:.2f}" fill="url(#hole-bevel)"/>')
            svg.append(f'<circle cx="{cdx}" cy="{ly}" r="{1.9*MM:.2f}" fill="url(#hole)"/>')

    # 8. FLAT DIMPLE at 1170mm — single Ø5.1
    fd_x = x_at(1170)
    svg.append(f'<circle cx="{fd_x}" cy="{cy}" r="{2.55*MM:.2f}" fill="url(#galv)" stroke="#5a626c" stroke-width="0.8" filter="url(#emboss)"/>')
    svg.append(f'<circle cx="{fd_x-1}" cy="{cy-1.5}" r="{2.55*MM*0.5:.2f}" fill="white" opacity="0.6"/>')

    # 9. CHAMFER CUT at 1290mm
    cc_x = x_at(1290)
    cc_size = 9*MM
    svg.append(f'<polygon points="{cc_x-cc_size},{stick_y_top} {cc_x},{stick_y_top} {cc_x},{stick_y_top+cc_size}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1.2"/>')
    svg.append(f'<polygon points="{cc_x-cc_size},{stick_y_bot} {cc_x},{stick_y_bot} {cc_x},{stick_y_bot-cc_size}" fill="url(#bg)" stroke="#1a1a1a" stroke-width="1.2"/>')

    # ----- LABELS BELOW THE STICK -----
    label_y = stick_y_bot + 50
    labels = [
        (wh_x, 'TOOL 1', 'WEB HOLE', '3 × Ø3.8mm', '#16a34a'),
        (wbh_x, 'TOOL 1', 'WEB BOLT HOLE', 'Ø13.5mm', '#7c3aed'),
        (lc_x, 'TOOL 2', 'LIP CUT', 'V-cut into lip', '#dc2626'),
        (wn_x, 'TOOL 2', 'WEB NOTCH', 'rectangular', '#dc2626'),
        (fc_x, 'TOOL 3', 'FLANGE CUT', '3mm wide', '#dc2626'),
        (sh_x, 'TOOL 3', 'SERVICE HOLE', 'Ø32mm', '#0891b2'),
        (mt_x, 'TOOL 5', 'MULTI TOOL', '4 dimples + 4 holes', '#d97706'),
        (fd_x, 'TOOL 5', 'FLAT DIMPLE', 'Ø5.1mm', '#d97706'),
        (cc_x, 'TOOL 4', 'CHAMFER', 'corner cut', '#dc2626'),
    ]
    for lx, station, name, dim, col in labels:
        svg.append(f'<line x1="{lx}" y1="{stick_y_bot+10}" x2="{lx}" y2="{label_y-10}" stroke="{col}" stroke-width="0.8" opacity="0.4"/>')
        svg.append(f'<text x="{lx}" y="{label_y}" text-anchor="middle" font-size="10" fill="{col}" font-weight="700">{station}</text>')
        svg.append(f'<text x="{lx}" y="{label_y+14}" text-anchor="middle" font-size="11" fill="#1a202c" font-weight="700">{name}</text>')
        svg.append(f'<text x="{lx}" y="{label_y+28}" text-anchor="middle" font-size="9" fill="#6b7280">{dim}</text>')

    # SWAGE label below stick (overall annotation)
    svg.append(f'<text x="{stick_x0+200}" y="{stick_y_top-20}" font-size="11" fill="#5b21b6" font-weight="600">SWAGE → continuous centre crimp along whole stick</text>')
    svg.append(f'<line x1="{stick_x0+200}" y1="{stick_y_top-15}" x2="{stick_x0+260}" y2="{cy-swage_h/2}" stroke="#5b21b6" stroke-width="0.8" opacity="0.5"/>')

    # Dimensions (89mm height)
    svg.append(f'<line x1="{stick_x0-30}" y1="{stick_y_top}" x2="{stick_x0-30}" y2="{stick_y_bot}" stroke="#374151" stroke-width="1"/>')
    svg.append(f'<line x1="{stick_x0-35}" y1="{stick_y_top}" x2="{stick_x0-25}" y2="{stick_y_top}" stroke="#374151" stroke-width="1"/>')
    svg.append(f'<line x1="{stick_x0-35}" y1="{stick_y_bot}" x2="{stick_x0-25}" y2="{stick_y_bot}" stroke="#374151" stroke-width="1"/>')
    svg.append(f'<text x="{stick_x0-40}" y="{cy+5}" text-anchor="end" font-size="12" fill="#374151" font-weight="600">89 mm</text>')

    # Profile cross-section card (top-right)
    cs_x = W - 320; cs_y = 100
    svg.append(f'<g filter="url(#ds-light)"><rect x="{cs_x}" y="{cs_y}" width="290" height="180" fill="white" stroke="#cbd5e0" rx="6"/></g>')
    svg.append(f'<text x="{cs_x+15}" y="{cs_y+22}" font-size="13" font-weight="700" fill="#1a202c">SWAGED "C" cross-section</text>')
    svg.append(f'<text x="{cs_x+15}" y="{cs_y+38}" font-size="10" fill="#4a5568">86.6 web · 41/38 flange · 12 lip · 5 swage</text>')
    # Mini cross-section drawing
    cs_cx = cs_x + 145; cs_cy = cs_y + 110
    cs_scale = 1.4
    # Web (vertical line)
    cs_w_top = cs_cy - 41*cs_scale; cs_w_bot = cs_cy + 38*cs_scale
    svg.append(f'<path d="M {cs_cx} {cs_w_top} L {cs_cx} {cs_cy-3*cs_scale} Q {cs_cx-5*cs_scale} {cs_cy} {cs_cx} {cs_cy+3*cs_scale} L {cs_cx} {cs_w_bot}" '
               f'fill="none" stroke="#5a626c" stroke-width="2"/>')
    # Top flange + lip
    svg.append(f'<path d="M {cs_cx} {cs_w_top} L {cs_cx-41*cs_scale} {cs_w_top} L {cs_cx-41*cs_scale} {cs_w_top+12*cs_scale}" fill="none" stroke="#5a626c" stroke-width="2"/>')
    # Bottom flange + lip
    svg.append(f'<path d="M {cs_cx} {cs_w_bot} L {cs_cx-38*cs_scale} {cs_w_bot} L {cs_cx-38*cs_scale} {cs_w_bot-12*cs_scale}" fill="none" stroke="#5a626c" stroke-width="2"/>')
    # Annotations
    svg.append(f'<text x="{cs_cx-50}" y="{cs_cy-30}" font-size="9" fill="#6b7280">41</text>')
    svg.append(f'<text x="{cs_cx-50}" y="{cs_cy+45}" font-size="9" fill="#6b7280">38</text>')
    svg.append(f'<text x="{cs_cx+5}" y="{cs_cy-3}" font-size="9" fill="#6b7280">↓ swage 5mm</text>')

    # Footer
    svg.append(f'<text x="30" y="{H-15}" font-size="11" fill="#6b7280">All tool dimensions from F37008 W089 F41-38 (FrameCAD profile drawing rev 0, 29.11.18). Galvanised AZ150 finish.</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# === RUN ===
print('Photoreal truss...')
truss_path = os.path.join(OUT_DIR, 'photoreal_truss.svg')
open(truss_path, 'w', encoding='utf-8').write(render_truss('TN2-1'))
print(f'  Wrote {truss_path}')

print('Photoreal tool reference...')
ref_path = os.path.join(OUT_DIR, 'photoreal_tools.svg')
open(ref_path, 'w', encoding='utf-8').write(render_tool_reference())
print(f'  Wrote {ref_path}')

# Index
idx = ['<!DOCTYPE html><html><head><title>Photoreal FrameCAD</title>',
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
       '.tall{height:1200px}',
       '</style></head><body>',
       '<h1>Photorealistic FrameCAD truss + tools</h1>',
       '<p class="sub">Galvanised steel finish, lit from above, drilled-through holes with proper depth, embossed swage, raw-edge cuts. Same data as before.</p>',
       '<div class="card"><div class="card-head"><div><h2>1. Truss frame TN2-1</h2><div style="font-size:12px;color:#4a5568">Photoreal galvanised steel · WEB HOLE pattern at every centreline crossing</div></div><a href="photoreal_truss.svg" target="_blank">open standalone &uarr;</a></div><iframe src="photoreal_truss.svg" class="tall"></iframe></div>',
       '<div class="card"><div class="card-head"><div><h2>2. Tool reference — all 9 stations on one stick</h2><div style="font-size:12px;color:#4a5568">5px = 1mm. Real dimensions from F37008 spec.</div></div><a href="photoreal_tools.svg" target="_blank">open standalone &uarr;</a></div><iframe src="photoreal_tools.svg" class="tall"></iframe></div>',
       '</body></html>']
idx_path = os.path.join(OUT_DIR, 'PHOTOREAL.html')
open(idx_path, 'w', encoding='utf-8').write('\n'.join(idx))
print(f'  Wrote {idx_path}')
