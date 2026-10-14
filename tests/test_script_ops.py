import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import script_ops as so  # noqa: E402

ROM = ROOT / "rom" / "Kabuki Rocks (Japan).sfc"
TRACE = Path(__file__).parent / "data" / "script_trace.txt"
JUNK_IDS = range(263, 271)  # all point at 0A:FF45, past the end of the scripts (garbage bytes)

needs_rom = pytest.mark.skipif(not ROM.exists(), reason="no ROM in rom/")


@pytest.fixture(scope="module")
def rom():
    return ROM.read_bytes()


def test_text_run_synthetic():
    # bank $80 maps file offset 0; chars, newline, delay, portrait, then op 8D ends the run
    data = bytes([0x00, 0xDF, 0x8F, 0x92, 0x05, 0xB8, 1, 2, 0x8D]) + bytes(0x8000)
    run, end = so.text_run(data, 0x808000)
    assert (run.size, end) == (8, 0x808008)


@needs_rom
def test_trace_lengths(rom):
    n = 0
    for line in TRACE.read_text().splitlines():
        if line.startswith("#"):
            continue
        a, op, b = (int(x, 16) for x in line.split())
        assert so.rd(rom, a) == op
        assert b in so.successors(rom, a), f"{a:06X} {op:02X} -> {b:06X}"
        n += 1
    assert n > 100


@needs_rom
def test_table_parses(rom):
    entries = so.table(rom)
    assert len(entries) == 676
    for i, e in enumerate(entries):
        if i in JUNK_IDS:
            with pytest.raises(ValueError):
                so.parse(rom, e)
        else:
            assert so.parse(rom, e), f"id {i}"
