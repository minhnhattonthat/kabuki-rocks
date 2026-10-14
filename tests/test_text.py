import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import text  # noqa: E402

pytestmark = pytest.mark.skipif(not text.ROM.exists(), reason="no ROM")


@pytest.fixture(scope="module")
def rom():
    return text.ROM.read_bytes()


def test_roundtrip_every_run(rom):
    bad = [f"{a:06X}" for a, it in text.runs(rom).items() if text.encode(text.decode(rom, it.args)) != it.args]
    assert not bad, bad[:10]


def test_json_matches_rom(rom):
    """script/*.json jp fields still encode to the ROM bytes (catches table edits without a re-dump)."""
    entries = text.load()
    assert entries
    for e in entries:
        o = text.script_ops.off(int(e["id"], 16))
        assert text.encode(e["jp"]) == rom[o:o + e["size"]], e["id"]
