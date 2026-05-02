"""Disassemble around 0x57aaa3, 0x57ac0d, 0x57dcdc - candidates for cache populators."""
import pefile, capstone, struct

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"
pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

def find_func_start(va):
    rva = va - image_base
    for off in range(rva, max(0, rva-3000), -1):
        if data[off:off+3] == b"\x55\x8b\xec":
            return image_base + off
    return va - 64

def disasm(va, n=400, label=""):
    print(f"\n=== {label} @ 0x{va:x} ===")
    fb = data[va - image_base:va - image_base + n*8]
    last_ret = 0
    count = 0
    for ins in md.disasm(fb, va):
        print(f"0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
        count += 1
        if ins.mnemonic == "ret":
            last_ret = ins.address
            if count > 10:
                return
        if count > n:
            return

# Find function start of 0x57aaa3 and disassemble
fs = find_func_start(0x57aaa3)
disasm(fs, 200, "Func with 0x57aaa3")
