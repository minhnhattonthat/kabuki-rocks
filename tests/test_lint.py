import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import lint  # noqa: E402

JP = "{name94}「あいう{jump:088000}"


def errs(en, jp=JP):
    return lint.check({"id": "0", "jp": jp, "en": en})


def test_tiny_cells():
    tiny = set("abcdefgh ")
    assert lint.tiny_cells("abc", tiny) == 2
    assert lint.tiny_cells("[01F0]abcd", tiny) == 3  # icon cell + 2
    assert lint.tiny_cells("abécd", tiny) == 3  # letter missing from the tiny font: full cell, pairing restarts
    assert lint.tiny_cells("aéb", tiny) == 3


def test_clean():
    assert errs("{name94} HELLO{wait}{clr}BYE{jump:088000}") == []


def test_lost_jump_and_name():
    assert any("control codes" in x for x in errs("HELLO"))


def test_too_wide_and_too_many_lines():
    long = "A" * 29
    assert any("over 28" in x for x in errs("{name94}" + long + "{jump:088000}"))
    assert any("arrow" in x for x in errs("{name94}" + "A" * 23 + "{wait}{jump:088000}"))  # 5 (name) + 23 = 28


def test_wrapped_long_text_passes():
    words = " ".join(["WORD"] * 60)
    assert errs("{name94} " + words + "{wait}{jump:088000}") == []


def test_japanese_left():
    assert any("Japanese" in x for x in errs("{name94}あ{jump:088000}"))
