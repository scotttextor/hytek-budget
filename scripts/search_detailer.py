"""Search FRAMECAD Detailer.exe for .incx, .vbsx, ScriptsX, EVP_*, decrypt patterns."""
import pefile, capstone, struct, os

EXE = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\FRAMECAD Detailer.exe"

print("Loading exe...")
pe = pefile.PE(EXE, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
print(f"ImageBase = 0x{image_base:x}")
data = pe.get_memory_mapped_image()
print(f"Image size: {len(data):,} bytes")

# String search
patterns = [b".incx\x00", b".vbsx\x00", b"ScriptsX",
            b"EVP_aes", b"EVP_DecryptInit_ex", b"EVP_CIPHER",
            b"PlaceServices", b".inc\x00"]
for pat in patterns:
    locs = []
    i = 0
    while len(locs) < 8:
        p = data.find(pat, i)
        if p < 0: break
        locs.append(image_base + p)
        i = p + 1
    print(f"\n{pat!r}: {len(locs)} hits {[hex(x) for x in locs]}")
    for loc in locs[:3]:
        rva = loc - image_base
        start = max(0, rva-20); end = rva+50
        ctx = data[start:end]
        printable = "".join(chr(b) if 32 <= b < 127 else "." for b in ctx)
        print(f"   ...{printable}...")

# Imports - look for OpenSSL
print("\n\n=== Crypto imports in Detailer.exe ===")
if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dll_name = entry.dll.decode("ascii", errors="replace").lower()
        if "crypto" in dll_name or "ssl" in dll_name:
            print(f"\n{entry.dll.decode()}:")
            for imp in entry.imports:
                if imp.name:
                    print(f"  0x{imp.address:x}  {imp.name.decode()}")
