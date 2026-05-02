"""Find xrefs to '.vbsx' string @ 0x17197c4 in Detailer.exe."""
import pefile, capstone, struct

EXE = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\FRAMECAD Detailer.exe"
print("Loading exe...")
pe = pefile.PE(EXE, fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()

target = 0x17197c4
needle = struct.pack("<I", target)
locs = []
i = 0
while True:
    p = data.find(needle, i)
    if p < 0: break
    locs.append(base + p)
    i = p + 1
print(f"Refs to 0x{target:x}: {[hex(x) for x in locs]}")

# For each ref, look 16 bytes around
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
for loc in locs:
    rva = loc - base
    print(f"\n=== Ref @ 0x{loc:x} ===")
    print("Bytes around:", data[rva-8:rva+8].hex())
    # Search for prologue function start back up to 4KB
    for off_back in range(0, 4096):
        p = rva - off_back
        if p < 0: break
        if data[p:p+3] == b"\x55\x8b\xec":
            func_start = base + p
            # Disassemble until we go past the ref
            fb = data[p:rva + 64]
            for ins in md.disasm(fb, func_start):
                print(f"  0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
                if ins.address > loc + 32:
                    break
            break
    print()
