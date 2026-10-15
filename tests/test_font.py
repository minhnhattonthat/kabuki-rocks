import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import font  # noqa: E402

pytestmark = pytest.mark.skipif(not font.ROM.exists(), reason="no ROM")


def render(rom, chr_, code):
    top, bottom = font.glyph_tiles(rom, code)
    return font.tile_pixels(chr_, top) + font.tile_pixels(chr_, bottom)


@pytest.fixture(scope="module")
def roms():
    orig = font.rom_bytes()
    rom = bytearray(orig)
    cmap = font.patch_font(rom)
    return orig, bytes(rom), cmap


def test_english_glyphs_render_from_ROM(roms):
    _, rom, cmap = roms
    chr_ = font.tiles(rom)  # decompresses the rewritten blocks
    glyphs = font.load_en()
    for code, (ch, rows) in glyphs.items():
        assert render(rom, chr_, code) == rows, f"{ch!r} {code:X}"
        assert cmap[ch] == code.to_bytes(2, "big")
    assert cmap[" "] == b"\x02\xff"


def test_kept_codes_unchanged_and_tiny_pool_free(roms):
    """Kana something may still draw and every kept code look the same; no kana touches the tiny-text pool."""
    import sysmsg
    orig, rom, _ = roms
    chr0, chr1 = font.tiles(orig), font.tiles(rom)
    glyphs = font.load_en()
    live = font.still_drawn(bytearray(orig)) | sysmsg.codes(orig)
    first, n = font.TINY_POOL
    assert first + n == 0x100 and n >= 64
    for code in filter(lambda c: font.is_real(orig, c), range(0x300)):
        if code < 0xB0:
            assert all(t < first or t == 0x3FF for t in font.glyph_tiles(rom, code)), f"{code:X}"
        if code in live if code < 0xB0 else code not in glyphs and code not in font.SACRIFICE:
            assert render(rom, chr1, code) == render(orig, chr0, code), f"{code:X}"
