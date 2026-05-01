"""FrameCAD .dat codec — solved 2026-05-01.

Format: lines are XOR-encoded with the 4-byte key [0x08, 0x01, 0x09, 0x05].
The keystream resets at every CRLF (\\r\\n is passed through verbatim).
Every encoded line has a literal leading ',' byte BEFORE the actual content,
which the loader strips. So plaintext line "//foo" stores as ",//foo" then
gets XOR'd. The leading comma even appears on blank lines (encoded as ",").

Encoder (encode_dat) and decoder (decode_dat) are exact inverses.
"""
import sys

KEY = bytes([0x08, 0x01, 0x09, 0x05])

def decode_dat(raw, strip_leading_comma=True):
    out = bytearray()
    idx = 0
    line_start = True
    for b in raw:
        if b in (0x0d, 0x0a):
            out.append(b)
            idx = 0
            if b == 0x0a:
                line_start = True
            continue
        decoded = b ^ KEY[idx % 4]
        idx += 1
        if line_start and strip_leading_comma and decoded == ord(','):
            line_start = False
            continue
        line_start = False
        out.append(decoded)
    return bytes(out)


def encode_dat(plain, add_leading_comma=True):
    """Inverse of decode_dat. Emits a leading ',' on every line, including blanks."""
    out = bytearray()
    idx = 0
    line_start = True
    for b in plain:
        if b in (0x0d, 0x0a):
            if line_start and add_leading_comma:
                out.append(ord(',') ^ KEY[idx % 4])
            out.append(b)
            idx = 0
            line_start = (b == 0x0a)
            continue
        if line_start and add_leading_comma:
            out.append(ord(',') ^ KEY[idx % 4])
            idx += 1
            line_start = False
        out.append(b ^ KEY[idx % 4])
        idx += 1
    if line_start and add_leading_comma:
        out.append(ord(',') ^ KEY[idx % 4])
    return bytes(out)

if __name__ == '__main__':
    QLD = r'C:/Users/Scott/AppData/Local/Temp/FC_Textor_Qld.dat'
    raw = open(QLD, 'rb').read()

    decoded_raw = decode_dat(raw, strip_leading_comma=False)
    decoded_clean = decode_dat(raw, strip_leading_comma=True)

    out_path = r'C:/Users/Scott/CLAUDE CODE/hytek-budget/scripts/FC_Textor_Qld.decoded.dat'
    with open(out_path, 'wb') as f:
        f.write(decoded_clean)
    print(f"Wrote: {out_path} ({len(decoded_clean)} bytes)")

    # Sample print
    print("\n=== First 1500 chars (clean) ===")
    print(decoded_clean[:1500].decode('latin1'))
    print("\n=== Section headers ===")
    for line in decoded_clean.decode('latin1', errors='replace').splitlines():
        if line.startswith('['):
            print(f"  {line}")
    print("\n=== Tail (last 500 chars) ===")
    print(decoded_clean[-500:].decode('latin1', errors='replace'))
