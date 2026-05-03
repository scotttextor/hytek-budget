"""Visualise W↔W centreline crossings and explain why they're skipped.

Renders 4 frames (TT2-1, TT3-1, U1-1, U3-1) showing:
  GREEN dots = web↔chord crossings = WEB HOLES placed here (kept)
  RED Xs   = web↔web crossings = mathematically intersect, but FrameCAD
             doesn't fasten W↔W in Linear trusses, so SKIPPED

Plus a side-explainer of why: webs don't physically touch each other on
the assembly bench — they all stack on chord webs. Their centrelines
just happen to mathematically cross in elevation view.
"""
import re, math, os

XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075 (1).xml'
OUT_DIR = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/'

text = open(XML).read()

def parse_frame(name):
    s = text.find(f'<frame name="{name}"')
    if s < 0: return None
    e = text.find('</frame>', s) + len('</frame>')
    f = text[s:e]
    sticks = []
    for sm in re.finditer(r'<stick\s+([^>]*?)>\s*<start>([^<]+)</start>\s*<end>([^<]+)</end>', f):
        attrs, st, en = sm.groups()
        def get(s, k):
            m = re.search(rf'\b{k}="([^"]*)"', s)
            return m.group(1) if m else ''
        name = get(attrs, 'name')
        usage = get(attrs, 'usage')
        sx, sy, sz = [float(v) for v in st.strip().split(',')]
        ex, ey, ez = [float(v) for v in en.strip().split(',')]
        sticks.append({'name':name, 'usage':usage, 'start':(sx,sz), 'end':(ex,ez)})
    return sticks

def line_int(s1, s2, slack=50):
    """Generous slack (50mm) to catch chord splices and end-to-end joints
    where centrelines meet at very ends of sticks."""
    x1, z1 = s1['start']; x2, z2 = s1['end']
    x3, z3 = s2['start']; x4, z4 = s2['end']
    d = (x1-x2)*(z3-z4) - (z1-z2)*(x3-x4)
    if abs(d) < 1e-9: return None
    t = ((x1-x3)*(z3-z4) - (z1-z3)*(x3-x4)) / d
    u = -((x1-x2)*(z1-z3) - (z1-z2)*(x1-x3)) / d
    L1 = math.hypot(x2-x1, z2-z1); L2 = math.hypot(x4-x3, z4-z3)
    if L1 == 0 or L2 == 0: return None
    st_ = slack/L1; su = slack/L2
    if not (-st_ <= t <= 1+st_): return None
    if not (-su <= u <= 1+su): return None
    return (x1 + t*(x2-x1), z1 + t*(z2-z1))

WIDTH_MM = 89.0

def render_frame(sticks, ox, oy, scale, name):
    """Render one truss frame at (ox, oy), return SVG fragments + crossing counts."""
    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    xmin, xmax = min(all_x)-150, max(all_x)+150
    zmin, zmax = min(all_z)-150, max(all_z)+150

    def to_px(x, z):
        return (ox + (x-xmin)*scale, oy + (zmax-z)*scale)

    def member_poly(s):
        sx, sz = s['start']; ex, ez = s['end']
        dx, dz = ex-sx, ez-sz
        L = math.hypot(dx, dz)
        if L == 0: return ''
        nx, nz = -dz/L, dx/L
        h = WIDTH_MM/2
        pts = [(sx+nx*h, sz+nz*h), (sx-nx*h, sz-nz*h), (ex-nx*h, ez-nz*h), (ex+nx*h, ez+nz*h)]
        return ' '.join(f'{a:.1f},{b:.1f}' for a,b in (to_px(*p) for p in pts))

    out = []
    # Layer order: chords FIRST (underneath), then webs ON TOP — matches real
    # assembly where webs lay on top of chord webs.
    chords = [s for s in sticks if 'chord' in s['usage'].lower()]
    webs   = [s for s in sticks if 'chord' not in s['usage'].lower()]
    for s in chords:
        out.append(f'<polygon points="{member_poly(s)}" fill="#dbeafe" stroke="#1d4ed8" stroke-width="0.8" opacity="0.85"/>')
    for s in webs:
        out.append(f'<polygon points="{member_poly(s)}" fill="#e2e8f0" stroke="#475569" stroke-width="0.9"/>')

    # Centrelines (chords first, then webs)
    for s in chords:
        x1, y1 = to_px(*s['start']); x2, y2 = to_px(*s['end'])
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#1d4ed8" stroke-width="0.5" stroke-dasharray="3 2" opacity="0.5"/>')
    for s in webs:
        x1, y1 = to_px(*s['start']); x2, y2 = to_px(*s['end'])
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#334155" stroke-width="0.5" stroke-dasharray="3 2" opacity="0.5"/>')

    # Find crossings
    web_chord_count = 0
    web_web_count = 0
    for i in range(len(sticks)):
        for j in range(i+1, len(sticks)):
            pt = line_int(sticks[i], sticks[j])
            if not pt: continue
            both_webs = (sticks[i]['usage'].lower() == 'web' and
                        sticks[j]['usage'].lower() == 'web')
            cx, cy = to_px(*pt)
            if both_webs:
                web_web_count += 1
                # Red X (skipped)
                out.append(f'<g stroke="#dc2626" stroke-width="2.5" opacity="0.9">')
                out.append(f'<line x1="{cx-7}" y1="{cy-7}" x2="{cx+7}" y2="{cy+7}"/>')
                out.append(f'<line x1="{cx-7}" y1="{cy+7}" x2="{cx+7}" y2="{cy-7}"/>')
                out.append(f'</g>')
            else:
                web_chord_count += 1
                # Green dot (kept) — bigger + bolder so it's never missed
                out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="#16a34a" stroke="#14532d" stroke-width="1.2"/>')

    # Member labels
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px, py = to_px(mx, mz)
        out.append(f'<text x="{px:.1f}" y="{py+3:.1f}" font-size="9" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="white" stroke-width="2.5" paint-order="stroke" opacity="0.9">{s["name"]}</text>')

    # Frame title
    out.insert(0, f'<text x="{ox + 10}" y="{oy + 18}" font-size="14" font-weight="700" fill="#1a202c">Frame {name} — {web_chord_count} kept · {web_web_count} W↔W skipped</text>')
    return '\n'.join(out), web_chord_count, web_web_count

# ----- BUILD -----
PAGE_W = 1900
PAGE_H = 1300
margin = 30
header_h = 130
gap = 20
panel_w = (PAGE_W - 2*margin - gap) / 2
panel_h = (PAGE_H - header_h - margin - gap) / 2

frames_to_show = ['TT2-1', 'TT3-1', 'U1-1', 'U3-1']
frame_data = []
for fn in frames_to_show:
    sticks = parse_frame(fn)
    frame_data.append((fn, sticks))

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="Segoe UI, Arial, sans-serif">')
svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="#f8fafc"/>')

# Header
svg.append(f'<text x="{margin}" y="40" font-size="22" font-weight="700" fill="#1a202c">W↔W centreline crossings — what we skip and why</text>')
svg.append(f'<text x="{margin}" y="64" font-size="13" fill="#4a5568">Two web members\' centrelines mathematically cross in elevation, but they don\'t physically touch in assembly (they\'re separate sticks stacked on chord webs).</text>')
svg.append(f'<text x="{margin}" y="84" font-size="13" fill="#4a5568">FrameCAD doesn\'t fasten W↔W in Linear trusses. Our simplifier follows the same rule — skip these crossings, keep only web↔chord and chord↔chord.</text>')

# Legend
lx = PAGE_W - 360; ly = 35
svg.append(f'<rect x="{lx}" y="{ly}" width="340" height="80" fill="white" stroke="#cbd5e0" rx="4"/>')
svg.append(f'<circle cx="{lx+20}" cy="{ly+25}" r="5" fill="#16a34a" stroke="#14532d" stroke-width="1"/>')
svg.append(f'<text x="{lx+35}" y="{ly+29}" font-size="12" fill="#1a202c"><tspan font-weight="700">GREEN</tspan> = web↔chord or chord↔chord = WEB HOLE placed</text>')
svg.append(f'<g transform="translate({lx+15},{ly+50})" stroke="#dc2626" stroke-width="2.2"><line x1="-5" y1="-5" x2="5" y2="5"/><line x1="-5" y1="5" x2="5" y2="-5"/></g>')
svg.append(f'<text x="{lx+35}" y="{ly+55}" font-size="12" fill="#1a202c"><tspan font-weight="700">RED X</tspan> = web↔web — skipped (no physical contact)</text>')
svg.append(f'<text x="{lx+15}" y="{ly+74}" font-size="10" fill="#6b7280">Both types are mathematical centreline crossings.</text>')

# 2x2 grid of frames
positions = [(margin, header_h), (margin + panel_w + gap, header_h),
             (margin, header_h + panel_h + gap), (margin + panel_w + gap, header_h + panel_h + gap)]

total_kept = 0
total_skipped = 0
for (fn, sticks), (px, py) in zip(frame_data, positions):
    if not sticks: continue
    # Compute scale to fit panel
    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    mm_w = max(all_x) - min(all_x) + 300
    mm_h = max(all_z) - min(all_z) + 300
    scale = min((panel_w - 20) / mm_w, (panel_h - 60) / mm_h)
    # Frame container
    svg.append(f'<rect x="{px}" y="{py}" width="{panel_w}" height="{panel_h}" fill="white" stroke="#cbd5e0" stroke-width="1" rx="3"/>')
    # Centre the frame inside its panel
    frag, kept, skipped = render_frame(sticks, px + 10, py + 30, scale, fn)
    svg.append(frag)
    total_kept += kept
    total_skipped += skipped

# Footer summary
fy = PAGE_H - 25
svg.append(f'<rect x="{margin}" y="{fy-15}" width="{PAGE_W - 2*margin}" height="35" fill="#f0fdf4" stroke="#16a34a" rx="3"/>')
svg.append(f'<text x="{margin + 15}" y="{fy+8}" font-size="13" fill="#14532d"><tspan font-weight="700">Across these 4 frames:</tspan> {total_kept} web↔chord crossings kept · {total_skipped} W↔W crossings skipped (correctly — no physical fastener at those points)</text>')

svg.append('</svg>')
out_path = os.path.join(OUT_DIR, 'ww_skip_explained.svg')
open(out_path, 'w', encoding='utf-8').write('\n'.join(svg))
print(f'Wrote {out_path}')
print(f'Total: {total_kept} kept, {total_skipped} W↔W skipped across 4 sample frames')
