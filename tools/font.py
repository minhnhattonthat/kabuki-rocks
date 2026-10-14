"""Kabuki Rocks dialogue font: 8x16 glyphs = top + bottom 8x8 BG3 tiles (2bpp), mapped by 00:BAEF.

    python -X utf8 tools/font.py sheet OUT.png [--from 0 --to 2FF] [--zoom 3]   # labelled glyph sheet
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lz  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ROM = ROOT / "rom" / "Kabuki Rocks (Japan).sfc"
FONT_BLOCKS = (0xF8000, 0xF987D)  # 1F:8000 -> BG3 tiles 0-511, 1F:987D -> 512-1023
SPACE = 0x02FF


def rom_bytes():
    return ROM.read_bytes()


def tiles(rom):
    return lz.decompress(rom, FONT_BLOCKS[0], 0x2000)[0] + lz.decompress(rom, FONT_BLOCKS[1], 0x2000)[0]


def glyph_tiles(rom, code):
    """(top, bottom) BG3 tile numbers for a glyph code < 0x300, as 00:BAEF computes them."""
    if code == SPACE:
        return 0x3FF, 0x3FF
    page = 3 if code >= 0x1C0 else 2 if code >= 0x140 else 1 if code >= 0xB0 else 0
    sub = int.from_bytes(rom[0x3B5A + 2 * page:0x3B5C + 2 * page], "little")
    add = int.from_bytes(rom[0x3B62 + 2 * page:0x3B64 + 2 * page], "little")
    x = ((code - sub) * 2 + add) & 0xFFFF
    t, b = rom[0x3C48 + x], rom[0x3C49 + x]
    return (0x3FF if t == 0xFF else page << 8 | t), (0x3FF if b == 0xFF else page << 8 | b)


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


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["sheet"])
    ap.add_argument("out")
    ap.add_argument("--from", dest="lo", default="0")
    ap.add_argument("--to", dest="hi", default="2FF")
    ap.add_argument("--zoom", type=int, default=3)
    ap.add_argument("--vram", help="take tiles from a VRAM dump (BG3 chr at byte $C000) instead of the ROM font")
    a = ap.parse_args()
    sheet(a.out, int(a.lo, 16), int(a.hi, 16), a.zoom, a.vram)
