"""HYTEK U4-1 workshop drawing — inline stick-by-stick layout with every
machine operation visible at its real position. The drawing an operator
would use to verify what comes off the rollformer.

Each row = one stick from the simplified CSV. Stick drawn at scale,
every op marked with its colour-coded symbol AT THE EXACT machine position.
Op-position numbers printed alongside so you can compare to the CSV.

Output: HYTEK_U4-1_workshop.svg on Desktop. Drawing is the SIMPLIFIED state
(centreline-rule bolt holes, 15/1200 dimples) — what gets cut on the F300i
when 'Simplify linear trusses' is ticked.
"""
import os, math

# Use SIMPLIFIED CSV — these are the positions that get cut on the rollformer
CSV = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.simplified.csv'
DESKTOP = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop'
TRUSS = 'U4-1'
OUT = os.path.join(DESKTOP, f'HYTEK_{TRUSS}_workshop.svg')

# ---------- Op classification ----------
OP_COLORS = {
    'BOLT HOLES':       ('#dc2626', 'BOLT'),
    'WEB HOLES':        ('#dc2626', 'BOLT'),
    'INNER DIMPLE':     ('#f59e0b', 'DIMP'),
    'SWAGE':            ('#94a3b8', 'SWAG'),
    'LIP NOTCH':        ('#a78bfa', 'LIPN'),
    'LEFT LEG NOTCH':   ('#06b6d4', 'LLG'),
    'RIGHT LEG NOTCH':  ('#0ea5e9', 'RLG'),
    'TRUSS CHAMFER':    ('#ec4899', 'CHFR'),
    'LEFT FLANGE':      ('#8b5cf6', 'LFLG'),
    'RIGHT FLANGE':     ('#8b5cf6', 'RFLG'),
    'LEFT PARTIAL FLANGE':  ('#7c3aed', 'LPF'),
    'RIGHT PARTIAL FLANGE': ('#7c3aed', 'RPF'),
    'SCREW HOLES':      ('#16a34a', 'SCRW'),
    'INNER NOTCH':      ('#84cc16', 'INTC'),
    'INNER SERVICE':    ('#65a30d', 'SVC'),
    'CHAMFER':          ('#ec4899', 'CHFR'),
}

# ---------- Parse CSV ----------
sticks = []
with open(CSV) as f:
    for line in f:
        parts = [p.strip() for p in line.strip().split(',')]
        if len(parts) < 13 or parts[0] != 'COMPONENT': continue
        name = parts[1]
        if not name.startswith(f'{TRUSS}-'): continue
        try:
            profile, usage = parts[2], parts[3]
            length = float(parts[7])
        except ValueError:
            continue
        ops = []
        i = 13
        while i + 1 < len(parts):
            op = parts[i]
            try: pos = float(parts[i+1])
            except ValueError: i += 2; continue
            ops.append((op, pos))
            i += 2
        sticks.append({'name': name, 'profile': profile, 'usage': usage,
                       'length': length, 'ops': ops})

# Sort: chords first (top→bottom by usage), then webs by name, then box pieces
def sort_key(s):
    u = (s['usage'] or '').upper()
    if 'CHORD' in u and 'TOP' in u:    g = 0
    elif 'CHORD' in u and 'BOTTOM' in u: g = 2
    elif 'CHORD' in u:                 g = 1
    elif 'WEB' in u:                   g = 3
    else:                              g = 4
    is_box = '(Box' in s['name']
    return (g, is_box, s['name'])
sticks.sort(key=sort_key)

# ---------- Page geometry ----------
ROW_H = 105            # per stick row
HEADER_H = 100
FOOTER_H = 130
LEFT_LBL_W = 220       # left label column (stick name + usage)
RIGHT_LBL_W = 110      # right label column (length)
PAD_X = 30
PAD_Y = 12
W = 1700
BAR_W = W - 2*PAD_X - LEFT_LBL_W - RIGHT_LBL_W
H = HEADER_H + ROW_H * len(sticks) + FOOTER_H

max_len = max(s['length'] for s in sticks)
SCALE = BAR_W / max_len  # px per mm — same scale for every stick

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')

# Defs
svg.append('''<defs>
  <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#e2e8f0"/><stop offset="100%" stop-color="#94a3b8"/>
  </linearGradient>
  <marker id="arrR" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
    <path d="M0,0 L5,3 L0,6 z" fill="#64748b"/>
  </marker>
</defs>''')
svg.append(f'<rect width="{W}" height="{H}" fill="#f8fafc"/>')

# Header
svg.append(f'<rect x="0" y="0" width="{W}" height="{HEADER_H}" fill="#231F20"/>')
svg.append(f'<rect x="0" y="0" width="8" height="{HEADER_H}" fill="#FFCB05"/>')
svg.append(f'<text x="30" y="36" font-size="22" font-weight="800" fill="#FFCB05">HYTEK Workshop Drawing — Truss {TRUSS}</text>')
svg.append(f'<text x="30" y="58" font-size="13" fill="white" opacity="0.9">Job 2603191 ROCKVILLE TH-TYPE-A1-LT  |  Plan GF-LIN-89.075  |  Profile 89x41 LC 0.75mm AZ150  |  {len(sticks)} sticks  |  3 fasteners per joint</text>')
svg.append(f'<text x="30" y="78" font-size="11" fill="#FFCB05" opacity="0.85">SIMPLIFIED state - bolt holes follow centreline-intersection rule, dimples follow 15mm/1200mm rule. This is what gets cut on the F300i.</text>')

# Scale bar (top-right)
sb_x = W - PAD_X - 200
sb_y = 70
sb_len_mm = 1000
sb_len_px = sb_len_mm * SCALE
svg.append(f'<line x1="{sb_x}" y1="{sb_y}" x2="{sb_x + sb_len_px}" y2="{sb_y}" stroke="white" stroke-width="2"/>')
svg.append(f'<line x1="{sb_x}" y1="{sb_y - 4}" x2="{sb_x}" y2="{sb_y + 4}" stroke="white" stroke-width="2"/>')
svg.append(f'<line x1="{sb_x + sb_len_px}" y1="{sb_y - 4}" x2="{sb_x + sb_len_px}" y2="{sb_y + 4}" stroke="white" stroke-width="2"/>')
svg.append(f'<text x="{sb_x + sb_len_px/2}" y="{sb_y - 6}" text-anchor="middle" font-size="10" font-weight="700" fill="white">scale: 1000mm</text>')

# ---------- Per-stick rows ----------
y = HEADER_H + 10
for s in sticks:
    bar_x = PAD_X + LEFT_LBL_W
    bar_y = y + 35
    bar_h = 22
    stick_w = s['length'] * SCALE
    short_name = s['name'].replace(f'{TRUSS}-', '')
    is_box = '(Box' in s['name']
    usage = (s['usage'] or '').upper()

    # Row background (alternating)
    if (sticks.index(s) % 2) == 0:
        svg.append(f'<rect x="0" y="{y}" width="{W}" height="{ROW_H}" fill="#ffffff"/>')
    else:
        svg.append(f'<rect x="0" y="{y}" width="{W}" height="{ROW_H}" fill="#f1f5f9"/>')

    # Left label
    svg.append(f'<text x="{PAD_X + 8}" y="{y + 28}" font-size="14" font-weight="800" fill="#1a202c" font-family="Consolas, monospace">{short_name}</text>')
    usage_label = usage.replace('CHORD', ' Chord').replace('TOP ', 'Top').replace('BOTTOM ', 'Bot')
    if is_box:
        usage_label = 'Box piece'
    svg.append(f'<text x="{PAD_X + 8}" y="{y + 48}" font-size="10" fill="#475569">{usage_label}</text>')
    svg.append(f'<text x="{PAD_X + 8}" y="{y + 64}" font-size="9" fill="#94a3b8">{s["profile"]}</text>')
    n_ops_tot = len(s['ops'])
    n_bolt = sum(1 for op,_ in s['ops'] if 'BOLT' in op.upper())
    svg.append(f'<text x="{PAD_X + 8}" y="{y + 80}" font-size="9" fill="#64748b">{n_ops_tot} ops / {n_bolt} bolts</text>')

    # Stick bar (steel)
    svg.append(f'<rect x="{bar_x}" y="{bar_y}" width="{stick_w}" height="{bar_h}" '
               f'fill="url(#steel)" stroke="#1e293b" stroke-width="1.5"/>')
    # End markers
    svg.append(f'<line x1="{bar_x}" y1="{bar_y - 4}" x2="{bar_x}" y2="{bar_y + bar_h + 4}" stroke="#1e293b" stroke-width="2"/>')
    svg.append(f'<line x1="{bar_x + stick_w}" y1="{bar_y - 4}" x2="{bar_x + stick_w}" y2="{bar_y + bar_h + 4}" stroke="#1e293b" stroke-width="2"/>')
    # Position 0 label
    svg.append(f'<text x="{bar_x}" y="{bar_y - 8}" text-anchor="middle" font-size="9" fill="#64748b">0</text>')

    # Group bolt holes by world position on this stick — actually, each bolt
    # entry IS one rollformer fire = 3 holes. Mark each one with a clear "BOLT(3)"
    # symbol so the operator sees "this is one cluster of 3, fired once".
    # Sort ops so we can lay text labels without overlap.
    sorted_ops = sorted(s['ops'], key=lambda x: x[1])

    # Bolt-hole positions get a vertical 3-dot cluster ABOVE the bar
    # All other ops get a colored mark ON the bar
    cluster_dy = 15  # vertical offset of cluster above bar
    PITCH_PX = max(2.4, 17 * SCALE)  # 17mm pitch in px (capped for tiny sticks)

    label_positions = []  # for collision detection
    for op, pos in sorted_ops:
        col, code = OP_COLORS.get(op, ('#888888', op[:4]))
        op_x = bar_x + pos * SCALE

        if 'BOLT' in op.upper() and 'HOLE' in op.upper():
            # Draw 3-hole cluster vertically (perpendicular to stick length)
            # Centred ON the stick at position
            cy_centre = bar_y + bar_h/2
            for k in (-1, 0, 1):
                hx = op_x
                hy = cy_centre + k * PITCH_PX
                svg.append(f'<circle cx="{hx:.2f}" cy="{hy:.2f}" r="2.0" fill="{col}" stroke="white" stroke-width="0.5"/>')
            # Halo to show it's one fire
            svg.append(f'<rect x="{op_x - 4:.1f}" y="{cy_centre - PITCH_PX*1.5 - 2:.1f}" '
                       f'width="8" height="{PITCH_PX*3 + 4:.1f}" fill="none" stroke="{col}" stroke-width="0.5" opacity="0.4"/>')
            # Position label below bar
            svg.append(f'<text x="{op_x:.1f}" y="{bar_y + bar_h + 14}" text-anchor="middle" font-size="8" fill="{col}" font-weight="700">{pos:.0f}</text>')
        elif op == 'INNER DIMPLE':
            # Diamond on the bar
            svg.append(f'<rect x="{op_x-3.5:.1f}" y="{bar_y + bar_h/2 - 3.5:.1f}" width="7" height="7" '
                       f'fill="{col}" stroke="white" stroke-width="0.6" '
                       f'transform="rotate(45 {op_x:.1f} {bar_y + bar_h/2:.1f})"/>')
            svg.append(f'<text x="{op_x:.1f}" y="{bar_y + bar_h + 14}" text-anchor="middle" font-size="8" fill="{col}" font-weight="700">{pos:.0f}</text>')
        elif op == 'SWAGE':
            # Light grey tick on bar
            svg.append(f'<line x1="{op_x:.1f}" y1="{bar_y + 2:.1f}" x2="{op_x:.1f}" y2="{bar_y + bar_h - 2:.1f}" stroke="{col}" stroke-width="1.0" opacity="0.65"/>')
        elif 'NOTCH' in op:
            # Triangle pointing into the stick
            tri_y = bar_y + bar_h - 1
            svg.append(f'<polygon points="{op_x-3.5},{tri_y} {op_x+3.5},{tri_y} {op_x},{tri_y - 6}" fill="{col}" opacity="0.9"/>')
        elif op == 'TRUSS CHAMFER' or op == 'CHAMFER':
            # Bigger triangle above bar
            tri_y = bar_y - 1
            svg.append(f'<polygon points="{op_x-4.5},{tri_y} {op_x+4.5},{tri_y} {op_x},{tri_y + 7}" fill="{col}"/>')
            svg.append(f'<text x="{op_x:.1f}" y="{bar_y - 10}" text-anchor="middle" font-size="8" fill="{col}" font-weight="700">{pos:.0f}</text>')
        elif 'FLANGE' in op:
            svg.append(f'<rect x="{op_x-2.2:.1f}" y="{bar_y + bar_h/2 - 2.2:.1f}" width="4.4" height="4.4" fill="{col}"/>')
        else:
            svg.append(f'<circle cx="{op_x:.1f}" cy="{bar_y + bar_h/2:.1f}" r="1.6" fill="{col}"/>')

    # Right label — length
    svg.append(f'<text x="{bar_x + stick_w + 10}" y="{bar_y + bar_h/2 + 4}" font-size="11" font-weight="700" fill="#1a202c">{s["length"]:.1f}mm</text>')

    # Row separator line
    svg.append(f'<line x1="0" y1="{y + ROW_H}" x2="{W}" y2="{y + ROW_H}" stroke="#cbd5e1" stroke-width="0.5"/>')

    y += ROW_H

# ---------- Legend / footer ----------
fy = y + 10
svg.append(f'<rect x="0" y="{fy - 5}" width="{W}" height="{FOOTER_H}" fill="#1f2937"/>')
svg.append(f'<text x="{PAD_X}" y="{fy + 18}" font-size="13" font-weight="700" fill="#FFCB05">LEGEND — every operation symbol</text>')

legend_items = [
    ('●●●', '#dc2626', 'BOLT HOLES', '3 holes Ø3.8mm @ 17mm pitch — one rollformer fire = web-to-chord screw connection'),
    ('◆',   '#f59e0b', 'INNER DIMPLE', 'Press-formed snap point — 15mm from end, 1200mm max gap between'),
    ('|',   '#94a3b8', 'SWAGE',         'Linear flange embossing — anti-buckling stiffener'),
    ('▲',   '#a78bfa', 'LIP NOTCH',     'Cuts the 11mm lip return so adjacent sticks lie flat'),
    ('▲',   '#06b6d4', 'LEG NOTCH',     'Trims flange-heel for stick-on-stick fit (left/right variants)'),
    ('▼',   '#ec4899', 'TRUSS CHAMFER', 'Diagonal end cut for steep-angle joints'),
    ('■',   '#8b5cf6', 'FLANGE',        'Flange bend point (left/right, full or partial)'),
]
lcol_x = PAD_X
lcol_y = fy + 38
for i, (sym, col, name, desc) in enumerate(legend_items):
    if i == 4:
        # Wrap to second line
        lcol_x = PAD_X
        lcol_y += 28
    svg.append(f'<text x="{lcol_x}" y="{lcol_y}" font-size="14" font-weight="700" fill="{col}">{sym}</text>')
    svg.append(f'<text x="{lcol_x + 22}" y="{lcol_y}" font-size="10" font-weight="700" fill="white">{name}</text>')
    svg.append(f'<text x="{lcol_x + 22}" y="{lcol_y + 12}" font-size="9" fill="#cbd5e1">{desc}</text>')
    lcol_x += 240 if i < 4 else 360

# Total ops summary
svg.append(f'<text x="{W - PAD_X}" y="{fy + 18}" text-anchor="end" font-size="11" fill="#FFCB05" font-weight="700">VERIFICATION</text>')
total_bolts = sum(1 for s in sticks for op,_ in s['ops'] if 'BOLT' in op.upper())
total_dimples = sum(1 for s in sticks for op,_ in s['ops'] if 'DIMPLE' in op.upper())
total_ops = sum(len(s['ops']) for s in sticks)
svg.append(f'<text x="{W - PAD_X}" y="{fy + 38}" text-anchor="end" font-size="10" fill="white">{total_ops} total ops on this truss</text>')
svg.append(f'<text x="{W - PAD_X}" y="{fy + 54}" text-anchor="end" font-size="10" fill="white">{total_bolts} bolt-hole fires (= {total_bolts*3} physical holes)</text>')
svg.append(f'<text x="{W - PAD_X}" y="{fy + 70}" text-anchor="end" font-size="10" fill="white">{total_dimples} inner dimples</text>')
svg.append(f'<text x="{W - PAD_X}" y="{fy + 90}" text-anchor="end" font-size="9" fill="#94a3b8">Numbers above each symbol = mm offset along stick</text>')
svg.append(f'<text x="{W - PAD_X}" y="{fy + 102}" text-anchor="end" font-size="9" fill="#94a3b8">from the LEFT cut end. Cross-check vs CSV.</text>')

svg.append('</svg>')
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(svg))
print(f'Wrote {OUT}')
print(f'Page size: {W} x {H}')
print(f'Sticks: {len(sticks)} | Total ops: {total_ops} | Bolts: {total_bolts} | Dimples: {total_dimples}')
