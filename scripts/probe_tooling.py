"""Probe Tooling.dll for the script decryption function."""
import pefile, capstone, struct, os

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\Tooling.dll"
pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

print(f"Tooling.dll size: {len(data):,}")

# Exports
print(f"\nExports:")
exports = []
if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if exp.name:
            n = exp.name.decode("ascii","replace")
            print(f"  0x{image_base+exp.address:08x}  {n}")
            exports.append((n, image_base + exp.address))

# Search for strings
patterns = [b".incx\x00", b".vbsx\x00", b"ScriptsX", b"PlaceServices", b".inc\x00", b".vbs\x00"]
print(f"\nString searches:")
for pat in patterns:
    locs = []
    i = 0
    while True:
        p = data.find(pat, i)
        if p < 0: break
        locs.append(image_base + p)
        i = p + 1
        if len(locs) > 5: break
    if locs:
        print(f"  {pat!r}: {[hex(x) for x in locs]}")
        for loc in locs[:2]:
            rva = loc - image_base
            ctx = data[max(0,rva-30):rva+50]
            printable = "".join(chr(b) if 32 <= b < 127 else "." for b in ctx)
            print(f"     ...{printable}...")

# Sections
print(f"\nSections:")
for s in pe.sections:
    print(f"  {s.Name.decode().rstrip(chr(0)):8s} VA=0x{image_base+s.VirtualAddress:08x} VSize=0x{s.Misc_VirtualSize:x}")

# Find IAT entries for EVP funcs
print(f"\nFind EVP_Decrypt* IAT addresses:")
for entry in pe.DIRECTORY_ENTRY_IMPORT:
    if "crypto" in entry.dll.decode().lower():
        for imp in entry.imports:
            if imp.name:
                n = imp.name.decode()
                if "Decrypt" in n or "CIPHER" in n or "aes" in n.lower():
                    print(f"  {n} @ 0x{imp.address:x}")
