"""Find functions that import EVP_DecryptInit_ex and trace back."""
import pefile, capstone, struct

DLL = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"
pe = pefile.PE(DLL, fast_load=False)
image_base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()

# IAT addresses
iat = {
    "EVP_aes_128_cbc": 0x5ac410,
    "EVP_CIPHER_CTX_free": 0x5ac414,
    "EVP_CIPHER_CTX_new": 0x5ac418,
    "EVP_DecryptInit_ex": 0x5ac41c,
    "EVP_DecryptUpdate": 0x5ac420,
    "EVP_DecryptFinal_ex": 0x5ac40c,
    "EVP_CIPHER_get_iv_length": 0x5ac424,
}

# Delphi imports are usually called via "call dword ptr [iat_addr]" => bytes ff 15 + addr
# OR via a thunk: jmp dword ptr [iat_addr] then call thunk
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

# Find direct call references (FF 15 or FF 25)
print("Searching for callers of EVP_DecryptInit_ex...")
text_start = 0x401000 - image_base
text_end = text_start + 0x19e030
text = data[text_start:text_end]

target = 0x5ac41c

# Search for "FF 15 1C C4 5A 00" (call dword [0x5ac41c])
needle = b"\xff\x15" + struct.pack("<I", target)
locs = []
i = 0
while True:
    p = text.find(needle, i)
    if p < 0: break
    va = image_base + text_start + p
    locs.append(va)
    i = p + 1
print(f"Direct call sites (FF 15) for EVP_DecryptInit_ex: {[hex(x) for x in locs]}")

# Also find thunk: jmp dword ptr [0x5ac41c] => FF 25
needle2 = b"\xff\x25" + struct.pack("<I", target)
locs2 = []
i = 0
while True:
    p = text.find(needle2, i)
    if p < 0: break
    va = image_base + text_start + p
    locs2.append(va)
    i = p + 1
print(f"Thunks (FF 25) for EVP_DecryptInit_ex: {[hex(x) for x in locs2]}")

# Find callers of those thunks
for thunk_va in locs2:
    needle3 = b"\xe8" + struct.pack("<i", 0)  # placeholder
    # Find e8 with relative offset matching thunk_va
    callers = []
    for p in range(len(text)):
        if text[p] == 0xe8:
            try:
                rel = struct.unpack("<i", text[p+1:p+5])[0]
                site_va = image_base + text_start + p
                target_va = site_va + 5 + rel
                if target_va == thunk_va:
                    callers.append(site_va)
            except struct.error:
                pass
    print(f"  Callers of thunk @ 0x{thunk_va:x}: {[hex(x) for x in callers[:20]]}")

# Disassemble around the first non-thunk caller
print("\nDisassembling around first caller:")
for caller in (locs + [c for thunk in locs2 for c in []]):
    rva = caller - image_base
    # Walk back ~64 bytes to find function start (push ebp; mov ebp,esp)
    start_rva = rva - 256
    bytes_ = data[start_rva:rva + 32]
    # Find prologue
    func_start = None
    for off in range(0, 256):
        if bytes_[off] == 0x55 and bytes_[off+1] == 0x8b and bytes_[off+2] == 0xec:
            func_start = start_rva + off
    if func_start:
        print(f"\n--- Function containing 0x{caller:x} (start 0x{image_base+func_start:x}) ---")
        fb = data[func_start:func_start + 800]
        for ins in md.disasm(fb, image_base + func_start):
            print(f"0x{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}")
            if ins.address >= caller + 16:
                pass
            if ins.mnemonic == "ret" and ins.address > caller + 32:
                break
        break
