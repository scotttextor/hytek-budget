"""Find xrefs to '.vbsx' string @ 0x01718b1c in Detailer.exe and disassemble caller."""
import pefile, capstone, struct

EXE = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\FRAMECAD Detailer.exe"
print("Loading exe...")
pe = pefile.PE(EXE, fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
print(f"Loaded, base=0x{base:x}")

# UTF16 ".vbsx" string at 0x1718b1c — but Delphi WideString has length prefix.
# The actual chars start at 0x1718b1c. The Delphi-style ref will point there.
target_strings = {
    ".vbsx_2": 0x17197c4,
}

text_start_va = 0x401000
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Search whole file for references to these addresses
for name, addr in target_strings.items():
    needle = struct.pack("<I", addr)
    locs = []
    i = 0
    while True:
        p = data.find(needle, i)
        if p < 0: break
        locs.append(base + p)
        i = p + 1
    print(f"\n{name} @ 0x{addr:x}: {len(locs)} refs")
    for loc in locs[:5]:
        rva = loc - base
        # Disassemble around: it's likely "mov edx, 0x1718b1c" => BA <addr>
        for off_back in range(0, 5):
            test_pos = rva - off_back
            if data[test_pos] in (0xb8, 0xb9, 0xba, 0xbb, 0xbe, 0xbf):
                # mov reg, imm32
                print(f"\n  Ref at 0x{loc:x}, instruction prefix at 0x{base+test_pos:x}:")
                # Walk back to find function start
                for find_back in range(test_pos, max(0, test_pos-2000), -1):
                    if data[find_back:find_back+3] == b"\x55\x8b\xec":
                        func_start = base + find_back
                        # Disassemble the function
                        fb = data[find_back:test_pos + 200]
                        for ins in md.disasm(fb, func_start):
                            print(f"    0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
                            if ins.address > base + test_pos + 100:
                                break
                        break
                break
