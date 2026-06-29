#!/usr/bin/env python
"""Generate the application icon (assets/icon.ico) — a white dumbbell on the brand accent.

Run once (or after changing the design):  python scripts/generate_icon.py
The .ico is committed so packaging/runtime don't depend on regenerating it.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ACCENT = (61, 90, 254, 255)  # #3d5afe
WHITE = (255, 255, 255, 255)
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def build_image(size: int = 256) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    s = size / 256.0
    draw.rounded_rectangle([8 * s, 8 * s, 248 * s, 248 * s], radius=int(48 * s), fill=ACCENT)
    # Dumbbell (centered bar + a pair of plates each side).
    draw.rounded_rectangle([78 * s, 118 * s, 178 * s, 138 * s], radius=int(10 * s), fill=WHITE)
    draw.rounded_rectangle([52 * s, 92 * s, 74 * s, 164 * s], radius=int(8 * s), fill=WHITE)
    draw.rounded_rectangle([36 * s, 108 * s, 54 * s, 148 * s], radius=int(6 * s), fill=WHITE)
    draw.rounded_rectangle([182 * s, 92 * s, 204 * s, 164 * s], radius=int(8 * s), fill=WHITE)
    draw.rounded_rectangle([202 * s, 108 * s, 220 * s, 148 * s], radius=int(6 * s), fill=WHITE)
    return image


def main() -> None:
    assets = Path(__file__).resolve().parent.parent / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    master = build_image(256)
    master.save(assets / "icon.ico", sizes=SIZES)
    master.save(assets / "icon.png")
    print("Wrote", assets / "icon.ico")


if __name__ == "__main__":
    main()
