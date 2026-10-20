"""Local release: build, fix the SNES checksum, make and verify the BPS, zip it with the player README. Never publishes.

    python -X utf8 tools/release.py [--ver 0.1]    # -> release/KabukiRocks_EN_v<ver>.zip (.bps + README.txt)
"""
import argparse
import os
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = Path(os.environ.get("SKILL", "C:/Users/Nathan/.claude/plugins/cache/retro-translation/translate-retro-game/"
                                     "29344d005fa4/skills/translate-retro-game")) / "scripts"  # as tools/qa_screens.sh
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
crc = f"{zlib.crc32(final.read_bytes()):08x}"
readme = (ROOT / "docs" / "release-readme.txt").read_text(encoding="utf-8").format(ver=a.ver, crc=crc)
with zipfile.ZipFile(out.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED) as z:
    z.write(out, out.name)
    z.writestr("README.txt", readme.replace("\n", "\r\n"))
print(f"patched CRC32 {crc}  patch {out} ({out.stat().st_size} bytes)  zip {out.with_suffix('.zip')}")
