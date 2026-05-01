"""Lifelike close-up of the LIP NOTCH operation on a real web stick.

Uses W6 from frame TN2-1: 2037.7mm long 89S41 stud with lip notches at
39.36mm (bottom-chord end) and 1997.02mm (top-chord end), plus the new
centreline-only bolt hole position.

Shows three views:
  1. Full stick elevation - whole 2037mm stick with all ops marked
  2. End-detail - close-up of the lip notch + bolt zone with real geometry
  3. Cross-section through the notch - showing what's cut and why

Geometry: 89mm web, 41mm flanges, 11mm lips, 0.75mm gauge.
"""
import os, math

OUT = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/lipnotch_detail.svg'

# Real W6 data from CSV
STICK_LEN = 2037.74
SWAGES = [27.5, 82.5, 137.5, 160.43, 1922.98, 1977.98, 2010.24]
LIP_NOTCHES = [39.36, 1997.02]
OLD_BOLTS = [56.73, 101.21, 1962.4, 1977.34, 1990.08]
NEW_BOLT_TOP = 2000   # approximate top chord crossing
NEW_BOLT_BOT = 40     # approximate bottom chord crossing

W = 1900
H = 1450
svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">')

# === Definitions ===
svg.append('''<defs>
  <!-- Steel surface gradient (gives 3D feel) -->
  <linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#f1f5f9"/>
    <stop offset="0.5" stop-color="#cbd5e0"/>
    <stop offset="1" stop-color="#94a3b8"/>
  </linearGradient>
  <linearGradient id="steel-dark" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#94a3b8"/>
    <stop offset="0.5" stop-color="#64748b"/>
    <stop offset="1" stop-color="#475569"/>
  </linearGradient>
  <linearGradient id="steel-flange" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#94a3b8"/>
    <stop offset="0.5" stop-color="#cbd5e0"/>
    <stop offset="1" stop-color="#94a3b8"/>
  </linearGradient>
  <linearGradient id="cut-surface" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#fbbf24"/>
    <stop offset="1" stop-color="#d97706"/>
  </linearGradient>
  <pattern id="hatch" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="#92400e" stroke-width="1"/>
  </pattern>
  <pattern id="cut-hatch" patternUnits="userSpaceOnUse" width="4" height="4" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="4" stroke="#dc2626" stroke-width="0.8"/>
  </pattern>
  <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
    <feOffset dx="2" dy="3"/>
    <feComponentTransfer><feFuncA type="linear" slope="0.3"/></feComponentTransfer>
    <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <marker id="ar" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
    <path d="M0,0 L9,4.5 L0,9 z" fill="#374151"/>
  </marker>
  <marker id="dot" markerWidth="6" markerHeight="6" refX="3" refY="3">
    <circle cx="3" cy="3" r="1.6" fill="#374151"/>
  </marker>
</defs>''')

# Background
svg.append(f'<rect width="{W}" height="{H}" fill="#fafaf8"/>')

# Title
svg.append(f'<text x="30" y="38" font-size="24" font-weight="700" fill="#1a202c">Lip Notch tool — lifelike detail</text>')
svg.append(f'<text x="30" y="62" font-size="14" fill="#4a5568">Web W6 of frame TN2-1 · 89S41-0.75 stud · 2037.74 mm long · two lip notches at 39.36mm and 1997.02mm</text>')

# ========== PANEL 1: Full elevation ==========
P1_X = 30
P1_Y = 90
P1_W = W - 60
P1_H = 230
svg.append(f'<rect x="{P1_X}" y="{P1_Y}" width="{P1_W}" height="{P1_H}" fill="white" stroke="#cbd5e0" rx="4"/>')
svg.append(f'<text x="{P1_X+15}" y="{P1_Y+22}" font-size="14" font-weight="700" fill="#1a202c">1.  Full stick elevation (W6 length 2037.74 mm) · ops shown to scale</text>')

# Scale: stick fits in P1_W - 100 px wide
stick_scale = (P1_W - 220) / STICK_LEN  # mm to px
stick_x0 = P1_X + 100
stick_x1 = stick_x0 + STICK_LEN * stick_scale
stick_y_centre = P1_Y + 130
stick_h_px = 89 * stick_scale * 6   # exaggerate vertical
stick_h_px = 50  # fixed height for visibility

# Stick body (web face seen from side)
svg.append(f'<rect x="{stick_x0}" y="{stick_y_centre - stick_h_px/2}" width="{STICK_LEN*stick_scale}" height="{stick_h_px}" fill="url(#steel)" stroke="#475569" stroke-width="1.5"/>')

# Lip edges (visible at top + bottom of stick in this view)
svg.append(f'<line x1="{stick_x0}" y1="{stick_y_centre - stick_h_px/2 + 4}" x2="{stick_x1}" y2="{stick_y_centre - stick_h_px/2 + 4}" stroke="#475569" stroke-width="0.8" opacity="0.6"/>')
svg.append(f'<line x1="{stick_x0}" y1="{stick_y_centre + stick_h_px/2 - 4}" x2="{stick_x1}" y2="{stick_y_centre + stick_h_px/2 - 4}" stroke="#475569" stroke-width="0.8" opacity="0.6"/>')

# Centreline
svg.append(f'<line x1="{stick_x0-15}" y1="{stick_y_centre}" x2="{stick_x1+15}" y2="{stick_y_centre}" stroke="#374151" stroke-width="0.8" stroke-dasharray="5 3" opacity="0.5"/>')

# End labels
svg.append(f'<text x="{stick_x0-12}" y="{stick_y_centre+5}" text-anchor="end" font-size="11" fill="#374151">start</text>')
svg.append(f'<text x="{stick_x1+12}" y="{stick_y_centre+5}" text-anchor="start" font-size="11" fill="#374151">end</text>')
svg.append(f'<text x="{stick_x0-12}" y="{stick_y_centre+19}" text-anchor="end" font-size="10" fill="#6b7280">0 mm</text>')
svg.append(f'<text x="{stick_x1+12}" y="{stick_y_centre+19}" text-anchor="start" font-size="10" fill="#6b7280">2037.74 mm</text>')

def x_at(mm): return stick_x0 + mm * stick_scale

# Draw swages — small dimples on the stick body
for s in SWAGES:
    x = x_at(s)
    svg.append(f'<circle cx="{x:.1f}" cy="{stick_y_centre}" r="3" fill="#7c3aed" stroke="#5b21b6" stroke-width="0.8"/>')

# Draw old (CSV) bolt holes - red small dots above stick
for b in OLD_BOLTS:
    x = x_at(b)
    svg.append(f'<circle cx="{x:.1f}" cy="{stick_y_centre - 24}" r="3.5" fill="#dc2626" stroke="#7f1d1d" stroke-width="0.8" opacity="0.4"/>')

# Draw NEW single bolt holes - green
for b in [NEW_BOLT_BOT, NEW_BOLT_TOP]:
    x = x_at(b)
    svg.append(f'<circle cx="{x:.1f}" cy="{stick_y_centre - 24}" r="5.5" fill="#16a34a" stroke="#14532d" stroke-width="1.4"/>')
    svg.append(f'<line x1="{x:.1f}" y1="{stick_y_centre - 19}" x2="{x:.1f}" y2="{stick_y_centre - 4}" stroke="#16a34a" stroke-width="1" stroke-dasharray="2 2"/>')

# Draw lip notches as small wedges at the lip edge (top edge of stick body)
for ln in LIP_NOTCHES:
    x = x_at(ln)
    # cut wedge into top edge
    svg.append(f'<polygon points="{x-6:.1f},{stick_y_centre-stick_h_px/2} {x+6:.1f},{stick_y_centre-stick_h_px/2} {x:.1f},{stick_y_centre-stick_h_px/2+10}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.2"/>')
    svg.append(f'<polygon points="{x-6:.1f},{stick_y_centre+stick_h_px/2} {x+6:.1f},{stick_y_centre+stick_h_px/2} {x:.1f},{stick_y_centre+stick_h_px/2-10}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.2"/>')

# Legend at right of panel 1
lx = P1_X + P1_W - 95
ly = P1_Y + 45
svg.append(f'<rect x="{lx}" y="{ly}" width="85" height="160" fill="#f8fafc" stroke="#e2e8f0" rx="3"/>')
svg.append(f'<text x="{lx+8}" y="{ly+16}" font-size="11" font-weight="700" fill="#1a202c">Legend</text>')
svg.append(f'<circle cx="{lx+15}" cy="{ly+34}" r="3" fill="#7c3aed"/>')
svg.append(f'<text x="{lx+24}" y="{ly+38}" font-size="10" fill="#374151">Swage</text>')
svg.append(f'<circle cx="{lx+15}" cy="{ly+54}" r="3.5" fill="#dc2626" opacity="0.4"/>')
svg.append(f'<text x="{lx+24}" y="{ly+58}" font-size="10" fill="#374151">Old bolt</text>')
svg.append(f'<circle cx="{lx+15}" cy="{ly+74}" r="5" fill="#16a34a" stroke="#14532d" stroke-width="1.2"/>')
svg.append(f'<text x="{lx+24}" y="{ly+78}" font-size="10" fill="#374151">NEW bolt</text>')
svg.append(f'<polygon points="{lx+9},{ly+92} {lx+21},{ly+92} {lx+15},{ly+101}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="0.8"/>')
svg.append(f'<text x="{lx+24}" y="{ly+101}" font-size="10" fill="#374151">Lip notch</text>')

# Annotation labels for ops
svg.append(f'<text x="{x_at(LIP_NOTCHES[0]):.1f}" y="{stick_y_centre+stick_h_px/2+18}" text-anchor="middle" font-size="10" fill="#dc2626" font-weight="600">LIP NOTCH @ 39.36</text>')
svg.append(f'<text x="{x_at(LIP_NOTCHES[1]):.1f}" y="{stick_y_centre-stick_h_px/2-12}" text-anchor="middle" font-size="10" fill="#dc2626" font-weight="600">LIP NOTCH @ 1997.02</text>')
svg.append(f'<text x="{x_at(NEW_BOLT_BOT):.1f}" y="{stick_y_centre-44}" text-anchor="middle" font-size="10" fill="#14532d" font-weight="700">BOLT @ 40 (centreline)</text>')
svg.append(f'<text x="{x_at(NEW_BOLT_TOP):.1f}" y="{stick_y_centre-44}" text-anchor="middle" font-size="10" fill="#14532d" font-weight="700">BOLT @ 2000 (centreline)</text>')

# Indicator arrow showing what we'll zoom on
zoom_x = x_at(LIP_NOTCHES[1])
svg.append(f'<line x1="{zoom_x}" y1="{stick_y_centre+stick_h_px/2+30}" x2="{zoom_x}" y2="{P1_Y+P1_H-2}" stroke="#374151" stroke-width="1.2" stroke-dasharray="4 3" marker-end="url(#ar)"/>')
svg.append(f'<text x="{zoom_x+10}" y="{P1_Y+P1_H-15}" font-size="11" fill="#374151" font-weight="600">zoom in below ↓</text>')

# ========== PANEL 2: End detail with C-section perspective ==========
P2_X = 30
P2_Y = P1_Y + P1_H + 20
P2_W = (W - 70) // 2
P2_H = 480
svg.append(f'<rect x="{P2_X}" y="{P2_Y}" width="{P2_W}" height="{P2_H}" fill="white" stroke="#cbd5e0" rx="4"/>')
svg.append(f'<text x="{P2_X+15}" y="{P2_Y+22}" font-size="14" font-weight="700" fill="#1a202c">2.  End detail — top-chord end of W6 (real proportions, 1mm = 4px)</text>')
svg.append(f'<text x="{P2_X+15}" y="{P2_Y+40}" font-size="12" fill="#4a5568">Last 60mm of stick · lip notch + bolt zone · drawn at 4× actual size</text>')

# 4 px per mm
MM = 4
# Show last 60mm of stick
zone_mm = 60  # last 60mm
view_x0 = P2_X + 50
view_y_top = P2_Y + 80
view_y_bot = view_y_top + 89*MM

# The end of stick is at right side
zone_px = zone_mm * MM
end_x = view_x0 + zone_px
start_x = view_x0

# Draw the C-section profile (89×41×11) viewed in elevation (web face visible)
# In elevation the lip is visible as a thin strip at each edge
# Top flange + lip
svg.append(f'<rect x="{start_x}" y="{view_y_top}" width="{zone_px}" height="{89*MM}" fill="url(#steel)" stroke="#475569" stroke-width="1.5"/>')

# Lip strips (the lip looks like a thin band at top and bottom edges)
LIP_W = 11 * MM  # we draw lip as a strip 11mm wide visible at edge
svg.append(f'<rect x="{start_x}" y="{view_y_top}" width="{zone_px}" height="{LIP_W}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1.2" opacity="0.9"/>')
svg.append(f'<rect x="{start_x}" y="{view_y_bot - LIP_W}" width="{zone_px}" height="{LIP_W}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1.2" opacity="0.9"/>')

# Show the centreline
svg.append(f'<line x1="{start_x-10}" y1="{(view_y_top+view_y_bot)/2}" x2="{end_x+10}" y2="{(view_y_top+view_y_bot)/2}" stroke="#374151" stroke-width="0.8" stroke-dasharray="5 3" opacity="0.5"/>')

# The lip notch — at position 1997.02 from start, but we're looking at last 60mm,
# so position from end = 2037.74 - 1997.02 = 40.72mm from end
# In our view: notch is at zone_px - 40.72*MM
notch_pos_from_end = STICK_LEN - 1997.02  # 40.72mm from cut end
notch_x = end_x - notch_pos_from_end * MM
notch_w = 12 * MM   # lip notch is typically ~12mm long
notch_h = 8 * MM    # cut depth into the lip about 8mm

# Top lip notch
svg.append(f'<rect x="{notch_x - notch_w/2}" y="{view_y_top}" width="{notch_w}" height="{notch_h}" fill="white" stroke="#dc2626" stroke-width="1.5"/>')
svg.append(f'<rect x="{notch_x - notch_w/2}" y="{view_y_top}" width="{notch_w}" height="{notch_h}" fill="url(#cut-hatch)" opacity="0.6"/>')
# Bottom lip notch
svg.append(f'<rect x="{notch_x - notch_w/2}" y="{view_y_bot - notch_h}" width="{notch_w}" height="{notch_h}" fill="white" stroke="#dc2626" stroke-width="1.5"/>')
svg.append(f'<rect x="{notch_x - notch_w/2}" y="{view_y_bot - notch_h}" width="{notch_w}" height="{notch_h}" fill="url(#cut-hatch)" opacity="0.6"/>')

# The bolt hole at centreline crossing — 40mm from end
# That's at end_x - 40*MM
bolt_x = end_x - 40 * MM
bolt_y = (view_y_top + view_y_bot) / 2
bolt_r = 6 * MM / 2   # 6mm dia M6 hole
svg.append(f'<circle cx="{bolt_x}" cy="{bolt_y}" r="{bolt_r:.1f}" fill="white" stroke="#16a34a" stroke-width="2"/>')
svg.append(f'<circle cx="{bolt_x}" cy="{bolt_y}" r="{bolt_r-1:.1f}" fill="none" stroke="#16a34a" stroke-width="1" stroke-dasharray="2 1.5"/>')

# Cut end of stick
svg.append(f'<line x1="{end_x}" y1="{view_y_top-10}" x2="{end_x}" y2="{view_y_bot+10}" stroke="#374151" stroke-width="2"/>')
svg.append(f'<text x="{end_x+8}" y="{view_y_top-3}" font-size="11" fill="#374151" font-weight="600">cut end</text>')

# Dimension lines & labels
# 89mm vertical
dim_x = start_x - 22
svg.append(f'<line x1="{dim_x}" y1="{view_y_top}" x2="{dim_x}" y2="{view_y_bot}" stroke="#374151" stroke-width="0.8" marker-start="url(#ar)" marker-end="url(#ar)"/>')
svg.append(f'<text x="{dim_x-6}" y="{(view_y_top+view_y_bot)/2+4}" text-anchor="end" font-size="11" fill="#374151">89 mm</text>')
# Lip 11mm
svg.append(f'<line x1="{end_x+15}" y1="{view_y_top}" x2="{end_x+15}" y2="{view_y_top+LIP_W}" stroke="#374151" stroke-width="0.8" marker-start="url(#ar)" marker-end="url(#ar)"/>')
svg.append(f'<text x="{end_x+19}" y="{view_y_top+LIP_W/2+4}" font-size="10" fill="#374151">11 mm lip</text>')

# Bolt distance from cut end
svg.append(f'<line x1="{bolt_x}" y1="{view_y_bot+18}" x2="{end_x}" y2="{view_y_bot+18}" stroke="#16a34a" stroke-width="1" marker-start="url(#ar)" marker-end="url(#ar)"/>')
svg.append(f'<text x="{(bolt_x+end_x)/2}" y="{view_y_bot+34}" text-anchor="middle" font-size="11" fill="#14532d" font-weight="700">40 mm (centreline crossing)</text>')

# Lip notch distance from end
svg.append(f'<line x1="{notch_x}" y1="{view_y_bot+50}" x2="{end_x}" y2="{view_y_bot+50}" stroke="#dc2626" stroke-width="1" marker-start="url(#ar)" marker-end="url(#ar)"/>')
svg.append(f'<text x="{(notch_x+end_x)/2}" y="{view_y_bot+66}" text-anchor="middle" font-size="11" fill="#7f1d1d" font-weight="700">40.72 mm to notch centre</text>')

# Annotations
svg.append(f'<text x="{notch_x}" y="{view_y_top - 8}" text-anchor="middle" font-size="11" fill="#7f1d1d" font-weight="700">LIP NOTCH cut</text>')
svg.append(f'<text x="{notch_x}" y="{view_y_top - 22}" text-anchor="middle" font-size="9" fill="#7f1d1d">~12mm wide × 8mm deep</text>')
svg.append(f'<text x="{bolt_x}" y="{bolt_y - bolt_r - 8}" text-anchor="middle" font-size="11" fill="#14532d" font-weight="700">M6 bolt (Ø6 hole)</text>')

# Caption
cap_y = P2_Y + P2_H - 80
svg.append(f'<rect x="{P2_X+15}" y="{cap_y}" width="{P2_W-30}" height="60" fill="#fef9c3" stroke="#ca8a04" rx="3"/>')
svg.append(f'<text x="{P2_X+25}" y="{cap_y+18}" font-size="12" font-weight="700" fill="#713f12">What you are seeing in this view:</text>')
svg.append(f'<text x="{P2_X+25}" y="{cap_y+34}" font-size="11" fill="#713f12">• Lip notch is a rectangular cut into the lip strip at the edge of the C-section,</text>')
svg.append(f'<text x="{P2_X+25}" y="{cap_y+48}" font-size="11" fill="#713f12">  ~40mm from the cut end. Same notch on top + bottom lips. Lets stick fit past chord flange.</text>')

# ========== PANEL 3: Cross-section perspective ==========
P3_X = P2_X + P2_W + 10
P3_Y = P2_Y
P3_W = W - P3_X - 30
P3_H = P2_H
svg.append(f'<rect x="{P3_X}" y="{P3_Y}" width="{P3_W}" height="{P3_H}" fill="white" stroke="#cbd5e0" rx="4"/>')
svg.append(f'<text x="{P3_X+15}" y="{P3_Y+22}" font-size="14" font-weight="700" fill="#1a202c">3.  3D-ish view — what the lip notch looks like on the actual section</text>')
svg.append(f'<text x="{P3_X+15}" y="{P3_Y+40}" font-size="12" fill="#4a5568">Looking at the end of the stick at an angle. C-section opens to the right.</text>')

# Draw isometric-ish view of the C-section near its cut end
iso_cx = P3_X + P3_W/2
iso_cy = P3_Y + P3_H/2 + 10

# Isometric scale factors
ISO = 1.7  # mm per px
SKEW = 0.5  # how much depth tilts back

# Define key points of the C-section in 3D space
# Web is the BACK face, flanges go forward, lips go inward toward each other
# Coordinates: x=stick-length (along stick), y=web-direction, z=depth (toward viewer)

def iso_proj(x, y, z):
    """Project 3D point to 2D iso view."""
    px = iso_cx + (x - z*0.6) * ISO
    py = iso_cy + (y + z*0.5) * ISO
    return (px, py)

# Stick local axes:
# x = along stick length (we'll show last 70mm)
# y = along web (top/bot) - 89mm extent
# z = perpendicular to web (depth) - flange direction

# Show last 70mm of stick in isometric
# Flanges are 41mm deep (z direction)
# Lips are 11mm tall (back into y direction at the flange top)

stick_end_x = 0       # cut end
stick_back_x = -70    # 70mm back from cut end

# Web face polygon (back face)
p1 = iso_proj(stick_back_x, -44.5, 0)   # back top
p2 = iso_proj(stick_end_x, -44.5, 0)    # cut top
p3 = iso_proj(stick_end_x, 44.5, 0)     # cut bottom
p4 = iso_proj(stick_back_x, 44.5, 0)    # back bottom
svg.append(f'<polygon points="{p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f} {p4[0]:.1f},{p4[1]:.1f}" fill="url(#steel)" stroke="#475569" stroke-width="1.5"/>')

# Top flange (extends forward 41mm in z)
t1 = iso_proj(stick_back_x, -44.5, 0)
t2 = iso_proj(stick_end_x, -44.5, 0)
t3 = iso_proj(stick_end_x, -44.5, 41)
t4 = iso_proj(stick_back_x, -44.5, 41)
svg.append(f'<polygon points="{t1[0]:.1f},{t1[1]:.1f} {t2[0]:.1f},{t2[1]:.1f} {t3[0]:.1f},{t3[1]:.1f} {t4[0]:.1f},{t4[1]:.1f}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1.2"/>')
# Bottom flange
b1 = iso_proj(stick_back_x, 44.5, 0)
b2 = iso_proj(stick_end_x, 44.5, 0)
b3 = iso_proj(stick_end_x, 44.5, 41)
b4 = iso_proj(stick_back_x, 44.5, 41)
svg.append(f'<polygon points="{b1[0]:.1f},{b1[1]:.1f} {b2[0]:.1f},{b2[1]:.1f} {b3[0]:.1f},{b3[1]:.1f} {b4[0]:.1f},{b4[1]:.1f}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1.2"/>')

# Top LIP (returns 11mm back toward web at the front of flange)
# Lip is at z=41 going from y=-44.5 to y=-44.5+11
l1 = iso_proj(stick_back_x, -44.5, 41)
l2 = iso_proj(stick_end_x, -44.5, 41)
l3 = iso_proj(stick_end_x, -44.5+11, 41)
l4 = iso_proj(stick_back_x, -44.5+11, 41)
# But we'll cut a notch in this lip
notch_start_x = -52     # 52mm back from end
notch_end_x = -40       # 40mm back from end (12mm long notch)
# Lip is split into 3 parts: back-of-notch, NOTCHED-OUT, front-to-end
# Part 1 (left of notch)
svg.append(f'<polygon points="{l1[0]:.1f},{l1[1]:.1f} {iso_proj(notch_start_x,-44.5,41)[0]:.1f},{iso_proj(notch_start_x,-44.5,41)[1]:.1f} {iso_proj(notch_start_x,-44.5+11,41)[0]:.1f},{iso_proj(notch_start_x,-44.5+11,41)[1]:.1f} {l4[0]:.1f},{l4[1]:.1f}" fill="url(#steel-dark)" stroke="#475569" stroke-width="1.2"/>')
# Part 2 (right of notch, near cut end)
svg.append(f'<polygon points="{iso_proj(notch_end_x,-44.5,41)[0]:.1f},{iso_proj(notch_end_x,-44.5,41)[1]:.1f} {l2[0]:.1f},{l2[1]:.1f} {l3[0]:.1f},{l3[1]:.1f} {iso_proj(notch_end_x,-44.5+11,41)[0]:.1f},{iso_proj(notch_end_x,-44.5+11,41)[1]:.1f}" fill="url(#steel-dark)" stroke="#475569" stroke-width="1.2"/>')

# Show the notch as a CUT — show the bare flange where the lip used to be
notch_floor_a = iso_proj(notch_start_x, -44.5, 41)
notch_floor_b = iso_proj(notch_end_x, -44.5, 41)
notch_floor_c = iso_proj(notch_end_x, -44.5+11, 41)
notch_floor_d = iso_proj(notch_start_x, -44.5+11, 41)
svg.append(f'<polygon points="{notch_floor_a[0]:.1f},{notch_floor_a[1]:.1f} {notch_floor_b[0]:.1f},{notch_floor_b[1]:.1f} {notch_floor_c[0]:.1f},{notch_floor_c[1]:.1f} {notch_floor_d[0]:.1f},{notch_floor_d[1]:.1f}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.2"/>')

# Bottom lip (mirror of top, also notched)
bl1 = iso_proj(stick_back_x, 44.5, 41)
bl2 = iso_proj(stick_end_x, 44.5, 41)
bl3 = iso_proj(stick_end_x, 44.5-11, 41)
bl4 = iso_proj(stick_back_x, 44.5-11, 41)
svg.append(f'<polygon points="{bl1[0]:.1f},{bl1[1]:.1f} {iso_proj(notch_start_x,44.5,41)[0]:.1f},{iso_proj(notch_start_x,44.5,41)[1]:.1f} {iso_proj(notch_start_x,44.5-11,41)[0]:.1f},{iso_proj(notch_start_x,44.5-11,41)[1]:.1f} {bl4[0]:.1f},{bl4[1]:.1f}" fill="url(#steel-dark)" stroke="#475569" stroke-width="1.2"/>')
svg.append(f'<polygon points="{iso_proj(notch_end_x,44.5,41)[0]:.1f},{iso_proj(notch_end_x,44.5,41)[1]:.1f} {bl2[0]:.1f},{bl2[1]:.1f} {bl3[0]:.1f},{bl3[1]:.1f} {iso_proj(notch_end_x,44.5-11,41)[0]:.1f},{iso_proj(notch_end_x,44.5-11,41)[1]:.1f}" fill="url(#steel-dark)" stroke="#475569" stroke-width="1.2"/>')
notch_floor_a2 = iso_proj(notch_start_x, 44.5, 41)
notch_floor_b2 = iso_proj(notch_end_x, 44.5, 41)
notch_floor_c2 = iso_proj(notch_end_x, 44.5-11, 41)
notch_floor_d2 = iso_proj(notch_start_x, 44.5-11, 41)
svg.append(f'<polygon points="{notch_floor_a2[0]:.1f},{notch_floor_a2[1]:.1f} {notch_floor_b2[0]:.1f},{notch_floor_b2[1]:.1f} {notch_floor_c2[0]:.1f},{notch_floor_c2[1]:.1f} {notch_floor_d2[0]:.1f},{notch_floor_d2[1]:.1f}" fill="url(#cut-hatch)" stroke="#dc2626" stroke-width="1.2"/>')

# The bolt hole (drilled through the web)
bolt_3d_x = -40   # 40mm back from end
bolt_centre = iso_proj(bolt_3d_x, 0, 0)
svg.append(f'<ellipse cx="{bolt_centre[0]:.1f}" cy="{bolt_centre[1]:.1f}" rx="{6*ISO/2:.1f}" ry="{6*ISO/2*0.85:.1f}" fill="white" stroke="#16a34a" stroke-width="2"/>')

# Annotations on the iso view
svg.append(f'<text x="{notch_floor_a[0]+10}" y="{notch_floor_a[1]-15}" font-size="11" font-weight="700" fill="#7f1d1d">Top lip notch</text>')
svg.append(f'<line x1="{notch_floor_a[0]+15}" y1="{notch_floor_a[1]-12}" x2="{(notch_floor_a[0]+notch_floor_b[0])/2}" y2="{(notch_floor_a[1]+notch_floor_b[1])/2-2}" stroke="#7f1d1d" stroke-width="0.8" marker-end="url(#ar)"/>')
svg.append(f'<text x="{notch_floor_a2[0]+10}" y="{notch_floor_a2[1]+20}" font-size="11" font-weight="700" fill="#7f1d1d">Bottom lip notch</text>')
svg.append(f'<line x1="{notch_floor_a2[0]+18}" y1="{notch_floor_a2[1]+15}" x2="{(notch_floor_a2[0]+notch_floor_b2[0])/2}" y2="{(notch_floor_a2[1]+notch_floor_b2[1])/2}" stroke="#7f1d1d" stroke-width="0.8" marker-end="url(#ar)"/>')

svg.append(f'<text x="{bolt_centre[0]-30}" y="{bolt_centre[1]-20}" font-size="11" font-weight="700" fill="#14532d">M6 bolt hole</text>')
svg.append(f'<text x="{bolt_centre[0]-30}" y="{bolt_centre[1]-7}" font-size="10" fill="#14532d">at centreline crossing</text>')
svg.append(f'<line x1="{bolt_centre[0]-12}" y1="{bolt_centre[1]-15}" x2="{bolt_centre[0]-3}" y2="{bolt_centre[1]-7}" stroke="#14532d" stroke-width="0.8" marker-end="url(#ar)"/>')

# Coordinate axes
ax_o = iso_proj(stick_back_x - 30, 60, 0)
for label, x, y, z in [('length', stick_back_x-30+25, 60, 0), ('web', stick_back_x-30, 60-25, 0)]:
    p = iso_proj(x, y, z)
    svg.append(f'<line x1="{ax_o[0]:.1f}" y1="{ax_o[1]:.1f}" x2="{p[0]:.1f}" y2="{p[1]:.1f}" stroke="#374151" stroke-width="1" marker-end="url(#ar)"/>')
    svg.append(f'<text x="{p[0]+3:.1f}" y="{p[1]+3:.1f}" font-size="9" fill="#374151">{label}</text>')

# Caption
cap_y = P3_Y + P3_H - 80
svg.append(f'<rect x="{P3_X+15}" y="{cap_y}" width="{P3_W-30}" height="60" fill="#dcfce7" stroke="#16a34a" rx="3"/>')
svg.append(f'<text x="{P3_X+25}" y="{cap_y+18}" font-size="12" font-weight="700" fill="#14532d">3D view shows:</text>')
svg.append(f'<text x="{P3_X+25}" y="{cap_y+34}" font-size="11" fill="#14532d">• Both lips notched (red hatched) so the stick can sit flush against the chord</text>')
svg.append(f'<text x="{P3_X+25}" y="{cap_y+48}" font-size="11" fill="#14532d">• Single bolt hole through the centre of the web at the centreline crossing</text>')

# ========== PANEL 4: Why the lip notch is needed (assembly view) ==========
P4_X = 30
P4_Y = P2_Y + P2_H + 20
P4_W = W - 60
P4_H = H - P4_Y - 30
svg.append(f'<rect x="{P4_X}" y="{P4_Y}" width="{P4_W}" height="{P4_H}" fill="white" stroke="#cbd5e0" rx="4"/>')
svg.append(f'<text x="{P4_X+15}" y="{P4_Y+22}" font-size="14" font-weight="700" fill="#1a202c">4.  Why the lip notch matters — assembly view (web meets chord)</text>')

# Two side-by-side: WITHOUT notch (won't fit) vs WITH notch (fits)
sub_w = (P4_W - 60) / 2
for sub_idx, (sub_label, has_notch) in enumerate([("WITHOUT lip notch — won't fit", False), ("WITH lip notch — sits flush", True)]):
    sx = P4_X + 20 + sub_idx*(sub_w + 20)
    sy = P4_Y + 50

    # Sub label
    col = '#dc2626' if not has_notch else '#16a34a'
    svg.append(f'<text x="{sx + sub_w/2}" y="{sy+15}" text-anchor="middle" font-size="13" font-weight="700" fill="{col}">{sub_label}</text>')

    # Draw the chord (horizontal) at top
    chord_y = sy + 60
    chord_h = 89 * 1.5  # smaller scale
    SC = 1.5
    svg.append(f'<rect x="{sx+30}" y="{chord_y}" width="{sub_w-60}" height="{chord_h}" fill="url(#steel)" stroke="#1d4ed8" stroke-width="1.5"/>')
    # Chord lips at top + bottom (visible as bands)
    svg.append(f'<rect x="{sx+30}" y="{chord_y}" width="{sub_w-60}" height="{11*SC}" fill="url(#steel-flange)" stroke="#1d4ed8" stroke-width="1"/>')
    svg.append(f'<rect x="{sx+30}" y="{chord_y+chord_h-11*SC}" width="{sub_w-60}" height="{11*SC}" fill="url(#steel-flange)" stroke="#1d4ed8" stroke-width="1"/>')
    svg.append(f'<text x="{sx+40}" y="{chord_y+18}" font-size="11" fill="#1d4ed8" font-weight="600">CHORD plate (laid flat)</text>')

    # Draw the web (vertical) coming up from below
    web_x = sx + sub_w/2
    web_top = chord_y + chord_h + 5  # web touches the bottom of chord
    if not has_notch:
        # Without notch: web's lip protrudes ABOVE the chord — gap shown
        web_top = chord_y + chord_h + 30  # web is held away by lip clash
    web_bot = sy + 280
    web_w_px = 89 * SC
    svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_top}" width="{web_w_px}" height="{web_bot-web_top}" fill="url(#steel)" stroke="#475569" stroke-width="1.5"/>')

    # Lips on the web (visible as bands)
    svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_top}" width="{web_w_px}" height="{11*SC}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1"/>')
    svg.append(f'<rect x="{web_x - web_w_px/2}" y="{web_bot-11*SC}" width="{web_w_px}" height="{11*SC}" fill="url(#steel-flange)" stroke="#475569" stroke-width="1"/>')
    svg.append(f'<text x="{web_x}" y="{web_bot-15}" text-anchor="middle" font-size="11" fill="#475569" font-weight="600">WEB stud</text>')

    if not has_notch:
        # Show the LIP on the web sticking PAST the chord — the clash zone
        clash_y = chord_y + chord_h
        svg.append(f'<rect x="{web_x - web_w_px/2}" y="{clash_y}" width="{web_w_px}" height="{30}" fill="#fee2e2" stroke="#dc2626" stroke-width="2" stroke-dasharray="4 2"/>')
        svg.append(f'<text x="{web_x}" y="{clash_y + 18}" text-anchor="middle" font-size="11" font-weight="700" fill="#7f1d1d">CLASH — gap of 11mm</text>')
        svg.append(f'<text x="{web_x}" y="{clash_y + 32}" text-anchor="middle" font-size="9" fill="#7f1d1d">web cannot sit flat on chord</text>')
    else:
        # Show the lip notch on the web at the top
        notch_y = web_top
        svg.append(f'<rect x="{web_x - web_w_px/2}" y="{notch_y}" width="{12*SC}" height="{11*SC + 2}" fill="white" stroke="#dc2626" stroke-width="1.5"/>')
        svg.append(f'<rect x="{web_x - web_w_px/2}" y="{notch_y}" width="{12*SC}" height="{11*SC + 2}" fill="url(#cut-hatch)" opacity="0.6"/>')
        svg.append(f'<rect x="{web_x + web_w_px/2 - 12*SC}" y="{notch_y}" width="{12*SC}" height="{11*SC + 2}" fill="white" stroke="#dc2626" stroke-width="1.5"/>')
        svg.append(f'<rect x="{web_x + web_w_px/2 - 12*SC}" y="{notch_y}" width="{12*SC}" height="{11*SC + 2}" fill="url(#cut-hatch)" opacity="0.6"/>')
        # Show the bolt
        bolt_y = chord_y + chord_h/2
        svg.append(f'<circle cx="{web_x}" cy="{bolt_y}" r="6" fill="white" stroke="#16a34a" stroke-width="2"/>')
        svg.append(f'<text x="{web_x+12}" y="{bolt_y+4}" font-size="10" fill="#14532d" font-weight="700">single bolt</text>')

# Footer
svg.append(f'<text x="30" y="{H-10}" font-size="11" fill="#6b7280">Source: 2603191 ROCKVILLE TH-TYPE-A1-LT, frame TN2-1, web W6 (89S41-0.75 stud, 2037.74 mm). Lip notch at 1997.02 mm = 40.72 mm from cut end. Notch ~12 mm wide × 8 mm deep.</text>')

svg.append('</svg>')
open(OUT, 'w', encoding='utf-8').write('\n'.join(svg))
print(f'Wrote {OUT}')
