"""Disassemble candidate decryptor in Detailer.exe at 0x8a2e28."""
import pefile, capstone, struct

EXE = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\FRAMECAD Detailer.exe"
print("Loading...")
pe = pefile.PE(EXE, fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

def disasm(va, n=300, label=""):
    print(f"\n=== {label} @ 0x{va:x} ===")
    fb = data[va - base:va - base + n*8]
    count = 0
    for ins in md.disasm(fb, va):
        print(f"0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
        count += 1
        if ins.mnemonic == "ret" and count > 20:
            return
        if count > n:
            return

# Show the data at 0x1e09624 (the second arg to 0x8a2e28)
print(f"\nData at 0x1e09624 (32 bytes): {data[0x1e09624 - base:0x1e09624 - base + 64].hex()}")
print(f"Data at 0x1e09624 (preceded by 4): {data[0x1e09624 - base - 4:0x1e09624 - base + 64].hex()}")

# 0x1e09624 is likely a Delphi WideString or AnsiString reference
# Try reading as len-prefixed ansi string
from_addr = 0x1e09624 - base
length_bytes = data[from_addr - 4:from_addr]
length = struct.unpack("<I", length_bytes)[0]
print(f"  As Delphi string: length={length}, data={data[from_addr:from_addr+min(length,64)]}")

# Disassemble 0x8a2b20
disasm(0x8a2b20, 400, "Decryptor inner @ 0x8a2b20")
