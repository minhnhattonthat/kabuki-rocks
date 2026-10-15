"""Kabuki Rocks dialogue font: 8x16 glyphs = top + bottom 8x8 BG3 tiles (2bpp), mapped by 00:BAEF.

    python -X utf8 tools/font.py sheet OUT.png [--from 0 --to 2FF] [--zoom 3]   # labelled glyph sheet
    python -X utf8 tools/font.py en-sheet OUT.png                              # English font review sheet
    python -X utf8 tools/font.py tiny-sheet OUT.png                            # tiny label font + sample labels
"""
import argparse
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / "rom" / "Kabuki Rocks (Japan).sfc"
FONT_BLOCKS = (0xF8000, 0xF987D)  # 1F:8000 -> BG3 tiles 0-511, 1F:987D -> 512-1023
SPACE = 0x02FF
TABLE = 0x3C48  # 00:BC48 byte-pair table: (top, bottom) tile byte per glyph code
FONT_EN = ROOT / "assets" / "font_en.txt"
FONT_TINY = ROOT / "assets" / "font_tiny.txt"  # 3x5 label font, two letters per 8-px cell
PIX = {".": 3, "#": 1, "+": 2}  # font_en.txt pixel chars -> palette index
# BG3 tiles the game overwrites at run time: 0x2E0-0x2FF (VRAM dump work/qa/ppu1), 0x380-0x3FF (menu overlay
# tiles, 00:B9B3)
VOLATILE = set(range(0x2E0, 0x300)) | set(range(0x380, 0x400))
# Page-2 kanji whose tiles the English glyphs may take. Codes 139-13F share table entries with 140-146,
# so each of those 14 bytes must be free in page 1 and page 2; these are the least-used kanji (script
# uses 3-20 each) sitting at bytes the English page 1 leaves free. 勇 16E, 王 195, 氏 196, 法 197,
# 色 190, 島 193, ヶ 19E, 原 19F, 坊 1A4, 葉 1A8, 雪 1A1, 口 1A3.
SACRIFICE = (0x16E, 0x195, 0x196, 0x197, 0x190, 0x193, 0x19E, 0x19F, 0x1A4, 0x1A8, 0x1A1, 0x1A3)


def rom_bytes():
    return ROM.read_bytes()


def tiles(rom):
    return lz.decompress(rom, FONT_BLOCKS[0], 0x2000)[0] + lz.decompress(rom, FONT_BLOCKS[1], 0x2000)[0]


def _add(rom, page):
    return int.from_bytes(rom[0x3B62 + 2 * page:0x3B64 + 2 * page], "little")


def entry(rom, code):
    """(page, offset into the byte-pair table at TABLE) for a glyph code < 0x300."""
    page = 3 if code >= 0x1C0 else 2 if code >= 0x140 else 1 if code >= 0xB0 else 0
    sub = int.from_bytes(rom[0x3B5A + 2 * page:0x3B5C + 2 * page], "little")
    return page, ((code - sub) * 2 + _add(rom, page)) & 0xFFFF


def is_real(rom, code):
    """False for codes past the end of their page's table (their entry belongs to the next page's codes)."""
    page, x = entry(rom, code)
    return page == 3 or x < _add(rom, page + 1)


def glyph_tiles(rom, code):
    """(top, bottom) BG3 tile numbers for a glyph code < 0x300, as 00:BAEF computes them."""
    if code == SPACE:
        return 0x3FF, 0x3FF
    page, x = entry(rom, code)
    t, b = rom[TABLE + x], rom[TABLE + x + 1]
    return (0x3FF if t == 0xFF else page << 8 | t), (0x3FF if b == 0xFF else page << 8 | b)


def load_en(path=FONT_EN):
    """{code: (char, 16 rows of 8 pixel indices)} from assets/font_en.txt."""
    glyphs, cur = {}, None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("== "):
            ch, code = line[3:].rsplit(" ", 1)
            cur = glyphs[int(code, 16)] = (ch, [])
        elif cur is not None and line:  # lines before the first header are comments
            row = [PIX[c] for c in line]
            assert len(row) == 8 and row[7] == 3, f"{cur[0]!r}: bad row {line!r}"
            cur[1].append(row)
    for code, (ch, rows) in glyphs.items():
        assert len(rows) == 16, f"{ch!r}: {len(rows)} rows"
        assert 0x100 < code < 0x170, f"{ch!r}: code {code:X}"
    return glyphs


def encode_tile(rows):
    """8 rows of pixel indices -> 16 bytes of SNES 2bpp."""
    out = bytearray()
    for r in rows:
        out.append(sum((p & 1) << (7 - x) for x, p in enumerate(r)))
        out.append(sum((p >> 1) << (7 - x) for x, p in enumerate(r)))
    return bytes(out)


EXT_BASE = {1: 0x400, 2: 0x600, 3: 0x800}  # first new glyph code per tile page (build.py install_glyph_ext)
TINY_POOL = (0, 0)  # set by patch_font: (first BG3 tile, count) of page 0 left for the runtime tiny text


def kanji_by_use(rom):
    """Page-1/2 kanji codes not taken by the English font and not still drawn, most used in the script first."""
    import text  # local: font is imported by text-free tools too
    use = {}
    for it in text.runs(rom).values():
        r, i = it.args, 0
        while i < len(r):
            if r[i] < 0x80:
                w = r[i] << 8 | r[i + 1]
                use[w] = use.get(w, 0) + 1
                i += 2
            else:
                i += 1 + (text.CTRL[r[i]][1] if r[i] in text.CTRL else 0)
    en = load_en()
    busy = still_drawn(rom)
    # page 3 (0x1C0-0x1EF) only when both tiles sit below 0x380 (menus load overlay tiles at 0x380+)
    users = {}
    for c in range(0x300):
        if c != SPACE and is_real(rom, c):
            for t in set(glyph_tiles(rom, c)):
                users[t] = users.get(t, 0) + 1
    page3 = [c for c in range(0x1C0, 0x1F0)
             if all(t < 0x380 and users.get(t, 0) == 1 for t in glyph_tiles(rom, c))]
    cands = [c for c in list(range(0xE6, 0x139)) + list(range(0x165, 0x1B9)) + page3
             if c not in en and c not in SACRIFICE and c not in busy and is_real(rom, c)]
    # most used in the (now English) dialogue first: rarely-used kanji tend to be menu kanji (持 金 代 単 価)
    # still drawn from arrays not catalogued yet
    return sorted(cands, key=lambda c: (-use.get(c, 0), c))


GLYPH_CALLS = (b"\x20\x1d\xb7", b"\x20\x25\xb7", b"\x22\x7b\xb7\x04", b"\x22\x7f\xb7\x04", b"\x22\x64\xb7\x04",
               b"\x22\x8f\xf0\x02", b"\x22\x84\xf0\x02", b"\x22\x9d\xba\x00")


def still_drawn(rom):
    """Glyph codes the English build may still draw: loaded as an immediate shortly before a glyph routine call
    (e.g. the money unit 両), or part of Japanese that is not translated yet (labels, code strings, dictionary)."""
    import json
    import re
    busy = set()
    root = ROOT / "script"
    replaced = set()  # LDA sites rewritten by translated "imm" labels
    if (root / "labels.json").exists():
        import immlabels
        groups = {immlabels.cpu(g[0][0]): g for g in immlabels.phrases(bytes(rom))}
        for e in json.loads((root / "labels.json").read_text(encoding="utf-8")):
            if e.get("kind") == "imm" and e["en"] and int(e["id"], 16) in groups:
                replaced.update(o for o, _ in groups[int(e["id"], 16)])
    for m in re.finditer(rb"\xa9(.)([\x00-\x02])", bytes(rom[:0x178000]), re.S):
        tail = rom[m.end():m.end() + 8]
        if m.start() not in replaced and any(c in tail for c in GLYPH_CALLS):
            busy.add(m[1][0] | m[2][0] << 8)

    def add_text(s):
        for ch in s:
            code = JP_CODE.get(ch)
            if code is not None:
                busy.add(code)
    if (root / "labels.json").exists():
        import labels as lab
        for e in json.loads((root / "labels.json").read_text(encoding="utf-8")):
            if not e["en"]:
                busy.update(lab.words(rom, int(e["id"], 16), e["cells"] * e["count"]))
    for name in ("code.json", "dict.json"):
        if (root / name).exists():
            for e in json.loads((root / name).read_text(encoding="utf-8")):
                if not e["en"]:
                    add_text(e["jp"])
    return busy


def _jp_codes():
    out = {}
    for line in (ROOT / "tbl" / "jp.tbl").read_text(encoding="utf-8").splitlines():
        k, sep, v = line.partition("=")
        if sep and len(k) == 4 and len(v) == 1:
            out.setdefault(v, int(k, 16))
    return out


JP_CODE = _jp_codes()


def patch_font(rom: bytearray, extra=(), extra_out=None) -> dict[str, bytes]:
    """Write the English glyphs of assets/font_en.txt into the ROM font; return {char: 2-byte BE code}.

    Each half reuses an identical tile already placed in its page, else the tile its table entry
    already points to, else a free tile of that page (one no kept code uses). Codes 139-13F share
    their table entry with 140-146 (page 1's table ends at 138), so those pairs need a byte that is
    free in both pages.
    extra: more 8x16 cells (16 rows of 8 palette indices, e.g. render_label output). They get NEW glyph codes
    (EXT_BASE per page) on the tiles of kanji no text draws any more (kanji_by_use); for each cell
    (code, page, top byte, bottom byte) is appended to extra_out. build.py installs the mapping (EXT_* below)."""
    glyphs = load_en()
    freed = set(kanji_by_use(rom)) if extra else set()
    chr_ = bytearray(tiles(rom))
    sizes = (FONT_BLOCKS[1] - FONT_BLOCKS[0], lz.decompress(rom, FONT_BLOCKS[1], 0x2000)[1])
    keep = {t for c in range(0x300) if c not in glyphs and c not in SACRIFICE and c not in freed
            and is_real(rom, c) for t in glyph_tiles(rom, c)}
    placed = {1: {}, 2: {}, 3: {}}  # page -> {byte: tile data}
    groups = {}  # table offset -> [(page, (top data, bottom data))]
    for code, (_, rows) in sorted(glyphs.items()):
        page, x = entry(rom, code)
        groups.setdefault(x, []).append((page, (encode_tile(rows[:8]), encode_tile(rows[8:]))))

    def put(x, half, members, cands):
        for b in cands:
            if b != 0xFF and all(placed[p][b] == d[half] if b in placed[p] else
                                 (p << 8 | b) not in keep and (p << 8 | b) not in VOLATILE for p, d in members):
                rom[TABLE + x + half] = b
                for p, d in members:
                    placed[p][b] = d[half]
                    chr_[(p << 8 | b) * 16:(p << 8 | b) * 16 + 16] = d[half]
                return True
        return False

    # pass 1: an identical tile already placed, else the entry's own tile; pass 2: any free tile,
    # shared-entry pairs first because they need a byte free in both pages
    halves = [(x, h, m) for x, m in sorted(groups.items()) for h in (0, 1)]
    later = [t for t in halves if not put(*t, [*placed[t[2][0][0]], rom[TABLE + t[0] + t[1]]])]
    for x, h, m in sorted(later, key=lambda t: -len(t[2])):
        if not put(x, h, m, range(0xFF)):
            raise ValueError(f"no free tile for table entry {x:#x} half {h}; add kanji to SACRIFICE")

    # label cells: new codes, tiles from what is free in pages 1-3 (deduplicated per page)
    counters = dict(EXT_BASE)

    def tile_for(p, d, pending):
        for b, v in list(placed[p].items()) + list(pending.items()):
            if v == d:
                return b
        return next((b for b in range(0xFF) if b not in placed[p] and b not in pending
                     and (p << 8 | b) not in keep and (p << 8 | b) not in VOLATILE), None)

    for cell in extra:
        top, bot = encode_tile(cell[:8]), encode_tile(cell[8:])
        for p in (1, 2, 3):
            if counters[p] >= EXT_BASE[p] + 0x100:
                continue
            pending = {}
            bt = tile_for(p, top, pending)
            if bt is None:
                continue
            pending[bt] = top
            bb = tile_for(p, bot, pending)
            if bb is None:
                continue
            pending[bb] = bot
            for b, d in pending.items():
                placed[p][b] = d
                chr_[(p << 8 | b) * 16:(p << 8 | b) * 16 + 16] = d
            if extra_out is not None:
                extra_out.append((counters[p], p, bt, bb))
            counters[p] += 1
            break
        else:
            raise ValueError("font full: no free tiles for a label cell")

    # page 0 (kana): the tiles of codes something may still draw, packed from tile 1 up (tile 0 is BG3's
    # transparent fill); the other kana codes go blank and tiles from there to 0xFF are the tiny-text pool
    import sysmsg
    live = still_drawn(rom) | sysmsg.codes(rom)
    real0 = {c: entry(rom, c)[1] for c in range(0xB0) if is_real(rom, c)}
    move = {}
    for c, x in real0.items():
        if c in live:
            for b in rom[TABLE + x:TABLE + x + 2]:
                if b not in (0, 0xFF):
                    move.setdefault(b, len(move) + 1)
    old = bytes(chr_[:0x1000])
    for x in real0.values():
        for h in (0, 1):
            b = rom[TABLE + x + h]
            if b:
                rom[TABLE + x + h] = move.get(b, 0xFF)
    for b, n in move.items():
        chr_[n * 16:n * 16 + 16] = old[b * 16:b * 16 + 16]
    first = len(move) + 1
    chr_[first * 16:0x1000] = b"\xff" * (0x1000 - first * 16)  # background colour 3
    global TINY_POOL
    TINY_POOL = (first, 0x100 - first)

    for i, off in enumerate(FONT_BLOCKS):
        new = lz.compress(bytes(chr_[i * 0x2000:(i + 1) * 0x2000]))
        assert len(new) <= sizes[i], f"font block {i}: {len(new):#x} > {sizes[i]:#x}"
        rom[off:off + len(new)] = new
    return {ch: code.to_bytes(2, "big") for code, (ch, _) in glyphs.items()
            if not ch.startswith("<label")} | {" ": SPACE.to_bytes(2, "big")}


def tile_pixels(chr_, n):
    d = chr_[n * 16:n * 16 + 16]
    return [[((d[2 * y] >> (7 - x)) & 1) | (((d[2 * y + 1] >> (7 - x)) & 1) << 1) for x in range(8)] for y in range(8)]


def sheet(out, lo, hi, zoom, vram=None):
    from PIL import Image, ImageDraw
    rom = rom_bytes()
    chr_ = Path(vram).read_bytes()[0xC000:0x10000] if vram else tiles(rom)
    cols = 16
    cw, chh = 8 * zoom + 34, 16 * zoom + 4
    rows = (hi - lo) // cols + 1
    img = Image.new("RGB", (cols * cw + 4, rows * chh + 4), "white")
    dr = ImageDraw.Draw(img)
    shade = [(255, 255, 255), (0, 0, 0), (110, 110, 110), (190, 190, 190)]
    for i, code in enumerate(range(lo, hi + 1)):
        cx, cy = 2 + (i % cols) * cw, 2 + (i // cols) * chh
        dr.text((cx, cy + 4 * zoom), f"{code:03X}", fill=(200, 0, 0))
        for half, t in enumerate(glyph_tiles(rom, code)):
            px = tile_pixels(chr_, t)
            for y in range(8):
                for x in range(8):
                    if px[y][x]:
                        x0, y0 = cx + 26 + x * zoom, cy + (half * 8 + y) * zoom
                        dr.rectangle([x0, y0, x0 + zoom - 1, y0 + zoom - 1], fill=shade[px[y][x]])
    img.save(out)
    print(out)


GAME_RGB = [(0, 0, 0), (198, 165, 231), (0, 0, 66), (0, 0, 33)]  # BG3 palette 3 (screenshot)
SAMPLE = "The quick brown fox jumps over the lazy dog! 0123456789 ?.,'\"-:;()"


def render_codes(rom, chr_, lines):
    """1x image of glyph-code lines, 8x16 per cell, as the text box draws them."""
    from PIL import Image
    img = Image.new("RGB", (8 * max(map(len, lines)), 16 * len(lines)), GAME_RGB[3])
    for row, codes in enumerate(lines):
        for col, code in enumerate(codes):
            for half, t in enumerate(glyph_tiles(rom, code)):
                for y, r in enumerate(tile_pixels(chr_, t)):
                    for x, p in enumerate(r):
                        img.putpixel((col * 8 + x, row * 16 + half * 8 + y), GAME_RGB[p])
    return img


def en_sheet(out, text=SAMPLE, zoom=4):
    """Every English glyph at `zoom` from a patched ROM copy, then `text` wrapped at 28 chars at 1x and 3x."""
    from PIL import Image, ImageDraw
    rom = bytearray(rom_bytes())
    cmap = patch_font(rom)
    chr_ = tiles(rom)
    codes = sorted(load_en())
    cols, cw, ch = 16, 8 * zoom + 8, 16 * zoom + 20
    grid = Image.new("RGB", (cols * cw + 8, -(-len(codes) // cols) * ch + 8), (60, 60, 60))
    dr = ImageDraw.Draw(grid)
    for i, code in enumerate(codes):
        x, y = 8 + i % cols * cw, 8 + i // cols * ch
        cell = render_codes(rom, chr_, [[code]]).resize((8 * zoom, 16 * zoom), Image.NEAREST)
        grid.paste(cell, (x, y))
        dr.text((x, y + 16 * zoom + 2), f"{code:X}", fill=(255, 255, 160))
    lines = textwrap.wrap(text, 28)  # box width
    box = render_codes(rom, chr_, [[int.from_bytes(cmap[c], "big") for c in ln] for ln in lines])
    big = box.resize((box.width * 3, box.height * 3), Image.NEAREST)
    img = Image.new("RGB", (max(grid.width, big.width + 16), grid.height + box.height + big.height + 32), (60, 60, 60))
    img.paste(grid, (0, 0))
    img.paste(box, (8, grid.height + 8))
    img.paste(big, (8, grid.height + box.height + 24))
    img.save(out)
    print(out)


def load_tiny(path=FONT_TINY):
    """{char: 6 rows x 4 px (1 = ink)} from assets/font_tiny.txt (3-px glyphs, column 4 is the gap)."""
    glyphs, cur = {}, None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("== "):
            cur = glyphs[line[3:]] = []
        elif cur is not None and line:  # lines before the first header are comments
            assert len(line) == 4 and line[3] == "." and set(line) <= {".", "#"}, f"{line!r}"
            cur.append([int(c == "#") for c in line])
    for ch, rows in glyphs.items():
        assert len(ch) == 1 and len(rows) == 6, f"{ch!r}: {len(rows)} rows"
    return glyphs


def render_label(text: str, cells: int, lines: int = 1) -> list[list[list[int]]]:
    """`cells` 8x16 cells (palette index 3 = background, 1 = ink) of `text` in the tiny font, two
    letters per cell, each line centred. lines=2 splits `text` at its one '/'."""
    if lines not in (1, 2) or (lines == 2 and text.count("/") != 1):
        raise ValueError(f"{text!r}: lines=2 needs exactly one '/'" if lines == 2 else f"lines={lines}")
    font = load_tiny()
    px = [[3] * (cells * 8) for _ in range(16)]
    parts = text.split("/") if lines == 2 else [text]
    for top, part in zip((5,) if lines == 1 else (1, 9), parts):
        if len(part) > 2 * cells:
            raise ValueError(f"{part!r}: {len(part)} chars > {2 * cells} for {cells} cells")
        x0 = (cells * 8 - (4 * len(part) - 1)) // 2  # centre the ink, not the trailing gap
        for i, ch in enumerate(part):
            for y, row in enumerate(font[ch]):
                for x, p in enumerate(row):
                    if p:
                        px[top + y][x0 + 4 * i + x] = 1
    return [[r[c * 8:c * 8 + 8] for r in px] for c in range(cells)]


TINY_SAMPLES = [("Song/Weapon", 3, 2), ("Item", 3, 1), ("Forte", 3, 1), ("Run", 3, 1), ("Attack", 3, 1),
                ("Equip", 4, 1), ("Status", 4, 1), ("Config", 4, 1)] + \
    [(w, 4, 1) for w in ("HP", "Voice", "Attack", "Accuracy", "Defense", "Evasion", "Speed", "Singing", "Spirit")] + \
    [("Change/Order", 4, 2), ("The quick brown fox jumps over/the lazy dog. 0123456789 rn m", 16, 2)]


def label_image(cells):
    """1x RGB image of render_label() output, game palette."""
    from PIL import Image
    img = Image.new("RGB", (8 * len(cells), 16))
    for c, cell in enumerate(cells):
        for y, row in enumerate(cell):
            for x, p in enumerate(row):
                img.putpixel((c * 8 + x, y), GAME_RGB[p])
    return img


def tiny_sheet(out, zoom=4):
    """Every tiny glyph at `zoom`, then TINY_SAMPLES at 1x and 3x."""
    from PIL import Image, ImageDraw
    font = load_tiny()
    cols, cw, ch = 16, 4 * zoom + 12, 6 * zoom + 16
    grid = Image.new("RGB", (cols * cw + 8, -(-len(font) // cols) * ch + 8), (60, 60, 60))
    dr = ImageDraw.Draw(grid)
    for i, (c, rows) in enumerate(font.items()):
        x, y = 8 + i % cols * cw, 8 + i // cols * ch
        g = Image.new("RGB", (5, 7), GAME_RGB[3])  # 1-px navy margin left/top so the glyph edge shows
        for gy, r in enumerate(rows):
            for gx, p in enumerate(r):
                if p:
                    g.putpixel((gx + 1, gy + 1), GAME_RGB[1])
        grid.paste(g.resize((5 * zoom, 7 * zoom), Image.NEAREST), (x, y))
        dr.text((x, y + 7 * zoom + 1), c if c.isascii() else f"{ord(c):X}", fill=(255, 255, 160))
    labels = [label_image(render_label(*s)) for s in TINY_SAMPLES]
    h = grid.height + sum(16 * 3 + 8 for _ in labels) + 8
    img = Image.new("RGB", (max(grid.width, 16 + max(4 * im.width for im in labels) + 16), h), (60, 60, 60))
    img.paste(grid, (0, 0))
    y = grid.height
    for im in labels:
        img.paste(im, (8, y + 16))
        img.paste(im.resize((im.width * 3, im.height * 3), Image.NEAREST), (16 + im.width, y))
        y += 16 * 3 + 8
    img.save(out)
    print(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sheet", "en-sheet", "tiny-sheet"])
    ap.add_argument("out")
    ap.add_argument("--from", dest="lo", default="0")
    ap.add_argument("--to", dest="hi", default="2FF")
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--vram", help="take tiles from a VRAM dump (BG3 chr at byte $C000) instead of the ROM font")
    ap.add_argument("--text", default=SAMPLE, help="en-sheet: sample text rendered as in the text box")
    a = ap.parse_args()
    if a.cmd == "en-sheet":
        en_sheet(a.out, a.text)
    elif a.cmd == "tiny-sheet":
        tiny_sheet(a.out)
    else:
        sheet(a.out, int(a.lo, 16), int(a.hi, 16), a.zoom, a.vram)
