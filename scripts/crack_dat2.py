"""Stage 2 attack: Index of Coincidence + known-plaintext.

Hypothesis: cipher is Vigenere XOR over the byte stream (CRLF skipped).
The frequency-analysis attack succeeded partially, suggesting we just need
to pin down the key length precisely.
"""
import sys
from collections import Counter

QLD = r'C:/Users/Scott/AppData/Local/Temp/FC_Textor_Qld.dat'
WA  = r'Y:/(08) DETAILING/(13) FRAMECAD/FrameCAD Structure/FC_Textor_WA.dat'

raw = open(QLD, 'rb').read()
content = bytes(b for b in raw if b not in (0x0d, 0x0a))

# ---------- Step 1: Index of Coincidence per key length ----------
# IoC = sum(n_i * (n_i - 1)) / (N * (N - 1))
# English IoC ~= 0.067, random ~= 0.038
def ioc(s):
    if len(s) < 2:
        return 0
    counts = Counter(s)
    n = len(s)
    return sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))

print("Index of Coincidence by key length (English ~0.066, random ~0.038):")
print(f"{'klen':>5} {'avg IoC':>10}")
ioc_results = []
for klen in range(1, 80):
    avg = sum(ioc(content[i::klen]) for i in range(klen)) / klen
    ioc_results.append((avg, klen))

# Sort by IoC descending
ioc_results.sort(reverse=True)
for ic, k in ioc_results[:15]:
    print(f"{k:>5} {ic:>10.5f}")

print("\n--- Same, sorted by klen ---")
ioc_by_k = sorted(ioc_results, key=lambda x: x[1])
for ic, k in ioc_by_k[:80]:
    marker = " <===" if ic > 0.045 else ""
    print(f"{k:>5} {ic:>10.5f}{marker}")
