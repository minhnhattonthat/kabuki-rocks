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

EXP_BANKS = range(0x30, 0x3B)  # LoROM 30:8000-3A:FFFF; $3B-$3C code strings, $3F QA debug scripts
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
# other `LDA #$012E` (▶) glyph sites: equip compare arrows (00:DF9E, JSL $04B764), cursors (00:E26E, 1E:CEB9).
# Bank 05's #$012E/#$012F go into an object list (05:EFA1), not the font.
ARROW_SITES = (0x00DF9E, 0x00E26E, 0x1ECEB9)
# shortcut: other `LDA #$012E/$012F` cursor sites (menus, docs/re/font.md) still draw N/O; fix with the menus
NAMES = {"name93": "Rock", "name94": "Makki"}  # glossary.md; widths in tools/wrap.py NAME_LEN
NAME_INIT = 0x009FE8  # LDX #imm / STX $614D.. pairs up to 00:A011, then REP #$30 at 00:A012


def patch_sysmsg(rom, space):
    """System messages (script/sysmsg.json): script bytes copied by 00:90C7 into 7F:4000 and run there. Each
    template is rewritten in place as: text op, then per English segment `86 ptr` (text jump) to the segment in
    the expansion area, which jumps back into 7F:4000 right after; a {slot} is a glyph word the code stores into
    the copy (its `STA $7F40xx` operands are repointed); then the original ops after the text."""
    import sysmsg
    p = ROOT / "script" / "sysmsg.json"
    for e in json.loads(p.read_text(encoding="utf-8")) if p.exists() else []:
        if not e["en"]:
            continue
        bank, y = int(e["site"], 16) >> 16, int(e["y"], 16)
        o, data = sysmsg.stream(rom, bank, y)
        op, run, tail = sysmsg.split(data)
        s = e["en"]
        for k, v in NAMES.items():
            s = s.replace("{" + k + "}", v)
        slots = e.get("slots", [])
        assert s.count("{slot}") == len(slots), e["site"]
        for _, width in slots:  # wrap with each slot as a word of its widest value
            s = s.replace("{slot}", "~" * width, 1)
        choice = s.endswith("{n}")  # a choice follows on the next line: the text must fit the first two lines
        segs = wrap.wrap(s[:-3]) + "{n}" if choice else wrap.wrap(s)
        assert not choice or (segs.count("{n}") <= 2 and "{clr}" not in segs), (e["site"], segs)
        for _, width in slots:
            segs = segs.replace("~" * width, "\0", 1)
        segs = segs.split("\0")
        tpl = bytearray([op])
        offs = []
        for i, seg in enumerate(segs):
            if seg:
                body = text.encode(seg, text.EN.enc) + jump(0x7F4000 + len(tpl) + 4)
                dst = space.alloc(len(body))
                rom[off(dst):off(dst) + len(body)] = body
                tpl += jump(dst)
            if i < len(slots):
                offs.append(len(tpl))
                tpl += b"\x00\x00"
        tpl += tail + b"\xff"  # tail ends with the first FF of the FFFF the copier stops at
        assert len(tpl) <= len(data) + 1, (e["site"], len(tpl), len(data))
        assert all(tpl[k:k + 2] != b"\xff\xff" for k in range(len(tpl) - 2)), e["site"]
        rom[o:o + len(tpl)] = tpl
        for (sites, _), at in zip(slots, offs):
            for site in sites:
                so = off(int(site, 16))
                assert rom[so] == 0x8F and rom[so + 2:so + 4] == b"\x40\x7f", site  # STA $7F40xx
                rom[so + 1] = at


PLACARD = 0x24AE58  # battle: empty party slot placard 出演者求む (compressed 4bpp, 6x6 tiles, OBJ 16x16 x 9)
PLACARD_ROWS = [0, 3, 1, 4, 2, 5]  # screen tile row -> tile row in the block (16x16 sprites: top halves first)


def patch_placard(rom):
    """Redraw the placard's paper (x 11-35, y 5-42) as ACTORS / WANTED, tiny font at double height."""
    import lz
    o = off(PLACARD)
    raw, used = lz.decompress(rom, o, 0x480)
    raw = bytearray(raw)
    img = [[0] * 48 for _ in range(48)]
    for cy in range(6):
        for cx in range(6):
            b = raw[(PLACARD_ROWS[cy] * 6 + cx) * 32:][:32]
            for y in range(8):
                for x in range(8):
                    bit = 7 - x
                    img[cy * 8 + y][cx * 8 + x] = sum((b[k + 2 * y] >> bit & 1) << n
                                                      for n, k in enumerate((0, 1, 16, 17)))
    for y in range(5, 43):
        for x in range(11, 36):
            img[y][x] = 0xF  # paper
    tiny = font.load_tiny()
    for top, word in ((11, "ACTORS"), (27, "WANTED")):
        x0 = 11 + (25 - (4 * len(word) - 1)) // 2
        for i, ch in enumerate(word):
            for gy, row in enumerate(tiny[ch][1:]):  # caps use glyph rows 1-5
                for gx, p in enumerate(row):
                    if p:
                        img[top + 2 * gy][x0 + 4 * i + gx] = img[top + 2 * gy + 1][x0 + 4 * i + gx] = 1  # ink
    for cy in range(6):
        for cx in range(6):
            t = bytearray(32)
            for y in range(8):
                for x in range(8):
                    c = img[cy * 8 + y][cx * 8 + x]
                    for n, k in enumerate((0, 1, 16, 17)):
                        t[k + 2 * y] |= (c >> n & 1) << (7 - x)
            k = (PLACARD_ROWS[cy] * 6 + cx) * 32
            raw[k:k + 32] = t
    new = lz.compress(bytes(raw))
    assert len(new) <= used, f"placard: {len(new):#x} > {used:#x}"
    rom[o:o + len(new)] = new


CAPS = {  # 4x7 capitals (W, M 5 wide; I, T 3) for the title graphics
    "A": ".##.|#..#|#..#|####|#..#|#..#|#..#", "C": ".##.|#..#|#...|#...|#...|#..#|.##.",
    "D": "###.|#..#|#..#|#..#|#..#|#..#|###.", "E": "####|#...|#...|###.|#...|#...|####",
    "G": ".##.|#..#|#...|#.##|#..#|#..#|.###", "I": "###|.#.|.#.|.#.|.#.|.#.|###",
    "L": "#...|#...|#...|#...|#...|#...|####", "M": "#...#|##.##|#.#.#|#.#.#|#...#|#...#|#...#",
    "N": "#..#|##.#|##.#|#.##|#.##|#..#|#..#", "O": ".##.|#..#|#..#|#..#|#..#|#..#|.##.",
    "R": "###.|#..#|#..#|###.|#.#.|#..#|#..#", "S": ".###|#...|#...|.##.|...#|...#|###.",
    "T": "###|.#.|.#.|.#.|.#.|.#.|.#.", "U": "#..#|#..#|#..#|#..#|#..#|#..#|.##.",
    "W": "#...#|#...#|#...#|#.#.#|#.#.#|##.##|#...#", " ": "..|..|..|..|..|..|..",
}
TITLE_TILES = 0x18D26D  # BG1 tiles of the title (compressed, $28A0 bytes, tile 0 = BG1 tile 0)
TITLE_MENU = [("NEW GAME", [[0x115, 0x116, 0x11D, 0x11E, 0x121, 0x122], [0x117, 0x118, 0x11F, 0x120, 0x123, 0x124]]),
              ("CONTINUE", [[0x119, 0x11A, 0x10C, 0x10D, 0x10E, 0x10F], [0x11B, 0x11C, 0x110, 0x111, 0x112, 0x113]])]
# the BG1 map stream (19:8xxx) has `85 n1..n6` runs per menu row; 再公演 reused 公演's tiles, so its row moves to
# the tiles $10C-$113 the title leaves unused
TITLE_MAP_EDITS = [(bytes.fromhex("85191a1d1e2122"), bytes.fromhex("85191a0c0d0e0f")),
                   (bytes.fromhex("851b1c1f202324"), bytes.fromhex("851b1c10111213"))]
# vertical curtain text れっど / あとらす (BG3 2bpp tiles, uncompressed in bank $18): file offset per tile, top down
TITLE_CURTAINS = [("RED", [0xC00A0, 0xC0130, 0xC00B0, 0xC0140]),
                  ("ATLUS", [0xC0150, 0xC0160, 0xC0170, 0xC0180, 0xC0190, 0xC00C0])]


def caps_mask(word):
    """[rows][cols] 0/1 of `word` in CAPS with 1-px gaps."""
    glyphs = [CAPS[ch].split("|") for ch in word]
    w = sum(len(g[0]) for g in glyphs) + len(glyphs) - 1
    rows = [[0] * w for _ in range(7)]
    x = 0
    for g in glyphs:
        for y, r in enumerate(g):
            for dx, p in enumerate(r):
                rows[y][x + dx] = p == "#"
        x += len(g[0]) + 1
    return rows


def patch_title(rom):
    """Title screen: menu 初公演 / 再公演 -> NEW GAME / CONTINUE (fill C, outline E like the kanji), curtain
    texts れっど / あとらす -> RED / ATLUS."""
    import lz
    o = off(TITLE_TILES)
    raw, used = lz.decompress(rom, o, 0x28A0)
    raw = bytearray(raw)
    for word, tiles in TITLE_MENU:
        m = caps_mask(word)
        x0, y0 = (48 - len(m[0])) // 2, 5
        img = [[0] * 48 for _ in range(16)]
        for y in range(7):
            for x in range(len(m[0])):
                if m[y][x]:
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if img[y0 + y + dy][x0 + x + dx] == 0:
                                img[y0 + y + dy][x0 + x + dx] = 0xE  # outline
        for y in range(7):
            for x in range(len(m[0])):
                if m[y][x]:
                    img[y0 + y][x0 + x] = 0xC  # fill
        for ty, row in enumerate(tiles):
            for tx, t in enumerate(row):
                b = bytearray(32)
                for y in range(8):
                    for x in range(8):
                        c = img[ty * 8 + y][tx * 8 + x]
                        for n, k in enumerate((0, 1, 16, 17)):
                            b[k + 2 * y] |= (c >> n & 1) << (7 - x)
                raw[t * 32:t * 32 + 32] = b
    new = lz.compress(bytes(raw))
    assert len(new) <= used, f"title tiles: {len(new):#x} > {used:#x}"
    rom[o:o + len(new)] = new
    for old, new in TITLE_MAP_EDITS:
        k = rom.find(old, off(0x198000), off(0x1A0000))
        assert k >= 0 and rom.find(old, k + 1, off(0x1A0000)) < 0, old.hex()
        rom[k:k + len(new)] = new
    for word, offs in TITLE_CURTAINS:
        for i, fo in enumerate(offs):
            rows = [[3] * 8 for _ in range(8)]  # curtain colour
            if i < len(word):
                m = caps_mask(word[i])
                for y in range(7):
                    for x in range(len(m[0])):
                        if m[y][x]:
                            rows[y][(8 - len(m[0])) // 2 + x] = 1  # ink
            rom[fo:fo + 16] = font.encode_tile(rows)


CHOICE_STORES = 0x03940B  # text printer yes/no (03:93E6): は い at cells 1-2, い い え at 9-11 (cells $80 apart)
CHOICE_AT = 0x3CBC00
CHOICE_ORIG = bytes.fromhex("daa91900229dba00faa5009d0028a5029d0228daa90100229dba00faa5009d80289d002c9d802ca5029d8228"
                            "9d022c9d822cdaa90300229dba00faa5009d002da5029d022d")


def patch_choice(rom):
    """Every Yes/No choice: 'Yes' after the first cursor cell, 'No' after the second (generated code, JSL)."""
    o = off(CHOICE_STORES)
    assert rom[o:o + len(CHOICE_ORIG)] == CHOICE_ORIG
    code = bytearray()
    for cell, ch in [(1, "Y"), (2, "e"), (3, "s"), (9, "N"), (10, "o"), (11, " ")]:
        a = 0x2780 + cell * 0x80
        g = int.from_bytes(text.EN.enc[ch], "big")
        code += bytes([0xDA, 0xA9, g & 0xFF, g >> 8, 0x22, 0x9D, 0xBA, 0x00, 0xFA,  # PHX ; LDA #g ; JSL $00BA9D ; PLX
                       0xAD, 0x00, 0x08, 0x9D, a & 0xFF, a >> 8,                    # LDA $0800 ; STA top,x
                       0xAD, 0x02, 0x08, 0x9D, (a + 2) & 0xFF, (a + 2) >> 8])       # LDA $0802 ; STA bottom,x
    code += b"\x6b"
    c = off(CHOICE_AT)
    assert rom[c:c + len(code)] == b"\xff" * len(code)
    rom[c:c + len(code)] = code
    rom[o:o + len(CHOICE_ORIG)] = bytes([0x22, CHOICE_AT & 0xFF, CHOICE_AT >> 8 & 0xFF, CHOICE_AT >> 16]) \
        + b"\xea" * (len(CHOICE_ORIG) - 4)


BATTLE_STORE = 0x02F08F  # battle glyph store: PHX PHY JSL $00BAEF PLY PLX, then $0800/$0802 -> $2780/$27C0,y
MSG_LINE, MSG_CELLS = 0x1044, 28  # battle message line (02:E9A3 clears it with X=$1C before most messages)


def patch_msgclear(rom, space):
    """A glyph drawn at the start of the battle message line blanks the whole line first. Some messages
    (" took damage") print without clearing; the JP texts were long enough to cover the previous one."""
    o = off(BATTLE_STORE)
    assert rom[o:o + 8] == bytes.fromhex("da5a22efba007afa")
    plain = bytes.fromhex("da5a22efba007afa6b")                          # PHX PHY JSL $00BAEF PLY PLX RTL
    def half(src, dst):  # LDA src ; AND #$E3FF ; ORA $000709 ; STA dst+line,x
        return (b"\xad" + src.to_bytes(2, "little") + bytes.fromhex("29ffe30f090700") + b"\x9d"
                + (dst + MSG_LINE).to_bytes(2, "little"))
    loop = (half(0x0800, 0x2780) + half(0x0802, 0x27C0)
            + b"\xe8\xe8\xe0" + (2 * MSG_CELLS).to_bytes(2, "little"))   # INX INX ; CPX #2*cells
    loop += bytes([0x90, (-(len(loop) + 2)) & 0xFF])                     # BCC loop
    clear = (bytes.fromhex("48da5a a9ff02 22efba00 7a a20000".replace(" ", ""))  # PHA PHX PHY ; blank tiles ; PLY
             + loop + b"\xfa\x68")                                       # PLX PLA
    code = b"\xc0" + MSG_LINE.to_bytes(2, "little") + bytes([0xD0, len(clear)]) + clear + plain  # CPY ; BNE plain
    at = space.alloc(len(code))
    rom[off(at):off(at) + len(code)] = code
    rom[o:o + 8] = bytes([0x22, at & 0xFF, at >> 8 & 0xFF, at >> 16]) + b"\xea" * 4


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


DICT_OVERFLOW = 0x30  # English dictionary words that do not fit bank $2F
DICT_READ = 0x318000  # helper: dictionary word read for the `LDA $2F0000,x ; BMI` loops
# Groups whose words must stay in bank $2F (read through a 24-bit pointer fixed to bank $2F, e.g. 02:93E2 battle
# messages), then the rest in order of how likely code reads them; the tail spills to DICT_OVERFLOW.
DICT_PRIORITY = (0x8, 0x9, 0x3, 0x4, 0x5, 0x6, 0xA)  # code >> 8 (0x6 covers 0x600-0x7FF)


def patch_dictionary(rom, entries):
    """English dictionary words, with the pointer tables left in place in bank $2F.

    Several routines read the tables directly (00:BBEE, `LDA $2FA74F,x` at 07:ADAA, `$2FDEAD,x` at 02:93DA) and
    bank $2F also holds item data, so only the pointers change. Words go into the old word space of bank $2F
    first (DICT_PRIORITY order); the rest go to bank DICT_OVERFLOW and their pointer is stored as address-$8000
    (< $8000). Every `LDA $2F0000,x ; BMI` word loop becomes JSL DICT_READ: X < $8000 reads DICT_OVERFLOW:8000+X,
    otherwise bank $2F as before. Japanese is kept where `en` is empty."""
    import dictwords
    en = {e["id"]: e["en"] for e in entries}
    # free space in bank $2F: the extents of the original word lists
    tables = [(base, base + 2 * n) for base, first, n in dictwords.GROUPS]
    spans = sorted({(dictwords.entry_addr(rom, c), len(dictwords.word(rom, c))) for c in dictwords.codes()})
    # junk codes point below $8000 or into the tables: never count those as free
    spans = [(a, n) for a, n in spans if 0xA74F <= a and a + 2 * n <= dictwords.DATA_END
             and not any(t0 < a + 2 * n and a < t1 for t0, t1 in tables)]
    free = []
    for a, n in spans:
        a, e = a, a + 2 * n
        if free and a <= free[-1][1]:
            free[-1][1] = max(free[-1][1], e)
        else:
            free.append([a, e])
    data_of = {}
    for code in dictwords.codes():
        s = en.get(f"{code:04X}", "")
        if s:
            b = text.encode(s, text.EN.enc)
            ws = [int.from_bytes(b[k:k + 2], "big") for k in range(0, len(b), 2)]
        else:
            ws = dictwords.word(rom, code)
        ws[-1] |= 0x8000
        data_of[code] = b"".join(w.to_bytes(2, "little") for w in ws)
    order = sorted(dictwords.codes(), key=lambda c: (DICT_PRIORITY.index(c >> 8 & 0xFE if c >> 8 in (6, 7)
                                                                         else c >> 8), c))
    placed, ptrs = {}, {}
    over = bytearray()
    for c in order:
        d = data_of[c]
        if d in placed:
            ptrs[c] = placed[d]
            continue
        for iv in free:
            if iv[1] - iv[0] >= len(d):
                p = iv[0]
                iv[0] += len(d)
                rom[off(0x2F << 16 | p):off(0x2F << 16 | p) + len(d)] = d
                break
        else:
            if 0x8000 + len(over) + len(d) > 0x10000:
                raise ValueError("dictionary overflow bank full")
            p = len(over)  # stored as address - $8000
            over += d
        placed[d] = ptrs[c] = p
    o = off(DICT_OVERFLOW << 16 | 0x8000)
    rom[o:o + len(over)] = over
    for base, first, n in dictwords.GROUPS:  # rewrite the pointer tables in place
        for i in range(n):
            t = off(0x2F << 16 | (base + 2 * i))
            rom[t:t + 2] = ptrs[first + i].to_bytes(2, "little")
    helper = bytes([0xE0, 0x00, 0x80, 0xB0, 0x05,                 # CPX #$8000 ; BCS in2f
                    0xBF, 0x00, 0x80, DICT_OVERFLOW, 0x6B,        # LDA $308000,x ; RTL
                    0xBF, 0x00, 0x00, 0x2F, 0x6B])                # in2f: LDA $2F0000,x ; RTL
    o = off(DICT_READ)
    rom[o:o + len(helper)] = helper
    for m in re.finditer(rb"\xbf\x00\x00\x2f\x30", bytes(rom[:0x178000])):
        rom[m.start():m.start() + 4] = bytes([0x22, DICT_READ & 0xFF, DICT_READ >> 8 & 0xFF, DICT_READ >> 16])
    return len(over)


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
            patch_sysmsg(rom, space)  # before the font: kana it no longer uses join the tiny-text pool
            patch_choice(rom)
            patch_placard(rom)
            patch_title(rom)
            patch_names(rom, space)
            patch_msgclear(rom, space)
            plan = label_plan()
            uniq = {}  # identical baked cells share one glyph code
            for _, cells in plan:
                for c in cells:
                    if isinstance(c, list):
                        uniq.setdefault(repr(c), c)
            ext = []
            font.patch_font(rom, extra=list(uniq.values()), extra_out=ext)
            install_glyph_ext(rom, ext)
            codes = [c for c, _, _, _ in ext]
            write_labels(rom, plan, dict(zip(uniq, codes)))
            # for QA (tools/jpscreen.py): glyph codes that now hold baked English label cells
            (ROOT / "build").mkdir(exist_ok=True)
            (ROOT / "build" / "baked_codes.json").write_text(json.dumps(codes), encoding="utf-8")
            # the yes/no cursor glyph 0x12E (▶) is now "N": point it at the English ▶
            for site in (CHOICE_CURSOR,) + ARROW_SITES:
                o = off(site)
                assert rom[o:o + 3] == b"\xa9\x2e\x01", hex(site)
                rom[o + 1:o + 3] = int.from_bytes(text.EN.enc["▶"], "big").to_bytes(2, "little")
            dentries = json.loads((ROOT / "script" / "dict.json").read_text(encoding="utf-8"))
            dict_end = patch_dictionary(rom, dentries) if any(e["en"] for e in dentries) else 0
            cpath = ROOT / "script" / "code.json"
            if cpath.exists():
                patch_codestr(rom, json.loads(cpath.read_text(encoding="utf-8")))
            patch_fixed(rom)
            patch_menutiles(rom)
            patch_name_limits(rom)
            patch_tab_spacers(rom)
            patch_tiny(rom, dict_end)
    if debug:
        patch_debug_start(rom, debug_bytes(debug))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_bytes(rom)
    return rom, len(todo)


CODESTR_BANK = 0x3B  # English for strings that live in code banks (script/code.json)
# not relocatable this way: 078D81 is a false hit (07:81A4 is LDA #$81 / STA $4200); 02F078/02F07E are read as
# $F078 + offset (fixed 6-byte slots; labels); banks $05/$0F use other readers (prologue, composer) - TODO
# 04AD5F/0FCA01: their only "reference" is an 8-bit LDX/LDY #imm misread as 16-bit (04:EEBE is LDX #$5F)
CODESTR_SKIP_IDS = {"078D81", "02F078", "02F07E", "0FCA01"}
CODESTR_SKIP_BANKS = {0x05, 0x0F}
CODESTR_HELPERS = 0x3C8000  # one reader helper per source bank


def patch_codestr(rom, entries):
    """English for bit-15 strings referenced from code (tools/codestr.py catalog).

    Each source bank B gets a window [S, E) of addresses: the English sits at those addresses in CODESTR_BANK,
    and [S, E) is chosen where bank B itself holds no strings. Every bit-15 reader of bank B (`LDA $B0000,x`
    followed by BMI) becomes JSL helper_B: read CODESTR_BANK when S <= X < E, else bank B as before. All
    references (LDX/LDY/LDA #imm, pointer-table words) of a translated string are repointed."""
    import codestr
    by_bank = {}
    for e in entries:
        bank = int(e["id"][:2], 16)
        if e["en"] and e["id"] not in CODESTR_SKIP_IDS and bank not in CODESTR_SKIP_BANKS:
            by_bank.setdefault(bank, []).append(e)
    if not by_bank:
        return 0
    taken = set()  # string-ish starts per bank, from the blind scan and the catalog
    for o, n, term, s in codestr.scan(bytes(rom[:0x180000]), 1):
        taken.add((o // 0x8000, codestr.cpu(o) & 0xFFFF))
    for e in entries:
        taken.add((int(e["id"][:2], 16), int(e["id"][2:], 16)))
    pos = 0x8000
    helpers = bytearray()
    for bank, es in sorted(by_bank.items()):
        blobs = []
        for e in es:
            b = text.encode(e["en"], text.EN.enc)
            ws = [int.from_bytes(b[k:k + 2], "big") for k in range(0, len(b), 2)]
            ws[-1] |= 0x8000
            blobs.append(b"".join(w.to_bytes(2, "little") for w in ws))
        size = sum(map(len, blobs))
        while any(bb == bank and pos <= a < pos + size for bb, a in taken):
            pos += 0x100
        if pos + size > 0x10000:
            raise ValueError(f"code strings do not fit bank ${CODESTR_BANK:02X}")
        start, end = pos, pos + size
        for e, blob in zip(es, blobs):
            old, new = int(e["id"][2:], 16), pos
            rom[off(CODESTR_BANK << 16 | pos):off(CODESTR_BANK << 16 | pos) + len(blob)] = blob
            for site, kind in e["refs"]:
                o = off(int(site, 16)) + (0 if kind == "table" else 1)
                if kind == "end":  # CPX #end of a run of consecutive strings printed in a loop (04:ABDA)
                    old_end, new_end = old + 2 * e["len"], new + len(blob)
                    assert int.from_bytes(rom[o:o + 2], "little") == old_end, (e["id"], site)
                    rom[o:o + 2] = new_end.to_bytes(2, "little")
                    continue
                assert int.from_bytes(rom[o:o + 2], "little") == old, (e["id"], site)
                rom[o:o + 2] = new.to_bytes(2, "little")
            pos += len(blob)
        pos = (pos + 0xFF) & ~0xFF
        h = CODESTR_HELPERS + len(helpers)
        helpers += bytes([0xE0, start & 0xFF, start >> 8, 0x90, 0x0A,           # CPX #S ; BCC old
                          0xE0, end & 0xFF, end >> 8, 0xB0, 0x05,               # CPX #E ; BCS old
                          0xBF, 0x00, 0x00, CODESTR_BANK, 0x6B,                 # LDA new,x ; RTL
                          0xBF, 0x00, 0x00, bank, 0x6B])                        # old: LDA $B0000,x ; RTL
        pat = bytes([0xBF, 0x00, 0x00, bank])
        for m in re.finditer(re.escape(pat), bytes(rom[:0x180000])):
            if rom[m.start() + 4] == 0x30:  # a string reader: LDA long,x ; BMI
                rom[m.start():m.start() + 4] = bytes([0x22, h & 0xFF, h >> 8 & 0xFF, h >> 16])
    o = off(CODESTR_HELPERS)
    rom[o:o + len(helpers)] = helpers
    return sum(len(v) for v in by_bank.values())


def label_plan():
    """[(addr, cells)] for every translated label in script/labels.json. Each cell is either a 2-byte glyph code
    (label fits the normal font) or an 8x16 pixel cell to bake with the tiny font (font.render_label)."""
    p = ROOT / "script" / "labels.json"
    plan = []
    imm = None
    for e in json.loads(p.read_text(encoding="utf-8")) if p.exists() else []:
        if not e["en"]:
            continue
        if e.get("kind") in ("tiny", "tinyrows", "tinytable"):  # build.py patch_tiny
            continue
        if e.get("kind") == "hook":
            for s in e["en"]:
                plan.append((("hook", e["id"]), label_cells(s, e["cells"])))
            continue
        if e.get("kind") == "imm":
            if imm is None:
                import immlabels
                imm = {immlabels.cpu(g[0][0]): g for g in immlabels.phrases(text.ROM.read_bytes())}
            g = imm[int(e["id"], 16)]
            assert len(g) == e["count"], (e["id"], len(g))
            split = e.get("split", [e["count"]])
            cells, k = [], 0
            for n, s in zip(split, e["en"]):
                if s is None:  # keep the original glyphs
                    cells += [g[k + i][1] for i in range(n)]
                else:
                    cells += label_cells(s, n)
                k += n
            plan.append((("imm", [immlabels.cpu(o) for o, _ in g]), cells))
            continue
        assert len(e["en"]) == e["count"], e["id"]
        for i, s in enumerate(e["en"]):
            n = e["cells"]
            addr = int(e["id"], 16) + 2 * n * i
            plan.append(((addr, e.get("term", False)), label_cells(s, n)))
    return plan


GLYPH_TABLE_EXT = 0x3D0000  # bank holding the extended copy of the glyph tile-pair table (at its old offset BC48)
PAGE_FN = 0x3D8000  # page selector for 00:BAEF / 00:BB6A that also knows the new label codes (font.EXT_BASE)
PAGE_SITES = (0x00BB0D, 0x00BB88)  # LDX #3 / CPY #$1C0 / ... page selection (21 bytes each)
TABLE_READS = (0x00BB3B, 0x00BB49, 0x00BBCF, 0x00BBDD)  # LDA $00BC48,x / LDA $00BC49,x


def install_glyph_ext(rom, ext):
    """Label glyph codes beyond the original set: code c on page p uses table index (c - SUB[p])*2 + ADD[p]
    exactly like the originals, read from a copy of 00:BC48 in GLYPH_TABLE_EXT that has room past its end."""
    sub = [int.from_bytes(rom[0x3B5A + 2 * p:0x3B5C + 2 * p], "little") for p in range(4)]
    add = [int.from_bytes(rom[0x3B62 + 2 * p:0x3B64 + 2 * p], "little") for p in range(4)]
    base = GLYPH_TABLE_EXT | 0xBC48
    o = off(base)
    rom[o:o + 0x5C8] = rom[0x3C48:0x3C48 + 0x5C8]  # original entries (page 3 runs to code 0x2FF)
    for code, p, top, bot in ext:
        idx = (code - sub[p]) * 2 + add[p]
        assert idx >= 0x5C8 and (base & 0xFFFF) + idx + 1 < 0x10000, hex(code)
        rom[o + idx:o + idx + 2] = bytes([top, bot])
    for site in TABLE_READS:
        so = off(site)
        assert rom[so] == 0xBF and rom[so + 3] == 0x00, hex(site)
        rom[so + 3] = GLYPH_TABLE_EXT >> 16
    b1, b2, b3 = font.EXT_BASE[1], font.EXT_BASE[2], font.EXT_BASE[3]
    fn = bytes([0xC0, b3 & 0xFF, b3 >> 8, 0xB0, 0x28,          # CPY #ext3 ; BCS p3 (idx 45)
                0xC0, b2 & 0xFF, b2 >> 8, 0xB0, 0x1F,          # CPY #ext2 ; BCS p2 (idx 41)
                0xC0, b1 & 0xFF, b1 >> 8, 0xB0, 0x16,          # CPY #ext1 ; BCS p1 (idx 37)
                0xA2, 0x03, 0x00, 0xC0, 0xC0, 0x01, 0xB0, 0x0D,  # the original selection
                0xCA, 0xC0, 0x40, 0x01, 0xB0, 0x07,
                0xCA, 0xC0, 0xB0, 0x00, 0xB0, 0x01, 0xCA, 0x6B,  # ... ; RTL
                0xA2, 0x01, 0x00, 0x6B,                        # p1: LDX #1 ; RTL
                0xA2, 0x02, 0x00, 0x6B,                        # p2: LDX #2 ; RTL
                0xA2, 0x03, 0x00, 0x6B])                       # p3: LDX #3 ; RTL
    rom[off(PAGE_FN):off(PAGE_FN) + len(fn)] = fn
    for site in PAGE_SITES:
        so = off(site)
        assert rom[so:so + 21] == bytes.fromhex("a20300c0c001b00dcac04001b007cac0b000b001ca"), hex(site)
        rom[so:so + 21] = bytes([0x22, PAGE_FN & 0xFF, PAGE_FN >> 8 & 0xFF, PAGE_FN >> 16]) + b"\xea" * 17


ASAR = ROOT / "tools" / "asar" / "asar.exe"  # gitignored binary (Asar 1.91)
TINY_AT = 0x3E8000  # asm/tiny.asm: item names in the field lists drawn in the tiny font at run time
TINY_FONT = 0x3E9000  # its letters: 8 bytes per glyph code from 0x100
TINY_CODES = 0x65  # codes 0x100-0x164 (ASCII + extras)
# item-name loops `JSL DICT_READ ; BMI ; draw ; INX ; INX ; BRA` -> JSL entry + what follows the loop
_B71D, _B725 = b"\x30\x07\x20\x1d\xb7\xe8\xe8\x80\xf3", b"\x30\x07\x20\x25\xb7\xe8\xe8\x80\xf3"
TINY_SITES = {0x049FE9: ("tiny71d", _B71D, b"\x80\x0d"),  # item list (BRA $9FFC)
              0x04BEA7: ("tiny725", _B725, b"\x80\x0d"),  # item list with greyed entries (BRA $BEBA)
              0x04C3FB: ("tiny725", _B725, b"\x60"),      # song weapon list (ended in JMP $B725)
              # equip/exchange slots (04:B65F), item and song description headers (04:C000, 04:C4F8)
              0x04C4FB: ("tiny71d", _B71D, b"\x60"),
              0x04DF22: ("tiny71d", _B71D, b"\x80\x0d"),  # shop list (BRA $DF35)
              0x04E118: ("tiny71d", _B71D, b"\x60"),      # shop (the loop ended the routine: RTS)
              # 00:E133 (dictionary word A at Y, e.g. the Forte description 04:9449); in battle it stays per-glyph
              0x00E139: ("tiny71d", b"\x30\x08\x22\x7b\xb7\x04\xe8\xe8\x80\xf2", b"\x6b"),
              # battle item and song lists (name pointer in $07E5; JSL $02F08F per glyph): BRA $DF4F
              0x02DF3A: ("tiny_f08f", b"\x30\x08\x22\x8f\xf0\x02\xe8\xe8\x80\xf2", b"\x80\x0f")}
# whole English phrases drawn by the tiny renderer instead of glyph-by-glyph code (labels.json kind "tiny", id =
# site): original bytes there, tilemap position, entry; the bytes become LDY #pos ; LDX #string ; JSL entry
TINY_HOOKS = {
    # shop confirm menu (04:D59B): はい / いいえ / 売る|買う + のをやめる
    "04D5AF": (bytes.fromhex("a0241ba91900201db7a90100201db7"), 0x1B24, "tiny71d"),
    "04D5BE": (bytes.fromhex("a0a41ba90100201db7a90100201db7a90300201db7"), 0x1BA4, "tiny71d"),
    "04D4B6": (bytes.fromhex("a0241ca94101201db7a92800201db7"), 0x1C24, "tiny71d"),
    "04D4E1": (bytes.fromhex("a0241ca94001201db7a90200201db7"), 0x1C24, "tiny71d"),
    "04ABB9": (bytes.fromhex("a0b608a97102201db7c8c8a9b001201db7"), 0x08B6, "tiny71d"),  # config title 設 定
    # button config title: string 04:AD7B (コントローラー, read directly) + 設定
    "04AEAC": (bytes.fromhex("a20000a0aa08bf7bad04300720" "1db7e8e880f329ff7f201db7a97102201db7a9b001201db7"),
               0x08AA, "tiny71d"),
    # battle song header 消費 / 効果 (02:BE24, attribute set just before)
    "02BE24": (bytes.fromhex("a9fb00a06610228ff002a90202228ff002"), 0x1066, "tiny_f08f"),
    "02BE35": (bytes.fromhex("a90502a07210228ff002a91a01228ff002"), 0x1072, "tiny_f08f"),
}


# code that printed fixed rows of labels -> one tiny string per row (labels.json kind "tinyrows", id = where it
# starts): original bytes there (replaced by JSL generated code, + RTL if `ret`), row positions (Y of the first row
# with Y passed in and a step, or a list), ret. Generated code at TINY_ROWS_AT.
TINY_ROWS = {
    "04A993": (bytes.fromhex("84e3a90900"), 0x80, True),  # status screen stat names (04:A99D loop, 9 rows)
    # button config: おわる / スタート / セレクト = first letter (table 04:B056) + inline (Y, string) pairs at 04:B05F
    "04AEFD": (bytes.fromhex("a25fb0a05c09bf000004a8e8e820aab2e077b090f1"), [0x095C, 0x0BDC, 0x0C5C], False),
}
TINY_ROWS_AT = 0x3CB000
# a printer of strings picked through a pointer table (labels.json kind "tinytable": "keys" = the X values at the
# `LDA long,x` that fetches the pointer, "en"): that LDA reads a new table of English string pointers instead, and
# the string loop that follows becomes JSL entry ; BRA cont. {id = the LDA: (loop start, cont, entry)}
TINY_TABLES = {
    "04ADCA": (0x04ADCF, 0x04ADE8, "tiny725"),  # config values (04:AD8D): 8-bit kana strings via 04:ADFB.. tables
    "04B104": (0x04B10A, 0x04B11D, "tiny725"),  # button functions (04:B0D5), X = function * 2
}
TINY_TABLE_AT = 0x3CB800


def patch_tiny(rom, dict_end=0):
    """Item names in the field lists two letters per cell, rendered at run time (asm/tiny.asm, font.TINY_POOL).
    dict_end: bytes used in DICT_OVERFLOW; the TINY_HOOKS strings go after them (DICT_READ reads them there)."""
    import subprocess
    char = {int.from_bytes(v, "big"): ch for ch, v in text.EN.enc.items() if len(v) == 2}
    tiny = font.load_tiny()
    tbl = bytearray(8 * TINY_CODES)
    for i in range(TINY_CODES):
        g = tiny.get(char.get(0x100 + i))
        if g:
            tbl[8 * i:8 * i + 7] = bytes(sum(p << (7 - x) for x, p in enumerate(r)) for r in g) + b"\x01"
    rom[off(TINY_FONT):off(TINY_FONT) + len(tbl)] = tbl
    t0, n = font.TINY_POOL
    defs = {"CODE": TINY_AT, "POOL_T0": t0, "POOL_N": n, "DICT_READ": DICT_READ, "TINY_FONT": TINY_FONT,
            "TINY_N": TINY_CODES}
    tmp = ROOT / "build" / "_tiny.sfc"
    tmp.parent.mkdir(exist_ok=True)
    tmp.write_bytes(rom)
    r = subprocess.run([str(ASAR), "--fix-checksum=off", "--no-title-check",
                        *(f"-D{k}=${v:X}" for k, v in defs.items()), str(ROOT / "asm" / "tiny.asm"), str(tmp)],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("asar: " + r.stdout + r.stderr)
    sym = {k: int(v, 16) for k, v in (line.split("=") for line in r.stdout.split())}
    assert sym["end"] <= TINY_FONT, "asm/tiny.asm runs into TINY_FONT"
    rom[:] = tmp.read_bytes()
    tmp.unlink()

    def jsl(name):
        return bytes([0x22, sym[name] & 0xFF, sym[name] >> 8 & 0xFF, sym[name] >> 16])

    read = bytes([0x22, DICT_READ & 0xFF, DICT_READ >> 8 & 0xFF, DICT_READ >> 16])
    for site, (entry, loop, after) in TINY_SITES.items():
        o = off(site)
        assert rom[o:o + 4 + len(loop)] == read + loop, hex(site)
        rom[o:o + 4 + len(after)] = jsl(entry) + after
    patches = {0x0082A8: (bytes.fromhex("a9808d1521"), jsl("nmi_upload") + b"\xea"),  # NMI: upload the cells
               0x00B817: (bytes.fromhex("221e8e00"), jsl("font_reload"))}  # font reload: upload them again
    for site, (old, new) in patches.items():
        o = off(site)
        assert rom[o:o + len(old)] == old and len(new) == len(old), hex(site)
        rom[o:o + len(new)] = new
    import lint
    pos = dict_end

    def put(s, cells, what):
        """English string s into DICT_OVERFLOW (where DICT_READ finds it); returns its pointer."""
        nonlocal pos
        assert lint.tiny_cells(s, font.load_tiny()) <= cells, (what, s)
        b = text.encode(s, text.EN.enc)
        ws = [int.from_bytes(b[k:k + 2], "big") for k in range(0, len(b), 2)]
        ws[-1] |= 0x8000
        data = b"".join(w.to_bytes(2, "little") for w in ws)
        assert pos + len(data) <= 0x8000, "tiny strings overflow bank DICT_OVERFLOW"
        o = off(DICT_OVERFLOW << 16 | 0x8000 | pos)
        rom[o:o + len(data)] = data
        pos += len(data)
        return pos - len(data)

    rows_at, table_at = TINY_ROWS_AT, TINY_TABLE_AT
    for e in json.loads((ROOT / "script" / "labels.json").read_text(encoding="utf-8")):
        if e.get("kind") == "tiny" and e["en"]:
            p = put(e["en"][0], e["cells"], e["id"])
            old, ypos, entry = TINY_HOOKS[e["id"]]
            so = off(int(e["id"], 16))
            assert rom[so:so + len(old)] == old, e["id"]
            new = bytes([0xA0, ypos & 0xFF, ypos >> 8, 0xA2, p & 0xFF, p >> 8]) + jsl(entry)
            rom[so:so + len(old)] = new + b"\xea" * (len(old) - len(new))
        elif e.get("kind") == "tinyrows" and e["en"]:
            old, rows, ret = TINY_ROWS[e["id"]]
            so = off(int(e["id"], 16))
            assert rom[so:so + len(old)] == old, e["id"]
            code = bytearray(b"\x5a")  # PHY (Y = first row when rows is a step)
            for i, s in enumerate(e["en"]):
                p = put(s, e["cells"], e["id"])
                if isinstance(rows, list):
                    code += bytes([0xA0, rows[i] & 0xFF, rows[i] >> 8])  # LDY #row
                else:
                    code += b"\x7a\x5a"  # PLY ; PHY
                    if i:
                        code += bytes([0x98, 0x18, 0x69, i * rows & 0xFF, i * rows >> 8, 0xA8])  # TYA CLC ADC TAY
                code += bytes([0xA2, p & 0xFF, p >> 8]) + jsl("tiny71d")  # LDX #string ; JSL
            code += b"\x7a\x6b"  # PLY ; RTL
            assert rom[off(rows_at):off(rows_at) + len(code)] == b"\xff" * len(code)
            rom[off(rows_at):off(rows_at) + len(code)] = code
            call = bytes([0x22, rows_at & 0xFF, rows_at >> 8 & 0xFF, rows_at >> 16]) + (b"\x6b" if ret else b"")
            rom[so:so + len(old)] = call + b"\xea" * (len(old) - len(call))
            rows_at += len(code)
        elif e.get("kind") == "tinytable" and e["en"]:
            loop, cont, entry = TINY_TABLES[e["id"]]
            so = off(int(e["id"], 16))
            assert rom[so] == 0xBF, e["id"]  # LDA long,x
            keys = {int(k, 16): s for k, s in zip(e["keys"], e["en"])}
            lo, hi = min(keys), max(keys)
            for x, s in keys.items():
                t = off(table_at + x - lo)
                assert rom[t:t + 2] == b"\xff\xff", hex(x)
                rom[t:t + 2] = put(s, e["cells"], e["id"]).to_bytes(2, "little")
            base = table_at - lo  # LDA base,x reads table_at + (X - lo)
            rom[so + 1:so + 4] = base.to_bytes(3, "little")
            table_at += hi - lo + 2
            lo_ = off(loop)
            new = jsl(entry) + bytes([0x80, cont - (loop + 6)])
            rom[lo_:off(cont)] = new + b"\xea" * (cont - loop - len(new))


HOOK_AT = 0x3CA000  # hook code + 16-bit label strings for routines that read 8-bit kana strings
# name -> (site, original bytes there (asserted), how the site calls the printer)
HOOKS = {  # name -> (site, original bytes, mode, bytes run before the JSL, RTS after the JSL?)
    # walking style (04:AE40): X = style*2 indexes the byte-string table 04:ADFB; prints, then returns
    "WALK": (0x04AE47, bytes.fromhex("bffbad04aae220bf000004c2203009"), "table", b"", True),
    # 「は装備していません」 after an equipment category (04:B619: 9 bytes from 04:B62D, then RTS at B62C)
    "EQUIPNONE": (0x04B619, bytes.fromhex("a20000bf2db60429ff00201db7e8e00900d0f0"), "single", b"", False),
    # equip title 「装 備」: LDA #$F3 ; LDY #$1098 ; JSR $B71D ; INY INY ; LDA #$F4 ; JMP $B71D (tail)
    "EQUIPTITLE": (0x04B465, bytes.fromhex("a9f300a09810201db7c8c8a9f4004c1db7"), "single", b"\xa0\x98\x10", True),
    # shop title 「武 器 屋」 (04:E12B: X = shop type*4, Y set): 5 cells, then return
    "SHOPTITLE": (0x04E133, bytes.fromhex("bf6ce104201db7a9ff02"), "table4", b"", True),
}


def install_hooks(rom, strings):
    """strings: {hook name: [list of glyph words per label]}. Writes the strings, a printer per hook, the patch."""
    pos = HOOK_AT
    for name, labels in strings.items():
        site, orig, how, pre, rts = HOOKS[name]
        o = off(site)
        assert rom[o:o + len(orig)] == orig, name
        addrs = []
        for ws in labels:
            ws = list(ws)
            ws[-1] |= 0x8000
            data = b"".join(w.to_bytes(2, "little") for w in ws)
            rom[off(pos):off(pos) + len(data)] = data
            addrs.append(pos & 0xFFFF)
            pos += len(data)
        bank = HOOK_AT >> 16
        loop = bytes([0xBF, 0x00, 0x00, bank, 0x30, 0x08,         # loop: LDA bank:0000,x ; BMI last
                      0x22, 0x7B, 0xB7, 0x04, 0xE8, 0xE8, 0x80, 0xF2,  # JSL $04B77B ; INX INX ; BRA loop
                      0x29, 0xFF, 0x7F, 0x22, 0x7B, 0xB7, 0x04, 0x6B])  # last: AND #$7FFF ; JSL ; RTL
        if how in ("table", "table4"):
            tbl = pos
            for a in addrs:
                rom[off(pos):off(pos) + 2] = a.to_bytes(2, "little")
                pos += 2 if how == "table" else 4  # table4: X is index*4 at the site
            code = bytes([0xBF, tbl & 0xFF, tbl >> 8 & 0xFF, bank, 0xAA]) + loop  # LDA tbl,x ; TAX ; loop
        else:
            code = bytes([0xA2, addrs[0] & 0xFF, addrs[0] >> 8]) + loop          # LDX #string ; loop
        entry = pos
        rom[off(pos):off(pos) + len(code)] = code
        pos += len(code)
        call = bytes([0x22, entry & 0xFF, entry >> 8 & 0xFF, entry >> 16])
        patch = pre + call + (b"\x60" if rts else b"")
        assert len(patch) <= len(orig), name
        rom[o:o + len(orig)] = patch + b"\xea" * (len(orig) - len(patch))


def label_cells(s, n):
    """n cells for label text s: raw [XXXX] codes, the normal font if it fits, else baked tiny-font cells."""
    if s.startswith("["):
        b = text.encode(s, text.EN.enc)
        cells = [int.from_bytes(b[k:k + 2], "big") for k in range(0, len(b), 2)]
        assert len(cells) == n, s
        return cells
    if "/" not in s and len(s) <= n:
        pad = n - len(s)
        s2 = " " * (pad // 2) + s + " " * (pad - pad // 2)
        return [int.from_bytes(text.EN.enc[ch], "big") for ch in s2]
    return font.render_label(s, n, 2 if "/" in s else 1)


def write_labels(rom, plan, code_of):
    """code_of: repr(baked cell) -> glyph code."""
    hooks = {}
    for (where, term), cells in plan:
        ws = [code_of[repr(c)] if isinstance(c, list) else c for c in cells]
        if where == "hook":
            hooks.setdefault(term, []).append(ws)
            continue
        if where == "imm":  # one `LDA #code` per cell
            for site, w in zip(term, ws):
                o = off(site)
                assert rom[o] == 0xA9, hex(site)
                rom[o + 1:o + 3] = w.to_bytes(2, "little")
            continue
        if term:
            ws[-1] |= 0x8000
        o = off(where)
        rom[o:o + 2 * len(ws)] = b"".join(w.to_bytes(2, "little") for w in ws)
    if hooks:
        install_hooks(rom, hooks)


# Menu overlay tiles (8x8 small kanji written straight into the menu tilemap, e.g. 04:BA01): decompressed by
# 00:B9B3 from bank $1F into BG tiles 0x380-0x3BF (0x400-byte blocks) and 0x3C0-0x3DF (0x200-byte blocks),
# one variant per window style ($0804 & 3; tables 00:BA85 = AB82 AF2C AF2C, 00:BA8B = B31B B50E B705). The variants
# hold different glyphs at some indexes, so a tile is changed only where it equals the default-style block's tile.
MENU_TILE_BLOCKS = [(0x1FAB82, 0x380, 0x400), (0x1FAF2C, 0x380, 0x400),
                    (0x1FB31B, 0x3C0, 0x200), (0x1FB50E, 0x3C0, 0x200), (0x1FB705, 0x3C0, 0x200)]
MENU_TILE_REF = {0x380: 0x1FAF2C, 0x3C0: 0x1FB50E}  # default style (field menus, shop)
MENU_TILES = {  # tile -> two tiny-font characters (tools/font.py load_tiny), or 8 rows of 8 pixels ('#' = ink)
    0x3BE: " H", 0x3AE: " V", 0x3C1: "P ",                     # 体力 -> HP, 声力 -> VP (力 is shared)
    0x3C0: "Ne", 0x3AC: "xt", 0x3D0: " r", 0x3D1: "an", 0x3BC: "k ", 0x3BD: "in",  # 次の役者まで -> Next rank in
    0x3AD: "  ",                                               # 個 after a count: nothing
    0x3AB: "Fr", 0x3BB: "ee",                                  # 空き (free inventory slots) -> Free
    0x3D3: "  ",                                               # status: 1回×13 (hits × power) -> 1 ×13    # equip window stat column 攻 守 早: Attack / Defense / Speed as the weapon, armor and footwear icons
    0x3C6: ["......##", ".....##.", "....##..", ".#.##...", "..##....", ".#.#....", "#.......", "........"],
    0x3D6: [".##..##.", ".######.", "########", ".######.", "..####..", "..####..", "..#..#..", "........"],
    0x3D5: ["...##...", "...##...", "...###..", "..#####.", ".######.", "########", "........", "........"],
}


def tiny_tile(two):
    """8x8 2bpp tile (bg 3, ink 1): two tiny-font characters on rows 1-6, or 8 rows of pixel art."""
    if isinstance(two, list):
        return font.encode_tile([[1 if p == "#" else 3 for p in r] for r in two])
    glyphs = font.load_tiny()
    rows = [[3] * 8 for _ in range(8)]
    for i, ch in enumerate(two):
        for y, r in enumerate(glyphs[ch]):
            for x, p in enumerate(r):
                if p:
                    rows[1 + y][4 * i + x] = 1
    return font.encode_tile(rows)


def patch_menutiles(rom):
    import lz
    ref = {first: lz.decompress(rom, off(src), size)[0] for first, src in MENU_TILE_REF.items()
           for s, f, size in MENU_TILE_BLOCKS if s == src}
    for src, first, size in MENU_TILE_BLOCKS:
        o = off(src)
        raw, used = lz.decompress(rom, o, size)
        raw = bytearray(raw)
        for t, art in MENU_TILES.items():
            k = (t - first) * 16
            if first <= t < first + size // 16 and raw[k:k + 16] == ref[first][k:k + 16]:
                raw[k:k + 16] = tiny_tile(art)
        new = lz.compress(bytes(raw))
        assert len(new) <= used, f"menu tiles at {src:06X}: {len(new):#x} > {used:#x}"
        rom[o:o + len(new)] = new


NAME_MAX_SITES = (0x04BBDF, 0x04BC02)  # `LDA #$0006`: glyph limit when drawing a party name (04:BBC9)
# `LDA #$02FF ; JSR $B71D` after every cell of the selected item/song tab ("戦 闘 用"): spaced-out kana/kanji
# would tear baked English labels apart ("Re me dy"), so the selected tab is drawn solid like the others
TAB_SPACERS = (0x04B7F0, 0x04B88C)
BATTLE_TAB_SPACERS = (0x02FDDB, 0x0FFB1F)  # same in battle: `LDA #$02FF ; JSL $02F084` (item / song tabs)


def patch_tab_spacers(rom):
    for site in TAB_SPACERS:
        o = off(site)
        assert rom[o:o + 6] == b"\xa9\xff\x02\x20\x1d\xb7", hex(site)
        rom[o:o + 6] = b"\xea" * 6
    for site in BATTLE_TAB_SPACERS:
        o = off(site)
        assert rom[o:o + 7] == b"\xa9\xff\x02\x22\x84\xf0\x02", hex(site)
        rom[o:o + 7] = b"\xea" * 7


def patch_name_limits(rom):
    """English party names run to 11 letters (Fuji Musume); the status rows have room for 12."""
    for site in NAME_MAX_SITES:
        o = off(site)
        assert rom[o:o + 3] == b"\xa9\x06\x00", hex(site)
        rom[o + 1] = 0x0C


FIXED_AT = 0x3C9000  # fixed-count strings (no terminator), see FIXED
# Strings printed with a hard-coded pointer, bank and glyph count (02:AFEE). Each: (LDA #ptr site, LDA #bank site,
# LDX #count site, English). The sites are opcode addresses; operands follow.
FIXED = [
    (0x0282E0, 0x0282E7, 0x0282F8, "Enemies appeared!"),  # てきがあらわれた！ (02:E12C, 12 cells)
]


def patch_fixed(rom):
    pos = FIXED_AT
    for ptr_site, bank_site, count_site, s in FIXED:
        b = text.encode(s, text.EN.enc)
        ws = [b[k:k + 2][::-1] for k in range(0, len(b), 2)]  # glyph words, little-endian
        o = off(pos)
        rom[o:o + 2 * len(ws)] = b"".join(ws)
        for site, op, val in ((ptr_site, 0xA9, pos & 0xFFFF), (bank_site, 0xA9, pos >> 16),
                              (count_site, 0xA2, len(ws))):
            so = off(site)
            assert rom[so] == op, hex(site)
            rom[so + 1:so + 3] = val.to_bytes(2, "little")
        pos += 2 * len(ws)


SCRIPT_TABLE = 0x03978E  # 3 bytes per script id; id 0 runs right after "new game"
DEBUG_AT = 0x3F8000  # last expansion bank: debug scripts only (QA builds, never in a release)


def debug_bytes(s):
    """Hex event-script bytes; '@' stands for the 3-byte address of the byte after it (a jump target that just
    continues, e.g. `A0 01 @` = give item 01 whether or not the inventory is full)."""
    out = bytearray()
    for tok in s.split():
        if tok == "@":
            out += (DEBUG_AT + len(out) + 3).to_bytes(3, "little")
        else:
            out += bytes.fromhex(tok)
    return bytes(out)


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
