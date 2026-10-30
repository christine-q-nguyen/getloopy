#!/usr/bin/env python3
"""Give periods and decimal points in the big type a little room.

The display face is set with tight negative tracking, which pinches a period against the letter before it and
the italic word after it ("training.AI"), and squeezes a decimal point until "2.5 weeks" reads as "25 weeks".
This wraps them in every headline (<h1>, <h2>), case and tile headline (<p class="out"><b>), result stat
(<div class="v">), and section question (<p class="hook">):

- a sentence-ending period outside the italic accent becomes <span class="pd">.</span>
- a decimal point between two digits becomes <span class="dp">.</span>

styles.css spaces both out. Safe to re-run: run it after editing big type.

    python3 tools/headline-periods.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIG = [
    re.compile(r"(<(h1|h2)\b[^>]*>)(.*?)(</\2>)", re.S),
    re.compile(r'(<p class="out(?: sm)?"><b()>)(.*?)(</b>)', re.S),
    re.compile(r'(<div class="v"()>)(.*?)(</div>)', re.S),
    re.compile(r'(<p class="hook"()>)(.*?)(</p>)', re.S),
]
ITALIC = re.compile(r"(<em\b[^>]*>.*?</em>)", re.S)
TEXT = re.compile(r"(^|>)([^<]+)")
DOT = re.compile(r"(?<=[A-Za-z0-9’'”)])\.(?=\s|$)")
DECIMAL = re.compile(r"(?<=\d)\.(?=\d)")
PERIOD, POINT = '<span class="pd">.</span>', '<span class="dp">.</span>'


def runs(markup: str, fix) -> str:
    # each text run between tags; a run ends at a tag, so "talk.</h2>" counts as sentence-ending
    return TEXT.sub(lambda m: m.group(1) + fix(m.group(2)), markup)


def wrap(inner: str) -> str:
    out = []
    for part in ITALIC.split(inner):
        if part.startswith("<em"):
            out.append(runs(part, lambda t: DECIMAL.sub(POINT, t)))
        else:
            out.append(runs(part, lambda t: DOT.sub(PERIOD, DECIMAL.sub(POINT, t))))
    return "".join(out)


def main() -> None:
    pages = sorted(ROOT.glob("*.html")) + sorted((ROOT / "work").glob("*.html"))
    changed = 0
    for page in pages:
        src = page.read_text(encoding="utf-8")
        new = src
        for pattern in BIG:
            new = pattern.sub(lambda m: m.group(1) + wrap(m.group(3)) + m.group(4), new)
        if new != src:
            page.write_text(new, encoding="utf-8")
            changed += 1
            print(f"{page.relative_to(ROOT)}: {new.count(PERIOD) - src.count(PERIOD)} periods, "
                  f"{new.count(POINT) - src.count(POINT)} decimal points")
    print(f"{changed} pages updated")


if __name__ == "__main__":
    main()
