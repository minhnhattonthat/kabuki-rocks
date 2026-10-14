"""Kabuki Rocks dialogue font: 8x16 glyphs = top + bottom 8x8 BG3 tiles (2bpp), mapped by 00:BAEF.

    python -X utf8 tools/font.py sheet OUT.png [--from 0 --to 2FF] [--zoom 3]   # labelled glyph sheet
    python -X utf8 tools/font.py en-sheet OUT.png                              # English font review sheet
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
PIX = {".": 3, "#": 1, "+": 2}  # font_en.txt pixel chars -> palette index
VOLATILE = range(0x2E0, 0x300)  # BG3 tiles the game overwrites at run time (VRAM dump work/qa/ppu1)
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


def patch_font(rom: bytearray) -> dict[str, bytes]:
    """Write the English glyphs of assets/font_en.txt into the ROM font; return {char: 2-byte BE code}.

    Each half reuses an identical tile already placed in its page, else the tile its table entry
    already points to, else a free tile of that page (one no kept code uses). Codes 139-13F share
    their table entry with 140-146 (page 1's table ends at 138), so those pairs need a byte that is
    free in both pages."""
    glyphs = load_en()
    chr_ = bytearray(tiles(rom))
    sizes = (FONT_BLOCKS[1] - FONT_BLOCKS[0], lz.decompress(rom, FONT_BLOCKS[1], 0x2000)[1])
    keep = {t for c in range(0x300) if c not in glyphs and c not in SACRIFICE and is_real(rom, c)
            for t in glyph_tiles(rom, c)}
    placed = {1: {}, 2: {}}  # page -> {byte: tile data}
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

    for i, off in enumerate(FONT_BLOCKS):
        new = lz.compress(bytes(chr_[i * 0x2000:(i + 1) * 0x2000]))
        assert len(new) <= sizes[i], f"font block {i}: {len(new):#x} > {sizes[i]:#x}"
        rom[off:off + len(new)] = new
    return {ch: code.to_bytes(2, "big") for code, (ch, _) in glyphs.items()} | {" ": SPACE.to_bytes(2, "big")}


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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sheet", "en-sheet"])
    ap.add_argument("out")
    ap.add_argument("--from", dest="lo", default="0")
    ap.add_argument("--to", dest="hi", default="2FF")
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--vram", help="take tiles from a VRAM dump (BG3 chr at byte $C000) instead of the ROM font")
    ap.add_argument("--text", default=SAMPLE, help="en-sheet: sample text rendered as in the text box")
    a = ap.parse_args()
    if a.cmd == "en-sheet":
        en_sheet(a.out, a.text)
    else:
        sheet(a.out, int(a.lo, 16), int(a.hi, 16), a.zoom, a.vram)
