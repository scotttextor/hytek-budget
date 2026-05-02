"""Disassemble helper thunks 0x59aca0..0x59acd0."""
import pefile, capstone

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"
pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Disassemble the thunk table
for va in [0x59aca0, 0x59aca8, 0x59acb0, 0x59acb8, 0x59acc0, 0x59acc8, 0x59acd0,
           0x59ac98]:
    rva = va - image_base
    fb = data[rva:rva + 32]
    print(f"\n--- 0x{va:x} ---")
    for ins in md.disasm(fb, va):
        print(f"0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
        if ins.mnemonic in ("ret", "jmp"):
            break
