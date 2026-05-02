"""Disassemble follow-through after auth check + look for jumps to real impl."""
import pefile, capstone

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"
pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

def disasm_at(va, max_ins=80, label=""):
    rva = va - image_base
    print(f"\n=== {label} @ 0x{va:x} ===")
    bytes_ = data[rva:rva + max_ins * 8]
    count = 0
    last_ret = None
    for ins in md.disasm(bytes_, va):
        print(f"0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
        count += 1
        if ins.mnemonic == "ret":
            return
        if count > max_ins:
            return

# Disassemble the entry continuation
disasm_at(0x59afe0, 80, "GetChars body @ 0x59afe0")
disasm_at(0x588904, 200, "Inner GetChars @ 0x588904")
disasm_at(0x5076dc, 80, "Lookup @ 0x5076dc")
disasm_at(0x558634, 80, "Init @ 0x558634")
