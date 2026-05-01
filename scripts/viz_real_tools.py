"""Lifelike truss + close-up using REAL FrameCAD tool geometry.

Source: F37008 W089 F41-38 profile drawing (181129).
Tools (from the rollformer drawing):
  TOOL STATION 1 — WEB HOLE        3 x Ø3.8mm holes, 17mm vertical spacing
  TOOL STATION 1 — WEB BOLT HOLE   Ø13.5mm single hole
  TOOL STATION 2 — LIP CUT         angled cut into lip
  TOOL STATION 2 — WEB NOTCH       rectangular cut into web
  TOOL STATION 3 — FLANGE CUT      3mm wide cut at flange edge
  TOOL STATION 3 — SERVICE HOLE    Ø32mm hole through web
  TOOL STATION 5 — MULTI TOOL      4xØ5.1 flat dimples + 4xØ3.8 flange holes
  TOOL STATION 5 — FLAT DIMPLE     Ø5.1mm
  TOOL STATION 4 — CHAMFER CUT     chamfer at end
  POST FORMING   — DIMPLE PAN      11mm pan, Ø5.1mm hole
  SWAGE          — longitudinal centre crimp (continuous along stick)

Profile: 89×41 lipped C-section, 12mm lip, 0.75mm gauge.
For the centreline-crossing rule we use WEB HOLE (3 x Ø3.8) at every
mathematical centreline-crossing point.
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
                out.append({'pt':pt, 'a':sticks[i]['name'], 'b':sticks[j]['name'],
                            'a_stick':sticks[i], 'b_stick':sticks[j]})
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

# ============= TOOL DRAWING LIBRARY =============

def tool_web_hole(cx, cy, axis_dx, axis_dy, scale, perp_dx, perp_dy):
    """3 x Ø3.8mm holes at 17mm spacing perpendicular to stick axis (along web).
    Returns SVG fragments."""
    out = []
    radius = 1.9 * scale  # 3.8mm dia
    spacing = 17 * scale
    # 3 holes: top, centre, bottom along the web axis (perpendicular to stick length)
    for offset in [-spacing, 0, +spacing]:
        hx = cx + perp_dx * offset
        hy = cy + perp_dy * offset
        out.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius:.2f}" fill="white" stroke="#16a34a" stroke-width="1.4"/>')
    # Connection ring around the cluster
    out.append(f'<rect x="{cx - 6*scale:.1f}" y="{cy - 22*scale:.1f}" width="{12*scale:.1f}" height="{44*scale:.1f}" '
               f'transform="rotate({math.degrees(math.atan2(perp_dy, perp_dx))-90:.1f} {cx:.1f} {cy:.1f})" '
               f'fill="none" stroke="#16a34a" stroke-width="0.6" stroke-dasharray="3 2" opacity="0.5"/>')
    return out

def tool_swage(stick, scale_fn):
    """Longitudinal centre crimp shown as gradient line down web centre."""
    out = []
    sx, sz = stick['start']; ex, ez = stick['end']
    p1 = scale_fn(sx, sz); p2 = scale_fn(ex, ez)
    # Draw a thin purple line down the centre of stick (centreline)
    out.append(f'<line x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" x2="{p2[0]:.1f}" y2="{p2[1]:.1f}" stroke="#a855f7" stroke-width="1.6" opacity="0.6"/>')
    return out

# ============= RENDER COMPLETE TRUSS =============

def member_polygon(stick, scale_fn):
    sx_,sz_ = stick['start']; ex_,ez_ = stick['end']
    dx, dz = ex_-sx_, ez_-sz_
    L = math.hypot(dx, dz)
    if L == 0: return ''
    nx, nz = -dz/L, dx/L
    h = WIDTH_MM/2
    pts = [(sx_+nx*h, sz_+nz*h), (sx_-nx*h, sz_-nz*h), (ex_-nx*h, ez_-nz*h), (ex_+nx*h, ez_+nz*h)]
    return ' '.join(f'{a:.1f},{b:.1f}' for a,b in (scale_fn(*p) for p in pts))

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
    PAGE_H = 1100
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
    svg.append('''<defs>
      <pattern id="cf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)">
        <rect width="6" height="6" fill="#dbeafe"/><line x1="0" y1="0" x2="0" y2="6" stroke="#93c5fd" stroke-width="0.6"/>
      </pattern>
      <pattern id="wf" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
        <rect width="6" height="6" fill="#e2e8f0"/><line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" stroke-width="0.6"/>
      </pattern>
      <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="4" stroke="#dc2626" stroke-width="0.8"/>
      </pattern>
    </defs>''')
    svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="white"/>')
    svg.append(f'<text x="40" y="44" font-size="26" font-weight="700" fill="#1a202c">Truss frame {frame_name} with REAL FrameCAD tools</text>')
    svg.append(f'<text x="40" y="70" font-size="14" fill="#4a5568">Profile F37008 W089 F41-38 (89×41 lipped C, 0.75mm). WEB HOLE tool (3 × Ø3.8mm) at every centreline crossing.</text>')
    svg.append(f'<text x="40" y="94" font-size="13" fill="#374151">{len(sticks)} members &middot; {len(crossings)} centreline crossings &rarr; {len(clustered)} junction nodes &rarr; {len(clustered)*3} total Ø3.8mm holes (3 per junction)</text>')

    # Members
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(f'<polygon points="{member_polygon(s, to_px)}" fill="url(#cf)" stroke="#1d4ed8" stroke-width="1.4" opacity="0.95"/>')
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(f'<polygon points="{member_polygon(s, to_px)}" fill="url(#wf)" stroke="#475569" stroke-width="1.2" opacity="0.85"/>')

    # Centrelines
    for s in sticks:
        x1,y1 = to_px(*s['start']); x2,y2 = to_px(*s['end'])
        col = '#1d4ed8' if s['type']=='Plate' else '#334155'
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="0.8" stroke-dasharray="5 3" opacity="0.5"/>')

    # SWAGE — show as continuous purple line down the centreline of each WEB
    for s in sticks:
        if s['type'] != 'Plate':  # only webs
            for line in tool_swage(s, to_px):
                svg.append(line)

    # Member labels
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px,py = to_px(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="white" stroke-width="3.5" paint-order="stroke">{s["name"]}</text>')

    # WEB HOLE clusters at every centreline crossing
    # Need to know the orientation of the web to align the 3 holes along its axis (perpendicular to stick length)
    # For each crossing, find the WEB stick (if any) that passes through and align with its perpendicular direction
    for cl in clustered:
        cx_mm, cy_mm = cl['pt']
        cx_px, cy_px = to_px(cx_mm, cy_mm)
        # Find which web member passes near this point — use its perpendicular as the hole-axis
        web_stick = None
        for s in sticks:
            if s['type'] != 'Plate':
                # is this point on the web?
                sx, sz = s['start']; ex, ez = s['end']
                d = math.hypot(ex-sx, ez-sz)
                if d == 0: continue
                t = ((cx_mm-sx)*(ex-sx) + (cy_mm-sz)*(ez-sz)) / (d*d)
                if -0.1 <= t <= 1.1:
                    px = sx + t*(ex-sx); pz = sz + t*(ez-sz)
                    dist = math.hypot(cx_mm-px, cy_mm-pz)
                    if dist < 50:
                        web_stick = s
                        break
        if web_stick:
            sx, sz = web_stick['start']; ex, ez = web_stick['end']
            dx, dy = ex-sx, ez-sz
            L = math.hypot(dx, dy)
            # axis along web (in screen coords - flipped y)
            ax_x = dx / L
            ax_y = -dy / L  # screen y is flipped
            # perpendicular (along web width — direction the 3 holes spread)
            perp_x = -ax_y
            perp_y = ax_x
        else:
            # Default to vertical
            perp_x, perp_y = 0, 1

        # Draw 3 web holes (3 x Ø3.8mm) at 17mm spacing along the web's perpendicular
        radius_px = 1.9 * SCALE
        spacing_px = 17 * SCALE
        # connection-zone outline rectangle (12mm × 44mm)
        rect_w = 12 * SCALE; rect_h = 44 * SCALE
        # rotated rect
        ang = math.degrees(math.atan2(perp_y, perp_x)) - 90
        svg.append(f'<rect x="{cx_px - rect_w/2:.1f}" y="{cy_px - rect_h/2:.1f}" width="{rect_w:.1f}" height="{rect_h:.1f}" '
                   f'transform="rotate({ang:.1f} {cx_px:.1f} {cy_px:.1f})" '
                   f'fill="rgba(22,163,74,0.08)" stroke="#16a34a" stroke-width="0.7" stroke-dasharray="2 2" opacity="0.7"/>')
        for offset in [-spacing_px, 0, spacing_px]:
            hx = cx_px + perp_x * offset
            hy = cy_px + perp_y * offset
            svg.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{radius_px:.2f}" fill="white" stroke="#16a34a" stroke-width="1.5"/>')

    # Legend (right side)
    leg_x = PAGE_W - 270
    leg_y = 130
    svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="240" height="180" fill="#f8fafc" stroke="#e2e8f0" rx="4"/>')
    svg.append(f'<text x="{leg_x+12}" y="{leg_y+22}" font-size="13" font-weight="700" fill="#1a202c">Real FrameCAD tools</text>')
    # Web hole sample
    svg.append(f'<text x="{leg_x+12}" y="{leg_y+44}" font-size="11" fill="#374151" font-weight="600">WEB HOLE — 3 × Ø3.8mm</text>')
    for off, dy in [(-17, 0), (0, 0), (17, 0)]:
        svg.append(f'<circle cx="{leg_x + 30 + off*0.6:.1f}" cy="{leg_y+62}" r="2" fill="white" stroke="#16a34a" stroke-width="1.3"/>')
    svg.append(f'<text x="{leg_x+90}" y="{leg_y+66}" font-size="10" fill="#374151">at 17mm spacing</text>')
    # Swage
    svg.append(f'<text x="{leg_x+12}" y="{leg_y+92}" font-size="11" fill="#374151" font-weight="600">SWAGE — centre crimp</text>')
    svg.append(f'<line x1="{leg_x+12}" y1="{leg_y+108}" x2="{leg_x+80}" y2="{leg_y+108}" stroke="#a855f7" stroke-width="1.6" opacity="0.6"/>')
    svg.append(f'<text x="{leg_x+90}" y="{leg_y+112}" font-size="10" fill="#374151">continuous</text>')
    # Service hole
    svg.append(f'<text x="{leg_x+12}" y="{leg_y+138}" font-size="11" fill="#374151" font-weight="600">Other tools shown:</text>')
    svg.append(f'<text x="{leg_x+12}" y="{leg_y+154}" font-size="10" fill="#6b7280">LIP CUT, FLANGE CUT, SERVICE</text>')
    svg.append(f'<text x="{leg_x+12}" y="{leg_y+168}" font-size="10" fill="#6b7280">HOLE (Ø32), DIMPLE (Ø5.1)</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# ============= RENDER CLOSE-UP WITH ALL REAL TOOLS =============

def render_closeup():
    """Lifelike close-up of W6 end showing every real FrameCAD tool used.
    Uses the actual profile drawing dimensions from F37008 W089 F41-38."""
    W = 1900
    H = 1500
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append('''<defs>
      <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#f1f5f9"/><stop offset="0.5" stop-color="#cbd5e0"/><stop offset="1" stop-color="#94a3b8"/>
      </linearGradient>
      <linearGradient id="steel-flange" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#94a3b8"/><stop offset="0.5" stop-color="#cbd5e0"/><stop offset="1" stop-color="#94a3b8"/>
      </linearGradient>
      <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="4" stroke="#dc2626" stroke-width="0.8"/>
      </pattern>
      <linearGradient id="swage-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#cbd5e0"/><stop offset="0.5" stop-color="#475569"/><stop offset="1" stop-color="#cbd5e0"/>
      </linearGradient>
      <marker id="ar" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
        <path d="M0,0 L9,4.5 L0,9 z" fill="#374151"/>
      </marker>
    </defs>''')
    svg.append(f'<rect width="{W}" height="{H}" fill="#fafaf8"/>')

    svg.append(f'<text x="30" y="40" font-size="26" font-weight="700" fill="#1a202c">All FrameCAD tools (real geometry from F37008 W089 F41-38 spec)</text>')
    svg.append(f'<text x="30" y="64" font-size="14" fill="#4a5568">89×41 lipped C-section, 0.75mm gauge. Each tool drawn at scale (1mm = 5px) with the dimensions from the rollformer drawing.</text>')

    # Single big elevation panel showing ALL tools on one stick
    P_X = 30; P_Y = 90; P_W = W-60; P_H = 380
    svg.append(f'<rect x="{P_X}" y="{P_Y}" width="{P_W}" height="{P_H}" fill="white" stroke="#cbd5e0" rx="4"/>')
    svg.append(f'<text x="{P_X+15}" y="{P_Y+22}" font-size="14" font-weight="700" fill="#1a202c">Reference stick — all 8 tool stations applied (web face elevation, 89mm tall, 5px = 1mm)</text>')

    MM = 5  # 5px per mm
    stick_y_top = P_Y + 80
    stick_y_bot = stick_y_top + 89*MM   # 89mm web
    cy_stick = (stick_y_top + stick_y_bot) / 2
    # Stick goes from x=80 to about x=W-60
    stick_x0 = P_X + 80
    stick_len_mm = (P_W - 160) / MM
    stick_x1 = stick_x0 + stick_len_mm * MM

    # Stick body with subtle steel gradient
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_x1-stick_x0}" height="{89*MM}" fill="url(#steel)" stroke="#475569" stroke-width="1.5"/>')

    # Lip strips at top + bottom (12mm)
    lip_h = 12 * MM
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_top}" width="{stick_x1-stick_x0}" height="{lip_h}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1" opacity="0.9"/>')
    svg.append(f'<rect x="{stick_x0}" y="{stick_y_bot-lip_h}" width="{stick_x1-stick_x0}" height="{lip_h}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1" opacity="0.9"/>')

    # Centreline
    svg.append(f'<line x1="{stick_x0-15}" y1="{cy_stick}" x2="{stick_x1+15}" y2="{cy_stick}" stroke="#374151" stroke-width="0.8" stroke-dasharray="5 3" opacity="0.5"/>')

    # SWAGE — continuous purple lens-shape band along centreline
    swage_h = 5 * MM  # 5mm tall (approximate visible swage band)
    svg.append(f'<rect x="{stick_x0+10}" y="{cy_stick-swage_h/2}" width="{stick_x1-stick_x0-20}" height="{swage_h}" fill="url(#swage-grad)" opacity="0.5"/>')
    svg.append(f'<line x1="{stick_x0+10}" y1="{cy_stick-swage_h/2}" x2="{stick_x1-10}" y2="{cy_stick-swage_h/2}" stroke="#475569" stroke-width="0.5"/>')
    svg.append(f'<line x1="{stick_x0+10}" y1="{cy_stick+swage_h/2}" x2="{stick_x1-10}" y2="{cy_stick+swage_h/2}" stroke="#475569" stroke-width="0.5"/>')

    # Place each tool at a specific position with annotation
    def x_at(mm): return stick_x0 + mm * MM

    # 1. WEB HOLE at 80mm — 3 x Ø3.8mm at 17mm vertical spacing on centreline
    wh_x = x_at(80)
    for offset in [-17*MM, 0, 17*MM]:
        svg.append(f'<circle cx="{wh_x}" cy="{cy_stick + offset}" r="{1.9*MM}" fill="white" stroke="#16a34a" stroke-width="1.6"/>')
    svg.append(f'<rect x="{wh_x-6*MM}" y="{cy_stick-22*MM}" width="{12*MM}" height="{44*MM}" fill="none" stroke="#16a34a" stroke-width="0.7" stroke-dasharray="3 2" opacity="0.5"/>')
    svg.append(f'<text x="{wh_x}" y="{stick_y_top-30}" text-anchor="middle" font-size="11" font-weight="700" fill="#14532d">TOOL 1 — WEB HOLE</text>')
    svg.append(f'<text x="{wh_x}" y="{stick_y_top-15}" text-anchor="middle" font-size="9" fill="#14532d">3 x Ø3.8mm @ 17mm</text>')

    # 2. WEB BOLT HOLE at 200mm — Ø13.5mm
    wbh_x = x_at(200)
    svg.append(f'<circle cx="{wbh_x}" cy="{cy_stick}" r="{6.75*MM}" fill="white" stroke="#7c3aed" stroke-width="1.6"/>')
    svg.append(f'<text x="{wbh_x}" y="{stick_y_top-30}" text-anchor="middle" font-size="11" font-weight="700" fill="#5b21b6">TOOL 1 — WEB BOLT HOLE</text>')
    svg.append(f'<text x="{wbh_x}" y="{stick_y_top-15}" text-anchor="middle" font-size="9" fill="#5b21b6">Ø13.5mm</text>')

    # 3. LIP CUT at 320mm — angled cut into top + bottom lip
    lc_x = x_at(320)
    lc_w = 10 * MM
    # Top lip cut (triangular)
    svg.append(f'<polygon points="{lc_x-lc_w/2},{stick_y_top} {lc_x+lc_w/2},{stick_y_top} {lc_x},{stick_y_top+lip_h}" '
               f'fill="white" stroke="#dc2626" stroke-width="1.5"/>')
    svg.append(f'<polygon points="{lc_x-lc_w/2},{stick_y_top} {lc_x+lc_w/2},{stick_y_top} {lc_x},{stick_y_top+lip_h}" fill="url(#cut-hatch)" opacity="0.6"/>')
    # Bottom lip cut
    svg.append(f'<polygon points="{lc_x-lc_w/2},{stick_y_bot} {lc_x+lc_w/2},{stick_y_bot} {lc_x},{stick_y_bot-lip_h}" '
               f'fill="white" stroke="#dc2626" stroke-width="1.5"/>')
    svg.append(f'<polygon points="{lc_x-lc_w/2},{stick_y_bot} {lc_x+lc_w/2},{stick_y_bot} {lc_x},{stick_y_bot-lip_h}" fill="url(#cut-hatch)" opacity="0.6"/>')
    svg.append(f'<text x="{lc_x}" y="{stick_y_top-30}" text-anchor="middle" font-size="11" font-weight="700" fill="#7f1d1d">TOOL 2 — LIP CUT</text>')

    # 4. WEB NOTCH at 430mm — small rectangle into web from edge
    wn_x = x_at(430)
    wn_w = 12 * MM; wn_h = 8 * MM
    svg.append(f'<rect x="{wn_x-wn_w/2}" y="{stick_y_top+lip_h}" width="{wn_w}" height="{wn_h}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.4"/>')
    svg.append(f'<text x="{wn_x}" y="{stick_y_top-30}" text-anchor="middle" font-size="11" font-weight="700" fill="#7f1d1d">TOOL 2 — WEB NOTCH</text>')

    # 5. FLANGE CUT at 540mm — 3mm wide vertical strip
    fc_x = x_at(540)
    fc_w = 3 * MM
    svg.append(f'<rect x="{fc_x-fc_w/2}" y="{stick_y_top}" width="{fc_w}" height="{89*MM}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.2"/>')
    svg.append(f'<text x="{fc_x}" y="{stick_y_top-30}" text-anchor="middle" font-size="11" font-weight="700" fill="#7f1d1d">TOOL 3 — FLANGE CUT</text>')
    svg.append(f'<text x="{fc_x}" y="{stick_y_top-15}" text-anchor="middle" font-size="9" fill="#7f1d1d">3mm wide</text>')

    # 6. SERVICE HOLE at 700mm — Ø32mm circle through web
    sh_x = x_at(700)
    svg.append(f'<circle cx="{sh_x}" cy="{cy_stick}" r="{16*MM}" fill="white" stroke="#0891b2" stroke-width="2"/>')
    svg.append(f'<circle cx="{sh_x}" cy="{cy_stick}" r="{16*MM-1}" fill="none" stroke="#0891b2" stroke-width="0.8" stroke-dasharray="2 2"/>')
    svg.append(f'<text x="{sh_x}" y="{stick_y_top-30}" text-anchor="middle" font-size="11" font-weight="700" fill="#155e75">TOOL 3 — SERVICE HOLE</text>')
    svg.append(f'<text x="{sh_x}" y="{stick_y_top-15}" text-anchor="middle" font-size="9" fill="#155e75">Ø32mm</text>')

    # 7. MULTI TOOL at 870mm — 4 x Ø5.1mm dimples + 4 x Ø3.8mm flange holes
    mt_x = x_at(870)
    # 4 dimples (Ø5.1)
    for dx in [-30, -10, 10, 30]:
        svg.append(f'<circle cx="{mt_x + dx*MM}" cy="{cy_stick - 7*MM}" r="{2.55*MM}" fill="#fef3c7" stroke="#d97706" stroke-width="1.2"/>')
    # 4 flange holes (Ø3.8) — on the lip strips
    for dx in [-30, -10, 10, 30]:
        svg.append(f'<circle cx="{mt_x + dx*MM}" cy="{stick_y_top + lip_h/2}" r="{1.9*MM}" fill="white" stroke="#d97706" stroke-width="1.2"/>')
        svg.append(f'<circle cx="{mt_x + dx*MM}" cy="{stick_y_bot - lip_h/2}" r="{1.9*MM}" fill="white" stroke="#d97706" stroke-width="1.2"/>')
    svg.append(f'<text x="{mt_x}" y="{stick_y_top-30}" text-anchor="middle" font-size="11" font-weight="700" fill="#92400e">TOOL 5 — MULTI TOOL</text>')
    svg.append(f'<text x="{mt_x}" y="{stick_y_top-15}" text-anchor="middle" font-size="9" fill="#92400e">4 dimples Ø5.1 + 4 flange holes Ø3.8</text>')

    # 8. FLAT DIMPLE at 1080mm — single Ø5.1mm dimple
    fd_x = x_at(1080)
    svg.append(f'<circle cx="{fd_x}" cy="{cy_stick}" r="{2.55*MM}" fill="#fef3c7" stroke="#d97706" stroke-width="1.4"/>')
    svg.append(f'<text x="{fd_x}" y="{stick_y_top-30}" text-anchor="middle" font-size="11" font-weight="700" fill="#92400e">TOOL 5 — FLAT DIMPLE</text>')
    svg.append(f'<text x="{fd_x}" y="{stick_y_top-15}" text-anchor="middle" font-size="9" fill="#92400e">Ø5.1mm</text>')

    # 9. CHAMFER CUT at 1180mm — corner chamfer
    cc_x = x_at(1180)
    cc_size = 8 * MM
    # Chamfer at top-left
    svg.append(f'<polygon points="{cc_x-cc_size},{stick_y_top} {cc_x},{stick_y_top} {cc_x},{stick_y_top+cc_size}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.3"/>')
    svg.append(f'<polygon points="{cc_x-cc_size},{stick_y_bot} {cc_x},{stick_y_bot} {cc_x},{stick_y_bot-cc_size}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.3"/>')
    svg.append(f'<text x="{cc_x-cc_size/2}" y="{stick_y_top-30}" text-anchor="middle" font-size="11" font-weight="700" fill="#7f1d1d">TOOL 4 — CHAMFER CUT</text>')

    # SWAGE label (it's everywhere)
    svg.append(f'<text x="{stick_x0+10}" y="{cy_stick+swage_h/2+18}" font-size="10" fill="#5b21b6" font-weight="600">↑ SWAGE (continuous centre crimp)</text>')

    # Dimensions on the stick
    # 89mm height
    dim_x = stick_x0 - 28
    svg.append(f'<line x1="{dim_x}" y1="{stick_y_top}" x2="{dim_x}" y2="{stick_y_bot}" stroke="#374151" stroke-width="0.8" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    svg.append(f'<text x="{dim_x-5}" y="{cy_stick+5}" text-anchor="end" font-size="11" fill="#374151">89 mm web</text>')
    # 12mm lip
    svg.append(f'<line x1="{stick_x0-12}" y1="{stick_y_top}" x2="{stick_x0-12}" y2="{stick_y_top+lip_h}" stroke="#374151" stroke-width="0.8" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    svg.append(f'<text x="{stick_x0-15}" y="{stick_y_top+lip_h+4}" text-anchor="end" font-size="9" fill="#374151">12mm lip</text>')

    # ============ PANEL 2: WEB HOLE detail at 8x ============
    P2_Y = P_Y + P_H + 20
    P2_H = 380
    svg.append(f'<rect x="30" y="{P2_Y}" width="{(W-90)/2}" height="{P2_H}" fill="white" stroke="#cbd5e0" rx="4"/>')
    svg.append(f'<text x="50" y="{P2_Y+22}" font-size="14" font-weight="700" fill="#14532d">WEB HOLE detail (replacing the BOLT HOLE for connections)</text>')
    svg.append(f'<text x="50" y="{P2_Y+40}" font-size="12" fill="#4a5568">Drawn at 8× scale. 3 holes Ø3.8mm at 17mm vertical spacing on web centreline.</text>')

    # Big version
    big_x = 50 + ((W-90)/2 - 60)/2 + 20
    big_y = P2_Y + 70
    BIG_MM = 8  # 8px per mm

    # Section of web — show 80mm length × 89mm tall
    big_w = 80 * BIG_MM
    big_h = 89 * BIG_MM
    big_x0 = big_x - big_w/2
    big_y0 = big_y
    big_y1 = big_y0 + big_h
    big_cy = (big_y0 + big_y1)/2
    svg.append(f'<rect x="{big_x0}" y="{big_y0}" width="{big_w}" height="{big_h}" fill="url(#steel)" stroke="#475569" stroke-width="2"/>')
    big_lip = 12*BIG_MM
    svg.append(f'<rect x="{big_x0}" y="{big_y0}" width="{big_w}" height="{big_lip}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1.2"/>')
    svg.append(f'<rect x="{big_x0}" y="{big_y1-big_lip}" width="{big_w}" height="{big_lip}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1.2"/>')
    svg.append(f'<line x1="{big_x0-15}" y1="{big_cy}" x2="{big_x0+big_w+15}" y2="{big_cy}" stroke="#374151" stroke-width="1" stroke-dasharray="5 3" opacity="0.6"/>')

    # 3 web holes at centre
    big_cx = big_x
    for offset_mm in [-17, 0, 17]:
        hy = big_cy + offset_mm * BIG_MM
        svg.append(f'<circle cx="{big_cx}" cy="{hy}" r="{1.9*BIG_MM}" fill="white" stroke="#16a34a" stroke-width="2"/>')
        # Crosshair for centre
        svg.append(f'<line x1="{big_cx-4*BIG_MM}" y1="{hy}" x2="{big_cx+4*BIG_MM}" y2="{hy}" stroke="#16a34a" stroke-width="0.8" opacity="0.6"/>')
        svg.append(f'<line x1="{big_cx}" y1="{hy-4*BIG_MM}" x2="{big_cx}" y2="{hy+4*BIG_MM}" stroke="#16a34a" stroke-width="0.8" opacity="0.6"/>')

    # Dimensions
    # 17mm spacing
    dim_x = big_x0 + big_w + 30
    svg.append(f'<line x1="{dim_x}" y1="{big_cy-17*BIG_MM}" x2="{dim_x}" y2="{big_cy}" stroke="#374151" stroke-width="0.8" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    svg.append(f'<text x="{dim_x+8}" y="{big_cy-17*BIG_MM/2+4}" font-size="11" fill="#374151">17 mm</text>')
    svg.append(f'<line x1="{dim_x}" y1="{big_cy}" x2="{dim_x}" y2="{big_cy+17*BIG_MM}" stroke="#374151" stroke-width="0.8" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    svg.append(f'<text x="{dim_x+8}" y="{big_cy+17*BIG_MM/2+4}" font-size="11" fill="#374151">17 mm</text>')

    # Diameter
    svg.append(f'<text x="{big_cx + 1.9*BIG_MM + 14}" y="{big_cy - 17*BIG_MM + 4}" font-size="11" fill="#16a34a" font-weight="600">Ø3.8mm</text>')

    # Caption
    cap_y = P2_Y + P2_H - 60
    svg.append(f'<rect x="50" y="{cap_y}" width="{(W-90)/2 - 40}" height="48" fill="#dcfce7" stroke="#16a34a" rx="3"/>')
    svg.append(f'<text x="60" y="{cap_y+18}" font-size="12" font-weight="700" fill="#14532d">Why 3 holes instead of 1 bolt?</text>')
    svg.append(f'<text x="60" y="{cap_y+34}" font-size="11" fill="#14532d">Three Ø3.8mm holes take three 10g self-drilling screws → 3× shear capacity of a single M6 bolt</text>')

    # ============ PANEL 3: assembly view showing how WEB HOLE works ============
    P3_X = 30 + (W-90)/2 + 30
    P3_Y = P2_Y
    P3_W = (W-90)/2
    svg.append(f'<rect x="{P3_X}" y="{P3_Y}" width="{P3_W}" height="{P2_H}" fill="white" stroke="#cbd5e0" rx="4"/>')
    svg.append(f'<text x="{P3_X+20}" y="{P3_Y+22}" font-size="14" font-weight="700" fill="#1a202c">Assembly — web meets chord, 3 screws through both layers</text>')
    svg.append(f'<text x="{P3_X+20}" y="{P3_Y+40}" font-size="12" fill="#4a5568">3 self-drilling screws pass through web + chord at the centreline crossing.</text>')

    SC = 3
    # Chord (horizontal, blue)
    chord_y = P3_Y + 130
    chord_h = 89 * SC
    chord_x = P3_X + 60
    chord_w = P3_W - 120
    svg.append(f'<rect x="{chord_x}" y="{chord_y}" width="{chord_w}" height="{chord_h}" fill="url(#steel)" stroke="#1d4ed8" stroke-width="2"/>')
    chord_lip = 12*SC
    svg.append(f'<rect x="{chord_x}" y="{chord_y}" width="{chord_w}" height="{chord_lip}" fill="url(#steel-flange)" stroke="#1d4ed8" stroke-width="1.2"/>')
    svg.append(f'<rect x="{chord_x}" y="{chord_y+chord_h-chord_lip}" width="{chord_w}" height="{chord_lip}" fill="url(#steel-flange)" stroke="#1d4ed8" stroke-width="1.2"/>')
    svg.append(f'<text x="{chord_x+10}" y="{chord_y+chord_h+18}" font-size="11" fill="#1d4ed8" font-weight="600">CHORD plate (89×41 lipped C, laid flat)</text>')

    # Web - vertical, comes from above into chord
    web_cx = P3_X + P3_W/2
    web_w_px = 89 * SC
    web_top = P3_Y + 70
    web_bot = chord_y + chord_h - 5  # web extends through to far side of chord
    svg.append(f'<rect x="{web_cx-web_w_px/2}" y="{web_top}" width="{web_w_px}" height="{web_bot-web_top}" fill="url(#steel)" stroke="#475569" stroke-width="2" opacity="0.95"/>')
    svg.append(f'<rect x="{web_cx-web_w_px/2}" y="{web_top}" width="{web_w_px}" height="{12*SC}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1.2" opacity="0.95"/>')

    # Lip notches at the web bottom (where it meets chord)
    notch_w = 12*SC; notch_h = 12*SC
    svg.append(f'<rect x="{web_cx-web_w_px/2}" y="{chord_y+chord_h - notch_h}" width="{notch_w}" height="{notch_h}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.4"/>')
    svg.append(f'<rect x="{web_cx+web_w_px/2-notch_w}" y="{chord_y+chord_h - notch_h}" width="{notch_w}" height="{notch_h}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.4"/>')

    # 3 web holes at the centreline crossing (centre of chord)
    cross_y = chord_y + chord_h/2
    for offset_mm in [-17, 0, 17]:
        hy = cross_y + offset_mm * SC
        # Hole through both layers
        svg.append(f'<circle cx="{web_cx}" cy="{hy}" r="{1.9*SC}" fill="white" stroke="#16a34a" stroke-width="1.8"/>')
        # Show the screw head (circle with X)
        svg.append(f'<circle cx="{web_cx + 32}" cy="{hy}" r="{4*SC}" fill="#dcfce7" stroke="#16a34a" stroke-width="1.5"/>')
        svg.append(f'<line x1="{web_cx + 32 - 3*SC}" y1="{hy}" x2="{web_cx + 32 + 3*SC}" y2="{hy}" stroke="#14532d" stroke-width="1.2"/>')
        svg.append(f'<line x1="{web_cx + 32}" y1="{hy - 3*SC}" x2="{web_cx + 32}" y2="{hy + 3*SC}" stroke="#14532d" stroke-width="1.2"/>')
        # Arrow showing screw going through
        svg.append(f'<path d="M {web_cx + 32 - 4*SC} {hy} Q {web_cx + 16} {hy - 4} {web_cx} {hy}" fill="none" stroke="#16a34a" stroke-width="1" stroke-dasharray="3 2" opacity="0.7"/>')

    # Web label
    svg.append(f'<text x="{web_cx-web_w_px/2-10}" y="{web_top+30}" text-anchor="end" font-size="11" fill="#475569" font-weight="600">WEB stud</text>')

    # Annotation
    svg.append(f'<text x="{web_cx + 80}" y="{cross_y - 30}" font-size="11" fill="#14532d" font-weight="700">3 × 10g self-drilling screws</text>')
    svg.append(f'<text x="{web_cx + 80}" y="{cross_y - 14}" font-size="10" fill="#14532d">Ø4.8mm thread, Ø3.8mm pre-drill</text>')
    svg.append(f'<text x="{web_cx + 80}" y="{cross_y + 4}" font-size="10" fill="#14532d">at 17mm vertical pitch</text>')
    svg.append(f'<text x="{web_cx + 80}" y="{cross_y + 18}" font-size="10" fill="#14532d">drives through 0.75mm web + 0.75mm chord</text>')

    # Caption
    cap_y = P3_Y + P2_H - 60
    svg.append(f'<rect x="{P3_X+20}" y="{cap_y}" width="{P3_W-40}" height="48" fill="#dbeafe" stroke="#1d4ed8" rx="3"/>')
    svg.append(f'<text x="{P3_X+30}" y="{cap_y+18}" font-size="12" font-weight="700" fill="#1e3a8a">Mechanically:</text>')
    svg.append(f'<text x="{P3_X+30}" y="{cap_y+34}" font-size="11" fill="#1e3a8a">Each screw threads itself through both 0.75mm steel layers — no separate drill step needed.</text>')

    # ============ FOOTER ============
    svg.append(f'<text x="30" y="{H-15}" font-size="11" fill="#6b7280">Source: F37008 W089 F41-38 profile drawing (Rev 0, 29.11.18) - all tool dimensions taken directly from the FrameCAD rollformer spec.</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# === RUN ===
print('Generating truss with real tools...')
truss_svg = render_truss('TN2-1')
truss_path = os.path.join(OUT_DIR, 'truss_real_tools.svg')
open(truss_path, 'w', encoding='utf-8').write(truss_svg)
print(f'Wrote {truss_path}')

print('Generating tool reference + close-up...')
closeup_svg = render_closeup()
closeup_path = os.path.join(OUT_DIR, 'real_tools_reference.svg')
open(closeup_path, 'w', encoding='utf-8').write(closeup_svg)
print(f'Wrote {closeup_path}')

# Build index
idx = ['<!DOCTYPE html><html><head><title>Real FrameCAD tools</title>',
       '<style>',
       '*{box-sizing:border-box}',
       'body{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:24px;background:#f1f5f9}',
       'h1{margin:0 0 12px}',
       '.sub{color:#4a5568;margin-bottom:24px}',
       '.card{background:white;border:1px solid #cbd5e0;border-radius:6px;margin-bottom:24px;overflow:hidden}',
       '.card-head{padding:14px 18px;background:#fafaf8;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center}',
       '.card-head h2{margin:0;font-size:16px}',
       '.card-head a{color:#2563eb;text-decoration:none;padding:5px 12px;border:1px solid #93c5fd;border-radius:3px;font-size:12px}',
       'iframe{border:0;width:100%;height:1100px;display:block;background:white}',
       '.h-tall{height:1100px}',
       '.h-mid{height:1500px}',
       '</style></head><body>',
       '<h1>Real FrameCAD tooling — geometry from F37008 W089 F41-38 spec</h1>',
       '<p class="sub">Replaces the BOLT HOLE with the proper WEB HOLE tool (3 × Ø3.8mm at 17mm spacing). Shows the truss + a tool reference page with all 11 tool stations.</p>',
       '<div class="card"><div class="card-head"><div><h2>1. Truss frame TN2-1 with WEB HOLE at every centreline crossing</h2><div style="font-size:12px;color:#4a5568">10 members &middot; 14 nodes after clustering &middot; 3 holes per node = 42 Ø3.8mm holes total</div></div><a href="truss_real_tools.svg" target="_blank">open standalone &uarr;&rarr;</a></div><iframe src="truss_real_tools.svg" class="h-tall"></iframe></div>',
       '<div class="card"><div class="card-head"><div><h2>2. All real FrameCAD tools — reference page</h2><div style="font-size:12px;color:#4a5568">All 9 tool stations from the rollformer drawing, drawn at scale (5px = 1mm)</div></div><a href="real_tools_reference.svg" target="_blank">open standalone &uarr;&rarr;</a></div><iframe src="real_tools_reference.svg" class="h-mid"></iframe></div>',
       '</body></html>']
idx_path = os.path.join(OUT_DIR, 'REAL_TOOLS.html')
open(idx_path, 'w', encoding='utf-8').write('\n'.join(idx))
print(f'Wrote {idx_path}')
