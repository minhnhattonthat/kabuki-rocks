"""Dictionary words: text codes >= 0x300 expand to a glyph list in bank $2F (00:BBEE + printer 03:94DD).

    python -X utf8 tools/dictwords.py            # dump every word that decodes
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK2F = 0x2F << 15  # file offset of 2F:8000 is 0x178000; 2F:xxxx -> 0x178000 + (xxxx - 0x8000)


def lo(addr):
    return 0x178000 + (addr - 0x8000)


def entry_addr(rom, code):
    """Bank-$2F address of the word list for dictionary code (>= 0x300), as 00:BBEE computes it."""
    g = (code >> 8) - 3
    y = code
    if g == 6 and code >= 0x980:
        y, base = code - 0x80, 0xF30B
    else:
        base = int.from_bytes(rom[0x3C38 + 2 * g:0x3C3A + 2 * g], "little")
    idx = y & 0x1FF if (y & 0xFE00) == 0x600 else y & 0xFF
    return int.from_bytes(rom[lo(base + 2 * idx):lo(base + 2 * idx) + 2], "little")


def word(rom, code, maxlen=64):
    """Glyph codes of a dictionary word (LE words, last one has bit 15 set)."""
    p = lo(entry_addr(rom, code))
    out = []
    for _ in range(maxlen):
        w = int.from_bytes(rom[p:p + 2], "little")
        out.append(w & 0x7FFF)
        if w & 0x8000:
            return out
        p += 2
    raise ValueError(f"dictionary word {code:#x} unterminated")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / ".claude/skills/translate-retro-game/scripts"))
    from tbl import Table
    t = Table.load(ROOT / "tbl/jp.tbl")
    rom = (ROOT / "rom/Kabuki Rocks (Japan).sfc").read_bytes()
    for code in range(0x300, 0xB00):
        try:
            ws = word(rom, code)
        except (ValueError, IndexError):
            continue
        s = "".join(t.dec.get(w.to_bytes(2, "big"), f"[{w:03X}]") for w in ws)
        print(f"{code:04X} {entry_addr(rom, code):04X} {s}")
