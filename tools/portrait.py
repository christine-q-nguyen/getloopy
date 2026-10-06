#!/usr/bin/env python3
"""Put a finished pencil portrait on the About page, drawn in when it scrolls into view.

    python3 tools/portrait.py _reference/portrait-sketch-source.jpg

Lifts the graphite off the paper so the drawing sits on the site's own background, then writes
two layers to assets/img: portrait.webp (the finished drawing) and portrait-lines.webp (only its
darkest strokes). The About figure gets mask strokes that uncover the lines from the eyes outward;
site.js plays them once, lets the shading settle in over the lines, then holds still. Without JS or
under reduced motion the finished drawing simply shows. Needs only Pillow.
"""
import re
import sys
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SIZE = 640                  # twice the widest the figure is shown at
INK = (24, 24, 24)          # --ink
FOCUS = (0.42, 0.36)        # where the drawing starts (between the eyes), as fractions of width and height
LINE_LEVEL = 118            # pixels darker than this count as line work
BANDS = 10
STAGGER, STROKE_FOR = 0.14, 0.8


def clamp(v):
    return 0 if v < 0 else 255 if v > 255 else round(v)


def paper_level(gray):
    w, h = gray.size
    m = max(4, w // 25)
    border = [gray.crop(b) for b in ((0, 0, w, m), (0, h - m, w, h), (0, 0, m, h), (w - m, 0, w, h))]
    values = sorted(v for part in border for v in part.tobytes())
    return values[len(values) // 2]


def edge_falloff(size):
    """Soft margins, so the drawing ends in the page instead of at a rectangle; the bottom dissolves."""
    w, h = size
    ramp = lambda d, span: min(1.0, max(0.0, d / span))
    side, top = 0.05 * w, 0.02 * h
    bottom0, bottom1 = 0.78 * h, h
    mask = Image.new("L", size)
    px = mask.load()
    for y in range(h):
        fy = ramp(y, top) * (1 - ramp(y - bottom0, bottom1 - bottom0))
        for x in range(w):
            px[x, y] = clamp(255 * fy * ramp(x, side) * ramp(w - 1 - x, side))
    return mask


def layer(gray, lighter_than, darkest, falloff):
    span = max(lighter_than - darkest, 1)
    alpha = gray.point(lambda v: clamp((lighter_than - v) * 255 / span))
    alpha = Image.composite(alpha, Image.new("L", gray.size), falloff)
    alpha = alpha.resize((SIZE, SIZE), Image.LANCZOS)
    out = Image.new("RGBA", (SIZE, SIZE), INK + (0,))
    out.putalpha(alpha)
    return out


def zigzag(x_from, x_to, y0, y1, step):
    """Slanted hatch from x_from toward x_to, alternating between the band's top and bottom edge."""
    direction = 1 if x_to >= x_from else -1
    pts, x, top = [], x_from, True
    while (x - x_to) * direction < 0:
        pts.append((x, y0 if top else y1))
        x += direction * step
        top = not top
    pts.append((x_to, y0 if top else y1))
    return "M" + "L".join(f"{px:.0f} {py:.0f}" for px, py in pts)


def reveal_strokes(lines_alpha):
    h = SIZE / BANDS
    fx, fy = FOCUS[0] * SIZE, FOCUS[1] * SIZE
    found = []
    for b in range(BANDS):
        y0, y1 = round(b * h), round((b + 1) * h)
        cols = lines_alpha.crop((0, y0, SIZE, y1)).resize((SIZE, 1), Image.BOX).tobytes()
        inked = [x for x, v in enumerate(cols) if v > 6]
        if not inked:
            continue
        x_min, x_max = inked[0] - h * 0.4, inked[-1] + h * 0.4
        start = min(max(fx, x_min), x_max)
        found.append((abs((y0 + y1) / 2 - fy), y0, y1, start, x_min, x_max))
    found.sort()
    paths = []
    for rank, (_, y0, y1, start, x_min, x_max) in enumerate(found):
        top, bottom = y0 - h * 0.18, y1 + h * 0.18
        for end in (x_min, x_max):
            if abs(end - start) > h * 0.3:
                paths.append(f'<path pathLength="1" data-at="{rank * STAGGER:.2f}" data-for="{STROKE_FOR}" d="{zigzag(start, end, top, bottom, h * 0.55)}"/>')
    return paths, round(h * 0.95)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sketch = Image.open(sys.argv[1]).convert("L")
    side = min(sketch.size)
    sketch = sketch.crop(((sketch.width - side) // 2, 0, (sketch.width + side) // 2, side))
    paper = paper_level(sketch) - 8
    falloff = edge_falloff(sketch.size)
    tone = layer(sketch, paper, 18, falloff)
    lines = layer(sketch.filter(ImageFilter.MedianFilter(3)), LINE_LEVEL, 25, falloff)

    out = ROOT / "assets/img"
    tone.save(out / "portrait.webp", "WEBP", quality=82, alpha_quality=60, method=6)
    lines.save(out / "portrait-lines.webp", "WEBP", quality=82, alpha_quality=60, method=6)

    paths, width = reveal_strokes(lines.getchannel("A"))
    figure = f'''<figure class="portrait" data-draw>
      <svg viewBox="0 0 {SIZE} {SIZE}" role="img" aria-labelledby="portrait-title">
        <title id="portrait-title">Christine Nguyen, drawn in pencil</title>
        <defs>
          <mask id="portrait-reveal" maskUnits="userSpaceOnUse" x="0" y="0" width="{SIZE}" height="{SIZE}"><g fill="none" stroke="#fff" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{"".join(paths)}</g></mask>
          <filter id="portrait-boil" x="-2%" y="-2%" width="104%" height="104%"><feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="2" seed="1"/><feDisplacementMap in="SourceGraphic" scale="2.5" xChannelSelector="R" yChannelSelector="G"/></filter>
        </defs>
        <image class="portrait-lines" href="assets/img/portrait-lines.webp" width="{SIZE}" height="{SIZE}" mask="url(#portrait-reveal)"/>
        <image class="portrait-tone" href="assets/img/portrait.webp" width="{SIZE}" height="{SIZE}"/>
      </svg>
    </figure>'''
    page = ROOT / "about.html"
    src = page.read_text(encoding="utf-8")
    src, n = re.subn(r'<figure class="portrait[^"]*".*?</figure>', lambda _: figure, src, count=1, flags=re.S)
    if n != 1:
        sys.exit("about.html has no portrait figure to replace")
    page.write_text(src, encoding="utf-8")
    sizes = ", ".join(f"{p.name} {p.stat().st_size // 1024} KB" for p in (out / "portrait.webp", out / "portrait-lines.webp"))
    print(f"portrait: {SIZE}x{SIZE}, {len(paths)} reveal strokes, {sizes}")


if __name__ == "__main__":
    main()
