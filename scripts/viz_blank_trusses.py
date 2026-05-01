"""Generate clean truss outlines with NO bolts, NO centreline-crossing dots.

The user will mark bolt positions on these themselves to show what they want.

Renders four different truss frames at print-size for marking up:
  TN1-1 — small hip truss (8 sticks)
  TN2-1 — complex truss with collar tie (10 sticks)
  TN1-3 — mid-position hip truss (different web pattern from TN1-1)
  TN2-3 — mid-position complex truss
"""
import re, math

XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075.xml'
OUT_DIR = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/'

text = open(XML).read()

def parse_frame(frame_name):
    s = text.find(f'<frame name="{frame_name}"')
    if s < 0: return None
    e = text.find('</frame>', s) + len('</frame>')
    frame = text[s:e]
    sticks = []
    for m in re.finditer(r'<stick name="([^"]+)" type="([^"]+)"[^>]*>\s*<start>([^<]+)</start>\s*<end>([^<]+)</end>', frame):
        name, typ, st, en = m.groups()
        sx,sy,sz = [float(v) for v in st.strip().split(',')]
        ex,ey,ez = [float(v) for v in en.strip().split(',')]
        sticks.append({'name':name,'type':typ,'start':(sx,sz),'end':(ex,ez)})
    return sticks

WIDTH_MM = 89.0

def render_clean(sticks, frame_name, description):
    if not sticks:
        return None
    all_x = [c for s in sticks for c in (s['start'][0], s['end'][0])]
    all_z = [c for s in sticks for c in (s['start'][1], s['end'][1])]
    xmin, xmax = min(all_x)-300, max(all_x)+300
    zmin, zmax = min(all_z)-300, max(all_z)+300
    mm_w = xmax-xmin; mm_h = zmax-zmin

    # Target page size — landscape, large for marking up
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

    # Title block
    svg.append(f'<text x="40" y="44" font-size="26" font-weight="700" fill="#1a202c">Truss frame {frame_name} — mark up where you want bolts</text>')
    svg.append(f'<text x="40" y="72" font-size="15" fill="#4a5568">{description}</text>')
    svg.append(f'<text x="40" y="98" font-size="13" fill="#374151">{len(sticks)} members  ·  blue hatched = chord plates  ·  grey hatched = web studs  ·  dashed = centrelines</text>')

    # Optional grid
    grid_step_mm = 500
    nx = int(mm_w / grid_step_mm) + 2
    nz = int(mm_h / grid_step_mm) + 2
    for i in range(nx):
        gx = xmin + i*grid_step_mm
        if gx < xmin or gx > xmax: continue
        gx_px, _ = to_px(gx, zmin)
        _, gy_top = to_px(gx, zmax)
        svg.append(f'<line x1="{gx_px:.1f}" y1="{gy_top:.1f}" x2="{gx_px:.1f}" y2="{oy+draw_h:.1f}" stroke="#f1f5f9" stroke-width="0.8"/>')
    for i in range(nz):
        gz = zmin + i*grid_step_mm
        if gz < zmin or gz > zmax: continue
        _, gy_px = to_px(xmin, gz)
        gx_left, _ = to_px(xmin, gz)
        gx_right, _ = to_px(xmax, gz)
        svg.append(f'<line x1="{gx_left:.1f}" y1="{gy_px:.1f}" x2="{gx_right:.1f}" y2="{gy_px:.1f}" stroke="#f1f5f9" stroke-width="0.8"/>')

    # Chord plates first
    for s in sticks:
        if s['type'] == 'Plate':
            svg.append(f'<polygon points="{member_polygon(s)}" fill="url(#cf)" stroke="#1d4ed8" stroke-width="1.6" opacity="0.95"/>')
    # Web studs on top
    for s in sticks:
        if s['type'] != 'Plate':
            svg.append(f'<polygon points="{member_polygon(s)}" fill="url(#wf)" stroke="#475569" stroke-width="1.4" opacity="0.85"/>')

    # Centrelines (faint dashed)
    for s in sticks:
        x1,y1 = to_px(*s['start']); x2,y2 = to_px(*s['end'])
        col = '#1d4ed8' if s['type']=='Plate' else '#334155'
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="1" stroke-dasharray="5 3" opacity="0.55"/>')

    # Member labels
    for s in sticks:
        mx = (s['start'][0]+s['end'][0])/2; mz = (s['start'][1]+s['end'][1])/2
        px,py = to_px(mx, mz)
        svg.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="14" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="white" stroke-width="3.5" paint-order="stroke">{s["name"]}</text>')

    # Footer instructions
    fy = PAGE_H - 35
    svg.append(f'<rect x="40" y="{fy-12}" width="{PAGE_W-80}" height="38" fill="#fef3c7" stroke="#d97706" rx="3"/>')
    svg.append(f'<text x="60" y="{fy+8}" font-size="13" fill="#7c2d12">Mark each bolt position with a dot or X. Mark direction/quantity if it matters. Save and send back.</text>')

    svg.append('</svg>')
    return '\n'.join(svg)

# Generate for several frames
frames_to_render = [
    ('TN1-1', 'Small hip truss — 8 members. Hip end of the building.'),
    ('TN2-1', 'Complex main truss with collar tie — 10 members at multiple angles.'),
    ('TN1-3', 'Mid-position truss — different web layout from TN1-1.'),
    ('TN2-3', 'Mid-position complex truss with collar tie.'),
]

import os
generated = []
for name, desc in frames_to_render:
    sticks = parse_frame(name)
    if not sticks:
        print(f'Frame {name} not found, skipping')
        continue
    svg = render_clean(sticks, name, desc)
    out_file = os.path.join(OUT_DIR, f'truss_blank_{name}.svg')
    open(out_file, 'w', encoding='utf-8').write(svg)
    generated.append((name, len(sticks), out_file))
    print(f'Wrote {out_file}  ({len(sticks)} sticks)')

# Build an index page just for these blanks
idx = ['<!DOCTYPE html>', '<html><head><title>Blank trusses for markup</title>',
       '<style>',
       '* { box-sizing: border-box; }',
       'body { font-family: Segoe UI, Arial, sans-serif; margin: 0; padding: 24px; background: #f1f5f9; }',
       'h1 { margin: 0 0 12px; }',
       '.sub { color: #4a5568; margin-bottom: 24px; }',
       '.card { background: white; border: 1px solid #cbd5e0; border-radius: 6px; margin-bottom: 24px; overflow: hidden; }',
       '.card-head { padding: 14px 18px; background: #fafaf8; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }',
       '.card-head h2 { margin: 0; font-size: 16px; }',
       '.card-head a { color: #2563eb; text-decoration: none; padding: 5px 12px; border: 1px solid #93c5fd; border-radius: 3px; font-size: 12px; }',
       '.card-head a:hover { background: #dbeafe; }',
       'iframe { border: 0; width: 100%; height: 880px; display: block; background: white; }',
       '</style></head><body>',
       '<h1>Blank trusses for markup</h1>',
       '<p class="sub">Open standalone, screenshot, draw on it, send back. No bolts shown — mark wherever you want them.</p>']

for name, count, path in generated:
    fname = os.path.basename(path)
    idx.append(f'<div class="card"><div class="card-head"><div><h2>{name}</h2><div style="font-size:12px;color:#4a5568">{count} members</div></div><a href="{fname}" target="_blank">open standalone ↗</a></div><iframe src="{fname}"></iframe></div>')

idx.append('</body></html>')
idx_path = os.path.join(OUT_DIR, 'BLANK_TRUSSES.html')
open(idx_path, 'w', encoding='utf-8').write('\n'.join(idx))
print(f'\nWrote index: {idx_path}')
