"""Crack the FrameCAD .dat cipher using known-plaintext + frequency analysis.

Hypothesis: polyalphabetic cipher (Vigenere XOR or additive) with short key.
Strategy: slice ciphertext into N columns, find best key byte per column by
maximising English+config-file character score.
"""
import sys

QLD = r'C:/Users/Scott/AppData/Local/Temp/FC_Textor_Qld.dat'
WA  = r'Y:/(08) DETAILING/(13) FRAMECAD/FrameCAD Structure/FC_Textor_WA.dat'

raw = open(QLD, 'rb').read()
wa  = open(WA, 'rb').read()

# Strip CRLF for column-wise analysis
content = bytes(b for b in raw if b not in (0x0d, 0x0a))
print(f"Qld total: {len(raw)}, after strip CRLF: {len(content)}")
print(f"WA  total: {len(wa)}")

# Score function: prefer printable ASCII, English letters, common config punct
ENGLISH = {ord(c): f for c, f in [
    (' ', 13.0), ('e', 12.7), ('t', 9.06), ('a', 8.17), ('o', 7.51),
    ('i', 6.97), ('n', 6.75), ('s', 6.33), ('h', 6.09), ('r', 5.99),
    ('d', 4.25), ('l', 4.03), ('c', 2.78), ('u', 2.76), ('m', 2.41),
    ('w', 2.36), ('f', 2.23), ('g', 2.02), ('y', 1.97), ('p', 1.93),
    ('b', 1.29), ('v', 0.98), ('k', 0.77),
]}

def score_byte(b):
    if not (0x20 <= b <= 0x7e):
        return -50.0
    s = 0.5
    if b in ENGLISH: s += ENGLISH[b]
    if b == 0x20: s += 4
    if 0x30 <= b <= 0x39: s += 2  # digit
    if 0x41 <= b <= 0x5a: s += 2  # upper
    if 0x61 <= b <= 0x7a: s += 1  # lower
    if b in b'_[]./"': s += 1
    return s

def score_text(t):
    return sum(score_byte(b) for b in t)

def find_key(ct, klen, op):
    key = []
    for col in range(klen):
        column = ct[col::klen]
        best_s, best_k = -1e18, 0
        for kb in range(256):
            if op == 'xor':
                dec = bytes(c ^ kb for c in column)
            elif op == 'sub':
                dec = bytes((c - kb) & 0xff for c in column)
            elif op == 'add':
                dec = bytes((c + kb) & 0xff for c in column)
            s = score_text(dec)
            if s > best_s:
                best_s, best_k = s, kb
        key.append(best_k)
    return bytes(key)

def apply_key(ct, key, op):
    out = bytearray(len(ct))
    for i, c in enumerate(ct):
        kb = key[i % len(key)]
        if op == 'xor':   out[i] = c ^ kb
        elif op == 'sub': out[i] = (c - kb) & 0xff
        elif op == 'add': out[i] = (c + kb) & 0xff
    return bytes(out)

# Test on first 8000 bytes (enough for stable column stats)
sample = content[:8000]
results = []
for op in ('xor', 'sub', 'add'):
    for klen in range(1, 41):
        key = find_key(sample, klen, op)
        dec = apply_key(sample[:300], key, op)
        s = score_text(dec) / len(dec)
        results.append((s, op, klen, key, dec))

results.sort(reverse=True)
print("\n=== Top 8 candidates ===")
for s, op, k, key, dec in results[:8]:
    print(f"\n[op={op:3} klen={k:2} avg_score={s:.2f}]")
    print(f"  key hex: {key.hex()}")
    try:
        keystr = key.decode('latin1')
        print(f"  key str: {keystr!r}")
    except:
        pass
    print(f"  decoded: {dec[:200]!r}")
