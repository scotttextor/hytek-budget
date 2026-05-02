"""Test decrypt FRAMECAD .incx using LCG stream cipher from 0x8a2b20."""
import os, struct

KEY_BYTES = bytes.fromhex("3b 0e 46 00 88 26".replace(" ", ""))
mult, inc, seed = struct.unpack("<HHH", KEY_BYTES)
print(f"Key: mult=0x{mult:04x}={mult}, inc=0x{inc:04x}={inc}, seed=0x{seed:04x}={seed}")

def decrypt(data, mult, inc, seed):
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

D = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\ScriptsX"

# Test on PlaceServices.incx
target = os.path.join(D, "PlaceServices.incx")
with open(target, "rb") as f:
    cipher = f.read()
print(f"\nFile: {target} ({len(cipher)} bytes)")

# Decrypt
plain = decrypt(cipher, mult, inc, seed)
print(f"Decrypted ({len(plain)} bytes)")
print(f"First 200 bytes (hex): {plain[:200].hex()}")
print(f"\nAs ASCII (first 800):")
try:
    print(plain[:800].decode("ascii", errors="replace"))
except:
    print(plain[:800])
