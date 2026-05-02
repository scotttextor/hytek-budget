"""Find all callers of decrypt fn 0x59ad04, and find the key data near 0x5a4840."""
import pefile, capstone, struct

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"
pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

target = 0x59ad04

# Search for E8 + relative => target
text_start_va = 0x401000
text_end_va = 0x401000 + 0x19e030
callers = []
for va in range(text_start_va, text_end_va - 5):
    rva = va - image_base
    if data[rva] == 0xe8:
        rel = struct.unpack("<i", data[rva+1:rva+5])[0]
        dest = va + 5 + rel
        if dest == target:
            callers.append(va)
print(f"Callers of decrypt @ 0x{target:x}: {len(callers)}")
for c in callers[:20]:
    print(f"  0x{c:x}")

# Show context around each
for caller in callers:
    print(f"\n=== Caller @ 0x{caller:x} ===")
    rva = caller - image_base
    # Walk back to find function start
    for off in range(rva, max(0, rva - 2000), -1):
        if data[off:off+3] == b"\x55\x8b\xec":
            func_start = image_base + off
            break
    else:
        func_start = caller - 64
    fb = data[func_start - image_base:rva + 32]
    for ins in md.disasm(fb, func_start):
        print(f"0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
        if ins.address >= caller + 16:
            break

# Show data at 0x5a4840 (the IV/key passed to decrypt during Authenticate)
print(f"\n=== Data @ 0x5a4840 (passed as key during Authenticate) ===")
rva = 0x5a4840 - image_base
print("Hex:", data[rva:rva+64].hex())

# Also where 0x5a4840 is referenced
needle = struct.pack("<I", 0x5a4840)
locs = []
i = 0
while True:
    p = data.find(needle, i)
    if p < 0: break
    locs.append(image_base + p)
    i = p + 1
print(f"References to 0x5a4840: {[hex(x) for x in locs]}")
