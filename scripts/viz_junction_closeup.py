"""Close-up of one web-to-chord junction showing the rule difference at bolt-detail."""

W = 1400
H = 720
OUT = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/junction_closeup.svg'

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')
svg.append('''<defs>
  <pattern id="diag" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="#cbd5e0" stroke-width="1.2"/>
  </pattern>
  <pattern id="diag2" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="#bee3f8" stroke-width="1.2"/>
  </pattern>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="#2d3748"/>
  </marker>
  <marker id="arrowred" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">
    <path d="M0,0 L10,5 L0,10 z" fill="#c53030"/>
  </marker>
</defs>''')
svg.append(f'<rect width="{W}" height="{H}" fill="#fafaf8"/>')

svg.append(f'<text x="20" y="34" font-size="22" font-weight="700" fill="#1a202c">Single junction close-up — W5 web meets B1 bottom chord</text>')
svg.append(f'<text x="20" y="58" font-size="14" fill="#4a5568">89×41 plate chord (horizontal) crossed by 89×41 stud web (vertical). 1mm = ~3.5px.</text>')

# Two side-by-side panels
panels = [
    {'x0': 50,   'label': 'CURRENT — 3 holes per junction, offset from centreline crossing', 'mode': 'old'},
    {'x0': 730,  'label': 'PROPOSED — 1 hole, exactly at centreline crossing', 'mode': 'new'},
]

for p in panels:
    x0 = p['x0']
    y0 = 110
    panel_w = 620
    panel_h = 540
    cx = x0 + panel_w/2
    cy = y0 + panel_h/2

    # Panel border
    svg.append(f'<rect x="{x0}" y="{y0}" width="{panel_w}" height="{panel_h}" fill="white" stroke="#cbd5e0" stroke-width="1"/>')
    color = '#2d3748' if p['mode'] == 'old' else '#22543d'
    svg.append(f'<text x="{cx:.0f}" y="{y0-12}" text-anchor="middle" font-size="14" font-weight="700" fill="{color}">{p["label"]}</text>')

    # Scale: each mm = 3.5 px. Chord is 89mm wide (horizontal band).
    MM = 3.5
    chord_w = 89 * MM    # 311.5 px wide (horizontal extent shown)
    chord_h = 89 * MM    # 311.5 px tall

    # Draw a horizontal chord band centered vertically in panel
    chord_top = cy - chord_h/2
    chord_bot = cy + chord_h/2
    chord_left = x0 + 50
    chord_right = x0 + panel_w - 50
    svg.append(f'<rect x="{chord_left}" y="{chord_top}" width="{chord_right-chord_left}" height="{chord_h}" fill="url(#diag2)" stroke="#2b6cb0" stroke-width="2"/>')
    # Chord lip indicators
    svg.append(f'<line x1="{chord_left}" y1="{chord_top}" x2="{chord_right}" y2="{chord_top}" stroke="#2b6cb0" stroke-width="3"/>')
    svg.append(f'<line x1="{chord_left}" y1="{chord_bot}" x2="{chord_right}" y2="{chord_bot}" stroke="#2b6cb0" stroke-width="3"/>')
    # Chord centreline
    svg.append(f'<line x1="{chord_left-20}" y1="{cy}" x2="{chord_right+20}" y2="{cy}" stroke="#2b6cb0" stroke-width="1.2" stroke-dasharray="6 4" opacity="0.7"/>')
    svg.append(f'<text x="{chord_right+25}" y="{cy+4}" font-size="11" fill="#2b6cb0">B1 chord ⊕</text>')
    svg.append(f'<text x="{chord_left+8}" y="{chord_top+18}" font-size="11" fill="#2b6cb0" font-weight="600">B1 (89mm × 0.75mm chord plate)</text>')

    # Vertical web band - W5 - 89mm wide, extends top and bottom of chord
    web_w = 89 * MM
    web_left = cx - web_w/2
    web_right = cx + web_w/2
    web_top = y0 + 30
    web_bot = y0 + panel_h - 30
    svg.append(f'<rect x="{web_left}" y="{web_top}" width="{web_w}" height="{web_bot-web_top}" fill="url(#diag)" stroke="#4a5568" stroke-width="2"/>')
    # Web lips (left/right edges)
    svg.append(f'<line x1="{web_left}" y1="{web_top}" x2="{web_left}" y2="{web_bot}" stroke="#4a5568" stroke-width="3"/>')
    svg.append(f'<line x1="{web_right}" y1="{web_top}" x2="{web_right}" y2="{web_bot}" stroke="#4a5568" stroke-width="3"/>')
    # Web centreline
    svg.append(f'<line x1="{cx}" y1="{web_top-20}" x2="{cx}" y2="{web_bot+20}" stroke="#4a5568" stroke-width="1.2" stroke-dasharray="6 4" opacity="0.7"/>')
    svg.append(f'<text x="{cx-4}" y="{web_top-25}" text-anchor="end" font-size="11" fill="#4a5568">W5 web ⊕</text>')
    svg.append(f'<text x="{web_left-8}" y="{web_bot-10}" text-anchor="end" font-size="11" fill="#4a5568" font-weight="600">W5</text>')
    svg.append(f'<text x="{web_left-8}" y="{web_bot+5}" text-anchor="end" font-size="10" fill="#4a5568">89mm × 0.75mm stud</text>')

    # Mark the centreline-crossing point
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="none" stroke="#38a169" stroke-width="1.5"/>')

    # Now place bolts according to the rule
    if p['mode'] == 'old':
        # Current rule: 3 holes near where the W5 stick ends meet the chord.
        # On a vertical web going UP from below: the web-to-chord junction is along
        # the chord; 3 holes are placed 14-35mm offset from the centreline crossing.
        # In the actual CSV: holes at 58.5mm and 77mm from stick start, where the stick
        # passes the chord centreline at 41.5mm. So holes are 17 and 35.5 mm BELOW the
        # centreline crossing (because the web came up from below and offsets are from
        # the stick end). We'll show 3 small holes clustered just below the chord
        # centreline.
        offsets = [
            (-15,  17 * MM, '17 mm below ⊕'),
            ( 15,  17 * MM, ''),
            (  0,  35.5 * MM, '35.5 mm below ⊕'),
        ]
        for dx, dy_mm, lab in offsets:
            bx = cx + dx
            by = cy + dy_mm
            svg.append(f'<circle cx="{bx}" cy="{by}" r="6" fill="#d53f8c" stroke="#97266d" stroke-width="1.5"/>')
            if lab:
                svg.append(f'<text x="{bx+12}" y="{by+4}" font-size="11" fill="#97266d">{lab}</text>')

        # Annotation arrow from centreline-crossing to bolt cluster
        svg.append(f'<line x1="{cx}" y1="{cy+8}" x2="{cx}" y2="{cy + 17 * MM - 8}" stroke="#c53030" stroke-width="1.5" marker-end="url(#arrowred)"/>')
        svg.append(f'<text x="{cx+12}" y="{cy + 17*MM/2}" font-size="11" fill="#c53030">offset</text>')
        # Caption box
        cap_y = y0 + panel_h - 78
        svg.append(f'<rect x="{x0+30}" y="{cap_y}" width="{panel_w-60}" height="58" fill="#fdf2f8" stroke="#d53f8c" stroke-width="1"/>')
        svg.append(f'<text x="{x0+45}" y="{cap_y+22}" font-size="12" fill="#97266d"><tspan font-weight="700">3 holes total</tspan> · positioned by rule:</text>')
        svg.append(f'<text x="{x0+45}" y="{cap_y+40}" font-size="12" fill="#97266d">  pos = material_offset (44.5) + geom_adjust (~14) = ~58.5 mm from W5 start</text>')

    else:
        # New rule: ONE hole exactly at the centreline crossing
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="#38a169" stroke="#22543d" stroke-width="2"/>')
        svg.append(f'<text x="{cx+15}" y="{cy+5}" font-size="11" fill="#22543d" font-weight="600">at centreline crossing</text>')
        # Caption box
        cap_y = y0 + panel_h - 78
        svg.append(f'<rect x="{x0+30}" y="{cap_y}" width="{panel_w-60}" height="58" fill="#f0fdf4" stroke="#38a169" stroke-width="1"/>')
        svg.append(f'<text x="{x0+45}" y="{cap_y+22}" font-size="12" fill="#22543d"><tspan font-weight="700">1 hole total</tspan> · positioned by maths:</text>')
        svg.append(f'<text x="{x0+45}" y="{cap_y+40}" font-size="12" fill="#22543d">  pos = (chord_centreline_Z − web_start_Z) = exactly 41.5 mm from W5 start</text>')

    # Legend
    leg_x = x0 + panel_w - 220
    leg_y = y0 + 15
    svg.append(f'<rect x="{leg_x}" y="{leg_y}" width="200" height="68" fill="white" stroke="#e2e8f0" rx="3"/>')
    svg.append(f'<rect x="{leg_x+10}" y="{leg_y+10}" width="14" height="8" fill="url(#diag2)" stroke="#2b6cb0"/>')
    svg.append(f'<text x="{leg_x+30}" y="{leg_y+18}" font-size="11" fill="#2d3748">chord (plate) — flat</text>')
    svg.append(f'<rect x="{leg_x+10}" y="{leg_y+25}" width="14" height="8" fill="url(#diag)" stroke="#4a5568"/>')
    svg.append(f'<text x="{leg_x+30}" y="{leg_y+33}" font-size="11" fill="#2d3748">web (stud) — vertical</text>')
    svg.append(f'<line x1="{leg_x+10}" y1="{leg_y+44}" x2="{leg_x+24}" y2="{leg_y+44}" stroke="#666" stroke-dasharray="4 3"/>')
    svg.append(f'<text x="{leg_x+30}" y="{leg_y+48}" font-size="11" fill="#2d3748">centreline ⊕</text>')
    if p['mode'] == 'old':
        svg.append(f'<circle cx="{leg_x+17}" cy="{leg_y+59}" r="4" fill="#d53f8c"/>')
        svg.append(f'<text x="{leg_x+30}" y="{leg_y+63}" font-size="11" fill="#2d3748">bolt hole</text>')
    else:
        svg.append(f'<circle cx="{leg_x+17}" cy="{leg_y+59}" r="4" fill="#38a169"/>')
        svg.append(f'<text x="{leg_x+30}" y="{leg_y+63}" font-size="11" fill="#2d3748">bolt hole</text>')

# Footer with the math
svg.append(f'<text x="20" y="{H-15}" font-size="11" fill="#4a5568">Source: 2603191 ROCKVILLE TH-TYPE-A1-LT, frame TN1-1, junction W5×B1. Stick W5: start (19395.016, _, 2743.000), end (19395.016, _, 4762.352). B1 centreline at z=2784.5.</text>')

svg.append('</svg>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(svg))
print(f'Wrote {OUT}')
