"""Visual explainer: shows the truss with each tool color-coded
PLUS annotations explaining what each tool DOES (its purpose).

Three views in one HTML page:
  1. Full truss with all tools color-coded
  2. Zoom on a typical web-meets-chord junction showing tools in action
  3. Before/after: same junction with tools missing vs tools applied
"""
import re, math, os

XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075 (1).xml'
CSV = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.csv'
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
                try:
                    pos = float(ops_raw[i+1])
                    ops.append((ops_raw[i], pos))
                except: pass
                i += 2
            out[short] = {'length':length, 'ops':ops}
    return out

def line_intersection(p1, p2, p3, p4, slack_mm=20):
    """Intersection only if it falls within both sticks' physical lengths
    (with small slack ~20mm for cut chamfers). No extrapolation into fresh air."""
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

def all_crossings(sticks):
    """Every pair of sticks whose centrelines actually intersect within both
    sticks' physical bounds (NO extrapolation into fresh air). Each intersection
    becomes a separate WEB HOLE pattern on EACH of the two sticks involved."""
    out = []
    for i in range(len(sticks)):
        for j in range(i+1, len(sticks)):
            pt = line_intersection(sticks[i]['start'], sticks[i]['end'],
                                   sticks[j]['start'], sticks[j]['end'])
            if pt: out.append({'pt':pt, 'a':sticks[i], 'b':sticks[j]})
    return out

WIDTH_MM = 89.0

# Tool colors with meaning
TOOL_COLORS = {
    'WEB_HOLE':      {'fill': '#16a34a', 'name': 'WEB HOLE',     'desc': '3 × Ø3.8mm vertical pattern at centreline crossing — sets out the truss + 3-screw connection'},
    'SWAGE':         {'fill': '#9333ea', 'name': 'SWAGE',        'desc': 'Continuous press-zone on web — adds stiffness at connection points'},
    'LIPNOTCH':      {'fill': '#fbbf24', 'name': 'LIP NOTCH',    'desc': 'Cuts the lip at angled stick-ends so it doesn\'t protrude'},
    'PARTIALFLANGE': {'fill': '#f97316', 'name': 'PARTIAL FLANGE','desc': 'Removes web\'s flange in overlap zone so web lays FLAT on chord'},
    'FLANGE':        {'fill': '#dc2626', 'name': 'FLANGE',        'desc': 'Trims chord flange flush with the angled end-cut so nothing protrudes'},
    'CHAMFER':       {'fill': '#06b6d4', 'name': 'TRUSS CHAMFER', 'desc': 'Angled end-cut so stick stays inside the chord boundary'},
}

def render_overview(sticks, ops, nodes):
    """Top-down truss view with all tools color-coded."""
    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    xmin, xmax = min(all_x)-300, max(all_x)+300
    zmin, zmax = min(all_z)-300, max(all_z)+300
    mm_w = xmax-xmin; mm_h = zmax-zmin

    PAGE_W = 1700
    PAGE_H = 950
    margin = 40
    margin_top = 120
    draw_w = PAGE_W - 2*margin
    draw_h = PAGE_H - margin_top - margin - 100
    SCALE = min(draw_w/mm_w, draw_h/mm_h)
    ox = margin + (draw_w - mm_w*SCALE)/2
    oy = margin_top + (draw_h - mm_h*SCALE)/2
    def to_px(x, z): return (ox + (x-xmin)*SCALE, oy + (zmax-z)*SCALE)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append('<defs>')
    svg.append('<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f1f5f9"/><stop offset="1" stop-color="#cbd5e0"/></linearGradient>')
    svg.append('<pattern id="cf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)"><rect width="6" height="6" fill="#dbeafe"/><line x1="0" y1="0" x2="0" y2="6" stroke="#93c5fd" stroke-width="0.6"/></pattern>')
    svg.append('<pattern id="wf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)"><rect width="6" height="6" fill="#e2e8f0"/><line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" stroke-width="0.6"/></pattern>')
    svg.append('</defs>')
    svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="url(#bg)"/>')

    # Title
    svg.append(f'<text x="40" y="44" font-size="26" font-weight="700" fill="#1a202c">Truss frame TN2-1 — every tool with its purpose</text>')
    svg.append(f'<text x="40" y="68" font-size="14" fill="#4a5568">Each tool color-coded. Hover or read legend for what each one does.</text>')

    # Member polygons
    def member_poly(stick):
        sx, sz = stick['start']; ex, ez = stick['end']
        dx, dz = ex-sx, ez-sz
        L = math.hypot(dx, dz)
        if L == 0: return ''
        nx, nz = -dz/L, dx/L
        h = WIDTH_MM/2
        pts = [(sx+nx*h, sz+nz*h), (sx-nx*h, sz-nz*h), (ex-nx*h, ez-nz*h), (ex+nx*h, ez+nz*h)]
        return ' '.join(f'{a:.1f},{b:.1f}' for a,b in (to_px(*p) for p in pts))

    # Draw all members
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(f'<polygon points="{member_poly(s)}" fill="url(#cf)" stroke="#1d4ed8" stroke-width="1.4"/>')
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(f'<polygon points="{member_poly(s)}" fill="url(#wf)" stroke="#475569" stroke-width="1.2"/>')

    # Centrelines
    for s in sticks:
        x1, y1 = to_px(*s['start']); x2, y2 = to_px(*s['end'])
        col = '#1d4ed8' if s['type']=='Plate' else '#334155'
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="0.7" stroke-dasharray="4 3" opacity="0.6"/>')

    # Tool features
    for s in sticks:
        info = ops.get(s['name'])
        if not info: continue
        sx_mm, sz_mm = s['start']; ex_mm, ez_mm = s['end']
        dx, dz = ex_mm-sx_mm, ez_mm-sz_mm
        L = math.hypot(dx, dz)
        ax_x, ax_z = dx/L, dz/L
        nx_, nz_ = -ax_z, ax_x  # perp

        for tool, pos in info['ops']:
            cx_mm = sx_mm + ax_x*pos
            cz_mm = sz_mm + ax_z*pos

            if tool == 'SWAGE':
                # Show as small purple rectangle on stick
                box_w = 8; box_h = 30
                pts = []
                for sgn_l, sgn_h in [(-1,1),(1,1),(1,-1),(-1,-1)]:
                    px = cx_mm + ax_x*sgn_l*box_w/2 + nx_*sgn_h*box_h/2
                    pz = cz_mm + ax_z*sgn_l*box_w/2 + nz_*sgn_h*box_h/2
                    pts.append(to_px(px, pz))
                pts_str = ' '.join(f'{a:.1f},{b:.1f}' for a,b in pts)
                svg.append(f'<polygon points="{pts_str}" fill="{TOOL_COLORS["SWAGE"]["fill"]}" opacity="0.85"/>')

            elif tool == 'LIP NOTCH':
                # Small yellow markers on edges
                for sgn in [-1, 1]:
                    cx_x = cx_mm + nx_*sgn*(WIDTH_MM/2 - 6)
                    cx_z = cz_mm + nz_*sgn*(WIDTH_MM/2 - 6)
                    px, pz = to_px(cx_x, cx_z)
                    svg.append(f'<circle cx="{px:.1f}" cy="{pz:.1f}" r="3" fill="{TOOL_COLORS["LIPNOTCH"]["fill"]}" stroke="#92400e" stroke-width="0.5"/>')

            elif tool in ('LEFT LEG NOTCH', 'RIGHT LEG NOTCH'):
                # Orange marker on appropriate flange
                sgn = 1 if tool == 'LEFT LEG NOTCH' else -1
                box_w = 12; box_h = 8
                cx_x = cx_mm + nx_*sgn*(WIDTH_MM/2 + 2)
                cx_z = cz_mm + nz_*sgn*(WIDTH_MM/2 + 2)
                pts = []
                for sgn_l, sgn_h in [(-1,1),(1,1),(1,-1),(-1,-1)]:
                    px = cx_x + ax_x*sgn_l*box_w/2 + nx_*sgn_h*box_h/2
                    pz = cx_z + ax_z*sgn_l*box_w/2 + nz_*sgn_h*box_h/2
                    pts.append(to_px(px, pz))
                pts_str = ' '.join(f'{a:.1f},{b:.1f}' for a,b in pts)
                col = TOOL_COLORS["PARTIALFLANGE"]["fill"] if s['type'] != 'Plate' else TOOL_COLORS["FLANGE"]["fill"]
                svg.append(f'<polygon points="{pts_str}" fill="{col}" stroke="#7c2d12" stroke-width="0.6"/>')

    # Web holes at every centreline crossing — each intersected stick gets
    # its OWN 3-hole pattern, oriented perpendicular to that stick's length.
    # Middle hole sits exactly on the stick's centreline at the intersection.
    def draw_pattern_on_stick(intersection, stick, opacity=1.0):
        cx_mm, cz_mm = intersection
        sx, sz = stick['start']; ex, ez = stick['end']
        dx, dz = ex-sx, ez-sz
        L = math.hypot(dx, dz)
        if L == 0: return
        # Perpendicular unit vector (to stick's length, in mm)
        perp_x_mm = -dz/L
        perp_z_mm = dx/L
        for off_mm, is_mid in [(-17, False), (0, True), (17, False)]:
            hx_mm = cx_mm + perp_x_mm * off_mm
            hz_mm = cz_mm + perp_z_mm * off_mm
            hx_px, hz_px = to_px(hx_mm, hz_mm)
            r = 2.5
            if is_mid:
                svg.append(f'<circle cx="{hx_px:.1f}" cy="{hz_px:.1f}" r="{r+1.5:.1f}" fill="none" stroke="#16a34a" stroke-width="1.5" opacity="{opacity*0.6:.2f}"/>')
                svg.append(f'<circle cx="{hx_px:.1f}" cy="{hz_px:.1f}" r="{r:.1f}" fill="#16a34a" stroke="#14532d" stroke-width="1.2" opacity="{opacity:.2f}"/>')
            else:
                svg.append(f'<circle cx="{hx_px:.1f}" cy="{hz_px:.1f}" r="{r:.1f}" fill="#16a34a" stroke="#14532d" stroke-width="1" opacity="{opacity:.2f}"/>')

    for n in nodes:
        # Each intersection means BOTH sticks get their own pattern,
        # oriented perpendicular to their respective lengths.
        draw_pattern_on_stick(n['pt'], n['a'])
        draw_pattern_on_stick(n['pt'], n['b'])

    # TRUSS CHAMFER markers — small cyan tags at the angled stick-ends
    for s in sticks:
        info = ops.get(s['name'])
        if not info: continue
        # Look for angled ends — basically every web end and angled chord end
        # For simplicity: mark BOTH ends of every web with cyan dots
        if s['type'] != 'Plate':
            for pos_mm in [0, info['length']]:
                sx_mm, sz_mm = s['start']
                dx, dz = s['end'][0]-sx_mm, s['end'][1]-sz_mm
                L = math.hypot(dx, dz)
                ax_x, ax_z = dx/L, dz/L
                cx_mm = sx_mm + ax_x*pos_mm
                cz_mm = sz_mm + ax_z*pos_mm
                cx_px, cz_px = to_px(cx_mm, cz_mm)
                svg.append(f'<rect x="{cx_px-4:.1f}" y="{cz_px-4:.1f}" width="8" height="8" fill="{TOOL_COLORS["CHAMFER"]["fill"]}" stroke="#0e7490" stroke-width="0.6" opacity="0.8" transform="rotate(45 {cx_px:.1f} {cz_px:.1f})"/>')

    # Member labels
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px, py = to_px(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py+4:.1f}" font-size="11" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="white" stroke-width="3.5" paint-order="stroke" opacity="0.9">{s["name"]}</text>')

    # Legend along the bottom
    legend_y = PAGE_H - 80
    svg.append(f'<rect x="40" y="{legend_y-10}" width="{PAGE_W-80}" height="80" fill="white" stroke="#cbd5e0" rx="4"/>')
    svg.append(f'<text x="55" y="{legend_y+10}" font-size="13" font-weight="700" fill="#1a202c">Tool legend — what each one DOES:</text>')
    items = [
        ('CHAMFER', 'angled cut so stick stays inside chord boundary'),
        ('FLANGE/PARTIAL FLANGE', 'flange removed so web lays FLAT on chord'),
        ('LIP NOTCH', 'lip cut so it doesn\'t poke up'),
        ('SWAGE', 'continuous press = stiffness at connection'),
        ('WEB HOLE (middle highlighted)', '3 × Ø3.8mm vertical = sets out truss + connection'),
    ]
    cols = [(60, '#06b6d4'), (340, '#f97316'), (660, '#fbbf24'), (910, '#9333ea'), (1140, '#16a34a')]
    for (x, col), (label, desc) in zip(cols, items):
        svg.append(f'<rect x="{x}" y="{legend_y+24}" width="14" height="14" fill="{col}" stroke="#1a202c" stroke-width="0.5"/>')
        svg.append(f'<text x="{x+22}" y="{legend_y+35}" font-size="11" font-weight="700" fill="#1a202c">{label}</text>')
        svg.append(f'<text x="{x+22}" y="{legend_y+50}" font-size="10" fill="#4a5568">{desc[:40]}</text>')

    svg.append('</svg>')
    return '\n'.join(svg)


def render_junction_explainer():
    """Detailed view of one junction showing how tools work together."""
    W, H = 1700, 1100
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append('<defs>')
    svg.append('<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f8fafc"/><stop offset="1" stop-color="#e2e8f0"/></linearGradient>')
    svg.append('<linearGradient id="steel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#dde6ed"/><stop offset="1" stop-color="#8a9ba9"/></linearGradient>')
    svg.append('<linearGradient id="chord" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#cfd9e2"/><stop offset="1" stop-color="#7a8c9b"/></linearGradient>')
    svg.append('</defs>')
    svg.append(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')

    svg.append(f'<text x="30" y="40" font-size="24" font-weight="700" fill="#1a202c">How the tools work together at a junction</text>')
    svg.append(f'<text x="30" y="64" font-size="14" fill="#4a5568">Vertical web W7 meeting horizontal bottom chord B1. Three views: WITHOUT tools / WITH tools / FINAL ASSEMBLED.</text>')

    # Three panels
    panels = [
        {'x': 30, 'title': '1. WITHOUT tools — won\'t fit', 'mode': 'before'},
        {'x': 580, 'title': '2. WITH all tools applied', 'mode': 'tools'},
        {'x': 1130, 'title': '3. ASSEMBLED — flat web-on-web', 'mode': 'after'},
    ]
    PW = 540; PH = 920
    PY = 100

    SC = 4.5  # 4.5 px per mm

    for p in panels:
        svg.append(f'<rect x="{p["x"]}" y="{PY}" width="{PW}" height="{PH}" fill="white" stroke="#cbd5e0" stroke-width="1" rx="4"/>')
        svg.append(f'<text x="{p["x"]+15}" y="{PY+25}" font-size="14" font-weight="700" fill="#1a202c">{p["title"]}</text>')

        cx = p['x'] + PW/2
        cy = PY + PH/2 + 30

        # Chord (horizontal, at the bottom of the layout)
        chord_y = cy + 60
        chord_w_px = WIDTH_MM * SC
        chord_len = 350  # px
        chord_left = cx - chord_len/2
        chord_right = cx + chord_len/2
        # Chord plate (laid flat, channel facing up = 89mm wide visible)
        svg.append(f'<rect x="{chord_left}" y="{chord_y - chord_w_px/2}" width="{chord_len}" height="{chord_w_px}" fill="url(#chord)" stroke="#1d4ed8" stroke-width="1.4"/>')
        # Chord lip strips (top and bottom edges)
        lip_h = 12 * SC
        svg.append(f'<rect x="{chord_left}" y="{chord_y - chord_w_px/2}" width="{chord_len}" height="{lip_h}" fill="#a4b6c4" stroke="#1d4ed8" stroke-width="0.8" opacity="0.95"/>')
        svg.append(f'<rect x="{chord_left}" y="{chord_y + chord_w_px/2 - lip_h}" width="{chord_len}" height="{lip_h}" fill="#a4b6c4" stroke="#1d4ed8" stroke-width="0.8" opacity="0.95"/>')
        # Chord centreline
        svg.append(f'<line x1="{chord_left-15}" y1="{chord_y}" x2="{chord_right+15}" y2="{chord_y}" stroke="#1d4ed8" stroke-width="1" stroke-dasharray="5 3" opacity="0.7"/>')
        svg.append(f'<text x="{chord_left+10}" y="{chord_y - chord_w_px/2 + 18}" font-size="11" fill="#1d4ed8" font-weight="600">B1 chord</text>')

        # Web (vertical, coming in from above)
        web_x = cx
        web_w_px = WIDTH_MM * SC
        web_top = PY + 130
        if p['mode'] == 'before':
            # Web doesn't fit — lifted off chord because flanges are still on
            web_bot = chord_y - chord_w_px/2 - 30  # gap of 30px
        else:
            web_bot = chord_y + chord_w_px/2 - 5  # web sits flat extending across chord

        # Web rectangle
        if p['mode'] == 'before':
            # Square cut at end (no chamfer)
            svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_top}" width="{web_w_px}" height="{web_bot-web_top}" fill="url(#steel)" stroke="#475569" stroke-width="1.4"/>')
            svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_top}" width="{web_w_px}" height="{lip_h}" fill="#94a3b8" stroke="#475569" stroke-width="0.8"/>')
            svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_bot-lip_h}" width="{web_w_px}" height="{lip_h}" fill="#94a3b8" stroke="#475569" stroke-width="0.8"/>')

            # Highlight the CLASH zone
            svg.append(f'<rect x="{web_x-web_w_px/2-5}" y="{web_bot}" width="{web_w_px+10}" height="30" fill="#fee2e2" stroke="#dc2626" stroke-width="2" stroke-dasharray="4 2"/>')
            svg.append(f'<text x="{cx}" y="{web_bot+18}" text-anchor="middle" font-size="11" font-weight="700" fill="#7f1d1d">FLANGES + LIPS CLASH</text>')
            svg.append(f'<text x="{cx}" y="{web_bot+30}" text-anchor="middle" font-size="9" fill="#7f1d1d">web cannot lay flat</text>')

            svg.append(f'<text x="{web_x+web_w_px/2 + 10}" y="{web_top + 30}" font-size="11" fill="#475569" font-weight="600">W7 web</text>')
            svg.append(f'<text x="{web_x+web_w_px/2 + 10}" y="{web_top + 45}" font-size="10" fill="#dc2626">no tools applied</text>')

        elif p['mode'] == 'tools':
            # Web with all tools applied
            svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_top}" width="{web_w_px}" height="{web_bot-web_top}" fill="url(#steel)" stroke="#475569" stroke-width="1.4"/>')

            # PARTIAL FLANGE cuts (orange) at bottom of web
            partial_h = 76 * SC * 0.3  # span ~76mm but compress for visibility
            partial_h = 65
            svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_bot - partial_h}" width="{web_w_px}" height="{partial_h}" fill="rgba(249,115,22,0.35)" stroke="#c2410c" stroke-width="1.5" stroke-dasharray="3 2"/>')
            svg.append(f'<text x="{web_x}" y="{web_bot - partial_h - 6}" text-anchor="middle" font-size="10" font-weight="700" fill="#c2410c">PARTIAL FLANGE (left + right)</text>')
            svg.append(f'<text x="{web_x}" y="{web_bot + partial_h*0.5 - 5}" text-anchor="middle" font-size="9" fill="#7c2d12">flange removed</text>')
            svg.append(f'<text x="{web_x}" y="{web_bot + partial_h*0.5 + 8}" text-anchor="middle" font-size="9" fill="#7c2d12">in overlap zone</text>')

            # LIP NOTCH (yellow) at very bottom corners
            lip_notch = 12 * SC
            svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_bot - lip_h}" width="{lip_notch}" height="{lip_h}" fill="#fbbf24" stroke="#92400e" stroke-width="1"/>')
            svg.append(f'<rect x="{web_x + web_w_px/2 - lip_notch}" y="{web_bot - lip_h}" width="{lip_notch}" height="{lip_h}" fill="#fbbf24" stroke="#92400e" stroke-width="1"/>')

            # SWAGE (purple) at junction zone
            svg.append(f'<rect x="{web_x - 5*SC}" y="{web_bot - 80}" width="{10*SC}" height="{30*SC}" fill="#9333ea" opacity="0.8" stroke="#581c87"/>')
            svg.append(f'<text x="{web_x + 30}" y="{web_bot - 80}" font-size="10" font-weight="700" fill="#581c87">SWAGE — stiffness</text>')

            # WEB HOLES (green) - 3 vertical holes centred on intersection
            int_y = chord_y  # intersection point is on chord centreline
            for off in [-17*SC, 0, 17*SC]:
                r = 3
                if off == 0:
                    svg.append(f'<circle cx="{web_x}" cy="{int_y + off}" r="{r+2}" fill="none" stroke="#16a34a" stroke-width="1.5"/>')
                    svg.append(f'<circle cx="{web_x}" cy="{int_y + off}" r="{r}" fill="#16a34a" stroke="#14532d" stroke-width="1.2"/>')
                else:
                    svg.append(f'<circle cx="{web_x}" cy="{int_y + off}" r="{r}" fill="#16a34a" stroke="#14532d" stroke-width="1"/>')
            svg.append(f'<text x="{web_x + 50}" y="{int_y - 4}" font-size="10" font-weight="700" fill="#14532d">WEB HOLE</text>')
            svg.append(f'<text x="{web_x + 50}" y="{int_y + 8}" font-size="9" fill="#14532d">3×Ø3.8mm @17pitch</text>')

            # CHAMFER markers at end
            svg.append(f'<polygon points="{web_x-web_w_px/2},{web_bot} {web_x-web_w_px/2+8},{web_bot} {web_x-web_w_px/2},{web_bot-8}" fill="#06b6d4" stroke="#0e7490" stroke-width="1"/>')
            svg.append(f'<polygon points="{web_x+web_w_px/2},{web_bot} {web_x+web_w_px/2-8},{web_bot} {web_x+web_w_px/2},{web_bot-8}" fill="#06b6d4" stroke="#0e7490" stroke-width="1"/>')
            svg.append(f'<text x="{web_x - web_w_px/2 - 8}" y="{web_bot - 12}" text-anchor="end" font-size="10" font-weight="700" fill="#0e7490">CHAMFER</text>')

        else:  # after / assembled
            # Web sits FLAT on chord — same color as chord, sits on top
            # Show as a slightly darker polygon to indicate it's stacked
            svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_top}" width="{web_w_px}" height="{web_bot-web_top}" fill="url(#steel)" stroke="#475569" stroke-width="1.4" opacity="0.9"/>')

            # Show the green-cap screws driven through (3 vertical) at the intersection
            for off in [-17*SC, 0, 17*SC]:
                # Drilled hole through both layers - dark
                svg.append(f'<circle cx="{web_x}" cy="{chord_y + off}" r="3.5" fill="#1a202c" stroke="black" stroke-width="0.6"/>')
                # Green screw cap on top
                svg.append(f'<circle cx="{web_x}" cy="{chord_y + off}" r="6" fill="#65a30d" stroke="#365314" stroke-width="1.2"/>')
                svg.append(f'<line x1="{web_x-3}" y1="{chord_y + off}" x2="{web_x+3}" y2="{chord_y + off}" stroke="#1a2e0a" stroke-width="0.7"/>')
                svg.append(f'<line x1="{web_x}" y1="{chord_y + off - 3}" x2="{web_x}" y2="{chord_y + off + 3}" stroke="#1a2e0a" stroke-width="0.7"/>')
            svg.append(f'<text x="{web_x + 35}" y="{chord_y - 30}" font-size="11" font-weight="700" fill="#14532d">3 screws driven through</text>')
            svg.append(f'<text x="{web_x + 35}" y="{chord_y - 16}" font-size="10" fill="#14532d">middle hole = registration</text>')
            svg.append(f'<text x="{web_x + 35}" y="{chord_y - 2}" font-size="10" fill="#14532d">top + bottom = lock angle</text>')

            # Caption
            svg.append(f'<rect x="{p["x"]+20}" y="{PY+PH-110}" width="{PW-40}" height="80" fill="#dcfce7" stroke="#16a34a" rx="3"/>')
            svg.append(f'<text x="{p["x"]+30}" y="{PY+PH-90}" font-size="12" font-weight="700" fill="#14532d">Result: web sits FLAT on chord</text>')
            svg.append(f'<text x="{p["x"]+30}" y="{PY+PH-72}" font-size="11" fill="#14532d">• Flanges removed in overlap → flat contact</text>')
            svg.append(f'<text x="{p["x"]+30}" y="{PY+PH-58}" font-size="11" fill="#14532d">• Middle screw aligns by design (auto-set-out)</text>')
            svg.append(f'<text x="{p["x"]+30}" y="{PY+PH-44}" font-size="11" fill="#14532d">• 3 screws lock position + angle</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# ============= BUILD ALL =============
sticks = parse_frame('TN2-1')
csv_ops = parse_csv_ops('TN2-1')
# No clustering - every pairwise centreline intersection is its own WEB HOLE
nodes = all_crossings(sticks)

print('Rendering overview...')
overview = render_overview(sticks, csv_ops, nodes)
open(os.path.join(OUT_DIR, 'tools_overview.svg'), 'w', encoding='utf-8').write(overview)

print('Rendering junction explainer...')
junction = render_junction_explainer()
open(os.path.join(OUT_DIR, 'tools_junction.svg'), 'w', encoding='utf-8').write(junction)

# Index
idx = '''<!DOCTYPE html><html><head><title>Tool explainer</title>
<style>
*{box-sizing:border-box}
body{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:24px;background:#1a202c;color:#e2e8f0}
h1{margin:0 0 12px;color:white}
.sub{color:#94a3b8;margin-bottom:24px}
.card{background:white;color:#1a202c;border:1px solid #4a5568;border-radius:6px;margin-bottom:24px;overflow:hidden}
.card-head{padding:14px 18px;background:#fafaf8;border-bottom:1px solid #e2e8f0}
.card-head h2{margin:0;font-size:16px}
.card-head .desc{font-size:12px;color:#4a5568;margin-top:4px}
iframe{border:0;width:100%;display:block;background:white}
.h-mid{height:980px}
.h-tall{height:1130px}
</style></head><body>
<h1>Truss tools — what each one DOES</h1>
<p class="sub">All 6 tools color-coded on a real truss + a junction breakdown showing how they work together.</p>
<div class="card">
  <div class="card-head"><h2>1. Overview — every tool color-coded on TN2-1</h2><div class="desc">All members + tools positioned per the actual CSV. Hover/read legend at bottom for each tool's purpose.</div></div>
  <iframe src="tools_overview.svg" class="h-mid"></iframe>
</div>
<div class="card">
  <div class="card-head"><h2>2. Junction breakdown — WITHOUT / WITH / ASSEMBLED</h2><div class="desc">Shows why each tool exists by comparing a junction with no tools applied (clash) vs with all tools (lays flat) vs final assembled (3 screws through both members).</div></div>
  <iframe src="tools_junction.svg" class="h-tall"></iframe>
</div>
</body></html>'''
open(os.path.join(OUT_DIR, 'TOOLS_EXPLAINED.html'), 'w', encoding='utf-8').write(idx)
print('Wrote TOOLS_EXPLAINED.html')
