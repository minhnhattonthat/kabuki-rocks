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


def test_kana_and_kept_codes_unchanged(roms):
    orig, rom, _ = roms
    chr0, chr1 = font.tiles(orig), font.tiles(rom)
    glyphs = font.load_en()
    for code in range(0x300):
        if code < 0xB0 or (code not in glyphs and code not in font.SACRIFICE and font.is_real(orig, code)):
            assert render(rom, chr1, code) == render(orig, chr0, code), f"{code:X}"
