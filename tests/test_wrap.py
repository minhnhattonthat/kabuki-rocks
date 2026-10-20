import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import wrap  # noqa: E402


def pages(s):
    return [p.split("{n}") for p in wrap.wrap(s).split("{wait}{clr}")]


def test_arrow_cells_free():
    for p in pages(" ".join(["abcdefghi"] * 40) + "{wait}"):
        assert len(p[-1].replace("{wait}", "")) <= wrap.WIDTH - wrap.ARROW


def test_widow_rebalanced():
    # 3 full lines + "more?" would leave a one-word last page
    s = "Actor A: The common folk have been far too merry of late. Do you not think they ought to suffer more?{wait}"
    p = pages(s)
    assert len(p) == 2
    assert len(p[-1]) > 1 or len(p[-1][0]) >= wrap.WIDTH // 2
