import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import font  # noqa: E402


def test_every_printable_ascii_glyph():
    glyphs = font.load_tiny()
    for ch in map(chr, range(0x20, 0x7F)):
        rows = glyphs[ch]
        assert len(rows) == 6 and all(len(r) == 4 and r[3] == 0 for r in rows), repr(ch)
    assert not any(map(any, glyphs[" "]))
    assert "▶" in glyphs


def ink_rows_cols(cells):
    full = [sum((c[y] for c in cells), []) for y in range(16)]
    pts = [(y, x) for y, r in enumerate(full) for x, p in enumerate(r) if p == 1]
    return {y for y, _ in pts}, [x for _, x in pts]


@pytest.mark.parametrize("text,cells,lines", [("Item", 3, 1), ("Attack", 3, 1), ("Accuracy", 4, 1),
                                              ("Song/Weapon", 3, 2), ("Change/Order", 4, 2)])
def test_render_label_shape_and_bands(text, cells, lines):
    out = font.render_label(text, cells, lines)
    assert len(out) == cells and all(len(c) == 16 and all(len(r) == 8 for r in c) for c in out)
    assert {p for c in out for r in c for p in r} <= {1, 3}
    ys, xs = ink_rows_cols(out)
    assert ys <= (set(range(5, 11)) if lines == 1 else set(range(1, 7)) | set(range(9, 15)))
    assert 0 <= min(xs) and max(xs) < cells * 8


def test_render_label_centres():
    # "HP" = 7 px of ink in 32 px -> starts at x 12 (rounded left)
    _, xs = ink_rows_cols(font.render_label("HP", 4))
    assert min(xs) == 12


def test_render_label_overflow_and_split():
    font.render_label("Accuracy", 4)  # exactly 8 chars fits
    with pytest.raises(ValueError):
        font.render_label("Accuracy!", 4)
    with pytest.raises(ValueError):
        font.render_label("Change/Ordered", 3, 2)  # second line 7 chars > 6
    with pytest.raises(ValueError):
        font.render_label("NoSlash", 4, 2)
    with pytest.raises(ValueError):
        font.render_label("a/b/c", 4, 2)
