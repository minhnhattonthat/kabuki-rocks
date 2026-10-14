"""Dictionary translation batches (script/dict.json).

    python -X utf8 tools/dictbatch.py split [--n 150]   # work/tl/dNNN.tsv: id<TAB>glyphs<TAB>jp
    python -X utf8 tools/dictbatch.py check dNNN        # validate work/tl/dNNN.out.tsv
    python -X utf8 tools/dictbatch.py merge dNNN        # check, then write `en` into script/dict.json

Output TSV: id<TAB>English (plain ASCII). Icon glyphs [01F0]..[01FA] (item category icons) must be kept verbatim;
other [XXXX] tokens are run-time kanji and are translated away. {...} tokens are not allowed.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DICT = ROOT / "script" / "dict.json"
TL = ROOT / "work" / "tl"
ICON = re.compile(r"\[01F[0-9A]\]")
PREFIX = "d"


def load():
    return json.loads(DICT.read_text(encoding="utf-8"))


def save(entries):
    with open(DICT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
        f.write("\n")


def split(n):
    TL.mkdir(parents=True, exist_ok=True)
    todo = [e for e in load() if not e["en"] and e["jp"].strip() not in ("", "％")]
    for i in range(0, len(todo), n):
        rows = "".join(f"{e['id']}\t{e['len']}\t{e['jp']}\n" for e in todo[i:i + n])
        (TL / f"{PREFIX}{i // n + 1:03d}.tsv").write_text(rows, encoding="utf-8", newline="\n")
    print(f"{(len(todo) + n - 1) // n} batches, {len(todo)} words")


def check(batch):
    rows = [l.split("\t") for l in (TL / f"{batch}.tsv").read_text(encoding="utf-8").splitlines() if l]
    jp = {r[0]: r[2] for r in rows}
    res = {}
    errs = []
    for n, line in enumerate((TL / f"{batch}.out.tsv").read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        k, sep, v = line.partition("\t")
        if not sep:
            errs.append(f"line {n}: no tab")
        elif k in res:
            errs.append(f"{k}: duplicate")
        res[k] = v
    if set(res) != set(jp):
        errs.append(f"ids: missing {sorted(set(jp) - set(res))} extra {sorted(set(res) - set(jp))}")
    for k, v in res.items():
        if k not in jp:
            continue
        if not v.replace("▶", "").isascii() or "{" in v or "\\" in v:
            errs.append(f"{k}: non-ASCII, '{{' or backslash")
        if Counter(ICON.findall(v)) != Counter(ICON.findall(jp[k])):
            errs.append(f"{k}: icon tokens differ (jp {ICON.findall(jp[k])} en {ICON.findall(v)})")
        if re.search(r"\[0[0-9A-F]{3}\]", ICON.sub("", v)):
            errs.append(f"{k}: stray [XXXX] token (run-time kanji must be translated)")
        if not v.strip():
            errs.append(f"{k}: empty")
    for x in errs:
        print(x)
    print("OK" if not errs else f"{len(errs)} errors")
    return None if errs else res


def merge(batch):
    res = check(batch)
    if res is None:
        sys.exit(1)
    entries = load()
    for e in entries:
        if e["id"] in res:
            e["en"] = res[e["id"]]
    save(entries)
    print(f"merged {len(res)} words")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["split", "check", "merge"])
    ap.add_argument("batch", nargs="?")
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--json", help="another word list with the same fields (e.g. script/code.json); "
                    "split then writes cNNN batches")
    a = ap.parse_args()
    if a.json:
        DICT = ROOT / a.json
        PREFIX = "c"
    if a.cmd == "split":
        split(a.n)
    elif a.cmd == "check":
        sys.exit(0 if check(a.batch) is not None else 1)
    else:
        merge(a.batch)
