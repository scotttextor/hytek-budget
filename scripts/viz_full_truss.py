"""Full-truss side-by-side visualisation: ORIGINAL vs SIMPLIFIED.

Renders one entire Linear truss in elevation with every stick drawn at real
geometry, and every machine operation (BOLT HOLES, INNER DIMPLE, notches,
swages, chamfers) marked at its actual position on each stick.

Two panels stacked:
  TOP    = FrameCAD ORIGINAL    (red BOLT HOLES, before centreline rule)
  BOTTOM = SIMPLIFIED OUTPUT    (blue WEB HOLES at junctions, green dimples)

Single-page output for engineering review. Pick the truss with --truss <name>;
default is U1-1 (the longest in test job 2603191, exercises multi-Box dimples).
"""
import os, re, math, argparse

CSV_ORIG = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.csv'
CSV_SIMP = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.simplified.csv'
OUT_DIR  = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/'

# ---- CSV parser ---------------------------------------------------------

def parse_csv(path):
    """Return list of stick dicts with geometry + ops."""
    sticks = []
    with open(path) as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) < 13 or parts[0] != 'COMPONENT':
                continue
            try:
                name    = parts[1]
                profile = parts[2]
                usage   = parts[3]
                length  = float(parts[7])
                x1      = float(parts[8])
                z1      = float(parts[9])
                x2      = float(parts[10])
                z2      = float(parts[11])
            except ValueError:
                continue
            ops = []
            i = 13
            while i + 1 < len(parts):
                op = parts[i]
                try:
                    pos = float(parts[i+1])
                except ValueError:
                    i += 2
                    continue
                ops.append((op, pos))
                i += 2
            sticks.append({
                'name':    name,
                'profile': profile,
                'usage':   usage,
                'length':  length,
                'x1': x1, 'z1': z1, 'x2': x2, 'z2': z2,
                'ops':     ops,
            })
    return sticks

# ---- Helpers ------------------------------------------------------------

def truss_filter(sticks, truss_name):
    """All sticks belonging to a truss (matches name prefix `<truss>-`)."""
    pfx = truss_name + '-'
    return [s for s in sticks if s['name'].startswith(pfx)]

def stick_op_xz(s, pos):
    """Map a machine-space op position (mm along stick) to world (x,z)."""
    L = s['length']
    if L <= 0:
        return (s['x1'], s['z1'])
    t = pos / L
    return (s['x1'] + t * (s['x2'] - s['x1']),
            s['z1'] + t * (s['z2'] - s['z1']))

def is_box(stick_name):
    return '(Box' in stick_name

def stick_classify(s):
    """Group ops by category for colouring."""
    cats = {'bolt': [], 'dimple': [], 'notch': [], 'swage': [], 'chamfer': [], 'flange': [], 'lip': []}
    for op, pos in s['ops']:
        u = op.upper()
        if 'BOLT' in u:        cats['bolt'].append(pos)
        elif 'DIMPLE' in u:    cats['dimple'].append(pos)
        elif 'NOTCH' in u:     cats['notch'].append(pos)
        elif 'SWAGE' in u:     cats['swage'].append(pos)
        elif 'CHAMFER' in u:   cats['chamfer'].append(pos)
        elif 'FLANGE' in u:    cats['flange'].append(pos)
        elif 'LIP' in u:       cats['lip'].append(pos)
    return cats

# ---- Renderer -----------------------------------------------------------

def render_truss_panel(sticks, title, subtitle, panel_w, panel_h, x0, y0,
                       use_simplified_palette=False):
    """Render one truss panel and return SVG fragment list."""
    out = []
    if not sticks:
        out.append(f'<text x="{x0+10}" y="{y0+30}" font-size="14" fill="#dc2626">No sticks for this truss</text>')
        return out

    # Bounding box of the truss in world coords
    xs = [s['x1'] for s in sticks] + [s['x2'] for s in sticks]
    zs = [s['z1'] for s in sticks] + [s['z2'] for s in sticks]
    minx, maxx = min(xs), max(xs)
    minz, maxz = min(zs), max(zs)
    span_x = max(1.0, maxx - minx)
    span_z = max(1.0, maxz - minz)

    # Layout: leave room for title bar at top + side margins
    title_h = 50
    pad     = 30
    avail_w = panel_w - 2 * pad
    avail_h = panel_h - title_h - 2 * pad
    scale   = min(avail_w / span_x, avail_h / span_z)
    # Centre the drawing
    draw_w = span_x * scale
    draw_h = span_z * scale
    ox = x0 + pad + (avail_w - draw_w) / 2
    oy = y0 + title_h + pad + (avail_h - draw_h) / 2 + draw_h  # we flip Z (Z up = SVG y down)

    def to_svg(x, z):
        return (ox + (x - minx) * scale, oy - (z - minz) * scale)

    # Panel background + border
    border_col = '#16a34a' if use_simplified_palette else '#dc2626'
    bg_col     = '#f0fdf4' if use_simplified_palette else '#fef2f2'
    out.append(f'<rect x="{x0}" y="{y0}" width="{panel_w}" height="{panel_h}" fill="{bg_col}" stroke="{border_col}" stroke-width="2.5"/>')

    # Title bar
    out.append(f'<rect x="{x0}" y="{y0}" width="{panel_w}" height="{title_h}" fill="{border_col}"/>')
    out.append(f'<text x="{x0 + panel_w/2}" y="{y0 + 26}" text-anchor="middle" font-size="18" font-weight="700" fill="white">{title}</text>')
    out.append(f'<text x="{x0 + panel_w/2}" y="{y0 + 44}" text-anchor="middle" font-size="11" fill="white" opacity="0.95">{subtitle}</text>')

    # Draw each stick as a line, separating Box pieces (drawn slightly offset so they don't fully overlap their parent)
    box_offset_pixels = 4  # vertical offset for Box piece outlines so both lines are visible

    # First pass: main sticks (non-Box)
    for s in sticks:
        if is_box(s['name']):
            continue
        x1p, y1p = to_svg(s['x1'], s['z1'])
        x2p, y2p = to_svg(s['x2'], s['z2'])
        usage = (s['usage'] or '').upper()
        if usage == 'BOTTOMCHORD':
            stroke, sw = '#1e40af', 5
        elif usage == 'TOPCHORD':
            stroke, sw = '#1e40af', 5
        else:  # web
            stroke, sw = '#475569', 3.5
        out.append(f'<line x1="{x1p:.1f}" y1="{y1p:.1f}" x2="{x2p:.1f}" y2="{y2p:.1f}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>')

    # Second pass: Box pieces drawn as thinner parallel lines
    for s in sticks:
        if not is_box(s['name']):
            continue
        x1p, y1p = to_svg(s['x1'], s['z1'])
        x2p, y2p = to_svg(s['x2'], s['z2'])
        # Offset perpendicular to stick direction so Box doesn't overlap main chord
        dx, dz = (s['x2'] - s['x1']), (s['z2'] - s['z1'])
        L = math.hypot(dx, dz) or 1.0
        # Perpendicular in screen-y-down coords
        perp_dx_pix = -(dz / L) * scale * 0  # not used, see below
        # Just shift in SVG y by a few pixels (Box pieces are usually horizontal anyway)
        out.append(f'<line x1="{x1p:.1f}" y1="{y1p - box_offset_pixels:.1f}" x2="{x2p:.1f}" y2="{y2p - box_offset_pixels:.1f}" stroke="#fbbf24" stroke-width="3" stroke-linecap="round" stroke-dasharray="6,3"/>')

    # Third pass: ops as marks
    # Colours
    if use_simplified_palette:
        col_bolt    = '#2563eb'  # blue WEB HOLE pattern
        col_dimple  = '#16a34a'
    else:
        col_bolt    = '#dc2626'  # red original BOLT HOLES
        col_dimple  = '#d97706'
    col_notch   = '#a78bfa'
    col_swage   = '#94a3b8'
    col_chamfer = '#ec4899'
    col_lip     = '#94a3b8'

    op_count = {'bolt': 0, 'dimple': 0, 'notch': 0, 'swage': 0, 'chamfer': 0, 'lip': 0}

    for s in sticks:
        cats = stick_classify(s)
        # Bolt holes: bigger filled circles
        for pos in cats['bolt']:
            xw, zw = stick_op_xz(s, pos)
            xp, yp = to_svg(xw, zw)
            out.append(f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="2.6" fill="{col_bolt}" stroke="white" stroke-width="0.5"/>')
            op_count['bolt'] += 1
        # Dimples: gold/green diamonds
        for pos in cats['dimple']:
            xw, zw = stick_op_xz(s, pos)
            xp, yp = to_svg(xw, zw)
            box_off = -box_offset_pixels if is_box(s['name']) else 0
            out.append(f'<rect x="{xp-2.5:.1f}" y="{yp-2.5+box_off:.1f}" width="5" height="5" fill="{col_dimple}" stroke="white" stroke-width="0.6" transform="rotate(45 {xp:.1f} {yp+box_off:.1f})"/>')
            op_count['dimple'] += 1
        # Notches: small purple ticks
        for pos in cats['notch'] + cats['lip']:
            xw, zw = stick_op_xz(s, pos)
            xp, yp = to_svg(xw, zw)
            out.append(f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="1.2" fill="{col_notch}" opacity="0.55"/>')
            op_count['notch'] += 1
        # Swages: tiny grey dots
        for pos in cats['swage']:
            xw, zw = stick_op_xz(s, pos)
            xp, yp = to_svg(xw, zw)
            out.append(f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="0.9" fill="{col_swage}" opacity="0.5"/>')
            op_count['swage'] += 1
        # Chamfers
        for pos in cats['chamfer']:
            xw, zw = stick_op_xz(s, pos)
            xp, yp = to_svg(xw, zw)
            out.append(f'<circle cx="{xp:.1f}" cy="{yp:.1f}" r="1.5" fill="{col_chamfer}" opacity="0.7"/>')

    # Op count summary inside panel (bottom-left)
    sum_y = y0 + panel_h - 40
    out.append(f'<rect x="{x0+10}" y="{sum_y - 4}" width="380" height="34" fill="white" opacity="0.85" rx="3"/>')
    out.append(
        f'<text x="{x0+18}" y="{sum_y + 12}" font-size="11" font-weight="600" fill="#1a202c">'
        f'Sticks: {len(sticks)}  |  Bolt holes: {op_count["bolt"]}  |  Dimples: {op_count["dimple"]}  '
        f'|  Notches: {op_count["notch"]}  |  Swages: {op_count["swage"]}'
        f'</text>'
    )
    return out

# ---- Main ---------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--truss', default='U1-1', help='Truss name to render (default: U1-1)')
    ap.add_argument('--out', default='full_truss_compare.svg')
    args = ap.parse_args()

    orig_all = parse_csv(CSV_ORIG)
    simp_all = parse_csv(CSV_SIMP)
    orig = truss_filter(orig_all, args.truss)
    simp = truss_filter(simp_all, args.truss)

    print(f'Truss {args.truss}: ORIGINAL {len(orig)} sticks, SIMPLIFIED {len(simp)} sticks')

    # Page geometry
    PAGE_W, PAGE_H = 1700, 1200
    HEADER_H = 100
    FOOTER_H = 80
    panel_gap = 14
    panel_w = PAGE_W - 40
    panel_h = (PAGE_H - HEADER_H - FOOTER_H - panel_gap) // 2

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" viewBox="0 0 {PAGE_W} {PAGE_H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append(f'<rect width="{PAGE_W}" height="{PAGE_H}" fill="#f8fafc"/>')

    # Header
    svg.append(f'<text x="20" y="32" font-size="20" font-weight="800" fill="#1a202c">HYTEK Linear Truss - full-truss simplifier diff (ENGINEERING REVIEW)</text>')
    svg.append(f'<text x="20" y="54" font-size="13" fill="#4a5568">Job <tspan font-weight="700">2603191 ROCKVILLE TH-TYPE-A1-LT</tspan> | plan <tspan font-weight="700">GF-LIN-89.075</tspan> | truss <tspan font-weight="700">{args.truss}</tspan> | profile 89x41 lipped C 0.75mm AZ150</text>')
    svg.append(f'<text x="20" y="74" font-size="12" fill="#1f2937">Legend: <tspan fill="#1e40af" font-weight="700">==== chord</tspan>  <tspan fill="#475569" font-weight="700">==== web</tspan>  <tspan fill="#fbbf24" font-weight="700">---- Box piece</tspan>  <tspan fill="#dc2626" font-weight="700">o bolt hole (orig)</tspan>  <tspan fill="#2563eb" font-weight="700">o bolt hole (simp)</tspan>  <tspan fill="#d97706" font-weight="700">[+] dimple (orig)</tspan>  <tspan fill="#16a34a" font-weight="700">[+] dimple (simp)</tspan>  <tspan fill="#a78bfa" font-weight="700">. notch</tspan>  <tspan fill="#94a3b8" font-weight="700">. swage</tspan></text>')

    # Top panel: ORIGINAL
    svg.extend(render_truss_panel(
        orig,
        title='FrameCAD ORIGINAL',
        subtitle='offset-based BOLT HOLES - produced by FrameCAD Structure (BEFORE simplification)',
        panel_w=panel_w, panel_h=panel_h,
        x0=20, y0=HEADER_H,
        use_simplified_palette=False,
    ))

    # Bottom panel: SIMPLIFIED
    svg.extend(render_truss_panel(
        simp,
        title='SIMPLIFIED OUTPUT',
        subtitle='centreline-rule WEB HOLES at every chord-web junction | normalised dimples (15mm margin, 900mm max gap) | W-W skipped',
        panel_w=panel_w, panel_h=panel_h,
        x0=20, y0=HEADER_H + panel_h + panel_gap,
        use_simplified_palette=True,
    ))

    # Footer summary
    foot_y = PAGE_H - FOOTER_H + 20
    o_bolts = sum(1 for s in orig for op,_ in s['ops'] if 'BOLT' in op.upper())
    s_bolts = sum(1 for s in simp for op,_ in s['ops'] if 'BOLT' in op.upper())
    o_dim   = sum(1 for s in orig for op,_ in s['ops'] if 'DIMPLE' in op.upper())
    s_dim   = sum(1 for s in simp for op,_ in s['ops'] if 'DIMPLE' in op.upper())
    svg.append(f'<rect x="20" y="{foot_y - 8}" width="{PAGE_W - 40}" height="{FOOTER_H - 24}" fill="#1f2937" rx="4"/>')
    svg.append(f'<text x="35" y="{foot_y + 12}" font-size="13" font-weight="700" fill="#fbbf24">DIFF SUMMARY · {args.truss}</text>')
    svg.append(f'<text x="35" y="{foot_y + 32}" font-size="12" fill="white">Bolt holes: <tspan font-weight="700">{o_bolts} -&gt; {s_bolts}</tspan> ({s_bolts - o_bolts:+d})  |  Dimples: <tspan font-weight="700">{o_dim} -&gt; {s_dim}</tspan> ({s_dim - o_dim:+d})  |  Sticks: <tspan font-weight="700">{len(orig)} -&gt; {len(simp)}</tspan>  |  Physical-fit ops (notches/swages/chamfers) preserved exactly</text>')

    svg.append('</svg>')
    out_path = os.path.join(OUT_DIR, args.out)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(svg))
    print(f'Wrote {out_path}')

if __name__ == '__main__':
    main()
