#!/usr/bin/env python3
"""Turn a screenshot of tools/paper.html into assets/img/paper.webp, the crease texture laid over every page.

The site used to multiply that texture over the page at 36% from SVG filters, which the browser had to rasterize
at load (slow on phones). Multiplying by a grey value L at opacity a is the same as laying black over the page at
alpha a * (1 - L), so the texture ships as black with that alpha and blends normally: same look, no filter, no
blend mode.

    python3 tools/paper.py paper-screenshot.png [--opacity 0.36] [--size 550] [--quality 70]

The darkest crease is only about 4% darker than the page, so the tile ships at half resolution and the stylesheet
draws it at 1100 px; nobody can see the lost detail at that contrast. Needs Pillow.
"""
import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("screenshot")
    ap.add_argument("--opacity", type=float, default=0.36)
    ap.add_argument("--size", type=int, default=550, help="tile size in pixels; the stylesheet draws it at 1100 px")
    ap.add_argument("--quality", type=int, default=70)
    ap.add_argument("--out", default=str(ROOT / "assets/img/paper.webp"))
    a = ap.parse_args()
    lum = Image.open(a.screenshot).convert("L")
    if lum.size != (a.size, a.size):
        lum = lum.resize((a.size, a.size), Image.LANCZOS)
    alpha = lum.point(lambda v: round(a.opacity * (255 - v)))
    black = Image.new("L", lum.size, 0)
    Image.merge("RGBA", (black, black, black, alpha)).save(a.out, "WEBP", quality=a.quality, alpha_quality=a.quality, method=6)
    lo, hi = alpha.getextrema()
    print(f"wrote {a.out}: {Path(a.out).stat().st_size // 1024} KB, alpha {lo}–{hi} of 255")


if __name__ == "__main__":
    main()
