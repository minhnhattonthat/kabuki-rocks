import hashlib
from pathlib import Path

import pytest

ROM = Path(__file__).resolve().parent.parent / "rom" / "Kabuki Rocks (Japan).sfc"
SHA1 = "391d2144290f287fb5fbc872c14a6102d98fc7f5"


@pytest.mark.skipif(not ROM.exists(), reason="no ROM in rom/")
def test_base_rom_hash():
    assert hashlib.sha1(ROM.read_bytes()).hexdigest() == SHA1
