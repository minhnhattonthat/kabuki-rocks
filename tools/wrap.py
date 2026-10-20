"""Reflow English into the 28x3 dialogue box.

Translators write a run's English with its control tokens but without {n}. Only {clr} and {p9a} start a new
page; {wait} {delay:XX} {ba} {b8:..} {choice:..} {jump:..} {name9x} are zero-width and stay where they fall, in the
same line (the game does not break the line there). Text is broken into lines of <= WIDTH cells and pages of LINES
lines; extra pages are joined with {wait}{clr}. The last line of a page and any line holding a {wait} keep ARROW cells
free for the blinking arrow; a last page of one short line is rebalanced (layout). A {n} the translator did write forces a line break.

    python -X utf8 tools/wrap.py "Makki: Oh, but first we have to ask Granny Ume for permission!{wait}"
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import text  # noqa: E402

WIDTH, LINES = 28, 3
ARROW = 2  # cells kept free on a line with the page arrow: it is drawn in cell 28, touching a 27-cell line
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
    """Tokens of one page-less segment -> string with {n} line breaks and {wait}{clr} page breaks. A last page
    of one short line (a widow) pulls words from the line before it instead, when the page count stays the same."""
    pages = pages_of(toks)
    if len(pages) > 1 and len(pages[-1]) == 1 and plain_width(pages[-1][0]) < WIDTH // 2:
        for shave in range(1, WIDTH // 2):
            p = pages_of(toks, shave)
            if len(p) == len(pages) and (len(p[-1]) > 1 or plain_width(p[-1][0]) >= WIDTH // 2):
                pages = p
                break
    return "{wait}{clr}".join("{n}".join(lines) for lines in pages)


def plain_width(line):
    return sum(width(m.group(0)) for m in text.TOKEN.finditer(line))


def pages_of(toks, shave=0):
    """Pages (lists of line strings); the last line of a full page is `shave` cells shorter."""
    pages, lines, cur, w = [], [], [], 0

    def newline():
        nonlocal cur, w
        lines.append("".join(cur))
        cur, w = [], 0
        if len(lines) == LINES:
            pages.append(lines[:])
            lines.clear()

    def limit_for(arrow):
        if len(lines) == LINES - 1:
            return WIDTH - ARROW - shave
        return WIDTH - ARROW if arrow else WIDTH

    for word in split_words(toks):
        if word == ["{n}"]:
            newline()
            continue
        ww = sum(width(t) for t in word)
        arrow = any(tok_name(t) == "wait" for t in word)
        limit = limit_for(arrow)
        need = ww + (1 if cur and ww else 0)
        if cur and w + need > limit and ww:
            newline()
            limit = limit_for(arrow)
            need = ww
        cur += ([" "] if cur and ww else []) + word
        w += need
    if cur or lines or not pages:
        lines.append("".join(cur))
        pages.append(lines[:])
    return pages


def wrap(en):
    if "{n}" in en:  # pre-formatted (credits, profile cards): the author laid out the lines; lint checks widths
        return en
    toks =[m.group(0) for m in text.TOKEN.finditer(en)]
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
