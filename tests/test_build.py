import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build  # noqa: E402
import text  # noqa: E402

pytestmark = pytest.mark.skipif(not text.ROM.exists(), reason="no ROM")


def test_identity_build(tmp_path, monkeypatch):
    """With every `en` empty the build is byte-identical to the original."""
    entries = [dict(e, en="") for e in text.load()]
    monkeypatch.setattr(text, "load", lambda: entries)
    rom, n = build.build(tmp_path / "id.sfc")
    assert n == 0
    assert bytes(rom) == text.ROM.read_bytes()


def test_relocated_run_jumps_back(tmp_path, monkeypatch):
    """A relocated run: start becomes `86 ptr`, the copy is the encoded text + jump to the next op."""
    entries = text.load()
    e = next(x for x in entries if x["size"] >= 8)
    entries = [dict(x, en="HELLO{wait}" if x is e else "") for x in entries]
    monkeypatch.setattr(text, "load", lambda: entries)
    rom, n = build.build(tmp_path / "one.sfc")
    a = int(e["id"], 16)
    o = build.off(a)
    assert n == 1 and len(rom) == build.ROM_SIZE and rom[o] == 0x86
    dst = rom[o + 1] | rom[o + 2] << 8 | rom[o + 3] << 16
    body = text.encode("HELLO{wait}", text.EN.enc)
    d = build.off(dst)
    assert rom[d:d + len(body) + 4] == body + build.jump(a + e["size"])
