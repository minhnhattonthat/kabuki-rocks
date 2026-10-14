"""Find words drawn one glyph at a time from immediates: `LDA #code` then a glyph call (JSR $B71D/$B725, JSL
$04B77B/$04B77F, JSL $02F08F), grouped into phrases when the sites follow each other closely.

    python -X utf8 tools/immlabels.py            # print phrases with their Japanese
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import text  # noqa: E402

CALLS = (b"\x20\x1d\xb7", b"\x20\x25\xb7", b"\x22\x7b\xb7\x04", b"\x22\x7f\xb7\x04", b"\x22\x8f\xf0\x02",
         b"\x22\x84\xf0\x02")


def cpu(o):
    return ((o // 0x8000) << 16) | 0x8000 | (o % 0x8000)


def sites(rom):
    """[(file offset of LDA, code)] for LDA #imm16 directly followed by a glyph call (or a 4C JMP $B71D)."""
    out = []
    for m in re.finditer(rb"\xa9(.)(.)", rom[:0x178000], re.S):
        o = m.start()
        code = m[1][0] | m[2][0] << 8
        if not (code < 0x300 or code == 0x02FF):
            continue
        tail = rom[o + 3:o + 7]
        if any(tail.startswith(c) for c in CALLS) or tail.startswith(b"\x4c\x1d\xb7") or tail.startswith(b"\x4c\x25\xb7"):
            out.append((o, code))
    return out


def phrases(rom, gap=14):
    groups, cur = [], []
    for o, code in sites(rom):
        if cur and o - cur[-1][0] > gap:
            groups.append(cur)
            cur = []
        cur.append((o, code))
    if cur:
        groups.append(cur)
    return groups


if __name__ == "__main__":
    rom = text.ROM.read_bytes()
    for g in phrases(rom):
        s = "".join(" " if c == 0x02FF else text.glyph(rom, c) for _, c in g)
        if any("぀" <= ch <= "鿿" for ch in s):
            print(f"{cpu(g[0][0]):06X} {len(g):2d} {s}")
