"""Find the system messages the code copies into the RAM script (7F:4000) with 00:90C2 / 00:90C7.

Each caller loads Y with the source address (LDY #imm16) shortly before `JSL/JSR $0090C2|$0090C7`; the helper copies
bytes until the word FFFF. The data is script bytes: a text op (87-8E), a text run, more ops, ending FF.

    python -X utf8 tools/sysmsg.py            # list call sites with the decoded Japanese
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import text  # noqa: E402
import script_ops  # noqa: E402

TEXT_OPS = {0x87, 0x88, 0x89, 0x8B, 0x8C, 0x8E}


def cpu(o):
    return ((o // 0x8000) << 16) | 0x8000 | (o % 0x8000)


def sites(rom):
    """[(call cpu addr, LDY# value)] for every call of the copier preceded by an LDY #imm within 14 bytes."""
    out = []
    for m in re.finditer(rb"\x22[\xc2\xc7]\x90\x00|\x20[\xc2\xc7]\x90", rom[:0x178000], re.S):
        h = m.start()
        for k in range(h - 3, max(h - 16, 0), -1):
            if rom[k] == 0xA0:
                out.append((cpu(h), rom[k + 1] | rom[k + 2] << 8))
                break
        else:
            out.append((cpu(h), None))
    return out


def stream(rom, bank, y):
    """Bytes of the message at bank:y up to the FFFF terminator (inclusive of the final byte before it)."""
    o = script_ops.off(bank << 16 | y)
    n = 0
    while rom[o + n:o + n + 2] != b"\xff\xff" and n < 400:
        n += 1
    return o, rom[o:o + n + 1]


def split(data):
    """(text op, text run bytes, the script ops after the run) of a message stream that starts with a text op."""
    assert data[0] in TEXT_OPS, data[:4].hex()
    i = 1
    while i < len(data):
        c = data[i]
        if c < 0x80:
            i += 2
        elif c in script_ops.TEXT_LEN:
            i += script_ops.TEXT_LEN[c]
        else:
            break
    return data[0], data[1:i], data[i:]


def codes(rom):
    """Every glyph code the system messages draw (they are not relocated or translated yet)."""
    out = set()
    for a, y in sites(rom):
        if y is None:
            continue
        data, i = stream(rom, a >> 16, y)[1], 0
        while i < len(data):
            if data[i] not in TEXT_OPS:
                i += 1
                continue
            i += 1
            while i < len(data):
                c = data[i]
                if c < 0x80 and i + 1 < len(data):
                    out.add(c << 8 | data[i + 1])
                    i += 2
                elif c in script_ops.TEXT_LEN:
                    i += script_ops.TEXT_LEN[c]
                else:
                    break
    return out


def readable(rom, data):
    out, i = [], 0
    while i < len(data):
        b = data[i]
        if b in TEXT_OPS:
            out.append(f"<{b:02X}>")
            i += 1
            while i < len(data):
                c = data[i]
                if c < 0x80:
                    out.append(text.glyph(rom, c << 8 | data[i + 1])); i += 2
                elif c in script_ops.TEXT_LEN:
                    n = script_ops.TEXT_LEN[c]
                    out.append("{" + text.CTRL[c][0] + "}" if c in text.CTRL else f"<{c:02X}>")
                    i += n
                else:
                    break
        else:
            out.append(f"<{b:02X}>")
            i += 1
    return "".join(out)


if __name__ == "__main__":
    rom = text.ROM.read_bytes()
    for a, y in sites(rom):
        if y is None:
            print(f"{a:06X}  (no LDY)")
            continue
        bank = a >> 16
        o, d = stream(rom, bank, y)
        print(f"{a:06X} Y={y:04X} file={o:06X} {readable(rom, d)}")
