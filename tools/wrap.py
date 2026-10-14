"""Reflow English into the 28x3 dialogue box.

Translators write a run's English with its control tokens but without {n}. Only {clr} and {p9a} start a new
page; {wait} {delay:XX} {ba} {b8:..} {choice:..} {jump:..} {name9x} are zero-width and stay where they fall, in the
same line (the game does not break the line there). Text is broken into lines of <= WIDTH cells and pages of LINES
lines; extra pages are joined with {wait}{clr}. The last line of a page and any line holding a {wait} keep one cell
free for the blinking arrow. A {n} the translator did write forces a line break.

    python -X utf8 tools/wrap.py "Makki: Oh, but first we have to ask Granny Ume for permission!{wait}"
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import text  # noqa: E402

WIDTH, LINES = 28, 3
NAME_LEN = {"name93": 4, "name94": 5}  # Rock, Makki (English names patched at 00:9FE8)
PAGE = {"clr", "p9a"}


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


def layout(toks):
    """Tokens of one page-less segment -> string with {n} line breaks and {wait}{clr} page breaks."""
    pages, lines, cur, w = [], [], [], 0

    def newline():
        nonlocal cur, w
        lines.append("".join(cur))
        cur, w = [], 0
        if len(lines) == LINES:
            pages.append("{n}".join(lines))
            lines.clear()

    for word in split_words(toks):
        if word == ["{n}"]:
            newline()
            continue
        ww = sum(width(t) for t in word)
        arrow = any(tok_name(t) == "wait" for t in word)
        limit = WIDTH - 1 if arrow or len(lines) == LINES - 1 else WIDTH
        need = ww + (1 if cur and ww else 0)
        if cur and w + need > limit and ww:
            newline()
            limit = WIDTH - 1 if arrow or len(lines) == LINES - 1 else WIDTH
            need = ww
        cur += ([" "] if cur and ww else []) + word
        w += need
    if cur or lines or not pages:
        lines.append("".join(cur))
        pages.append("{n}".join(lines))
    return "{wait}{clr}".join(pages)


def wrap(en):
    toks = [m.group(0) for m in text.TOKEN.finditer(en)]
    out, seg = [], []
    for t in toks + [None]:
        if t is not None and tok_name(t) not in PAGE:
            seg.append(t)
            continue
        out.append(layout(seg) if any(x.strip() for x in seg) else "".join(seg))
        seg = []
        if t is not None:
            out.append(t)
    return "".join(out)


if __name__ == "__main__":
    print(wrap(sys.argv[1]).replace("{n}", "{n}\n").replace("{clr}", "{clr}\n"))
