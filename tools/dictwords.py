"""Dictionary words: text codes >= 0x300 expand to a glyph list in bank $2F (00:BBEE + printer 03:94DD).

    python -X utf8 tools/dictwords.py dump [--force]   # script/dict.json
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


# (pointer table base in bank $2F, first code, entries): a table ends where the first word data starts.
GROUPS = [(0xA74F, 0x300, 255), (0xB789, 0x400, 83), (0xBC2F, 0x500, 158), (0xC3F5, 0x600, 349),
          (0xDEAD, 0x800, 190), (0xF13B, 0x900, 45), (0xF30B, 0x980, 60), (0xF5BD, 0xA00, 191)]
DATA_END = 0xFDC0  # shortcut: end of the last word (max pointer 0xFDB3 + its length); verify before reusing space


def codes():
    return [c for _, first, n in GROUPS for c in range(first, first + n)]


def dump(force=False):
    import json
    sys.path.insert(0, str(ROOT / ".claude/skills/translate-retro-game/scripts"))
    from tbl import Table
    t = Table.load(ROOT / "tbl/jp.tbl")
    rom = (ROOT / "rom/Kabuki Rocks (Japan).sfc").read_bytes()
    out = []
    for code in codes():
        ws = word(rom, code)
        s = "".join(t.dec.get(w.to_bytes(2, "big"), f"[{w:04X}]") for w in ws)
        out.append({"id": f"{code:04X}", "ptr": f"{entry_addr(rom, code):04X}", "len": len(ws), "jp": s, "en": "",
                    "notes": ""})
    p = ROOT / "script" / "dict.json"
    if p.exists() and not force:
        sys.exit(f"{p} exists; --force overwrites English")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print(f"{p.name}: {len(out)} words")


if __name__ == "__main__":
    if sys.argv[1:2] == ["dump"]:
        dump("--force" in sys.argv)
    else:
        print(__doc__)
