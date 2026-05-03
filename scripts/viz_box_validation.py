"""Mock-up: what --check-boxes would output during the simplifier run,
plus a drawing-style visualization of how a boxed zone would be marked
on the factory shop drawing.

Two outputs:
  1. console_output.txt  — what the audit log looks like at run-time
  2. box_drawing_mockup.svg — what the boxed-zone callout looks like on the
     factory elevation drawing
"""
import re, math, os
from collections import defaultdict

CSV = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.csv'
OUT_DIR = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/'

# ---------- Find all box pairs in the job ----------
sticks = {}
with open(CSV) as f:
    for line in f:
        parts = [p.strip() for p in line.strip().split(',')]
        if len(parts) < 14 or parts[0] != 'COMPONENT': continue
        name = parts[1]
        length = float(parts[7])
        ops_raw = parts[13:]
        bolts, dimples = [], []
        i = 0
        while i+1 < len(ops_raw):
            try:
                pos = float(ops_raw[i+1])
                if ops_raw[i] == 'INNER DIMPLE': dimples.append(pos)
                elif ops_raw[i] == 'BOLT HOLES': bolts.append(pos)
            except: pass
            i += 2
        sticks[name] = {'length': length, 'bolts': sorted(bolts), 'dimples': sorted(dimples)}

# ---------- Build box-pair table ----------
pairs = []
for name in sticks:
    if '(Box1)' in name or '(Box2)' in name:
        main = re.sub(r' \(Box\d+\)$', '', name)
        if main in sticks:
            box_idx = re.search(r'\(Box(\d+)\)', name).group(1)
            pairs.append({
                'main_name': main,
                'box_name': name,
                'box_index': int(box_idx),
                'main_length': sticks[main]['length'],
                'box_length': sticks[name]['length'],
                'main_dimples': sticks[main]['dimples'],
                'box_dimples': sticks[name]['dimples'],
                'main_bolts': sticks[main]['bolts'],
                'box_bolts': sticks[name]['bolts'],
            })

# ---------- Validate each pair ----------
def validate(pair):
    md = pair['main_dimples']
    bd = pair['box_dimples']
    issues = []
    # Check 1: same number of dimples on each side
    if len(md) != len(bd):
        issues.append(f'dimple count mismatch ({len(md)} on main vs {len(bd)} on Box)')
    # Check 2: dimple GAPS must match (the snap-fit condition)
    if len(md) >= 2 and len(bd) >= 2:
        main_gaps = [round(md[i+1]-md[i], 1) for i in range(len(md)-1)]
        box_gaps = [round(bd[i+1]-bd[i], 1) for i in range(len(bd)-1)]
        # The gaps in the box piece (excluding the 10mm engagement margins) must match
        # corresponding gaps in the main piece
        if main_gaps[0] != box_gaps[0]:
            # Allow 5mm tolerance
            if abs(main_gaps[0] - box_gaps[0]) > 5:
                issues.append(f'dimple gap mismatch (main {main_gaps[0]}mm vs Box {box_gaps[0]}mm)')
    # Check 3: Box piece has NO bolt holes (would punch wrong layer)
    if pair['box_bolts']:
        issues.append(f'Box piece has {len(pair["box_bolts"])} BOLT HOLES (should have zero)')
    # Check 4: Engagement margin on Box (first dimple should be ~10mm from start, last ~10mm from end)
    if bd:
        margin_start = bd[0]
        margin_end = pair['box_length'] - bd[-1]
        if margin_start > 30 or margin_end > 30:
            issues.append(f'engagement margin large (start {margin_start}mm, end {margin_end}mm — typical 10mm)')
    return issues

# ---------- Mock console output ----------
lines = []
lines.append('=' * 80)
lines.append('HYTEK Linear-Truss simplifier with --check-boxes validation')
lines.append('=' * 80)
lines.append('')
lines.append('STEP 1 — 4-layer detection per frame (existing audit log):')
lines.append('-' * 80)
lines.append('  TN1-1 ... TN1-8         APPLY     all 4 layers passed')
lines.append('  TN2-1 ... TN2-6         APPLY     all 4 layers passed')
lines.append('  TT1-1 ... TT4-1         APPLY     all 4 layers passed')
lines.append('  U1-1 ... U4-1           APPLY     all 4 layers passed')
lines.append('  Applied: 22 frames, Skipped: 0')
lines.append('')
lines.append('STEP 2 — BOX VALIDATION (new):')
lines.append('-' * 80)
lines.append(f'  Detected {len(pairs)} chord+Box pairs across the job:')
lines.append('')
header = f'  {"Main stick":<20} {"Length":>9} {"Box piece":<20} {"Length":>9} {"Gap match":<14} {"Engagement":<12} Status'
lines.append(header)
lines.append('  ' + '-' * (len(header)-2))
all_pass = True
for p in sorted(pairs, key=lambda x: x['main_name']):
    issues = validate(p)
    if not p['main_dimples'] or not p['box_dimples']:
        gap_match = '(no dimples)'
    else:
        main_gap = round(p['main_dimples'][1]-p['main_dimples'][0], 1) if len(p['main_dimples']) >= 2 else 'n/a'
        box_gap = round(p['box_dimples'][1]-p['box_dimples'][0], 1) if len(p['box_dimples']) >= 2 else 'n/a'
        gap_match = f'{main_gap}={box_gap}mm' if main_gap == box_gap else f'{main_gap}vs{box_gap}'
    if p['box_dimples']:
        eng = f'{p["box_dimples"][0]:.0f}mm/{p["box_length"] - p["box_dimples"][-1]:.0f}mm'
    else:
        eng = 'n/a'
    if issues:
        status = 'FAIL: ' + '; '.join(issues)
        all_pass = False
    else:
        status = 'CLIP OK'
    lines.append(f'  {p["main_name"]:<20} {p["main_length"]:>9.1f} {p["box_name"]:<20} {p["box_length"]:>9.1f} {gap_match:<14} {eng:<12} {status}')

lines.append('')
lines.append('-' * 80)
if all_pass:
    lines.append(f'  ALL {len(pairs)} BOX PAIRS VALID. No structural concerns.')
else:
    lines.append(f'  WARNING: {sum(1 for p in pairs if validate(p))} box pairs have issues — review above.')
lines.append('')
lines.append('STEP 3 — CSV/RFY simplification (existing):')
lines.append('-' * 80)
lines.append('  Original BOLT HOLES: 1462')
lines.append('  Simplified:           826')
lines.append('  Reduction:           -636 (-43.5%)')
lines.append('')
lines.append('Output:')
lines.append('  C:\\...\\2603191-GF-LIN-89.075.simplified.csv')
lines.append('  C:\\...\\2603191-GF-LIN-89.075.simplified.rfy')
lines.append('')

console = '\n'.join(lines)
open(os.path.join(OUT_DIR, 'box_validation_console.txt'), 'w', encoding='utf-8').write(console)
print('Console mockup:')
print(console)

# ---------- Drawing mockup: U3-1 B1 with boxed zone highlighted ----------
# Real U3-1 data
B1_LEN = 8164.8
B1_DIMPLES = [4249.9, 4529.9]
BOX_LEN = 300.0
BOX_DIMPLES = [10.0, 290.0]
WEB_CROSSINGS = [44.5, 252.66, 2028.8, 3803.2, 3943.52, 4067.62, 4389.9, 4558.27, 5854.4, 7141.9, 7319.79, 7865.72, 8088.11]

W = 1900
H = 700
margin = 50
draw_w = W - 2*margin
mm_to_px = draw_w / B1_LEN

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
svg.append('<defs>')
svg.append('<pattern id="box-zone" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)"><rect width="8" height="8" fill="#fef3c7"/><line x1="0" y1="0" x2="0" y2="8" stroke="#d97706" stroke-width="1"/></pattern>')
svg.append('<pattern id="steel" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)"><rect width="6" height="6" fill="#dbeafe"/><line x1="0" y1="0" x2="0" y2="6" stroke="#93c5fd" stroke-width="0.6"/></pattern>')
svg.append('</defs>')
svg.append(f'<rect width="{W}" height="{H}" fill="#f8fafc"/>')

svg.append(f'<text x="{margin}" y="40" font-size="20" font-weight="700" fill="#1a202c">U3-1 / B1 — boxed-zone callout (factory shop drawing mockup)</text>')
svg.append(f'<text x="{margin}" y="62" font-size="13" fill="#4a5568">8164.8mm bottom chord with B1(Box1) clip-on at the high-shear web cluster (W14 area)</text>')

# Main chord B1
chord_y = 220
chord_h = 36
chord_x0 = margin
chord_x1 = margin + B1_LEN * mm_to_px
svg.append(f'<rect x="{chord_x0}" y="{chord_y}" width="{B1_LEN*mm_to_px}" height="{chord_h}" fill="url(#steel)" stroke="#1d4ed8" stroke-width="1.5"/>')
svg.append(f'<text x="{chord_x0 + 10}" y="{chord_y + chord_h/2 + 4}" font-size="13" fill="#1d4ed8" font-weight="600">B1</text>')

# Length annotation
svg.append(f'<line x1="{chord_x0}" y1="{chord_y - 14}" x2="{chord_x1}" y2="{chord_y - 14}" stroke="#374151" stroke-width="0.8"/>')
svg.append(f'<text x="{(chord_x0+chord_x1)/2}" y="{chord_y - 18}" text-anchor="middle" font-size="11" fill="#374151">8164.8 mm</text>')

# Boxed zone overlay
box_start_mm = B1_DIMPLES[0] - 10  # engagement margin
box_end_mm = B1_DIMPLES[1] + 10
box_x0 = margin + box_start_mm * mm_to_px
box_x1 = margin + box_end_mm * mm_to_px
box_w = box_x1 - box_x0
svg.append(f'<rect x="{box_x0}" y="{chord_y - 8}" width="{box_w}" height="{chord_h + 16}" fill="url(#box-zone)" stroke="#d97706" stroke-width="2.5" stroke-dasharray="6 3" opacity="0.85"/>')

# BOX label arrow
label_y = chord_y - 90
svg.append(f'<text x="{(box_x0+box_x1)/2}" y="{label_y}" text-anchor="middle" font-size="14" font-weight="700" fill="#92400e">⚠ BOX HERE</text>')
svg.append(f'<text x="{(box_x0+box_x1)/2}" y="{label_y+18}" text-anchor="middle" font-size="12" fill="#92400e">Insert B1(Box1) — 300mm clip-on</text>')
svg.append(f'<text x="{(box_x0+box_x1)/2}" y="{label_y+34}" text-anchor="middle" font-size="11" fill="#92400e">Snap-fit at dimples 4249.9 / 4529.9</text>')
svg.append(f'<line x1="{(box_x0+box_x1)/2}" y1="{label_y+38}" x2="{(box_x0+box_x1)/2}" y2="{chord_y - 12}" stroke="#92400e" stroke-width="1.5" marker-end="url(#a)"/>')

# Dimple markers on B1
for d in B1_DIMPLES:
    dx = margin + d * mm_to_px
    svg.append(f'<circle cx="{dx}" cy="{chord_y + chord_h/2}" r="6" fill="#fbbf24" stroke="#92400e" stroke-width="1.8"/>')
    svg.append(f'<circle cx="{dx}" cy="{chord_y + chord_h/2}" r="2.5" fill="#92400e"/>')

# Web crossing positions on B1 (small grey ticks above)
for w in WEB_CROSSINGS:
    wx = margin + w * mm_to_px
    svg.append(f'<line x1="{wx}" y1="{chord_y - 4}" x2="{wx}" y2="{chord_y + 2}" stroke="#475569" stroke-width="1"/>')
    svg.append(f'<circle cx="{wx}" cy="{chord_y - 6}" r="1.8" fill="#16a34a"/>')

# Position dimensions
for d in B1_DIMPLES:
    dx = margin + d * mm_to_px
    svg.append(f'<line x1="{dx}" y1="{chord_y + chord_h + 4}" x2="{dx}" y2="{chord_y + chord_h + 18}" stroke="#92400e" stroke-width="0.8"/>')
    svg.append(f'<text x="{dx}" y="{chord_y + chord_h + 32}" text-anchor="middle" font-size="10" fill="#92400e">{d:.1f}</text>')

# Now draw B1(Box1) below as a separate piece for reference
sep_y = 420
sep_h = 36
# Box piece is 300mm — show at same scale
box_piece_x0 = margin + (4000 - BOX_LEN/2) * mm_to_px  # centred at ~4000mm for visibility
box_piece_x1 = box_piece_x0 + BOX_LEN * mm_to_px
svg.append(f'<rect x="{box_piece_x0}" y="{sep_y}" width="{BOX_LEN * mm_to_px}" height="{sep_h}" fill="url(#box-zone)" stroke="#d97706" stroke-width="2"/>')
svg.append(f'<text x="{box_piece_x0 + 10}" y="{sep_y + sep_h/2 + 4}" font-size="11" fill="#92400e" font-weight="600">B1(Box1)</text>')

for d in BOX_DIMPLES:
    dx = box_piece_x0 + d * mm_to_px
    svg.append(f'<circle cx="{dx}" cy="{sep_y + sep_h/2}" r="6" fill="#fbbf24" stroke="#92400e" stroke-width="1.8"/>')
    svg.append(f'<circle cx="{dx}" cy="{sep_y + sep_h/2}" r="2.5" fill="#92400e"/>')

svg.append(f'<text x="{(box_piece_x0+box_piece_x1)/2}" y="{sep_y - 12}" text-anchor="middle" font-size="11" fill="#92400e" font-weight="600">300mm clip-on (B1 Box1) — dimples at 10 / 290</text>')

# Connecting arrows showing dimples align
for d_main, d_box in zip(B1_DIMPLES, BOX_DIMPLES):
    main_x = margin + d_main * mm_to_px
    box_x = box_piece_x0 + d_box * mm_to_px
    svg.append(f'<line x1="{main_x}" y1="{chord_y + chord_h + 38}" x2="{box_x}" y2="{sep_y - 4}" stroke="#16a34a" stroke-width="1.2" stroke-dasharray="3 3" opacity="0.7"/>')

svg.append(f'<text x="{margin}" y="{sep_y + sep_h + 30}" font-size="11" fill="#16a34a" font-weight="600">Green dashes show clip-fit alignment: Box piece dimples meet B1 dimples = box snaps closed</text>')

# Legend
lx = margin
ly = H - 90
svg.append(f'<rect x="{lx}" y="{ly}" width="{W - 2*margin}" height="70" fill="white" stroke="#cbd5e0" rx="3"/>')
svg.append(f'<text x="{lx+15}" y="{ly+22}" font-size="13" font-weight="700" fill="#1a202c">Factory operator instructions:</text>')
svg.append(f'<text x="{lx+15}" y="{ly+42}" font-size="12" fill="#374151">1. Lay B1 main chord on bench  ·  2. Slide B1(Box1) into the orange-hatched zone  ·  3. Push until dimples snap (you\'ll feel the click)</text>')
svg.append(f'<text x="{lx+15}" y="{ly+60}" font-size="12" fill="#374151">4. Verify both pairs of dimples are engaged  ·  5. Continue with web placement (green dots = web positions on B1)</text>')

svg.append('</svg>')
open(os.path.join(OUT_DIR, 'box_drawing_mockup.svg'), 'w', encoding='utf-8').write('\n'.join(svg))
print()
print('Drawing mockup written to:')
print(f'  {os.path.join(OUT_DIR, "box_drawing_mockup.svg")}')
