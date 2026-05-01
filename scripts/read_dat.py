"""Read a FrameCAD Structure .dat file (encrypted or plain).

Usage:
  python3 read_dat.py <file>                    # show all sections + line counts
  python3 read_dat.py <file> --section "TRUSS"  # dump that section
  python3 read_dat.py <file> --grep "89S41"     # grep within decoded
  python3 read_dat.py <file> --save out.txt     # write decoded plain text

Auto-detects encryption: if file starts with "$.&" it's the FrameCAD cipher
(XOR 0x08 0x01 0x09 0x05 per line + leading comma marker), else treated as plain.
"""
import sys
import argparse

KEY = bytes([0x08, 0x01, 0x09, 0x05])


def decode_dat(raw, strip_leading_comma=True):
    out = bytearray()
    idx = 0
    line_start = True
    for b in raw:
        if b in (0x0d, 0x0a):
            out.append(b)
            idx = 0
            if b == 0x0a:
                line_start = True
            continue
        decoded = b ^ KEY[idx % 4]
        idx += 1
        if line_start and strip_leading_comma and decoded == ord(','):
            line_start = False
            continue
        line_start = False
        out.append(decoded)
    return bytes(out)


def is_encrypted(raw):
    return raw[:3] == b'$.&'


def load(path):
    raw = open(path, 'rb').read()
    if is_encrypted(raw):
        print(f"  [encrypted — decoding with FrameCAD cipher]", file=sys.stderr)
        return decode_dat(raw)
    return raw


def parse_sections(text):
    """Return list of (section_name, start_line, lines)."""
    lines = text.splitlines()
    sections = []
    current = None
    current_lines = []
    header_lines = []
    for i, line in enumerate(lines):
        if line.startswith('[') and ']' in line:
            if current is not None:
                sections.append((current, current_start, current_lines))
            else:
                # everything before first section is "header"
                if header_lines:
                    sections.append(('__HEADER__', 0, header_lines))
            current = line.strip('[] \t')
            current_start = i + 1
            current_lines = []
        else:
            if current is None:
                header_lines.append(line)
            else:
                current_lines.append(line)
    if current is not None:
        sections.append((current, current_start, current_lines))
    return sections


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--section', help='dump a section by name (substring match)')
    ap.add_argument('--grep', help='grep decoded plaintext')
    ap.add_argument('--save', help='write decoded plain text to file')
    ap.add_argument('--material', help='show MATERIAL_ entries matching substring')
    args = ap.parse_args()

    plain = load(args.file)
    text = plain.decode('latin1', errors='replace')

    if args.save:
        with open(args.save, 'wb') as f:
            f.write(plain)
        print(f"Saved {len(plain)} bytes to {args.save}")
        return

    if args.grep:
        for i, line in enumerate(text.splitlines(), 1):
            if args.grep.lower() in line.lower():
                print(f"{i:5d}: {line}")
        return

    if args.material:
        for line in text.splitlines():
            if line.startswith('MATERIAL_') and args.material.lower() in line.lower():
                print(line)
        return

    sections = parse_sections(text)

    if args.section:
        for name, start, lines in sections:
            if args.section.lower() in name.lower():
                print(f"=== [{name}] (line {start}, {len(lines)} lines) ===")
                for line in lines:
                    print(line)
                print()
        return

    # Default: list sections + counts + sample first record
    print(f"{'Section':<35} {'Line':>6} {'#lines':>7}  Preview")
    print('-' * 100)
    for name, start, lines in sections:
        nonblank = [l for l in lines if l.strip()]
        preview = nonblank[0][:60] if nonblank else ''
        print(f"{name:<35} {start:>6} {len(lines):>7}  {preview}")


if __name__ == '__main__':
    main()
