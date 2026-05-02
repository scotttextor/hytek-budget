"""Disassemble AutoFrame.dll exports to determine GetChars signature."""
import pefile
import capstone

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"

pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
print(f"ImageBase = 0x{image_base:x}")

# Enumerate exports
exports = []
for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
    if exp.name:
        exports.append((exp.name.decode("ascii", errors="replace"), exp.address))
        # exp.address is the RVA
print(f"Found {len(exports)} exports:")
for name, rva in sorted(exports, key=lambda x: x[1]):
    print(f"  0x{rva:08x}  {name}")

# Disassemble GetChars
print("\n" + "="*70)
print("Disassembling AutoFrame_GetChars")
print("="*70)
target_name = "AutoFrame_GetChars"
target_rva = None
for name, rva in exports:
    if name == target_name:
        target_rva = rva
        break
print(f"GetChars RVA: 0x{target_rva:x}")

# Get raw bytes
data = pe.get_memory_mapped_image()
func_bytes = data[target_rva:target_rva + 4096]

md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True

count = 0
for ins in md.disasm(func_bytes, image_base + target_rva):
    print(f"0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
    count += 1
    # Stop at ret unless we see another prologue
    if ins.mnemonic == "ret":
        print("--- ret ---")
        break
    if count > 200:
        break
