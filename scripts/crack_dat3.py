"""Stage 3: known-plaintext attack against multiple cipher hypotheses.

Try:
  1. Vigenere XOR (already failed but verify on first line)
  2. ct[i] = pt[i] XOR (key[i%K] + i)
  3. ct[i] = (pt[i] + key[i%K] + i) mod 95 (printable shift)
  4. ct[i] = pt[i] XOR keystream[i] where keystream is from LCG/PRNG
  5. ct[i] = pt[i] XOR position_byte (single-byte position shift)
"""
QLD = r'C:/Users/Scott/AppData/Local/Temp/FC_Textor_Qld.dat'
WA  = r'Y:/(08) DETAILING/(13) FRAMECAD/FrameCAD Structure/FC_Textor_WA.dat'

raw = open(QLD, 'rb').read()
content = bytes(b for b in raw if b not in (0x0d, 0x0a))

# Get Qld line 1 (before first CRLF)
crlf_idx = raw.find(b'\r\n')
qld_line1 = raw[:crlf_idx]
print(f"Qld line 1 ({len(qld_line1)} bytes): {qld_line1!r}")

# Get WA line 1
wa = open(WA, 'rb').read()
wa_line1 = wa[:wa.find(b'\r\n')]
print(f"WA  line 1 ({len(wa_line1)} bytes): {wa_line1!r}")

# Plaintext candidates for Qld line 1 (length 56 — WA was 55, so 1 extra char)
candidates = [
    b'//Data file for Textor Metal Industries - 21/11/18 - CA ',
    b'//Data file for Textor Metal Industries - 02/11/18 - CA ',
    b'//Data file for Textor Metal Industries - 12/11/18 - CA ',
    b'//Data file for Textor Metal Industries - 22/11/18 - CA ',
    b'//Data file for Textor Metal Industries - 2/11/18 - CA  ',  # extra trailing space
    b'//Data file for Textor Metal Industries - 2/11/18  - CA ',  # extra middle space
    b'//Data file for Textor Metal Industries  - 2/11/18 - CA ',  # extra middle space
    b'//Data file for  Textor Metal Industries - 2/11/18 - CA ',
    b'// Data file for Textor Metal Industries - 2/11/18 - CA ',
]

print(f"\nQld line 1 hex: {qld_line1.hex()}")
print(f"\nKey hex per candidate (XOR):")
for cand in candidates:
    if len(cand) != len(qld_line1):
        print(f"  [skip] len {len(cand)} vs {len(qld_line1)}: {cand!r}")
        continue
    key = bytes(c ^ p for c, p in zip(qld_line1, cand))
    # check periodicity by autocorrelation
    print(f"\n  PT: {cand!r}")
    print(f"  KEY: {key.hex()}")
    # Look for repeats in key
    for plen in range(1, 30):
        # check if key[plen:] == key[:-plen] for first segment
        matches = sum(1 for i in range(plen, len(key)) if key[i] == key[i % plen])
        ratio = matches / max(1, len(key) - plen)
        if ratio > 0.6:
            print(f"    period={plen} match_ratio={ratio:.2f}")

# ---------- Hypothesis 5: ct = pt XOR f(i) (position only) ----------
# If true, comparing Qld byte i with Qld byte j where pt is the same
# should give same result. We have multiple lines that we believe start
# with "MATERIAL_" — if they start at different file positions but same
# content, the key bytes at those positions would tell us about f(i).

# Find all occurrences of "$CLDER)V[" in Qld (encrypted MATERIAL_ prefix)
import re
pattern = b'$CLDER)V['
positions = []
i = 0
while True:
    j = raw.find(pattern, i)
    if j < 0: break
    positions.append(j)
    i = j + 1
print(f"\n\nFound '$CLDER)V[' at {len(positions)} positions: {positions[:10]}")
if positions:
    print("File offsets (decimal):")
    for p in positions[:20]:
        print(f"  offset={p:6d}  context={raw[max(0,p-5):p+20]!r}")
