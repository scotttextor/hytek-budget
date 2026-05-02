"""Disassemble the AES decrypt wrapper around 0x59adad and find its callers."""
import pefile, capstone, struct

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"
pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Find function start before 0x59adad
target_va = 0x59adad
target_rva = target_va - image_base

# Walk backward looking for "push ebp; mov ebp,esp" (55 8b ec)
search_start = target_rva - 1024
for off in range(target_rva - search_start, -1, -1):
    p = search_start + off
    if data[p:p+3] == b"\x55\x8b\xec":
        # Possibly a function start
        func_start_rva = p
        func_start_va = image_base + p
        print(f"Function start candidate @ 0x{func_start_va:x}")
        break

# Disassemble entire function from there
func_bytes = data[func_start_rva:func_start_rva + 4000]
ret_count = 0
for ins in md.disasm(func_bytes, image_base + func_start_rva):
    print(f"0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
    if ins.mnemonic == "ret":
        ret_count += 1
        if ret_count >= 1 and ins.address > target_va + 256:
            break
    if ins.address > target_va + 1500:
        break
