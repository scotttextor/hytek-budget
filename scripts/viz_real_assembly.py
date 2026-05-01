"""Truss matching the real assembly photo.

Observations from the physical truss photo (IMG_6032):
  - Galv steel = silvery-blue tone, not pure grey
  - All sticks coplanar, lying flat web-face-down on the assembly bench
  - All lips face the SAME direction (consistent orientation)
  - Green-capped self-drilling screws at every junction
  - Channels are clearly visible as open-top U-troughs at the chords

So this drawing:
  - Top-down workshop view (matching photo angle)
  - All members show the OPEN-CHANNEL side (lips on far edge from viewer)
  - Green screw heads at WEB HOLE positions (3 per junction)
  - Workshop concrete-floor background
  - Consistent lip orientation across every member
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
                out.append({'pt':pt})
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

# Render
def render(frame_name='TN2-1'):
    sticks = parse_frame(frame_name)
    crossings = all_crossings(sticks)
    nodes = cluster(crossings, 180)

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

    # Defs - galv steel matched to the real photo
    svg.append('''<defs>
      <!-- Workshop concrete floor -->
      <pattern id="concrete" patternUnits="userSpaceOnUse" width="80" height="80">
        <rect width="80" height="80" fill="#8a8e95"/>
        <circle cx="20" cy="30" r="2" fill="#7a7e85" opacity="0.4"/>
        <circle cx="55" cy="55" r="3" fill="#7a7e85" opacity="0.3"/>
        <circle cx="65" cy="15" r="1.5" fill="#9a9ea5" opacity="0.5"/>
        <circle cx="10" cy="65" r="2.5" fill="#7a7e85" opacity="0.35"/>
        <circle cx="40" cy="10" r="1" fill="#9a9ea5" opacity="0.4"/>
      </pattern>
      <radialGradient id="floor-light" cx="0.5" cy="0.4" r="0.7">
        <stop offset="0%" stop-color="white" stop-opacity="0.15"/>
        <stop offset="100%" stop-color="black" stop-opacity="0.15"/>
      </radialGradient>

      <!-- Galv steel — silvery blue tone matching the photo -->
      <linearGradient id="galv-real" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#dde6ed"/>
        <stop offset="40%" stop-color="#b8c8d4"/>
        <stop offset="80%" stop-color="#8a9ba9"/>
        <stop offset="100%" stop-color="#6a7c8b"/>
      </linearGradient>
      <linearGradient id="galv-real-chord" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#d2dde5"/>
        <stop offset="50%" stop-color="#a4b6c4"/>
        <stop offset="100%" stop-color="#6e8090"/>
      </linearGradient>
      <!-- Inside-of-channel (slightly darker since it's the underside) -->
      <linearGradient id="channel-inside" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#9aabb9"/>
        <stop offset="100%" stop-color="#7a8b9a"/>
      </linearGradient>
      <!-- Lip strip on the OPEN side — catches workshop light -->
      <linearGradient id="lip-bright" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#e8f0f6"/>
        <stop offset="100%" stop-color="#9eafbd"/>
      </linearGradient>

      <!-- Green screw cap (matches photo) -->
      <radialGradient id="screw-cap" cx="0.35" cy="0.35" r="0.7">
        <stop offset="0%" stop-color="#a3e635"/>
        <stop offset="40%" stop-color="#65a30d"/>
        <stop offset="100%" stop-color="#365314"/>
      </radialGradient>
      <radialGradient id="screw-shine" cx="0.3" cy="0.3" r="0.4">
        <stop offset="0%" stop-color="white" stop-opacity="0.7"/>
        <stop offset="100%" stop-color="white" stop-opacity="0"/>
      </radialGradient>

      <!-- Spangle texture for galv -->
      <pattern id="spangle" patternUnits="userSpaceOnUse" width="50" height="50">
        <rect width="50" height="50" fill="none"/>
        <ellipse cx="10" cy="15" rx="6" ry="3" fill="white" opacity="0.05" transform="rotate(20 10 15)"/>
        <ellipse cx="35" cy="30" rx="8" ry="4" fill="white" opacity="0.04" transform="rotate(-15 35 30)"/>
        <ellipse cx="20" cy="42" rx="5" ry="2.5" fill="white" opacity="0.06" transform="rotate(40 20 42)"/>
      </pattern>

      <filter id="blur5"><feGaussianBlur stdDeviation="5"/></filter>
      <filter id="blur3"><feGaussianBlur stdDeviation="3"/></filter>
    </defs>''')

    # Background — workshop floor
    svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="url(#concrete)"/>')
    svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="url(#floor-light)"/>')

    # Title bar
    svg.append(f'<rect x="0" y="0" width="{PAGE_W}" height="105" fill="white" opacity="0.95"/>')
    svg.append(f'<text x="40" y="42" font-size="26" font-weight="700" fill="#1a202c">Truss frame {frame_name} — matching real assembly</text>')
    svg.append(f'<text x="40" y="68" font-size="14" fill="#4a5568">Galv finish · all lips facing same direction · green-capped self-drilling screws at each junction (3 × Ø3.8mm pattern)</text>')
    svg.append(f'<text x="40" y="92" font-size="13" fill="#374151">{len(sticks)} members &middot; {len(nodes)} junction nodes &middot; {len(nodes)*3} screws total (down from ~70 in current FrameCAD spec)</text>')

    # Build each member as a polygon — top-down view
    # In top-down view, looking at the OPEN side of C, you see:
    #   the bright lip-strip on the FAR edge (the side away from viewer in 3D)
    #   the dark channel-inside on most of the visible width
    #   subtle near-edge highlight (the side toward viewer)
    # Since all sticks have lips facing same way, the lip strip is on the
    # consistent "down" side of every member's drawn rectangle.
    # We choose: lip strip = on the side perpendicular to stick axis, on the +y side.
    # Better: define a global "lip side" vector and show the lip strip on whichever
    # side of the member is CLOSER to that direction.

    # Render: shadow pass then body pass
    def member_poly_corners(stick):
        sx, sz = stick['start']; ex, ez = stick['end']
        dx, dz = ex-sx, ez-sz
        L = math.hypot(dx, dz)
        if L == 0: return None
        nx, nz = -dz/L, dx/L  # left perp (CCW)
        h = WIDTH_MM/2
        # Outer corners (full width)
        TL = (sx + nx*h, sz + nz*h)
        BL = (sx - nx*h, sz - nz*h)
        TR = (ex - nx*h, ez - nz*h)
        BR = (ex + nx*h, ez + nz*h)
        # Inner-lip corners (one side is bright lip, other side is just the channel)
        TL_in = (sx + nx*(h-LIP_MM), sz + nz*(h-LIP_MM))
        TR_in = (ex - nx*(h-LIP_MM), ez - nz*(h-LIP_MM))
        BL_in = (sx - nx*(h-LIP_MM), sz - nz*(h-LIP_MM))
        BR_in = (ex + nx*(h-LIP_MM), ez + nz*(h-LIP_MM))
        return TL, BL, TR, BR, TL_in, TR_in, BL_in, BR_in

    pts = lambda lst: ' '.join(f'{a:.1f},{b:.1f}' for a,b in (to_px(*p) for p in lst))

    # Decide lip orientation: lips on the +Z (upward in real world) side of every stick.
    # In our coord system Z = vertical (height). A stick's "+nz" perpendicular component
    # tells us which side is up. We'll put the LIP STRIP on the side whose nz > 0.
    # If nz < 0, flip top/bottom.

    def member_oriented(stick):
        c = member_poly_corners(stick)
        if c is None: return None
        TL, BL, TR, BR, TL_in, TR_in, BL_in, BR_in = c
        sx, sz = stick['start']; ex, ez = stick['end']
        dx, dz = ex-sx, ez-sz
        L = math.hypot(dx, dz)
        nz = dx / L  # nx,nz = (-dz/L, dx/L), so the Z-component of the left-perp is dx/L
        # If positive, the "TL/TR" (left perp) side faces up. If negative, flip.
        if nz >= 0:
            return TL, BL, TR, BR, TL_in, TR_in, BL_in, BR_in, 'normal'
        else:
            return BL, TL, BR, TR, BL_in, BR_in, TL_in, TR_in, 'flipped'

    # Drop shadows first (separate pass for proper layering)
    svg.append('<g opacity="0.55">')
    SHADOW_OFFSET = 6
    for s in sticks:
        c = member_poly_corners(s)
        if c is None: continue
        TL, BL, TR, BR, *_ = c
        ps = []
        for p in [TL, BL, TR, BR]:
            sx, sy = to_px(*p)
            ps.append(f'{sx+SHADOW_OFFSET:.1f},{sy+SHADOW_OFFSET:.1f}')
        svg.append(f'<polygon points="{" ".join(ps)}" fill="black" opacity="0.4" filter="url(#blur5)"/>')
    svg.append('</g>')

    # Members - chords first
    for s in sticks:
        c = member_oriented(s)
        if c is None: continue
        TL, BL, TR, BR, TL_in, TR_in, BL_in, BR_in, orient = c

        if s['type'] == 'Plate':
            fill = 'url(#galv-real-chord)'
        else:
            fill = 'url(#galv-real)'
        # Body
        svg.append(f'<polygon points="{pts([TL, BL, BR, TR])}" fill="{fill}"/>')
        # Spangle
        svg.append(f'<polygon points="{pts([TL, BL, BR, TR])}" fill="url(#spangle)" opacity="0.6"/>')
        # Channel-inside band (the wider middle area)
        svg.append(f'<polygon points="{pts([TL_in, BL_in, BR_in, TR_in])}" fill="url(#channel-inside)" opacity="0.6"/>')
        # Lip strip on the TOP side (bright - catches workshop light)
        svg.append(f'<polygon points="{pts([TL, TR, TR_in, TL_in])}" fill="url(#lip-bright)" stroke="#5a6c7c" stroke-width="0.6"/>')
        # Tiny dark line where lip meets web (inside of the C)
        svg.append(f'<polyline points="{pts([TL_in, TR_in])}" fill="none" stroke="#1f2329" stroke-width="0.7" opacity="0.7"/>')
        # Bottom edge — just a darker line (no lip visible from this side because lips face away/up)
        svg.append(f'<polyline points="{pts([BL, BR])}" fill="none" stroke="#3a4654" stroke-width="0.9" opacity="0.85"/>')
        # Outer outline
        svg.append(f'<polygon points="{pts([TL, BL, BR, TR])}" fill="none" stroke="#2a3540" stroke-width="0.9"/>')
        # Top edge highlight (bright catch from light)
        svg.append(f'<polyline points="{pts([TL, TR])}" fill="none" stroke="#f2f6fa" stroke-width="1" opacity="0.7"/>')

    # Webs on top of chords
    # (Already done in the loop above — sticks are in document order which matches typical
    # stacking from the XML. If web overlap looks wrong, we can sort.)

    # Member labels
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px,py = to_px(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py+4:.1f}" font-size="13" font-weight="700" text-anchor="middle" fill="#1a202c" stroke="white" stroke-width="3.5" paint-order="stroke" opacity="0.9">{s["name"]}</text>')

    # Green-capped screws at each centreline crossing (3 per node, on web centreline)
    SCREW_R_MM = 7   # 7mm dia visible cap (green protective end)
    HOLE_PITCH_MM = 17

    for n in nodes:
        cx_mm, cz_mm = n['pt']

        # Find a web that crosses here to align the 3-screw pattern with web direction
        web_stick = None
        for s in sticks:
            if s['type'] != 'Plate':
                sx, sz = s['start']; ex, ez = s['end']
                d = math.hypot(ex-sx, ez-sz)
                if d == 0: continue
                t = ((cx_mm-sx)*(ex-sx) + (cz_mm-sz)*(ez-sz)) / (d*d)
                if -0.1 <= t <= 1.1:
                    px = sx + t*(ex-sx); pz = sz + t*(ez-sz)
                    if math.hypot(cx_mm-px, cz_mm-pz) < 50:
                        web_stick = s; break

        if web_stick:
            sx, sz = web_stick['start']; ex, ez = web_stick['end']
            dx, dy = ex-sx, ez-sz
            L = math.hypot(dx, dy)
            ax_x, ax_y = dx/L, dy/L  # along web
            perp_x, perp_y = -ax_y, ax_x  # across web (in MM coords)
        else:
            ax_x, ax_y = 1, 0; perp_x, perp_y = 0, 1

        # Place 3 screws at -17, 0, +17 mm along the web's PERPENDICULAR (the spacing axis)
        # Wait - actually web hole is along the web LENGTH? Let me check the F37008 drawing.
        # In the drawing, 17.0 is the spacing between holes — drawn vertically when stick is horizontal.
        # So holes are spread ACROSS the web (perpendicular to length).
        # Screws are inserted PERPENDICULAR to the steel surface (into the page).
        # So in our top-down drawing the 3 screw caps are visible at the centreline crossing,
        # spread across the web's perpendicular direction.

        for offset_mm in [-HOLE_PITCH_MM, 0, HOLE_PITCH_MM]:
            sx_mm = cx_mm + perp_x * offset_mm
            sz_mm = cz_mm + perp_y * offset_mm
            sx_px, sy_px = to_px(sx_mm, sz_mm)
            r_px = SCREW_R_MM/2 * SCALE
            # Drop shadow
            svg.append(f'<circle cx="{sx_px+1.5:.1f}" cy="{sy_px+2:.1f}" r="{r_px+0.5:.2f}" fill="black" opacity="0.35" filter="url(#blur3)"/>')
            # Cap base (dark)
            svg.append(f'<circle cx="{sx_px:.1f}" cy="{sy_px:.1f}" r="{r_px+0.5:.2f}" fill="#365314"/>')
            # Cap green
            svg.append(f'<circle cx="{sx_px:.1f}" cy="{sy_px:.1f}" r="{r_px:.2f}" fill="url(#screw-cap)"/>')
            # Cap shine
            svg.append(f'<circle cx="{sx_px-r_px*0.3:.1f}" cy="{sy_px-r_px*0.3:.1f}" r="{r_px*0.4:.2f}" fill="url(#screw-shine)"/>')
            # Phillips head cross (subtle dark cross on cap)
            svg.append(f'<line x1="{sx_px-r_px*0.5:.1f}" y1="{sy_px:.1f}" x2="{sx_px+r_px*0.5:.1f}" y2="{sy_px:.1f}" stroke="#1a2e0a" stroke-width="0.7" opacity="0.7"/>')
            svg.append(f'<line x1="{sx_px:.1f}" y1="{sy_px-r_px*0.5:.1f}" x2="{sx_px:.1f}" y2="{sy_px+r_px*0.5:.1f}" stroke="#1a2e0a" stroke-width="0.7" opacity="0.7"/>')

    # Footer caption
    cap_y = PAGE_H - 70
    svg.append(f'<rect x="40" y="{cap_y}" width="{PAGE_W-80}" height="50" fill="white" opacity="0.92" rx="4"/>')
    svg.append(f'<text x="60" y="{cap_y+22}" font-size="13" font-weight="700" fill="#1a202c">Reading the diagram:</text>')
    svg.append(f'<text x="60" y="{cap_y+40}" font-size="11" fill="#4a5568">Bright top edge of each member = the LIP strip on the open-channel side (lips all facing same direction). Green discs = self-drilling screws (visible cap, like the photo). Real concrete-floor background.</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# RUN
print('Real-assembly photoreal truss...')
truss_path = os.path.join(OUT_DIR, 'real_assembly_truss.svg')
open(truss_path, 'w', encoding='utf-8').write(render('TN2-1'))
print(f'  Wrote {truss_path}')

# Index
idx = '''<!DOCTYPE html><html><head><title>Real assembly truss</title>
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
<h1>Real assembly photoreal — matched to your photo</h1>
<p class="sub">Galv steel tone, all lips facing same direction, green-capped screws at every junction, workshop concrete floor background.</p>
<div class="card"><div class="card-head"><div><h2>Truss frame TN2-1 - real assembly view</h2><div style="font-size:12px;color:#4a5568">Matches the photographed truss · 3 green screws per junction · 14 nodes</div></div><a href="real_assembly_truss.svg" target="_blank">open standalone &uarr;</a></div><iframe src="real_assembly_truss.svg"></iframe></div>
</body></html>'''
idx_path = os.path.join(OUT_DIR, 'REAL_ASSEMBLY.html')
open(idx_path, 'w', encoding='utf-8').write(idx)
print(f'  Wrote {idx_path}')
