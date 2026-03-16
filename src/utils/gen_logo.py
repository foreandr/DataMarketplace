"""Generate a polished 500x500 logo using Pillow — gradient bg, glow text, decorative circles.

Install:  pip install Pillow
Usage:    python src/tools/gen_logo.py
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT_DIR  = Path(__file__).resolve().parents[2]
LOGOS_DIR = ROOT_DIR / "static" / "logos"

# ── Colour schemes ─────────────────────────────────────────────────────────────
# Each entry: gradient top → bottom, bright accent, soft circle tint
_SCHEMES = [
    {"top": (12, 10, 40),  "bot": (50, 15, 85),  "accent": (240, 70,  110), "circ": (180, 50, 140)},  # purple/coral
    {"top": (8,  22, 68),  "bot": (18, 65, 130), "accent": (252, 180, 50),  "circ": (40, 120, 220)},  # navy/amber
    {"top": (10, 42, 32),  "bot": (18, 88, 62),  "accent": (55,  210, 140), "circ": (25, 150, 100)},  # forest/mint
    {"top": (30, 18, 58),  "bot": (22, 48, 100), "accent": (80,  185, 255), "circ": (50, 90,  210)},  # indigo/sky
    {"top": (68, 12, 18),  "bot": (120, 35, 55), "accent": (255, 185, 55),  "circ": (200, 55, 75)},   # crimson/gold
    {"top": (12, 52, 62),  "bot": (10, 95, 108), "accent": (145, 240, 225), "circ": (18, 145, 165)},  # teal/cyan
    {"top": (48, 28, 8),   "bot": (88, 58, 12),  "accent": (255, 202, 75),  "circ": (195, 125, 25)},  # bronze/gold
    {"top": (42, 8,  52),  "bot": (68, 18, 98),  "accent": (205, 155, 255), "circ": (145, 45, 195)},  # violet/lilac
    {"top": (8,  28, 55),  "bot": (30, 70, 90),  "accent": (100, 220, 190), "circ": (20, 140, 160)},  # deep teal
    {"top": (18, 18, 18),  "bot": (45, 45, 65),  "accent": (200, 200, 255), "circ": (80, 80,  160)},  # charcoal
]

_FONT_PATHS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in _FONT_PATHS:
        try:
            return ImageFont.truetype(p, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def _scheme(module_name: str) -> dict:
    idx = int(hashlib.md5(module_name.encode()).hexdigest(), 16) % len(_SCHEMES)
    return _SCHEMES[idx]


def _lerp(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _wrap(draw: ImageDraw.Draw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    bb = draw.textbbox((0, 0), text, font=font)
    if bb[2] - bb[0] <= max_w or len(words) < 2:
        return [text]
    # find best 2-line split
    for i in range(1, len(words)):
        l1, l2 = " ".join(words[:i]), " ".join(words[i:])
        b1 = draw.textbbox((0, 0), l1, font=font)
        b2 = draw.textbbox((0, 0), l2, font=font)
        if max(b1[2] - b1[0], b2[2] - b2[0]) <= max_w:
            return [l1, l2]
    return [text]


def gen_logo(module_name: str, out_path: Path | None = None) -> Path:
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)

    if out_path is None:
        slug     = module_name.lstrip("_")
        out_path = LOGOS_DIR / f"{slug}.png"

    display = module_name.lstrip("_").replace("_", " ").title()
    sc      = _scheme(module_name)
    SIZE    = 500

    # ── 1. Gradient background (RGBA throughout) ──────────────────────────────
    img = Image.new("RGBA", (SIZE, SIZE))
    for y in range(SIZE):
        t     = y / SIZE
        color = _lerp(sc["top"], sc["bot"], t) + (255,)
        ImageDraw.Draw(img).line([(0, y), (SIZE, y)], fill=color)

    # ── 2. Large decorative circle — top-right, extends off canvas ────────────
    circle_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    cd = ImageDraw.Draw(circle_layer)
    cr = sc["circ"]
    # big circle top-right
    cd.ellipse([(SIZE * 0.45, -SIZE * 0.3), (SIZE * 1.35, SIZE * 0.55)],
               fill=(*cr, 38))
    # softer second ring (same circle, slightly bigger, lower opacity)
    cd.ellipse([(SIZE * 0.38, -SIZE * 0.4), (SIZE * 1.5, SIZE * 0.65)],
               fill=(*cr, 15))
    # small accent circle — bottom-left
    ac = sc["accent"]
    cd.ellipse([(-SIZE * 0.06, SIZE * 0.62), (SIZE * 0.32, SIZE * 1.0)],
               fill=(*ac, 28))
    circle_layer = circle_layer.filter(ImageFilter.GaussianBlur(radius=4))
    img = Image.alpha_composite(img, circle_layer)

    # ── 3. Subtle diagonal lines (texture) ───────────────────────────────────
    line_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ld = ImageDraw.Draw(line_layer)
    for i in range(-SIZE, SIZE * 2, 28):
        ld.line([(i, 0), (i + SIZE, SIZE)], fill=(255, 255, 255, 8), width=1)
    img = Image.alpha_composite(img, line_layer)

    # ── 4. Bottom accent bar ──────────────────────────────────────────────────
    draw = ImageDraw.Draw(img)
    BAR  = 20
    draw.rectangle([(0, SIZE - BAR), (SIZE, SIZE)], fill=(*ac, 255))
    # thin top line
    draw.rectangle([(0, 0), (SIZE, 3)], fill=(*ac, 200))

    # ── 5. Find best font size + line wrapping ────────────────────────────────
    PADDING     = 52
    max_w       = SIZE - PADDING * 2
    chosen_font = None
    chosen_lines: list[str] = [display]

    for fs in range(100, 20, -4):
        f     = _load_font(fs)
        lines = _wrap(draw, display, f, max_w)
        if all((draw.textbbox((0, 0), ln, font=f)[2] -
                draw.textbbox((0, 0), ln, font=f)[0]) <= max_w
               for ln in lines):
            chosen_font  = f
            chosen_lines = lines
            break

    if chosen_font is None:
        chosen_font = _load_font(24)

    # measure actual line height
    ref_bb  = draw.textbbox((0, 0), "Ag", font=chosen_font)
    line_h  = (ref_bb[3] - ref_bb[1]) + 18
    block_h = line_h * len(chosen_lines) - 18
    usable  = SIZE - BAR
    y0      = (usable - block_h) // 2

    # ── 6. Text glow (blur a copy of the text) ────────────────────────────────
    glow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(glow)
    for i, line in enumerate(chosen_lines):
        bb = gd.textbbox((0, 0), line, font=chosen_font)
        x  = (SIZE - (bb[2] - bb[0])) // 2
        y  = y0 + i * line_h
        gd.text((x, y), line, font=chosen_font, fill=(*ac, 130))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=14))
    img  = Image.alpha_composite(img, glow)
    draw = ImageDraw.Draw(img)

    # ── 7. Final text ─────────────────────────────────────────────────────────
    for i, line in enumerate(chosen_lines):
        bb = draw.textbbox((0, 0), line, font=chosen_font)
        x  = (SIZE - (bb[2] - bb[0])) // 2
        y  = y0 + i * line_h
        # dark shadow
        draw.text((x + 3, y + 3), line, font=chosen_font, fill=(0, 0, 0, 160))
        # white text
        draw.text((x, y), line, font=chosen_font, fill=(255, 255, 255, 255))

    img.convert("RGB").save(str(out_path))
    print(f"[gen_logo] {module_name!r} → {out_path}")
    return out_path


if __name__ == "__main__":
    gen_logo("_craigslist_cars")
