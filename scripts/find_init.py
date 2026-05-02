"""Find who initialises [0x506760] (the script TList)."""
import pefile, capstone, struct

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"
pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Search for references to 0x506760 (the global TList)
# Could appear in mov eax, 0x506760  => B8 60 67 50 00
needle = struct.pack("<I", 0x506760)
locs = []
i = 0
while True:
    p = data.find(needle, i)
    if p < 0: break
    locs.append(image_base + p)
    i = p + 1
print(f"References to 0x506760 (count={len(locs)}):")
for loc in locs:
    rva = loc - image_base
    # Show 16 bytes context
    print(f"  0x{loc:x}: {data[rva-4:rva+8].hex()}")

# Disassemble each context
for loc in locs:
    rva = loc - image_base
    # back up 1 byte (B8 instruction would be at rva-1)
    start = rva - 32
    fb = data[start:rva + 64]
    print(f"\n--- Around 0x{loc:x} ---")
    for ins in md.disasm(fb, image_base + start):
        print(f"0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
        if ins.address > loc + 30:
            break

# Also: where is the FlagAuth byte 0x5a4850 written outside Authenticate?
# (already know Authenticate writes it; what other code reads it?)
print("\n=== References to 0x5a4850 (auth flag) ===")
needle = struct.pack("<I", 0x5a4850)
i = 0
locs2 = []
while True:
    p = data.find(needle, i)
    if p < 0: break
    locs2.append(image_base + p)
    i = p + 1
print(f"  count={len(locs2)}: {[hex(x) for x in locs2[:30]]}")
