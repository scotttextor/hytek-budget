"""Realistic junction view: W5 web butts up against B1 chord, web-face-to-web-face.

Showing the actual physical assembly:
- Chord laid flat (89mm web horizontal in view)
- Web stud butts up against chord's web face — its END terminates at the chord
- Overlap zone = 89×89mm square of doubled-up steel
- Bolt goes through both layers within that overlap
"""

W = 1500
H = 800
OUT = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/junction_v2.svg'

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')

# Patterns and definitions
svg.append('''<defs>
  <pattern id="chord-fill" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(-45)">
    <rect width="6" height="6" fill="#dbeafe"/>
    <line x1="0" y1="0" x2="0" y2="6" stroke="#93c5fd" stroke-width="0.8"/>
  </pattern>
  <pattern id="web-fill" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
    <rect width="6" height="6" fill="#e2e8f0"/>
    <line x1="0" y1="0" x2="0" y2="6" stroke="#94a3b8" stroke-width="0.8"/>
  </pattern>
  <pattern id="overlap-fill" patternUnits="userSpaceOnUse" width="8" height="8">
    <rect width="8" height="8" fill="#fde68a"/>
    <line x1="0" y1="0" x2="8" y2="8" stroke="#d97706" stroke-width="0.8"/>
    <line x1="8" y1="0" x2="0" y2="8" stroke="#d97706" stroke-width="0.8"/>
  </pattern>
  <marker id="ar" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
    <path d="M0,0 L9,4.5 L0,9 z" fill="#374151"/>
  </marker>
</defs>''')

svg.append(f'<rect width="{W}" height="{H}" fill="#fafaf8"/>')
svg.append(f'<text x="20" y="34" font-size="22" font-weight="700" fill="#1a202c">Single junction — realistic web-on-chord assembly view</text>')
svg.append(f'<text x="20" y="58" font-size="14" fill="#4a5568">Looking at the truss from the side. Both C-sections sit in the same plane, web-faces touching. The orange overlap zone is where two layers of steel are stacked — that\'s where the bolt goes through.</text>')

# 1mm = 4px
MM = 4

panels = [
    {'x0': 40,  'label': 'CURRENT — 3 bolts in overlap, near the chord-end side', 'mode': 'old'},
    {'x0': 770, 'label': 'PROPOSED — 1 bolt at the overlap centre', 'mode': 'new'},
]

for p in panels:
    x0 = p['x0']
    y0 = 110
    panel_w = 690
    panel_h = 620
    cx = x0 + panel_w/2
    cy = y0 + panel_h*0.55  # bias chord toward bottom so web extends UP a long way

    # Panel border
    color = '#374151' if p['mode']=='old' else '#22543d'
    svg.append(f'<rect x="{x0}" y="{y0}" width="{panel_w}" height="{panel_h}" fill="white" stroke="#cbd5e0" stroke-width="1"/>')
    svg.append(f'<text x="{cx:.0f}" y="{y0-12}" text-anchor="middle" font-size="14" font-weight="700" fill="{color}">{p["label"]}</text>')

    # ---- Draw the chord as a horizontal band ----
    # Chord: 89mm web height (vertical extent in view), extending across the panel.
    chord_h = 89 * MM        # 356px
    chord_top = cy - chord_h/2
    chord_bot = cy + chord_h/2
    chord_left = x0 + 30
    chord_right = x0 + panel_w - 30
    chord_w = chord_right - chord_left

    # Chord rectangle (the "web" face we're looking at)
    svg.append(f'<rect x="{chord_left}" y="{chord_top}" width="{chord_w}" height="{chord_h}" fill="url(#chord-fill)" stroke="#1d4ed8" stroke-width="2.5"/>')
    # The lip edges of the chord (it's a C-section — lips face the viewer or away)
    # Show small lip ticks at top and bottom of the chord
    for x in range(int(chord_left)+10, int(chord_right)-10, 60):
        svg.append(f'<line x1="{x}" y1="{chord_top-3}" x2="{x}" y2="{chord_top+3}" stroke="#1d4ed8" stroke-width="1"/>')
        svg.append(f'<line x1="{x}" y1="{chord_bot-3}" x2="{x}" y2="{chord_bot+3}" stroke="#1d4ed8" stroke-width="1"/>')
    # Chord centreline
    svg.append(f'<line x1="{chord_left-15}" y1="{cy}" x2="{chord_right+15}" y2="{cy}" stroke="#1d4ed8" stroke-width="1.4" stroke-dasharray="6 4" opacity="0.85"/>')
    # Chord label
    svg.append(f'<text x="{chord_left+10}" y="{chord_top-8}" font-size="12" fill="#1d4ed8" font-weight="600">B1 — bottom chord (89mm × 0.75mm plate, laid flat)</text>')
    svg.append(f'<text x="{chord_right+18}" y="{cy+4}" font-size="11" fill="#1d4ed8">⊕ chord ℄</text>')
    # Chord width annotation on right
    svg.append(f'<line x1="{chord_right+5}" y1="{chord_top}" x2="{chord_right+5}" y2="{chord_bot}" stroke="#374151" stroke-width="1" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    svg.append(f'<text x="{chord_right+30}" y="{cy-chord_h/2+15}" font-size="11" fill="#374151">89mm</text>')

    # ---- Draw the web as a vertical band ----
    # Web: 89mm wide. Its END (BOTTOM end) butts up against the TOP of the chord —
    # i.e. they overlap at the chord position. Actually in a real truss the web
    # OVERLAPS the chord (web's web-face contacts chord's web-face). Show web
    # extending from the chord centreline (or slightly past) UP to a long way above.
    web_w = 89 * MM           # 356px
    web_left = cx - web_w/2
    web_right = cx + web_w/2
    web_top = y0 + 25
    web_bot = chord_bot       # web's actual cut end is at the chord's bottom edge or centreline
    # In FrameCAD, the web stick "ends" past the chord's centreline — its physical end
    # is set back by ~17mm from the chord's outer flange, but its CONTACT face
    # extends across the whole chord-width zone. For a clean visual, show the web's
    # cut end at the chord's far flange (chord_bot in this view = chord's bottom edge)

    svg.append(f'<rect x="{web_left}" y="{web_top}" width="{web_w}" height="{web_bot-web_top}" fill="url(#web-fill)" stroke="#475569" stroke-width="2.5"/>')
    # Web lips
    for y in range(int(web_top)+15, int(web_bot)-5, 60):
        svg.append(f'<line x1="{web_left-3}" y1="{y}" x2="{web_left+3}" y2="{y}" stroke="#475569" stroke-width="1"/>')
        svg.append(f'<line x1="{web_right-3}" y1="{y}" x2="{web_right+3}" y2="{y}" stroke="#475569" stroke-width="1"/>')
    # Web centreline
    svg.append(f'<line x1="{cx}" y1="{web_top-15}" x2="{cx}" y2="{web_bot+15}" stroke="#475569" stroke-width="1.4" stroke-dasharray="6 4" opacity="0.85"/>')
    # Web label
    svg.append(f'<text x="{web_left-8}" y="{web_top+15}" text-anchor="end" font-size="12" fill="#475569" font-weight="600">W5 — web</text>')
    svg.append(f'<text x="{web_left-8}" y="{web_top+30}" text-anchor="end" font-size="10" fill="#475569">89mm × 0.75mm stud</text>')
    svg.append(f'<text x="{web_left-8}" y="{web_top+44}" text-anchor="end" font-size="10" fill="#475569">(extends up to next chord)</text>')
    svg.append(f'<text x="{cx-4}" y="{web_top-20}" text-anchor="end" font-size="11" fill="#475569">⊕ web ℄</text>')
    # Web width annotation top
    svg.append(f'<line x1="{web_left}" y1="{web_top-8}" x2="{web_right}" y2="{web_top-8}" stroke="#374151" stroke-width="1" marker-start="url(#ar)" marker-end="url(#ar)"/>')
    svg.append(f'<text x="{cx:.0f}" y="{web_top-12}" text-anchor="middle" font-size="11" fill="#374151">89mm</text>')

    # ---- Draw the OVERLAP zone where they meet ----
    # The overlap is where the web's web-face contacts the chord's web-face.
    # In this top-down/side view, that's the rectangle where both shapes occupy
    # the same x,y in the page (= 89mm × 89mm square).
    ov_left = web_left
    ov_right = web_right
    ov_top = chord_top
    ov_bot = chord_bot
    svg.append(f'<rect x="{ov_left}" y="{ov_top}" width="{ov_right-ov_left}" height="{ov_bot-ov_top}" fill="url(#overlap-fill)" stroke="#d97706" stroke-width="2" stroke-dasharray="3 2"/>')
    # Overlap label outside the box (it gets crowded inside)
    svg.append(f'<text x="{ov_left-8}" y="{cy+4}" text-anchor="end" font-size="11" font-weight="600" fill="#92400e">overlap zone</text>')
    svg.append(f'<text x="{ov_left-8}" y="{cy+18}" text-anchor="end" font-size="10" fill="#92400e">2 layers of steel</text>')
    svg.append(f'<text x="{ov_left-8}" y="{cy+30}" text-anchor="end" font-size="10" fill="#92400e">89×89 mm</text>')

    # The centreline-crossing dot
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="none" stroke="#16a34a" stroke-width="1.5"/>')

    # ---- Place bolts ----
    if p['mode'] == 'old':
        # Real CSV: bolts at 58.5 and 77 mm from W5 stick start.
        # W5 stick starts at the FAR end of the overlap (where the cut end is).
        # The cut end is at chord_bot in this view. So position 0 on stick = chord_bot.
        # Hole at 58.5mm from start = 58.5mm UP from chord_bot = above the centreline by 17mm.
        # Hole at 77mm from start = 77mm UP from chord_bot = 32.5mm above centreline.
        # Plus a 3rd hole laterally offset.
        bolt_y_1 = chord_bot - 58.5 * MM   # 58.5mm above the cut end
        bolt_y_2 = chord_bot - 77 * MM     # 77mm above the cut end
        # Two bolts in line + one lateral (matching count=3 cluster)
        # Show 3 bolts: two stacked, one offset to the side
        svg.append(f'<circle cx="{cx-12}" cy="{bolt_y_1:.1f}" r="6" fill="#dc2626" stroke="#7f1d1d" stroke-width="1.5"/>')
        svg.append(f'<circle cx="{cx+12}" cy="{bolt_y_1:.1f}" r="6" fill="#dc2626" stroke="#7f1d1d" stroke-width="1.5"/>')
        svg.append(f'<circle cx="{cx}" cy="{bolt_y_2:.1f}" r="6" fill="#dc2626" stroke="#7f1d1d" stroke-width="1.5"/>')
        # Annotations
        svg.append(f'<text x="{cx+22}" y="{bolt_y_1+4:.1f}" font-size="11" fill="#7f1d1d">at 58.5 mm from web start</text>')
        svg.append(f'<text x="{cx+22}" y="{bolt_y_2+4:.1f}" font-size="11" fill="#7f1d1d">at 77 mm from web start</text>')
        # Distance from centreline crossing arrow
        svg.append(f'<line x1="{cx-30}" y1="{cy}" x2="{cx-30}" y2="{bolt_y_1}" stroke="#dc2626" stroke-width="1.2" marker-end="url(#ar)"/>')
        svg.append(f'<text x="{cx-36}" y="{(cy+bolt_y_1)/2:.1f}" text-anchor="end" font-size="10" fill="#dc2626">17mm offset</text>')
        # Caption
        cap_y = y0 + panel_h - 60
        svg.append(f'<rect x="{x0+20}" y="{cap_y}" width="{panel_w-40}" height="48" fill="#fef2f2" stroke="#dc2626" stroke-width="1" rx="3"/>')
        svg.append(f'<text x="{x0+30}" y="{cap_y+18}" font-size="12" fill="#7f1d1d"><tspan font-weight="700">3 bolts in this overlap, stacked away from centreline</tspan></text>')
        svg.append(f'<text x="{x0+30}" y="{cap_y+36}" font-size="11" fill="#7f1d1d">positioned by FrameCAD rule = material_offset (44.5) + adjustments</text>')
    else:
        # Single bolt at exact centre of overlap
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="#16a34a" stroke="#14532d" stroke-width="2"/>')
        svg.append(f'<text x="{cx+18}" y="{cy+5}" font-size="11" fill="#14532d" font-weight="600">bolt at centreline crossing</text>')
        # Caption
        cap_y = y0 + panel_h - 60
        svg.append(f'<rect x="{x0+20}" y="{cap_y}" width="{panel_w-40}" height="48" fill="#f0fdf4" stroke="#16a34a" stroke-width="1" rx="3"/>')
        svg.append(f'<text x="{x0+30}" y="{cap_y+18}" font-size="12" fill="#14532d"><tspan font-weight="700">1 bolt at the centre of the overlap</tspan></text>')
        svg.append(f'<text x="{x0+30}" y="{cap_y+36}" font-size="11" fill="#14532d">positioned by maths = (chord ℄ − web start) = exactly 41.5mm from W5 start</text>')

# Footnote explaining what we're seeing
svg.append(f'<rect x="20" y="{H-58}" width="{W-40}" height="40" fill="#f1f5f9" stroke="#cbd5e0" rx="3"/>')
svg.append(f'<text x="32" y="{H-38}" font-size="11" fill="#374151"><tspan font-weight="700">View geometry:</tspan> looking edge-on at the truss panel. Both members are C-section steel laid in the same plane with their web-faces touching.</text>')
svg.append(f'<text x="32" y="{H-22}" font-size="11" fill="#374151">The orange overlap zone is two layers of 0.75mm steel stacked together (1.5mm total) — that\'s what the bolt screws through. The web stick\'s actual cut end is along the chord\'s far flange.</text>')

svg.append('</svg>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(svg))
print(f'Wrote {OUT}')
