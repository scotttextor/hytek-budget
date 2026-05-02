"""Search for ".incx", ".vbsx", ScriptsX, AES_, EVP_ etc references."""
import pefile, capstone, re

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"
pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()

# Find ALL strings of interest
patterns = [b".incx\x00", b".vbsx\x00", b"ScriptsX", b"PlaceServices",
            b"EVP_", b"AES_", b"RC4_", b"BF_", b"DES_",
            b".incx", b".vbsx"]

print("String references in DLL:")
for pat in patterns:
    idx = 0
    while True:
        loc = data.find(pat, idx)
        if loc < 0:
            break
        va = image_base + loc
        # Show context
        start = max(0, loc - 40)
        end = min(len(data), loc + 60)
        ctx = data[start:end]
        printable = "".join(chr(b) if 32 <= b < 127 else "." for b in ctx)
        print(f"  0x{va:08x} ({pat!r}): ...{printable}...")
        idx = loc + 1

# Find imports
print("\nImports:")
if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dll_name = entry.dll.decode("ascii", errors="replace")
        for imp in entry.imports:
            if imp.name:
                name = imp.name.decode("ascii", errors="replace")
                if any(s in name.upper() for s in ["EVP", "AES", "RC4", "DES", "BF_", "CRYPT", "MD5", "SHA"]):
                    print(f"  {dll_name}!{name} @ 0x{imp.address:x}")

print("\nAll DLLs imported:")
if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        print(f"  {entry.dll.decode('ascii', errors='replace')}")

# Look for SECTION info
print("\nSections:")
for s in pe.sections:
    print(f"  {s.Name.decode().rstrip(chr(0)):8s} VA=0x{image_base+s.VirtualAddress:08x} VSize=0x{s.Misc_VirtualSize:x}")
