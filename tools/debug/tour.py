"""Debug tool: reach any scene in tools/debug/scenes.tsv from a cold boot and shoot it (QA builds, never released).

Each scene is a copy of build/kabuki_en.sfc whose new-game script (id 0) runs the scene's event-script bytes
(build.py --debug syntax, docs/re/debug.md). The run boots, picks NEW GAME, mashes A and writes
work/qa/tour/<scene>/ (shots, sheet_NN.png = 12 changed frames each) plus work/states/<scene>.mss at the last frame.

    python -X utf8 tools/debug/tour.py                 # every scene (3 emulators at a time)
    python -X utf8 tools/debug/tour.py card05 gameover # only these (prefix match)
    python -X utf8 tools/debug/tour.py --jp exchange   # same on build/kabuki_jp.sfc -> work/qa/tour_jp/
"""
import os
import shlex
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

SKILL = Path(os.environ.get("SKILL", "C:/Users/Nathan/.claude/plugins/cache/retro-translation/translate-retro-game/"
                                     "29344d005fa4/skills/translate-retro-game")) / "scripts"  # as tools/qa_screens.sh
sys.path.insert(0, str(SKILL))
import sheet  # noqa: E402
BOOT = "1100 -;6 start;200 -;6 start;200 -"  # title -> NEW GAME; script id 0 starts ~f1806
OUT = ROOT / "work" / "qa" / "tour"


def scenes():
    for line in (ROOT / "tools" / "debug" / "scenes.tsv").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, frames, mash, every, hexes, route, sav, *extra = line.split("\t")
            yield name, int(frames), int(mash), every, hexes, BOOT if route == "-" else route, sav, extra


def run(scene, base):
    name, frames, mash, every, hexes, route, sav, extra = scene
    rom = bytearray(base)
    build.patch_debug_start(rom, build.debug_bytes(hexes))
    path = ROOT / "build" / "debug" / OUT.name / f"{name}.sfc"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(rom)
    cmd = [sys.executable, "-X", "utf8", str(SKILL / "emu.py"), str(path), "--out", str(OUT / name),
           "--route-str", route, "--frames", str(frames), "--shot-every", every,
           "--state-out", str(ROOT / "work" / "states" / f"{name}{'_jp' if OUT.name == 'tour_jp' else ''}.mss")]
    if mash:
        cmd += ["--mash", str(mash)]
    if sav != "-":
        cmd += ["--sav", str(ROOT / sav)]
    cmd += shlex.split(extra[0]) if extra else []
    out = OUT / name
    shutil.rmtree(out, ignore_errors=True)  # stale frames of a longer earlier run would land in the sheets
    r = subprocess.run(cmd, capture_output=True, text=True)
    # pages of 12 full-size frames that changed, from NEW GAME on (the boot logos are the same in every scene)
    kept = sheet.select(sheet.collect(str(out), 1700 if route == BOOT else 0), 0.02)
    for k in range(0, len(kept), 12):
        sheet.sheet([img for _, img in kept[k:k + 12]], 4, str(out / f"sheet_{k // 12 + 1:02d}.png"))
    return name, r.returncode, [f"{len(kept)} frames"] + (r.stdout + r.stderr).strip().splitlines()[-1:]


if __name__ == "__main__":
    args = sys.argv[1:]
    base = (ROOT / "build" / "kabuki_en.sfc").read_bytes()
    if args[:1] == ["--jp"]:  # Japanese reference: build.py --reloc-jp --out build/kabuki_jp.sfc
        args, base, OUT = args[1:], (ROOT / "build" / "kabuki_jp.sfc").read_bytes(), OUT.with_name("tour_jp")
    todo = [s for s in scenes() if not args or any(s[0].startswith(p) for p in args)]
    with ThreadPoolExecutor(3) as ex:
        res = list(ex.map(lambda s: run(s, base), todo))
    for name, code, tail in res:
        print(f"{'ok ' if code == 0 else 'ERR'} {name}: {' '.join(tail)}")
    sys.exit(any(code for _, code, _ in res))
