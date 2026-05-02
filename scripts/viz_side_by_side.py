"""Side-by-side BOLT HOLES comparison: Original vs Simplified, per frame.

Reads:
  XML  — FrameCAD plan geometry (sticks per frame)
  CSV  — original FrameCAD CSV (BOLT HOLES at original positions)
  CSV  — simplifier output (BOLT HOLES at centreline-intersection positions)

Renders for every Linear-truss frame:
  - Two equal-scale panels side by side (Original | Simplified)
  - Members drawn as 89mm-wide hatched polygons (chord = blue, web = grey)
  - Stick name labels overlaid on each member
  - Original panel: red dots at every BOLT HOLES position from original CSV
  - Simplified panel: green 3-hole patterns perp to each stick, middle hole on
    the centreline intersection with the crossing stick
  - Per-stick "X bolts" badge in each panel
  - Frame-level summary: "Original X bolts -> Simplified Y bolts (Z% reduction)"

Outputs:
  scripts/side_by_side/{FRAME}.svg   (one per frame)
  scripts/SIDE_BY_SIDE.html          (index, embeds each SVG in an iframe)

Constraints (per task):
  - re-only XML/CSV parsing, no extra deps
  - all printable ASCII in print() output (cp1252 terminal)
  - SVG content can use UTF-8 chars (file encoding is utf-8)
  - Length-match for chord splices ("B1 (Box1)" CSV name -> XML "B2", 5mm tol)
  - Girder duplicate sticks (same name at different X) are all rendered
"""
import re
import math
import os
import subprocess
from collections import defaultdict

# -------- Inputs --------
XML = r'C:/Users/Scott/AppData/Local/Temp/2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075 (1).xml'
CSV_ORIG = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.csv'
CSV_SIMP = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop/2603191-GF-LIN-89.075.simplified.csv'

# -------- Outputs --------
OUT_DIR = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/side_by_side'
OUT_INDEX = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/SIDE_BY_SIDE.html'

os.makedirs(OUT_DIR, exist_ok=True)

WIDTH_MM = 89.0  # member section width
HOLE_PITCH_MM = 17.0  # 3 x 17mm


# ---------- XML parsing ----------

def parse_xml(xml_path):
    """Returns list of plans, each with frames and sticks (XZ planar)."""
    text = open(xml_path).read()
    plans = []
    for plan_match in re.finditer(r'<plan name="([^"]+)">(.*?)</plan>', text, re.DOTALL):
        plan_name = plan_match.group(1)
        plan_body = plan_match.group(2)
        frames = []
        for frame_match in re.finditer(r'<frame name="([^"]+)" type="([^"]+)"[^>]*>(.*?)</frame>', plan_body, re.DOTALL):
            frame_name = frame_match.group(1)
            frame_type = frame_match.group(2)
            frame_body = frame_match.group(3)
            sticks = []
            for stick_match in re.finditer(
                r'<stick\s+([^>]*?)>\s*<start>([^<]+)</start>\s*<end>([^<]+)</end>\s*<profile\s+([^/>]*?)/?>',
                frame_body
            ):
                attrs_str, st, en, prof_str = stick_match.groups()

                def get_attr(s, key):
                    m = re.search(rf'\b{key}="([^"]*)"', s)
                    return m.group(1) if m else ''

                name = get_attr(attrs_str, 'name')
                typ = get_attr(attrs_str, 'type')
                gauge = get_attr(attrs_str, 'gauge')
                usage = get_attr(attrs_str, 'usage')
                sx, sy, sz = [float(v) for v in st.strip().split(',')]
                ex, ey, ez = [float(v) for v in en.strip().split(',')]
                sticks.append({
                    'name': name, 'type': typ, 'gauge': gauge, 'usage': usage,
                    'start_xz': (sx, sz), 'end_xz': (ex, ez),
                    'start': (sx, sy, sz), 'end': (ex, ey, ez),
                    'profile': {
                        'web': get_attr(prof_str, 'web'),
                        'l_flange': get_attr(prof_str, 'l_flange'),
                        'r_flange': get_attr(prof_str, 'r_flange'),
                        'l_lip': get_attr(prof_str, 'l_lip'),
                        'r_lip': get_attr(prof_str, 'r_lip'),
                        'shape': get_attr(prof_str, 'shape'),
                    },
                })
            frames.append({'name': frame_name, 'type': frame_type, 'sticks': sticks})
        plans.append({'name': plan_name, 'frames': frames})
    return plans


def is_linear_truss(plan, frame):
    """4-layer detection -- mirrors simplify-truss.py exactly."""
    if frame['type'] != 'Truss':
        return False
    if not re.search(r'-LIN-', plan['name'], re.IGNORECASE):
        return False
    for s in frame['sticks']:
        p = s['profile']
        if (p['web'] != '89' or p['r_flange'] != '41' or p['l_flange'] != '38' or
                p['l_lip'] != '11.0' or p['r_lip'] != '11.0' or p['shape'] != 'C'):
            return False
        if s['gauge'] != '0.75':
            return False
    has_chord = any(s['usage'].lower() in ('bottomchord', 'topchord') for s in frame['sticks'])
    has_web = any(s['usage'].lower() == 'web' for s in frame['sticks'])
    return has_chord and has_web


# ---------- CSV parsing ----------

def parse_csv(csv_path):
    """Returns dict: full_component_name -> {header[13], ops[(tool,pos)...] }"""
    out = {}
    with open(csv_path) as f:
        for line in f:
            parts = [p.strip() for p in line.strip().split(',')]
            if len(parts) < 14 or parts[0] != 'COMPONENT':
                continue
            full = parts[1]
            ops_raw = parts[13:]
            ops = []
            i = 0
            while i + 1 < len(ops_raw):
                tool = ops_raw[i]
                try:
                    pos = float(ops_raw[i + 1])
                    ops.append((tool, pos))
                except ValueError:
                    pass
                i += 2
            out[full] = {'header': parts[:13], 'ops': ops}
    return out


# ---------- CSV -> XML stick mapping ----------

def stick_length(s):
    return math.hypot(s['end'][0] - s['start'][0], s['end'][2] - s['start'][2])


def map_csv_to_xml(frame, csv_components):
    """Returns dict: csv_full_name -> xml_stick_index. Mirrors simplify-truss.py."""
    sticks = frame['sticks']
    prefix = frame['name'] + '-'
    csv_in_frame = [name for name in csv_components if name.startswith(prefix)]

    xml_used = [False] * len(sticks)
    mapping = {}
    for full in csv_in_frame:
        comp = csv_components[full]
        short = full[len(prefix):]
        base = re.sub(r'\s*\(Box\d+\)\s*$', '', short).strip()
        try:
            comp_len = float(comp['header'][7])
        except (ValueError, IndexError):
            continue
        # Pass 1: exact name + length match (within 1mm)
        best_idx = None
        for i, s in enumerate(sticks):
            if xml_used[i]:
                continue
            if s['name'] == base and abs(stick_length(s) - comp_len) < 1.0:
                best_idx = i
                break
        # Pass 2: length match only (within 5mm)
        if best_idx is None:
            best_diff = 5.0
            for i, s in enumerate(sticks):
                if xml_used[i]:
                    continue
                d = abs(stick_length(s) - comp_len)
                if d < best_diff:
                    best_diff = d
                    best_idx = i
        if best_idx is not None:
            xml_used[best_idx] = True
            mapping[full] = best_idx
    return mapping


# ---------- SVG rendering ----------

def member_polygon_pts(stick, to_px):
    sx, sz = stick['start_xz']
    ex, ez = stick['end_xz']
    dx, dz = ex - sx, ez - sz
    L = math.hypot(dx, dz)
    if L == 0:
        return ''
    nx, nz = -dz / L, dx / L
    half = WIDTH_MM / 2
    pts_mm = [
        (sx + nx * half, sz + nz * half),
        (sx - nx * half, sz - nz * half),
        (ex - nx * half, ez - nz * half),
        (ex + nx * half, ez + nz * half),
    ]
    return ' '.join(f'{a:.1f},{b:.1f}' for a, b in (to_px(*p) for p in pts_mm))


def stick_axis_unit(stick):
    sx, sz = stick['start_xz']
    ex, ez = stick['end_xz']
    dx, dz = ex - sx, ez - sz
    L = math.hypot(dx, dz)
    if L == 0:
        return (1.0, 0.0), (0.0, 1.0), 0.0
    ax = (dx / L, dz / L)
    perp = (-dz / L, dx / L)
    return ax, perp, L


def stick_point_at(stick, pos_mm):
    """Return XZ point at a given local position along the stick."""
    sx, sz = stick['start_xz']
    ax, _, L = stick_axis_unit(stick)
    return (sx + ax[0] * pos_mm, sz + ax[1] * pos_mm)


def render_panel(svg, sticks, to_px, mode, csv_to_xml, csv_components, frame_name):
    """Draw one panel (members + bolt holes). Returns total bolt count.

    mode = 'orig'  -> red dots at original CSV BOLT HOLES positions
    mode = 'simp'  -> green 3-hole patterns perp to stick at simplified positions
    """
    # Members: draw chords first (under), then webs (over), then centrelines, then labels
    chord_polys = []
    web_polys = []
    for s in sticks:
        poly = member_polygon_pts(s, to_px)
        if not poly:
            continue
        if s['type'] == 'Plate':
            chord_polys.append((s, poly))
        else:
            web_polys.append((s, poly))
    for s, poly in chord_polys:
        svg.append(f'<polygon points="{poly}" fill="url(#chord-fill)" stroke="#1d4ed8" stroke-width="1.4" opacity="0.95"/>')
    for s, poly in web_polys:
        svg.append(f'<polygon points="{poly}" fill="url(#web-fill)" stroke="#475569" stroke-width="1.2" opacity="0.85"/>')

    # Centrelines (dashed, faint)
    for s in sticks:
        x1, y1 = to_px(*s['start_xz'])
        x2, y2 = to_px(*s['end_xz'])
        col = '#1d4ed8' if s['type'] == 'Plate' else '#334155'
        svg.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" stroke-width="0.6" stroke-dasharray="4 3" opacity="0.55"/>')

    # Per-stick bolt counts (so we can show the badge & sum total)
    per_stick_bolts = defaultdict(int)  # xml_index -> count
    total_bolts = 0

    prefix = frame_name + '-'
    csv_in_frame = [name for name in csv_components if name.startswith(prefix)]

    # Draw bolts
    for full in csv_in_frame:
        xml_idx = csv_to_xml.get(full)
        if xml_idx is None:
            continue
        stick = sticks[xml_idx]
        ax, perp, _L = stick_axis_unit(stick)
        comp = csv_components[full]
        bolt_positions = [pos for tool, pos in comp['ops'] if tool == 'BOLT HOLES']

        if mode == 'orig':
            # Single red dot per BOLT HOLES, at the position on the stick centreline
            for pos in bolt_positions:
                x_mm, z_mm = stick_point_at(stick, pos)
                cx, cy = to_px(x_mm, z_mm)
                svg.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.4" fill="#dc2626" stroke="#7f1d1d" stroke-width="0.6"/>')
            n = len(bolt_positions)
        else:  # simp
            # 3-hole pattern perpendicular to stick: -17, 0, +17
            for pos in bolt_positions:
                x_mm, z_mm = stick_point_at(stick, pos)
                for off, is_mid in [(-HOLE_PITCH_MM, False), (0.0, True), (HOLE_PITCH_MM, False)]:
                    hx_mm = x_mm + perp[0] * off
                    hz_mm = z_mm + perp[1] * off
                    hx, hy = to_px(hx_mm, hz_mm)
                    if is_mid:
                        svg.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="3.6" fill="none" stroke="#16a34a" stroke-width="1.2" opacity="0.5"/>')
                        svg.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="2.3" fill="#16a34a" stroke="#14532d" stroke-width="0.9"/>')
                    else:
                        svg.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="2.0" fill="#16a34a" stroke="#14532d" stroke-width="0.7"/>')
            n = len(bolt_positions)

        per_stick_bolts[xml_idx] += n
        total_bolts += n

    # Labels: stick name + "X bolts" badge, anchored at midpoint
    for i, s in enumerate(sticks):
        mx = (s['start_xz'][0] + s['end_xz'][0]) / 2
        mz = (s['start_xz'][1] + s['end_xz'][1]) / 2
        px, py = to_px(mx, mz)
        nbolts = per_stick_bolts.get(i, 0)
        svg.append(f'<text x="{px:.1f}" y="{py - 4:.1f}" font-size="11" font-weight="700" text-anchor="middle" fill="#0f172a" stroke="white" stroke-width="3.2" paint-order="stroke">{s["name"]}</text>')
        badge_col = '#7f1d1d' if mode == 'orig' else '#14532d'
        svg.append(f'<text x="{px:.1f}" y="{py + 9:.1f}" font-size="9" font-weight="600" text-anchor="middle" fill="{badge_col}" stroke="white" stroke-width="2.6" paint-order="stroke">{nbolts} bolts</text>')

    return total_bolts


def render_frame_svg(plan, frame, csv_orig, csv_simp):
    sticks = frame['sticks']
    if not sticks:
        return None, 0, 0

    mapping_orig = map_csv_to_xml(frame, csv_orig)
    mapping_simp = map_csv_to_xml(frame, csv_simp)

    # Bounding box across all sticks (XZ)
    all_x = [c for s in sticks for c in (s['start_xz'][0], s['end_xz'][0])]
    all_z = [c for s in sticks for c in (s['start_xz'][1], s['end_xz'][1])]
    pad = 250
    xmin, xmax = min(all_x) - pad, max(all_x) + pad
    zmin, zmax = min(all_z) - pad, max(all_z) + pad

    panel_w_mm = (xmax - xmin)
    panel_h_mm = (zmax - zmin)
    gap_mm = 800
    total_w_mm = panel_w_mm * 2 + gap_mm

    # Cap render width at 1900px, keep mm-aspect uniform across both panels
    SCALE = min(1900.0 / total_w_mm, 950.0 / panel_h_mm)
    W = int(total_w_mm * SCALE) + 80
    panel_h_px = panel_h_mm * SCALE
    H = int(panel_h_px) + 220  # room for header + footer

    header_h = 110
    footer_h = 90

    def to_px_left(x, z):
        # X grows right, Z grows up (so flip to SVG y)
        px = 40 + (x - xmin) * SCALE
        py = header_h + (zmax - z) * SCALE
        return px, py

    def to_px_right(x, z):
        px = 40 + (panel_w_mm + gap_mm + (x - xmin)) * SCALE
        py = header_h + (zmax - z) * SCALE
        return px, py

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
    svg.append('<defs>')
    svg.append('<pattern id="chord-fill" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)"><rect width="6" height="6" fill="#dbeafe"/><line x1="0" y1="0" x2="0" y2="6" stroke="#93c5fd" stroke-width="0.6"/></pattern>')
    svg.append('<pattern id="web-fill" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)"><rect width="6" height="6" fill="#e2e8f0"/><line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" stroke-width="0.6"/></pattern>')
    svg.append('</defs>')
    svg.append(f'<rect width="{W}" height="{H}" fill="#fafaf8"/>')

    # Title bar
    title = f'Frame {frame["name"]} - plan {plan["name"]}'
    svg.append(f'<text x="20" y="32" font-size="20" font-weight="700" fill="#1a202c">{title}</text>')
    svg.append(f'<text x="20" y="54" font-size="12" fill="#4a5568">{len(sticks)} sticks. Same scale, both panels.</text>')

    # Panel labels
    left_cx = 40 + panel_w_mm * SCALE / 2
    right_cx = 40 + (panel_w_mm * 1.5 + gap_mm) * SCALE
    svg.append(f'<text x="{left_cx:.0f}" y="92" text-anchor="middle" font-size="15" font-weight="700" fill="#7f1d1d">ORIGINAL - FrameCAD CSV BOLT HOLES (red dots)</text>')
    svg.append(f'<text x="{right_cx:.0f}" y="92" text-anchor="middle" font-size="15" font-weight="700" fill="#14532d">SIMPLIFIED - centreline-intersection 3-hole pattern (green)</text>')

    # Panel borders
    svg.append(f'<rect x="40" y="{header_h}" width="{panel_w_mm * SCALE:.1f}" height="{panel_h_px:.1f}" fill="none" stroke="#cbd5e0" stroke-width="0.8"/>')
    svg.append(f'<rect x="{40 + (panel_w_mm + gap_mm) * SCALE:.1f}" y="{header_h}" width="{panel_w_mm * SCALE:.1f}" height="{panel_h_px:.1f}" fill="none" stroke="#cbd5e0" stroke-width="0.8"/>')

    # Render
    orig_total = render_panel(svg, sticks, to_px_left, 'orig', mapping_orig, csv_orig, frame['name'])
    simp_total = render_panel(svg, sticks, to_px_right, 'simp', mapping_simp, csv_simp, frame['name'])

    # Footer summary
    foot_y = header_h + panel_h_px + 30
    pct = 100.0 * (orig_total - simp_total) / max(orig_total, 1)
    svg.append(f'<rect x="40" y="{foot_y - 20}" width="{W - 80}" height="60" fill="#f1f5f9" stroke="#cbd5e0" rx="4"/>')
    svg.append(f'<text x="{W // 2}" y="{foot_y + 6}" text-anchor="middle" font-size="16" font-weight="700" fill="#1a202c">'
               f'Original {orig_total} bolts -> Simplified {simp_total} bolts ({pct:.0f}% reduction)</text>')
    svg.append(f'<text x="{W // 2}" y="{foot_y + 28}" text-anchor="middle" font-size="11" fill="#4a5568">'
               f'Per-stick counts shown beneath each member name. Each green dot in the right panel = a 3-hole pattern (3 x diam.3.8mm at 17mm pitch).</text>')

    svg.append('</svg>')
    return '\n'.join(svg), orig_total, simp_total


def main():
    print(f'Reading XML : {XML}')
    plans = parse_xml(XML)

    print(f'Reading CSV : {CSV_ORIG}')
    csv_orig = parse_csv(CSV_ORIG)

    print(f'Reading CSV : {CSV_SIMP}')
    csv_simp = parse_csv(CSV_SIMP)

    rendered = []  # (frame_name, plan_name, n_sticks, orig, simp, pct, svg_path)
    grand_orig = 0
    grand_simp = 0

    print()
    print('Rendering side-by-side SVGs...')
    print('-' * 72)
    print(f'{"Frame":<10} {"Plan":<35} {"Sticks":>6} {"Orig":>6} {"Simp":>6} {"Reduce":>7}')
    print('-' * 72)

    for plan in plans:
        for frame in plan['frames']:
            if not is_linear_truss(plan, frame):
                continue
            result = render_frame_svg(plan, frame, csv_orig, csv_simp)
            if not result or not result[0]:
                continue
            svg_text, orig_total, simp_total = result
            out_path = os.path.join(OUT_DIR, f'{frame["name"]}.svg')
            open(out_path, 'w', encoding='utf-8').write(svg_text)
            pct = 100.0 * (orig_total - simp_total) / max(orig_total, 1)
            rendered.append((frame['name'], plan['name'], len(frame['sticks']),
                             orig_total, simp_total, pct, out_path))
            grand_orig += orig_total
            grand_simp += simp_total
            print(f'{frame["name"]:<10} {plan["name"][:35]:<35} {len(frame["sticks"]):>6} '
                  f'{orig_total:>6} {simp_total:>6} {pct:>6.0f}%')

    print('-' * 72)
    grand_pct = 100.0 * (grand_orig - grand_simp) / max(grand_orig, 1)
    print(f'{"TOTAL":<10} {"":<35} {"":>6} {grand_orig:>6} {grand_simp:>6} {grand_pct:>6.0f}%')
    print()

    # Sort by frame name for index display
    rendered.sort(key=lambda r: (r[0]))

    # Index HTML
    rows_html = []
    for fname, pname, nsticks, orig, simp, pct, svg_path in rendered:
        rel = f'side_by_side/{fname}.svg'
        rows_html.append(
            f'<div class="card">'
            f'<div class="card-head">'
            f'<h2>{fname} <span class="plan">- {pname}</span></h2>'
            f'<div class="meta">{nsticks} sticks &middot; '
            f'<span class="orig">{orig} original bolts</span> &rarr; '
            f'<span class="simp">{simp} simplified bolts</span> &middot; '
            f'<b>{pct:.0f}% reduction</b></div>'
            f'</div>'
            f'<iframe src="{rel}" loading="lazy"></iframe>'
            f'</div>'
        )

    body = '\n'.join(rows_html)
    summary_html = (
        f'<div class="summary">'
        f'<div class="big">{grand_orig} &rarr; {grand_simp}</div>'
        f'<div class="small">{grand_pct:.0f}% reduction across {len(rendered)} frames '
        f'({grand_orig - grand_simp} fewer BOLT HOLES ops)</div>'
        f'</div>'
    )

    html = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
<title>BOLT HOLES - side by side: original vs simplified</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;padding:24px;background:#1a202c;color:#e2e8f0}}
h1{{margin:0 0 8px;color:white;font-size:22px}}
.sub{{color:#94a3b8;margin-bottom:18px;font-size:13px}}
.summary{{background:#0f172a;border:1px solid #334155;border-radius:8px;padding:16px 20px;margin-bottom:24px;display:flex;flex-direction:column;gap:6px}}
.summary .big{{font-size:22px;font-weight:700;color:#facc15}}
.summary .small{{font-size:13px;color:#cbd5e0}}
.card{{background:white;color:#1a202c;border:1px solid #475569;border-radius:6px;margin-bottom:18px;overflow:hidden}}
.card-head{{padding:10px 16px;background:#fafaf8;border-bottom:1px solid #e2e8f0}}
.card-head h2{{margin:0;font-size:15px}}
.card-head .plan{{color:#475569;font-weight:400;font-size:13px}}
.card-head .meta{{font-size:12px;color:#374151;margin-top:3px}}
.card-head .orig{{color:#7f1d1d;font-weight:600}}
.card-head .simp{{color:#14532d;font-weight:600}}
iframe{{border:0;width:100%;height:760px;display:block;background:white}}
</style></head><body>
<h1>HYTEK Linear-Truss simplifier - per-frame side-by-side</h1>
<p class="sub">Job 2603191 ROCKVILLE TH-TYPE-A1-LT-GF-LIN-89.075. Each row: full frame
geometry rendered to scale; left panel shows the original FrameCAD BOLT HOLES (red),
right panel shows the simplified centreline-intersection 3-hole patterns (green).</p>
{summary_html}
{body}
</body></html>'''
    open(OUT_INDEX, 'w', encoding='utf-8').write(html)
    print(f'Wrote {len(rendered)} SVGs to {OUT_DIR}')
    print(f'Wrote index {OUT_INDEX}')

    # Open the index
    try:
        subprocess.Popen(['cmd.exe', '/c', 'start', '""', OUT_INDEX], shell=False)
        print('Opened index in default browser.')
    except Exception as e:
        print(f'Could not auto-open index: {e}')


if __name__ == '__main__':
    main()
