"""Decrypt all FRAMECAD Detailer .incx/.vbsx scripts.

Cipher is a 16-bit LCG-style XOR keystream extracted from
FRAMECAD Detailer.exe @ 0x8a2b20.

Pseudocode:
    state = seed
    for each input byte b:
        ks   = (state >> 8) & 0xFF
        out  = ks ^ b
        st_l = state & 0xFF
        nb   = (out + st_l) & 0xFF
        state = (nb * mult + inc) & 0xFFFF

The 6-byte key (mult, inc, seed in u16 LE) is stored at
Detailer.exe + 0x1e09624 = "3b 0e 46 00 88 26"
  -> mult = 0x0e3b
  -> inc  = 0x0046
  -> seed = 0x2688
"""
import os, struct, sys

# Key found at Detailer.exe + 0x1e09624
KEY_BYTES = bytes.fromhex("3b0e46008826")
mult, inc, seed = struct.unpack("<HHH", KEY_BYTES)


def decrypt(data: bytes, mult: int, inc: int, seed: int) -> bytes:
    out = bytearray()
    state = seed
    for b in data:
        ks = (state >> 8) & 0xFF
        out_byte = ks ^ b
        state_lo = state & 0xFF
        new_byte = (out_byte + state_lo) & 0xFF
        state = (new_byte * mult + inc) & 0xFFFF
        out.append(out_byte)
    return bytes(out)


def looks_like_vbscript(text: str) -> bool:
    keywords = ("'**", "Sub ", "End Sub", "Function ", "End Function",
                "Const ", "Dim ", "If ", "Then", "With ")
    return any(k in text for k in keywords)


def main():
    src = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\ScriptsX"
    dst = r"C:\Users\Scott\CLAUDE CODE\hytek-rfy-codec\extracted-scripts"
    os.makedirs(dst, exist_ok=True)

    print(f"Key: mult=0x{mult:04x} inc=0x{inc:04x} seed=0x{seed:04x}")
    print(f"Source: {src}")
    print(f"Dest:   {dst}\n")

    failures = []
    for fname in sorted(os.listdir(src)):
        spath = os.path.join(src, fname)
        if not os.path.isfile(spath):
            continue
        with open(spath, "rb") as fp:
            cipher = fp.read()

        if fname.endswith(".inc"):
            # Plaintext file (e.g. Constants.inc)
            plain = cipher
            verdict = "PLAIN"
        elif fname.endswith(".incx") or fname.endswith(".vbsx"):
            plain = decrypt(cipher, mult, inc, seed)
            try:
                txt = plain.decode("ascii")
            except UnicodeDecodeError:
                txt = plain.decode("latin-1", errors="replace")
            ok = looks_like_vbscript(txt[:500])
            verdict = "OK   " if ok else "FAIL "
            if not ok:
                failures.append(fname)
        else:
            continue

        # Strip extension trailing 'x' for output: .incx -> .inc, .vbsx -> .vbs
        out_name = fname
        if out_name.endswith("x"):
            out_name = out_name[:-1]
        outpath = os.path.join(dst, out_name)
        with open(outpath, "wb") as fp:
            fp.write(plain)
        print(f"  {verdict} {fname:40s} -> {out_name} ({len(plain)} bytes)")

    print(f"\nFailures: {failures}")


if __name__ == "__main__":
    main()
