import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import lz  # noqa: E402

ROM = ROOT / "rom" / "Kabuki Rocks (Japan).sfc"
FONT_BLOCKS = [0xF8000, 0xF987D]  # 1F:8000, 1F:987D -> VRAM $6000/$7000 (00:B7F6)


def test_roundtrip_synthetic():
    rnd = random.Random(1)
    raw = bytes(rnd.choice([0, 0, 0, 7, 0xFF, rnd.randrange(256)]) for _ in range(5000)) + bytes(300) + b"ab" * 40
    packed = lz.compress(raw)
    assert lz.decompress(packed, 0)[0] == raw


@pytest.mark.skipif(not ROM.exists(), reason="no ROM")
@pytest.mark.parametrize("off", FONT_BLOCKS)
def test_font_blocks_roundtrip(off):
    rom = ROM.read_bytes()
    raw, _ = lz.decompress(rom, off, 0x2000)
    assert len(raw) == 0x2000
    assert lz.decompress(lz.compress(raw), 0, 0x2000)[0] == raw
