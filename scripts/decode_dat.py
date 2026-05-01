"""Decode FC_Textor_Qld.dat - cipher is XOR with 4-byte key 08 01 09 05.

Key found via known-plaintext attack:
- Qld line 1 plaintext is `,//Data file for Textor Metal Industries - 2/11/18 - CA `
- The leading comma is part of the format
- CRLF bytes are passed through verbatim (encoder skips them)
"""
import sys

KEY = bytes([0x08, 0x01, 0x09, 0x05])

QLD = r'C:/Users/Scott/AppData/Local/Temp/FC_Textor_Qld.dat'
raw = open(QLD, 'rb').read()

def decode(raw, reset_per_line=False, continuous=True):
    """Try two modes: continuous keystream vs per-line reset."""
    out = bytearray()
    if continuous:
        idx = 0  # keystream index (skips CRLF)
        for b in raw:
            if b in (0x0d, 0x0a):
                out.append(b)
            else:
                out.append(b ^ KEY[idx % 4])
                idx += 1
    elif reset_per_line:
        idx = 0
        for b in raw:
            if b in (0x0d, 0x0a):
                out.append(b)
                idx = 0
            else:
                out.append(b ^ KEY[idx % 4])
                idx += 1
    return bytes(out)

# Try continuous mode
decoded_cont = decode(raw, continuous=True)
# Try per-line reset
decoded_line = decode(raw, continuous=False, reset_per_line=True)

print("=== Continuous keystream (skip CRLF) - first 800 chars ===")
print(decoded_cont[:800].decode('latin1'))
print("\n=== Per-line reset - first 800 chars ===")
print(decoded_line[:800].decode('latin1'))

# Save both
open('decoded_continuous.dat', 'wb').write(decoded_cont)
open('decoded_perline.dat', 'wb').write(decoded_line)
print("\nSaved decoded_continuous.dat and decoded_perline.dat")

# Also check tail to see which mode works
print("\n=== Continuous - last 600 chars ===")
print(decoded_cont[-600:].decode('latin1'))
