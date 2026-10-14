"""Build the patched ROM.

    python -X utf8 build.py [--out build/kabuki_en.sfc] [--marker]

Text runs with an `en` field are encoded into the expansion area (banks $30-$3F, file 0x180000-0x1FFFFF) and the
original run start is overwritten with `86 lo hi bank` (text-mode jump). The English ends with a jump back to the
byte after the original run (the next script op), unless it already ends with a {jump}. Runs without English stay
untouched, so a build with no English is byte-identical to the original (tests/test_build.py).
--marker replaces every run with "[id]" marker text (phase 4 tour).
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import font  # noqa: E402
import text  # noqa: E402
import wrap  # noqa: E402
from script_ops import off  # noqa: E402

EXP_BANKS = range(0x30, 0x40)  # LoROM 30:8000-3F:FFFF = file 0x180000-0x1FFFFF
ROM_SIZE = 0x200000


class Space:
    """Bump allocator in the expansion banks; a block never crosses a bank (text is read via [$27],y)."""

    def __init__(self):
        self.bank, self.pos = EXP_BANKS[0], 0x8000

    def alloc(self, n):
        if n > 0x8000:
            raise ValueError(f"block of {n} bytes cannot fit a bank")
        if self.pos + n > 0x10000:
            self.bank, self.pos = self.bank + 1, 0x8000
            if self.bank not in EXP_BANKS:
                raise ValueError("expansion area full")
        a = self.bank << 16 | self.pos
        self.pos += n
        return a


def jump(a):
    return bytes([0x86, a & 0xFF, a >> 8 & 0xFF, a >> 16])


CTRL_TOKEN = re.compile(r"\{\w+(?::[0-9A-F]+)?\}")


def marker_text(e):
    """'(ID)' then the run's control codes in order, so waits, choices and jumps keep working."""
    return f"({e['id']})" + "".join(CTRL_TOKEN.findall(e["jp"]))


CHOICE_CURSOR = 0x0393EF  # LDA #$012E in the text printer's yes/no handler
# shortcut: other `LDA #$012E/$012F` cursor sites (menus, docs/re/font.md) still draw N/O; fix with the menus
NAMES = {"name93": "Rock", "name94": "Makki"}  # glossary.md; widths in tools/wrap.py NAME_LEN
NAME_INIT = 0x009FE8  # LDX #imm / STX $614D.. pairs up to 00:A011, then REP #$30 at 00:A012


def patch_names(rom, space):
    """Replace the hard-coded JP name init with JSL to a loop copying both 6-word slots (7E:614D, 7E:6159)."""
    data = b""
    for key in ("name93", "name94"):
        ws = [int.from_bytes(text.EN.enc[c], "big") for c in NAMES[key]]
        assert len(ws) <= 6, key
        ws[-1] |= 0x8000
        data += b"".join(w.to_bytes(2, "little") for w in ws).ljust(12, b"\0")
    tbl = space.alloc(len(data))
    code_at = space.alloc(32)
    code = bytes([0x08, 0xC2, 0x30, 0xA2, 0x16, 0x00,                     # PHP; REP #$30; LDX #$0016
                  0xBF, tbl & 0xFF, tbl >> 8 & 0xFF, tbl >> 16,            # loop: LDA.l tbl,x
                  0x9F, 0x4D, 0x61, 0x7E,                                  # STA.l $7E614D,x
                  0xCA, 0xCA, 0x10, 0xF4,                                  # DEX; DEX; BPL loop
                  0x28, 0x6B])                                             # PLP; RTL
    rom[off(tbl):off(tbl) + len(data)] = data
    rom[off(code_at):off(code_at) + len(code)] = code
    o = off(NAME_INIT)
    rom[o:o + 6] = bytes([0x22, code_at & 0xFF, code_at >> 8 & 0xFF, code_at >> 16, 0x80, 0x24])  # JSL; BRA $A012
    assert NAME_INIT + 6 + 0x24 == 0x00A012


def build(out, marker=False, reloc_jp=False, qa=None):
    """qa: {id: text} overrides (stress lines for the width gate)."""
    rom = bytearray(text.ROM.read_bytes())
    entries = text.load()
    qa = qa or {}
    todo = []
    for e in entries:
        if e["size"] == 0:
            continue
        if e["id"] in qa:
            s, enc = qa[e["id"]], text.EN.enc
        elif reloc_jp:
            s, enc = e["jp"], text.JP.enc
        else:
            s, enc = (marker_text(e) if marker else e["en"]), text.EN.enc
        if s:
            todo.append((e, s, enc))
    if todo:
        rom += b"\xff" * (ROM_SIZE - len(rom))
        space = Space()
        for e, s, enc in todo:
            a = int(e["id"], 16)
            if enc is text.EN.enc:
                # a name code at a line start sets the JP hanging indent (03:93BD) and garbles English;
                # the names are fixed (00:9FE8, no rename seen), so write them as text
                for k, v in NAMES.items():
                    s = s.replace("{" + k + "}", v)
                s = wrap.wrap(s)
            body = text.encode(s, enc)
            if not re.search(r"\{jump:[0-9A-F]{6}\}$", s):
                body += jump(a + e["size"])
            dst = space.alloc(len(body))
            rom[off(dst):off(dst) + len(body)] = body
            rom[off(a):off(a) + 4] = jump(dst)
        if not reloc_jp:
            patch_names(rom, space)
            font.patch_font(rom)
            # the yes/no cursor glyph 0x12E (▶) is now "N": point it at the English ▶
            o = off(CHOICE_CURSOR)
            assert rom[o:o + 3] == b"\xa9\x2e\x01"
            rom[o + 1:o + 3] = int.from_bytes(text.EN.enc["▶"], "big").to_bytes(2, "little")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(rom)
    return rom, len(todo)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "build" / "kabuki_en.sfc"))
    ap.add_argument("--marker", action="store_true")
    ap.add_argument("--reloc-jp", action="store_true", help="relocate the Japanese runs unchanged (mechanism test)")
    ap.add_argument("--qa", action="append", default=[], metavar="ID=TEXT", help="override one run (stress lines)")
    a = ap.parse_args()
    rom, n = build(a.out, a.marker, a.reloc_jp, dict(q.split("=", 1) for q in a.qa))
    print(f"{a.out}: {len(rom):#x} bytes, {n} runs relocated")
