"""Translation batches.

    python -X utf8 tools/batches.py split [--chars 3500]   # work/tl/bNNN.tsv for every untranslated run
    python -X utf8 tools/batches.py check bNNN [--out F]    # validate work/tl/bNNN.out.tsv (exit 1 on errors)
    python -X utf8 tools/batches.py merge bNNN [--out F]    # check, then write the English into script/*.json

Input TSV: id<TAB>jp (readable: dictionary words expanded, {n} shown as " / "). Output TSV: id<TAB>en.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import lint  # noqa: E402
import text  # noqa: E402

TL = ROOT / "work" / "tl"


def readable(jp):
    s = re.sub(r"\{([^{}#:]*)#[0-9A-F]{4}\}", r"\1", jp)
    return s.replace("{n}", " / ")


def split(chars):
    TL.mkdir(parents=True, exist_ok=True)
    todo = [e for e in text.load() if not e["en"] and e["size"]]
    batches, cur, n = [], [], 0
    for e in todo:
        r = readable(e["jp"])
        if cur and n + len(r) > chars:
            batches.append(cur); cur, n = [], 0
        cur.append((e["id"], r)); n += len(r)
    if cur:
        batches.append(cur)
    for i, b in enumerate(batches, 1):
        p = TL / f"b{i:03d}.tsv"
        p.write_text("".join(f"{k}\t{v}\n" for k, v in b), encoding="utf-8", newline="\n")
    print(f"{len(batches)} batches, {len(todo)} runs -> {TL}")


def read_out(path):
    out = {}
    for n, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        k, sep, v = line.partition("\t")
        if not sep:
            raise ValueError(f"{path}:{n}: no tab")
        if k in out:
            raise ValueError(f"{path}:{n}: duplicate id {k}")
        out[k] = v
    return out


def check(batch, out=None):
    ids = [l.split("\t", 1)[0] for l in (TL / f"{batch}.tsv").read_text(encoding="utf-8").splitlines() if l]
    res = read_out(out or TL / f"{batch}.out.tsv")
    errs = []
    if set(res) != set(ids):
        errs.append(f"ids: missing {sorted(set(ids) - set(res))} extra {sorted(set(res) - set(ids))}")
    byid = {e["id"]: e for e in text.load()}
    for k, en in res.items():
        if k not in byid:
            continue
        if not en.isascii() or "\\u" in en or "\t" in en:
            errs.append(f"{k}: non-ASCII, tab or \\u escape")
        if "{n}" in en:
            errs.append(f"{k}: don't write {{n}}; the build wraps lines")
        for x in lint.check(dict(byid[k], en=en)):
            errs.append(f"{k}: {x}")
    for x in errs:
        print(x)
    print("OK" if not errs else f"{len(errs)} errors")
    return res if not errs else None


def merge(batch, out=None):
    res = check(batch, out)
    if res is None:
        sys.exit(1)
    for p in sorted(text.SCRIPT.glob("bank_*.json")):
        entries = json.loads(p.read_text(encoding="utf-8"))
        hit = False
        for e in entries:
            if e["id"] in res:
                e["en"] = res[e["id"]]; hit = True
        if hit:
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                json.dump(entries, f, ensure_ascii=False, indent=1)
                f.write("\n")
    print(f"merged {len(res)} runs")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["split", "check", "merge"])
    ap.add_argument("batch", nargs="?")
    ap.add_argument("--chars", type=int, default=3500)
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "split":
        split(a.chars)
    elif a.cmd == "check":
        sys.exit(0 if check(a.batch, a.out) is not None else 1)
    else:
        merge(a.batch, a.out)
