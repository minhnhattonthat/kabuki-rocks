"""Local playtest release: build, fix the SNES checksum, make and verify the BPS. Never publishes anything.

    python -X utf8 tools/release.py [--ver 0.1]    # -> release/KabukiRocks_EN_v<ver>.bps (+ checksummed ROM in build/)
"""
import argparse
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "translate-retro-game" / "scripts"
py = [sys.executable, "-X", "utf8"]


def run(*a):
    r = subprocess.call([*py, *map(str, a)], cwd=ROOT)
    if r:
        sys.exit(r)


ap = argparse.ArgumentParser()
ap.add_argument("--ver", default="0.1")
a = ap.parse_args()
orig = ROOT / "rom" / "Kabuki Rocks (Japan).sfc"
built = ROOT / "build" / "kabuki_en.sfc"
final = ROOT / "build" / "kabuki_en_cs.sfc"
out = ROOT / "release" / f"KabukiRocks_EN_v{a.ver}.bps"
out.parent.mkdir(exist_ok=True)
run(ROOT / "tools" / "check.py")
run(ROOT / "build.py", "--out", built)
run(SKILL / "bps.py", "snes-checksum", built, "--out", final)
run(SKILL / "bps.py", "make", orig, final, out)
print(f"patched CRC32 {zlib.crc32(final.read_bytes()):08x}  patch {out} ({out.stat().st_size} bytes)")
