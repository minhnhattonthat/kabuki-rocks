"""Reflow English into the 28x3 dialogue box.

Translators write a run's English with the run's control tokens but without {n}: text between "box ends"
({wait} {delay:XX} {clr} {p9a} {choice:..} {jump:..}) is one utterance. wrap() breaks it into lines of
<= WIDTH cells and pages of LINES lines; extra pages are joined with {wait}{clr} (or {delay:XX}{clr} when the
box auto-advances). A {n} the translator did write forces a line break. {b8:..} {ba} {name93} {name94} stay inline.

    python -X utf8 tools/wrap.py "Makki: Oh, but first we have to ask Granny Ume for permission!{wait}"
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import text  # noqa: E402

WIDTH, LINES = 28, 3
NAME_LEN = {"name93": 4, "name94": 5}  # Rock, Makki (English names patched at 00:9FE8)
ENDS = {"wait", "delay", "clr", "p9a", "choice", "jump"}
ZERO = {"b8", "ba"}


def tok_name(tok):
    m = re.fullmatch(r"\{(\w+)(?::[0-9A-F]+)?\}", tok)
    return m[1] if m else None


def width(tok):
    m = text.TOKEN.fullmatch(tok)
    if m[2]:
        return len(m[1])  # dictionary word
    n = tok_name(tok)
    if n:
        return NAME_LEN.get(n, 0)
    return 1


def split_words(toks):
    """Tokens -> words (lists of tokens) separated by single spaces; {n} kept as its own word."""
    words, cur = [], []
    for t in toks:
        if t == " ":
            if cur:
                words.append(cur)
            cur = []
        elif t == "{n}":
            if cur:
                words.append(cur)
            words.append([t])
            cur = []
        else:
            cur.append(t)
    if cur:
        words.append(cur)
    return words


def wrap_segment(toks, width_last):
    """Words -> list of lines (each a token string). width_last: limit for the final line (arrow)."""
    lines, cur, w = [], [], 0
    for word in split_words(toks):
        if word == ["{n}"]:
            lines.append(cur); cur, w = [], 0
            continue
        ww = sum(width(t) for t in word)
        need = ww + (1 if cur else 0)
        if cur and w + need > WIDTH:
            lines.append(cur); cur, w, need = [], 0, ww
        cur = cur + ([" "] if cur else []) + word
        w += need
    if cur or not lines:
        lines.append(cur)
    # the last line shares its row with the {wait} arrow: push its last word down if needed
    last = lines[-1]
    if sum(width(t) for t in last) > width_last:
        words = split_words(last)
        lines[-1] = [t for i, wd in enumerate(words[:-1]) for t in ([" "] if i else []) + wd]
        lines.append(words[-1])
    return ["".join(line) for line in lines]


def wrap(en):
    toks = [m.group(0) for m in text.TOKEN.finditer(en)]
    out, seg = [], []
    for t in toks + [None]:
        n = tok_name(t) if t else "end"
        if t is not None and n not in ENDS and n != "clr":
            seg.append(t)
            continue
        if any(x.strip() for x in seg):
            lines = wrap_segment(seg, WIDTH - 1 if n in ("wait",) else WIDTH)
            pages = [lines[i:i + LINES] for i in range(0, len(lines), LINES)]
            sep = "{wait}{clr}" if n != "delay" else t + "{clr}"
            out.append(sep.join("{n}".join(p) for p in pages))
        else:
            out.append("".join(seg))
        seg = []
        if t is not None:
            out.append(t)
    return "".join(out)


if __name__ == "__main__":
    print(wrap(sys.argv[1]).replace("{n}", "{n}\n").replace("{clr}", "{clr}\n"))
