"""Build the patched ROM.

    python -X utf8 build.py [--out build/kabuki_en.sfc] [--marker]

Text runs with an `en` field are encoded into the expansion area (banks $30-$3F, file 0x180000-0x1FFFFF) and the
original run start is overwritten with `86 lo hi bank` (text-mode jump). The English ends with a jump back to the
byte after the original run (the next script op), unless it already ends with a {jump}. Runs without English stay
untouched, so a build with no English is byte-identical to the original (tests/test_build.py).
--marker replaces every run with "[id]" marker text (phase 4 tour).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import font  # noqa: E402
import text  # noqa: E402
import wrap  # noqa: E402
from script_ops import off  # noqa: E402

EXP_BANKS = range(0x30, 0x3F)  # LoROM 30:8000-3E:FFFF; bank $3F is reserved for QA debug scripts
ROM_SIZE = 0x200000
DICT_BANK = 0x30


class Space:
    """Bump allocator in the expansion banks; a block never crosses a bank (text is read via [$27],y)."""

    def __init__(self):
        self.bank, self.pos = DICT_BANK + 2, 0x8000  # banks $30-$31 hold the English dictionary

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


DICT_LOOKUP = 0x00BC31  # `LDA $2F0000,x` in 00:BBEE: reads the word pointer; becomes JML to dict_tail
DICT_READERS = (0x00E11D, 0x00E139, 0x039669, 0x0394E3)  # `LDA $2F0000,x` word readers; become JSL dict_read
DICT_SEL = 0x7FFFF8  # WRAM word: 0 = words in bank $30, 1 = bank $31 (never written in the original; RAM scan)
SPLIT_CODE = 0x0600  # codes below live in bank $30, the rest in bank $31 (the bank-$31 words follow the code)
DICT_BASES = 0x003C38  # 8 words: pointer-table base per code group (00:BC38)
DICT_BASE_9XX = 0x003C0B  # `LDA #$F30B` operand: base for codes >= 0x980 (00:BC0A)


def patch_dictionary(rom, entries):
    """Move the dictionary out of bank $2F (English does not fit one bank) into banks $30 and $31.

    Bank $30: the pointer tables (same group/index scheme as the original, dictwords.GROUPS) and the words for
    codes < SPLIT_CODE. Bank $31: two small routines, then the words for the other codes. Japanese words are
    copied where `en` is empty. 00:BBEE's pointer read becomes a JML to dict_tail, which also stores which bank
    the word is in (DICT_SEL); the four word readers become JSL dict_read, which reads from that bank."""
    import dictwords
    en = {e["id"]: e["en"] for e in entries}
    code_at = 0x318000
    helper = bytes([0xAF, DICT_SEL & 0xFF, DICT_SEL >> 8 & 0xFF, DICT_SEL >> 16,  # dict_read: LDA.l DICT_SEL
                    0xD0, 0x05,                                                   # BNE hi
                    0xBF, 0x00, 0x00, 0x30, 0x6B,                                 # LDA $300000,x ; RTL
                    0xBF, 0x00, 0x00, 0x31, 0x6B])                                # hi: LDA $310000,x ; RTL
    sel = [0x8F, DICT_SEL & 0xFF, DICT_SEL >> 8 & 0xFF, DICT_SEL >> 16]           # STA.l DICT_SEL
    tail = bytes([0xBF, 0x00, 0x00, 0x30, 0x48, 0xAA,                             # dict_tail: LDA $300000,x ; PHA ; TAX
                  0xC0, SPLIT_CODE & 0xFF, SPLIT_CODE >> 8, 0xB0, 0x09,           # CPY #SPLIT ; BCS hi
                  0xA9, 0x00, 0x00, *sel, 0x80, 0x07,                             # LDA #0 ; STA.l ; BRA done
                  0xA9, 0x01, 0x00, *sel,                                         # hi: LDA #1 ; STA.l
                  0x68, 0x28, 0x6B])                                              # done: PLA ; PLP ; RTL
    tail_at = code_at + len(helper)
    pos = 0x8000
    tables = []
    for base, first, n in dictwords.GROUPS:
        tables.append(pos)
        pos += 2 * n
    lo, hi = bytearray(), bytearray()
    lo_base, hi_base = pos, 0x8000 + len(helper) + len(tail)
    words = {}  # (bank, word bytes) -> offset
    ptrs = {}
    for base, first, n in dictwords.GROUPS:
        for i in range(n):
            code = first + i
            s = en.get(f"{code:04X}", "")
            if s:
                b = text.encode(s, text.EN.enc)
                ws = [int.from_bytes(b[k:k + 2], "big") for k in range(0, len(b), 2)]
            else:
                ws = dictwords.word(rom, code)
            ws[-1] |= 0x8000
            data = b"".join(w.to_bytes(2, "little") for w in ws)
            blob, start = (lo, lo_base) if code < SPLIT_CODE else (hi, hi_base)
            if (code < SPLIT_CODE, data) not in words:
                words[(code < SPLIT_CODE, data)] = start + len(blob)
                blob += data
            ptrs[code] = words[(code < SPLIT_CODE, data)]
    for name, end in (("$30", lo_base + len(lo)), ("$31", hi_base + len(hi))):
        if end > 0x10000:
            raise ValueError(f"dictionary does not fit bank {name}: {end - 0x10000:#x} bytes over")
    table = bytearray()
    for base, first, n in dictwords.GROUPS:
        for i in range(n):
            table += ptrs[first + i].to_bytes(2, "little")
    o = off(0x30 << 16 | 0x8000)
    rom[o:o + len(table) + len(lo)] = table + lo
    o = off(code_at)
    rom[o:o + len(helper) + len(tail) + len(hi)] = helper + tail + hi
    g0, g1, g2, g3, g5, g6, g6b, g7 = tables
    for k, v in enumerate((g0, g1, g2, g3, g3, g5, g6, g7)):
        rom[DICT_BASES + 2 * k:DICT_BASES + 2 * k + 2] = v.to_bytes(2, "little")
    assert rom[DICT_BASE_9XX - 1] == 0xA9
    rom[DICT_BASE_9XX:DICT_BASE_9XX + 2] = g6b.to_bytes(2, "little")
    o = off(DICT_LOOKUP)
    assert rom[o:o + 4] == b"\xbf\x00\x00\x2f"
    rom[o:o + 4] = bytes([0x5C, tail_at & 0xFF, tail_at >> 8 & 0xFF, tail_at >> 16])
    for a in DICT_READERS:
        o = off(a)
        assert rom[o:o + 4] == b"\xbf\x00\x00\x2f", hex(a)
        rom[o:o + 4] = bytes([0x22, code_at & 0xFF, code_at >> 8 & 0xFF, code_at >> 16])
    return len(table) + len(lo) + len(hi)


def build(out, marker=False, reloc_jp=False, qa=None, debug=None):
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
            dentries = json.loads((ROOT / "script" / "dict.json").read_text(encoding="utf-8"))
            if any(e["en"] for e in dentries):
                patch_dictionary(rom, dentries)
    if debug:
        patch_debug_start(rom, bytes.fromhex(debug.replace(" ", "")))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(rom)
    return rom, len(todo)


SCRIPT_TABLE = 0x03978E  # 3 bytes per script id; id 0 runs right after "new game"
DEBUG_AT = 0x3F8000  # last expansion bank: debug scripts only (QA builds, never in a release)


def patch_debug_start(rom, script):
    """QA only: script id 0 (the new-game script) runs `script` (raw event-script bytes) instead."""
    if len(rom) < ROM_SIZE:
        rom += b"\xff" * (ROM_SIZE - len(rom))
    o = off(DEBUG_AT)
    rom[o:o + len(script)] = script
    t = off(SCRIPT_TABLE)
    rom[t:t + 3] = DEBUG_AT.to_bytes(3, "little")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "build" / "kabuki_en.sfc"))
    ap.add_argument("--marker", action="store_true")
    ap.add_argument("--reloc-jp", action="store_true", help="relocate the Japanese runs unchanged (mechanism test)")
    ap.add_argument("--qa", action="append", default=[], metavar="ID=TEXT", help="override one run (stress lines)")
    ap.add_argument("--debug", metavar="HEX", help="QA build: new game runs these event-script bytes "
                    "(e.g. 'A4 30 75 B5 1B C8 00 0A 0A 0B FF'); see docs/re/debug.md")
    a = ap.parse_args()
    rom, n = build(a.out, a.marker, a.reloc_jp, dict(q.split("=", 1) for q in a.qa), a.debug)
    print(f"{a.out}: {len(rom):#x} bytes, {n} runs relocated")
