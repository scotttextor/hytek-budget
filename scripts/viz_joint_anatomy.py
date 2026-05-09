"""Visual explainer of the HYTEK Linear-truss web-to-chord joint rule.

One page, four panels:
  1. PLAN VIEW of one real joint (W10 meets B1) — shows centreline rule + 3-hole
     cluster on each stick at the right perpendicular orientation
  2. WEB HOLE tool schematic (3 x Ø3.8mm at 17mm pitch — one machine fire)
  3. BOLT cross-section through the joined sticks
  4. RULES IN ACTION strip — W↔W skip, apex collision, end-zone exclusion

Output: HYTEK_joint_anatomy.svg on Scott's Desktop.
"""
import os, math

DESKTOP = r'C:/Users/Scott/OneDrive - Textor Metal Industries/Desktop'
OUT = os.path.join(DESKTOP, 'HYTEK_joint_anatomy.svg')

# Page geometry
W, H = 1700, 1180
svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')

# Defs (gradients + patterns)
svg.append('''<defs>
  <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#e2e8f0"/>
    <stop offset="50%" stop-color="#cbd5e1"/>
    <stop offset="100%" stop-color="#94a3b8"/>
  </linearGradient>
  <linearGradient id="steelV" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#e2e8f0"/>
    <stop offset="50%" stop-color="#cbd5e1"/>
    <stop offset="100%" stop-color="#94a3b8"/>
  </linearGradient>
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="4" stroke="#64748b" stroke-width="0.4"/>
  </pattern>
  <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
    <path d="M0,0 L9,3 L0,6 z" fill="#1e40af"/>
  </marker>
  <marker id="arrowDim" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
    <path d="M0,0 L7,3 L0,6 z" fill="#374151"/>
  </marker>
</defs>''')

svg.append(f'<rect width="{W}" height="{H}" fill="#f8fafc"/>')

# ============== HEADER ==============
svg.append(f'<rect x="0" y="0" width="{W}" height="60" fill="#231F20"/>')
svg.append(f'<rect x="0" y="0" width="8" height="60" fill="#FFCB05"/>')
svg.append('<text x="30" y="36" font-size="22" font-weight="800" fill="#FFCB05">HYTEK Linear Truss — anatomy of ONE joint</text>')
svg.append('<text x="30" y="52" font-size="12" fill="white" opacity="0.85">centreline-intersection rule | WEB HOLE tool | 3 x Ø3.8mm @ 17mm pitch | M3.5 structural screws</text>')

# ============== PANEL 1: ONE JOINT IN PLAN VIEW ==============
# Big panel taking left 60% of width
P1_X, P1_Y, P1_W, P1_H = 30, 80, 1010, 720
svg.append(f'<rect x="{P1_X}" y="{P1_Y}" width="{P1_W}" height="{P1_H}" fill="white" stroke="#cbd5e1" stroke-width="1.5" rx="6"/>')
svg.append(f'<text x="{P1_X + 20}" y="{P1_Y + 28}" font-size="16" font-weight="700" fill="#1a202c">1 &#160; ONE JOINT — plan view (top-down on the steel)</text>')
svg.append(f'<text x="{P1_X + 20}" y="{P1_Y + 48}" font-size="12" fill="#4a5568">Web W10 meets bottom chord B1 at world position (299, 2784). The centreline of each stick crosses at one point — that point becomes the joint.</text>')

# Drawing area inside panel 1
DA_X, DA_Y = P1_X + 60, P1_Y + 80
DA_W, DA_H = P1_W - 120, P1_H - 130

# Coordinate frame for the joint:
# B1 is horizontal — runs left-right across the panel, very long (we show ~600mm of it)
# W10 is vertical — runs up-down, full 187mm
# Scale: 1 mm = 1.4 px (so 600mm chord segment ≈ 840px)
SCALE = 1.4
# B1 segment we draw: from 100mm before joint to 500mm after = 600mm window, joint sits 167px from left of drawing area
joint_x = DA_X + 250  # x in svg of the joint
joint_y = DA_Y + 320  # y in svg of the joint

# Web of B1 (the 89mm-deep flat that the bolt holes go through)
# Drawn as a horizontal band, 89 * SCALE = 124.6 px tall, centred on joint_y
B1_HALF_DEPTH = 89/2 * SCALE
b1_top = joint_y - B1_HALF_DEPTH
b1_bot = joint_y + B1_HALF_DEPTH
b1_left = DA_X + 30
b1_right = DA_X + DA_W - 30

# B1 web fill
svg.append(f'<rect x="{b1_left}" y="{b1_top}" width="{b1_right - b1_left}" height="{2*B1_HALF_DEPTH}" '
           f'fill="url(#steel)" stroke="#475569" stroke-width="1.2"/>')

# B1 flanges (the C-section flanges as thin lines just outside the web — 38mm left flange, 41mm right flange)
# In plan view these are seen edge-on as parallel lines
LFLG = 38 * 0.25 * SCALE  # show as small ticks
RFLG = 41 * 0.25 * SCALE
svg.append(f'<line x1="{b1_left}" y1="{b1_top}" x2="{b1_right}" y2="{b1_top}" stroke="#1e293b" stroke-width="2.2"/>')
svg.append(f'<line x1="{b1_left}" y1="{b1_bot}" x2="{b1_right}" y2="{b1_bot}" stroke="#1e293b" stroke-width="2.2"/>')

# B1 centreline (dashed)
svg.append(f'<line x1="{b1_left + 6}" y1="{joint_y}" x2="{b1_right - 6}" y2="{joint_y}" '
           f'stroke="#dc2626" stroke-width="1.2" stroke-dasharray="6,4"/>')
svg.append(f'<text x="{b1_right - 50}" y="{joint_y - 6}" font-size="10" fill="#dc2626" font-weight="700">CL of B1</text>')

# B1 label
svg.append(f'<text x="{b1_right + 8}" y="{joint_y + 4}" font-size="13" font-weight="700" fill="#1a202c">B1</text>')
svg.append(f'<text x="{b1_right + 8}" y="{joint_y + 18}" font-size="9" fill="#475569">89 x 41 LC 0.75</text>')
svg.append(f'<text x="{b1_left - 75}" y="{joint_y + 4}" font-size="11" fill="#475569" font-weight="600">←  CHORD  →</text>')

# B1 length label
svg.append(f'<text x="{b1_left + 4}" y="{b1_top - 10}" font-size="9" fill="#64748b">(B1 is 5509mm — only 600mm shown)</text>')

# W10 — vertical web crossing B1
# 187mm long, drawn as a 50mm-wide-ish band (89mm * SCALE) centred on joint_x
W10_HALF_DEPTH = 89/2 * SCALE
w10_left = joint_x - W10_HALF_DEPTH
w10_right = joint_x + W10_HALF_DEPTH
# W10 starts at 30mm above the joint (chord stand-off), but for visual clarity we draw it
# starting AT the joint and extending up. Actually, model it correctly: W10's centreline crosses
# B1's centreline, and W10 extends UP only.
w10_top = joint_y - 187.5 * SCALE - 30  # extend further up
w10_bot = joint_y + 30  # slight extension below joint for visual

# W10 fill
svg.append(f'<rect x="{w10_left}" y="{w10_top}" width="{2*W10_HALF_DEPTH}" height="{w10_bot - w10_top}" '
           f'fill="url(#steelV)" stroke="#475569" stroke-width="1.2"/>')
svg.append(f'<line x1="{w10_left}" y1="{w10_top}" x2="{w10_left}" y2="{w10_bot}" stroke="#1e293b" stroke-width="2.2"/>')
svg.append(f'<line x1="{w10_right}" y1="{w10_top}" x2="{w10_right}" y2="{w10_bot}" stroke="#1e293b" stroke-width="2.2"/>')

# W10 centreline (dashed)
svg.append(f'<line x1="{joint_x}" y1="{w10_top + 6}" x2="{joint_x}" y2="{w10_bot - 6}" '
           f'stroke="#1e40af" stroke-width="1.2" stroke-dasharray="6,4"/>')
svg.append(f'<text x="{joint_x + 4}" y="{w10_top + 18}" font-size="10" fill="#1e40af" font-weight="700">CL of W10</text>')

# W10 label
svg.append(f'<text x="{joint_x - 16}" y="{w10_top - 8}" font-size="13" font-weight="700" fill="#1a202c">W10</text>')
svg.append(f'<text x="{joint_x - 30}" y="{w10_top - 22}" font-size="9" fill="#475569">187mm web</text>')

# Centreline INTERSECTION marker
svg.append(f'<circle cx="{joint_x}" cy="{joint_y}" r="9" fill="#dc2626" stroke="white" stroke-width="2"/>')
svg.append(f'<circle cx="{joint_x}" cy="{joint_y}" r="3.5" fill="white"/>')
svg.append(f'<text x="{joint_x + 14}" y="{joint_y - 12}" font-size="11" font-weight="700" fill="#dc2626">CENTRELINE INTERSECTION</text>')
svg.append(f'<text x="{joint_x + 14}" y="{joint_y + 2}" font-size="10" fill="#7f1d1d">B1 @ 299.11mm</text>')
svg.append(f'<text x="{joint_x + 14}" y="{joint_y + 16}" font-size="10" fill="#7f1d1d">W10 @ 30mm</text>')

# 3-hole cluster on B1 — perpendicular to B1's length = vertical line of 3 holes
# 17mm pitch * SCALE = 23.8 px between holes
HOLE_R = 4.2  # Ø3.8mm * SCALE / 2
PITCH = 17 * SCALE
# Three holes: -PITCH, 0, +PITCH from joint_y; all at joint_x
for i, dy in enumerate([-PITCH, 0, PITCH]):
    cx = joint_x
    cy = joint_y + dy
    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{HOLE_R}" fill="#231F20" stroke="#FFCB05" stroke-width="1.2"/>')

# Annotate B1's 3-hole cluster
svg.append(f'<line x1="{joint_x + 30}" y1="{joint_y - PITCH}" x2="{joint_x + 70}" y2="{joint_y - PITCH - 30}" '
           f'stroke="#374151" stroke-width="0.8"/>')
svg.append(f'<text x="{joint_x + 75}" y="{joint_y - PITCH - 28}" font-size="11" font-weight="700" fill="#231F20">3 x Ø3.8mm holes</text>')
svg.append(f'<text x="{joint_x + 75}" y="{joint_y - PITCH - 14}" font-size="10" fill="#374151">on B1, perpendicular to chord length</text>')
svg.append(f'<text x="{joint_x + 75}" y="{joint_y - PITCH}" font-size="10" fill="#374151">17mm pitch — one rollformer fire</text>')

# 3-hole cluster on W10 — perpendicular to W10's length = HORIZONTAL line of 3 holes
# But we already drew W10 over B1, so the W10 holes coincide spatially with B1 holes when assembled.
# To show W10's holes distinctly, draw a small INSET to the right showing W10 alone with its 3 holes.

# INSET: W10 alone with its 3 horizontal holes
inset_x = DA_X + DA_W - 280
inset_y = DA_Y + 30
inset_w = 250
inset_h = 200
svg.append(f'<rect x="{inset_x}" y="{inset_y}" width="{inset_w}" height="{inset_h}" '
           f'fill="#fefce8" stroke="#a16207" stroke-width="1.2" rx="4"/>')
svg.append(f'<text x="{inset_x + 10}" y="{inset_y + 18}" font-size="11" font-weight="700" fill="#713f12">W10 stick on its own (after rollformer)</text>')
svg.append(f'<text x="{inset_x + 10}" y="{inset_y + 32}" font-size="9" fill="#713f12">holes perpendicular to W10\'s length</text>')

# Draw W10 alone in the inset, oriented vertically
inset_stick_x = inset_x + inset_w/2
inset_top = inset_y + 50
inset_bot = inset_y + inset_h - 30
inset_half = 25
svg.append(f'<rect x="{inset_stick_x - inset_half}" y="{inset_top}" width="{2*inset_half}" '
           f'height="{inset_bot - inset_top}" fill="url(#steelV)" stroke="#475569" stroke-width="1"/>')
svg.append(f'<line x1="{inset_stick_x}" y1="{inset_top + 4}" x2="{inset_stick_x}" y2="{inset_bot - 4}" '
           f'stroke="#1e40af" stroke-width="1" stroke-dasharray="3,2"/>')

# 3 holes on W10 inset — at 30mm from top end, three holes ACROSS the web (horizontal)
hole_y_inset = inset_top + 30 * SCALE * 0.4  # compressed for inset
for dx in [-PITCH * 0.6, 0, PITCH * 0.6]:
    svg.append(f'<circle cx="{inset_stick_x + dx}" cy="{hole_y_inset}" r="3.2" '
               f'fill="#231F20" stroke="#FFCB05" stroke-width="1"/>')
svg.append(f'<text x="{inset_stick_x - 60}" y="{hole_y_inset + 4}" font-size="9" fill="#374151">30mm</text>')
svg.append(f'<line x1="{inset_stick_x - 32}" y1="{hole_y_inset}" x2="{inset_stick_x - 14}" y2="{hole_y_inset}" '
           f'stroke="#374151" stroke-width="0.8" marker-end="url(#arrowDim)"/>')

# Bottom annotation in main panel
foot_y = DA_Y + DA_H - 30
svg.append(f'<text x="{DA_X + DA_W/2}" y="{foot_y}" text-anchor="middle" font-size="11" font-style="italic" fill="#1a202c">'
           'When assembled, both 3-hole clusters share the SAME point in space — bolts pass through both sticks.'
           '</text>')

# ============== PANEL 2: WEB HOLE TOOL ==============
P2_X, P2_Y, P2_W, P2_H = 1060, 80, 610, 220
svg.append(f'<rect x="{P2_X}" y="{P2_Y}" width="{P2_W}" height="{P2_H}" fill="white" stroke="#cbd5e1" stroke-width="1.5" rx="6"/>')
svg.append(f'<text x="{P2_X + 20}" y="{P2_Y + 28}" font-size="16" font-weight="700" fill="#1a202c">2 &#160; WEB HOLE tool — one fire, three holes</text>')
svg.append(f'<text x="{P2_X + 20}" y="{P2_Y + 46}" font-size="11" fill="#4a5568">F300i has a station with three Ø3.8mm punches in a line. One machine cycle = three physical holes.</text>')

# Tool schematic
tool_y = P2_Y + 110
tool_cx = P2_X + 200
PUNCH_PITCH = 60
PUNCH_R = 14

# Tool body
svg.append(f'<rect x="{tool_cx - 130}" y="{tool_y - 40}" width="260" height="80" fill="#475569" stroke="#1e293b" stroke-width="2" rx="6"/>')
svg.append(f'<text x="{tool_cx}" y="{tool_y - 22}" text-anchor="middle" font-size="10" font-weight="700" fill="white">F300i WEB HOLE STATION</text>')

# Three punches
for i, dx in enumerate([-PUNCH_PITCH, 0, PUNCH_PITCH]):
    svg.append(f'<rect x="{tool_cx + dx - PUNCH_R/2}" y="{tool_y - 5}" width="{PUNCH_R}" height="35" fill="#fbbf24" stroke="#92400e" stroke-width="1.5"/>')
    svg.append(f'<polygon points="{tool_cx + dx},{tool_y + 38} {tool_cx + dx - 5},{tool_y + 30} {tool_cx + dx + 5},{tool_y + 30}" fill="#92400e"/>')

# Pitch dimensions
dim_y = tool_y + 60
svg.append(f'<line x1="{tool_cx - PUNCH_PITCH}" y1="{dim_y}" x2="{tool_cx}" y2="{dim_y}" stroke="#374151" stroke-width="0.8" marker-start="url(#arrowDim)" marker-end="url(#arrowDim)"/>')
svg.append(f'<text x="{tool_cx - PUNCH_PITCH/2}" y="{dim_y - 4}" text-anchor="middle" font-size="10" font-weight="700" fill="#374151">17mm</text>')
svg.append(f'<line x1="{tool_cx}" y1="{dim_y}" x2="{tool_cx + PUNCH_PITCH}" y2="{dim_y}" stroke="#374151" stroke-width="0.8" marker-start="url(#arrowDim)" marker-end="url(#arrowDim)"/>')
svg.append(f'<text x="{tool_cx + PUNCH_PITCH/2}" y="{dim_y - 4}" text-anchor="middle" font-size="10" font-weight="700" fill="#374151">17mm</text>')

# Resulting holes on stock (below)
stock_y = dim_y + 30
svg.append(f'<rect x="{tool_cx - 130}" y="{stock_y}" width="260" height="50" fill="url(#steel)" stroke="#475569" stroke-width="1"/>')
for dx in [-PUNCH_PITCH, 0, PUNCH_PITCH]:
    svg.append(f'<circle cx="{tool_cx + dx}" cy="{stock_y + 25}" r="5" fill="#231F20" stroke="#FFCB05" stroke-width="1"/>')

# Spec column right
spec_x = P2_X + 380
svg.append(f'<text x="{spec_x}" y="{P2_Y + 75}" font-size="11" font-weight="700" fill="#1a202c">Tool spec</text>')
svg.append(f'<text x="{spec_x}" y="{P2_Y + 95}" font-size="11" fill="#374151">• Hole diameter: <tspan font-weight="700">Ø3.8mm</tspan></text>')
svg.append(f'<text x="{spec_x}" y="{P2_Y + 113}" font-size="11" fill="#374151">• Punches per fire: <tspan font-weight="700">3</tspan></text>')
svg.append(f'<text x="{spec_x}" y="{P2_Y + 131}" font-size="11" fill="#374151">• Pitch: <tspan font-weight="700">17mm</tspan></text>')
svg.append(f'<text x="{spec_x}" y="{P2_Y + 149}" font-size="11" fill="#374151">• Fastener: <tspan font-weight="700">M3.5</tspan> structural screw</text>')
svg.append(f'<text x="{spec_x}" y="{P2_Y + 167}" font-size="11" fill="#374151">• Material: <tspan font-weight="700">0.75mm AZ150 G550</tspan></text>')
svg.append(f'<text x="{spec_x}" y="{P2_Y + 190}" font-size="10" font-style="italic" fill="#64748b">Three M3.5 screws → ~2x safety</text>')
svg.append(f'<text x="{spec_x}" y="{P2_Y + 204}" font-size="10" font-style="italic" fill="#64748b">factor on shear demand per joint</text>')

# ============== PANEL 3: BOLT THROUGH BOTH ==============
P3_X, P3_Y, P3_W, P3_H = 1060, 320, 610, 220
svg.append(f'<rect x="{P3_X}" y="{P3_Y}" width="{P3_W}" height="{P3_H}" fill="white" stroke="#cbd5e1" stroke-width="1.5" rx="6"/>')
svg.append(f'<text x="{P3_X + 20}" y="{P3_Y + 28}" font-size="16" font-weight="700" fill="#1a202c">3 &#160; ASSEMBLED — bolt passes through both sticks</text>')
svg.append(f'<text x="{P3_X + 20}" y="{P3_Y + 46}" font-size="11" fill="#4a5568">Cross-section through one screw. Three of these per joint = the bolted connection.</text>')

# Cross-section: stack two C-sections vertically, screw through both
xs_cx = P3_X + 250
xs_cy = P3_Y + 130

# Bottom stick (B1) — horizontal C profile seen end-on, viewed in cross-section
B_W, B_T = 89 * 1.2, 0.75 * 6  # exaggerate thickness for visibility
b1_xs_y = xs_cy + 30
svg.append(f'<rect x="{xs_cx - B_W/2}" y="{b1_xs_y}" width="{B_W}" height="{B_T}" fill="#94a3b8" stroke="#1e293b" stroke-width="1.5"/>')
svg.append(f'<text x="{xs_cx - B_W/2 - 8}" y="{b1_xs_y + B_T + 4}" text-anchor="end" font-size="10" font-weight="700" fill="#1a202c">B1</text>')

# Top stick (W10) — also horizontal seen end-on, but on top
w10_xs_y = xs_cy + 30 - B_T - 4
svg.append(f'<rect x="{xs_cx - B_W/2}" y="{w10_xs_y}" width="{B_W}" height="{B_T}" fill="#94a3b8" stroke="#1e293b" stroke-width="1.5"/>')
svg.append(f'<text x="{xs_cx - B_W/2 - 8}" y="{w10_xs_y + B_T + 4}" text-anchor="end" font-size="10" font-weight="700" fill="#1a202c">W10</text>')

# M3.5 screw through both
screw_top = w10_xs_y - 30
screw_bot = b1_xs_y + B_T + 30
SCREW_R = 3.5 * 1.4
# Head
svg.append(f'<rect x="{xs_cx - SCREW_R*1.6}" y="{screw_top - 12}" width="{SCREW_R*3.2}" height="12" fill="#231F20" rx="2"/>')
# Shank
svg.append(f'<rect x="{xs_cx - SCREW_R/2}" y="{screw_top}" width="{SCREW_R}" height="{screw_bot - screw_top}" fill="#231F20"/>')
# Threads (small ticks)
for ty in range(int(screw_top + 6), int(screw_bot), 4):
    svg.append(f'<line x1="{xs_cx - SCREW_R}" y1="{ty}" x2="{xs_cx + SCREW_R}" y2="{ty}" stroke="#fbbf24" stroke-width="0.5"/>')
# Point
svg.append(f'<polygon points="{xs_cx},{screw_bot + 8} {xs_cx - SCREW_R/2},{screw_bot} {xs_cx + SCREW_R/2},{screw_bot}" fill="#231F20"/>')

# Labels
svg.append(f'<text x="{xs_cx + 70}" y="{screw_top - 2}" font-size="11" font-weight="700" fill="#1a202c">M3.5 structural screw</text>')
svg.append(f'<text x="{xs_cx + 70}" y="{xs_cy + 30}" font-size="10" fill="#374151">passes through W10\'s flange</text>')
svg.append(f'<text x="{xs_cx + 70}" y="{xs_cy + 44}" font-size="10" fill="#374151">into B1\'s flange — joint complete</text>')
svg.append(f'<text x="{xs_cx + 70}" y="{xs_cy + 68}" font-size="10" font-style="italic" fill="#16a34a" font-weight="700">x 3 (one for each hole in cluster)</text>')

# ============== PANEL 4: RULES IN ACTION ==============
P4_X, P4_Y, P4_W, P4_H = 30, 820, 1640, 320
svg.append(f'<rect x="{P4_X}" y="{P4_Y}" width="{P4_W}" height="{P4_H}" fill="white" stroke="#cbd5e1" stroke-width="1.5" rx="6"/>')
svg.append(f'<text x="{P4_X + 20}" y="{P4_Y + 28}" font-size="16" font-weight="700" fill="#1a202c">4 &#160; RULES IN ACTION — when the bare centreline rule needs to be modified</text>')

# Sub-panel coords
SP_W = 380
SP_H = 240
SP_Y = P4_Y + 50
SP_GAP = 28
SP_PAD = 30

# Sub 4a: W↔W skip
sa_x = P4_X + SP_PAD
svg.append(f'<rect x="{sa_x}" y="{SP_Y}" width="{SP_W}" height="{SP_H}" fill="#fef2f2" stroke="#dc2626" stroke-width="1.2" rx="4"/>')
svg.append(f'<text x="{sa_x + 12}" y="{SP_Y + 22}" font-size="13" font-weight="700" fill="#7f1d1d">W↔W skip</text>')
svg.append(f'<text x="{sa_x + 12}" y="{SP_Y + 38}" font-size="10" fill="#7f1d1d">Two webs that mathematically cross mid-air don\'t actually fasten — webs only bolt to chords.</text>')

# Drawing: two webs crossing X
sx_cx = sa_x + SP_W/2
sx_cy = SP_Y + 130
svg.append(f'<line x1="{sx_cx - 70}" y1="{sx_cy - 50}" x2="{sx_cx + 70}" y2="{sx_cy + 50}" stroke="#94a3b8" stroke-width="14"/>')
svg.append(f'<line x1="{sx_cx + 70}" y1="{sx_cy - 50}" x2="{sx_cx - 70}" y2="{sx_cy + 50}" stroke="#94a3b8" stroke-width="14"/>')
svg.append(f'<line x1="{sx_cx - 70}" y1="{sx_cy - 50}" x2="{sx_cx + 70}" y2="{sx_cy + 50}" stroke="#1e40af" stroke-width="1" stroke-dasharray="4,3"/>')
svg.append(f'<line x1="{sx_cx + 70}" y1="{sx_cy - 50}" x2="{sx_cx - 70}" y2="{sx_cy + 50}" stroke="#1e40af" stroke-width="1" stroke-dasharray="4,3"/>')
svg.append(f'<text x="{sx_cx - 90}" y="{sx_cy - 56}" font-size="11" font-weight="700" fill="#1e40af">W6</text>')
svg.append(f'<text x="{sx_cx + 76}" y="{sx_cy - 56}" font-size="11" font-weight="700" fill="#1e40af">W7</text>')
# Big red X over the intersection
svg.append(f'<circle cx="{sx_cx}" cy="{sx_cy}" r="22" fill="white" stroke="#dc2626" stroke-width="3"/>')
svg.append(f'<line x1="{sx_cx - 14}" y1="{sx_cy - 14}" x2="{sx_cx + 14}" y2="{sx_cy + 14}" stroke="#dc2626" stroke-width="3.5"/>')
svg.append(f'<line x1="{sx_cx + 14}" y1="{sx_cy - 14}" x2="{sx_cx - 14}" y2="{sx_cy + 14}" stroke="#dc2626" stroke-width="3.5"/>')
svg.append(f'<text x="{sx_cx}" y="{SP_Y + SP_H - 18}" text-anchor="middle" font-size="11" font-weight="700" fill="#7f1d1d">no joint emitted</text>')

# Sub 4b: Apex collision dedup
sb_x = sa_x + SP_W + SP_GAP
svg.append(f'<rect x="{sb_x}" y="{SP_Y}" width="{SP_W}" height="{SP_H}" fill="#fef3c7" stroke="#d97706" stroke-width="1.2" rx="4"/>')
svg.append(f'<text x="{sb_x + 12}" y="{SP_Y + 22}" font-size="13" font-weight="700" fill="#92400e">Apex collision dedup</text>')
svg.append(f'<text x="{sb_x + 12}" y="{SP_Y + 38}" font-size="10" fill="#92400e">Multiple webs converge to one point on the chord. Combine into ONE 3-hole cluster.</text>')

# Drawing: three webs into chord
sb_cx = sb_x + SP_W/2
sb_apex_y = SP_Y + 95
sb_chord_y = SP_Y + 165
# Chord horizontal
svg.append(f'<rect x="{sb_x + 30}" y="{sb_chord_y}" width="{SP_W - 60}" height="20" fill="url(#steel)" stroke="#475569" stroke-width="1"/>')
# Three webs
for dx in [-45, 0, 45]:
    svg.append(f'<line x1="{sb_cx + dx*0.4}" y1="{sb_apex_y}" x2="{sb_cx + dx}" y2="{sb_chord_y + 10}" stroke="#94a3b8" stroke-width="10"/>')
    svg.append(f'<text x="{sb_cx + dx*0.4 - 10}" y="{sb_apex_y - 4}" font-size="10" font-weight="700" fill="#1e40af">W{6+int((dx+45)/45)}</text>')
# One cluster (instead of three)
cluster_x = sb_cx
cluster_y = sb_chord_y + 10
for dx in [-PITCH * 0.4, 0, PITCH * 0.4]:
    svg.append(f'<circle cx="{cluster_x + dx}" cy="{cluster_y}" r="3.5" fill="#231F20" stroke="#FFCB05" stroke-width="1"/>')
svg.append(f'<text x="{sb_cx}" y="{SP_Y + SP_H - 18}" text-anchor="middle" font-size="11" font-weight="700" fill="#92400e">one cluster — joins W6+W7+W8</text>')

# Sub 4c: End-zone exclusion
sc_x = sb_x + SP_W + SP_GAP
svg.append(f'<rect x="{sc_x}" y="{SP_Y}" width="{SP_W}" height="{SP_H}" fill="#dbeafe" stroke="#1e40af" stroke-width="1.2" rx="4"/>')
svg.append(f'<text x="{sc_x + 12}" y="{SP_Y + 22}" font-size="13" font-weight="700" fill="#1e3a8a">End-zone exclusion (30mm)</text>')
svg.append(f'<text x="{sc_x + 12}" y="{SP_Y + 38}" font-size="10" fill="#1e3a8a">Hole within 30mm of either cut end → punch zone too tight. Stick FALLBACKs to FrameCAD\'s holes.</text>')

# Drawing: a stick with shaded end zones and one hole that lands in the dead zone
stick_x = sc_x + 25
stick_w = SP_W - 50
stick_y = SP_Y + 110
stick_h = 40
EZ_W = 50
svg.append(f'<rect x="{stick_x}" y="{stick_y}" width="{stick_w}" height="{stick_h}" fill="url(#steel)" stroke="#475569" stroke-width="1"/>')
# Dead zones
svg.append(f'<rect x="{stick_x}" y="{stick_y}" width="{EZ_W}" height="{stick_h}" fill="url(#hatch)" stroke="none" opacity="0.5"/>')
svg.append(f'<rect x="{stick_x + stick_w - EZ_W}" y="{stick_y}" width="{EZ_W}" height="{stick_h}" fill="url(#hatch)" stroke="none" opacity="0.5"/>')
svg.append(f'<text x="{stick_x + EZ_W/2}" y="{stick_y - 4}" text-anchor="middle" font-size="9" fill="#7f1d1d">30mm DEAD</text>')
svg.append(f'<text x="{stick_x + stick_w - EZ_W/2}" y="{stick_y - 4}" text-anchor="middle" font-size="9" fill="#7f1d1d">30mm DEAD</text>')

# A safe hole in the middle — green
safe_x = stick_x + stick_w * 0.55
svg.append(f'<circle cx="{safe_x}" cy="{stick_y + stick_h/2}" r="6" fill="#16a34a" stroke="white" stroke-width="1.5"/>')
svg.append(f'<text x="{safe_x}" y="{stick_y + stick_h + 16}" text-anchor="middle" font-size="9" font-weight="700" fill="#14532d">safe</text>')

# A bad hole near left end — red X
bad_x = stick_x + 25
svg.append(f'<circle cx="{bad_x}" cy="{stick_y + stick_h/2}" r="6" fill="white" stroke="#dc2626" stroke-width="2.5"/>')
svg.append(f'<line x1="{bad_x - 4}" y1="{stick_y + stick_h/2 - 4}" x2="{bad_x + 4}" y2="{stick_y + stick_h/2 + 4}" stroke="#dc2626" stroke-width="2"/>')
svg.append(f'<line x1="{bad_x + 4}" y1="{stick_y + stick_h/2 - 4}" x2="{bad_x - 4}" y2="{stick_y + stick_h/2 + 4}" stroke="#dc2626" stroke-width="2"/>')
svg.append(f'<text x="{bad_x}" y="{stick_y + stick_h + 16}" text-anchor="middle" font-size="9" font-weight="700" fill="#7f1d1d">FALLBACK</text>')

svg.append(f'<text x="{sc_x + SP_W/2}" y="{SP_Y + SP_H - 18}" text-anchor="middle" font-size="11" font-weight="700" fill="#1e3a8a">protects rollformer + steel edge</text>')

# Closing footer
svg.append(f'<text x="{W/2}" y="{H - 8}" text-anchor="middle" font-size="10" fill="#64748b">'
           'HYTEK Linear-truss simplifier — visual reference for engineering review.  '
           '15mm dimple margin / 900mm max gap / W↔W skip / 30mm end-zone / 17mm apex dedup'
           '</text>')

svg.append('</svg>')

with open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(svg))
print(f'Wrote {OUT}')
