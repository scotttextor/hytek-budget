"""Try calling AutoFrame_GetChars with auth bypassed."""
import ctypes, sys, os
from ctypes import wintypes

DLL_PATH = r"C:\Program Files (x86)\FRAMECAD\Detailer\Version 5\AutoFrame.dll"

# Change to DLL dir so dependencies load (libcrypto-3.dll etc.)
os.chdir(os.path.dirname(DLL_PATH))

# Add to DLL search path
ctypes.windll.kernel32.SetDllDirectoryW(os.path.dirname(DLL_PATH))

print(f"Python bitness: {ctypes.sizeof(ctypes.c_void_p)*8}")

dll = ctypes.WinDLL(DLL_PATH)
print(f"Loaded {DLL_PATH}")

# Get base address
mod_handle = ctypes.windll.kernel32.GetModuleHandleW(DLL_PATH)
print(f"Module base: 0x{mod_handle:x}")

# Image base from PE header is 0x400000 — actual base may differ due to ASLR
# Calculate offset for auth flag at 0x5a4850 — that's RVA 0x1a4850
auth_flag_rva = 0x5a4850 - 0x400000
auth_flag_addr = mod_handle + auth_flag_rva
print(f"Auth flag addr: 0x{auth_flag_addr:x}")

# Read current auth flag
flag_byte = ctypes.c_ubyte.from_address(auth_flag_addr)
print(f"Current auth flag: {flag_byte.value}")

# Force-set auth flag
ctypes.c_ubyte.from_address(auth_flag_addr).value = 1
print(f"After setting: {ctypes.c_ubyte.from_address(auth_flag_addr).value}")

# Now call GetChars
GetChars = dll.AutoFrame_GetChars

# Delphi register convention => need CFUNCTYPE? No — Delphi register is non-standard.
# Real signature based on disasm: stdcall caller (push args), but inside it reads ebp+8 (arg1) and ebp+0xc (arg2)
# That looks like cdecl/stdcall (args on stack), not register

# Standard Win32 stdcall: 2 args
# arg1 = pointer to AnsiString (script name as a Delphi string — pointer, with len at -4)
# arg2 = pointer to AnsiString receiver (pointer-to-pointer)

# Try simplest: just pass char* and char**
GetChars.restype = ctypes.c_int
GetChars.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]

# Build a Delphi-style AnsiString for "PlaceServices"
# Delphi AnsiString: pointer points to the chars; len is at ptr-4, refcount at ptr-8
# But many APIs accept a regular char* — Delphi compares using SysUtils.AnsiCompareStr which reads the chars
# Let's try a regular C string

name = b"PlaceServices"
out_ptr = ctypes.c_void_p(0)

result = GetChars(name, ctypes.byref(out_ptr))
print(f"\nGetChars('PlaceServices') => result={result}")
print(f"out_ptr = 0x{out_ptr.value or 0:x}")

if out_ptr.value:
    # Read length (at out_ptr - 4) and then the string
    length_addr = out_ptr.value - 4
    length = ctypes.c_int.from_address(length_addr).value
    print(f"AnsiString length = {length}")
    if 0 < length < 100000:
        chars = ctypes.string_at(out_ptr.value, length)
        print(f"First 200: {chars[:200]!r}")
