"""生成应用图标：深蓝夜空 + 金色新月 + 桌面图标网格。

输出：
    resources/icons/icon.png       1024px 透明圆角 PNG
    resources/icons/icon.ico       多尺寸 Windows 图标
    docs/screenshots/06-app-icon.png  浅色/深色背景预览
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "resources" / "icons"
DOCS = ROOT / "docs" / "screenshots"
ICONS.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

BASE = 1024
SS = 2
S = BASE * SS


def sc(value: float) -> int:
    return int(round(value * S / BASE))


def lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def vertical_gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(image)
    for y in range(size):
        t = y / max(1, size - 1)
        t = t ** 1.15
        draw.line([(0, y), (size, y)], fill=lerp(top, bottom, t) + (255,))
    return image


def rounded_mask(size: int, radius: float) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def sparkle(draw: ImageDraw.ImageDraw, center: tuple[float, float], radius: float,
            color: tuple[int, int, int, int]) -> None:
    cx, cy = center
    points = []
    for i in range(8):
        r = radius if i % 2 == 0 else radius * 0.28
        angle = math.radians(-90 + i * 45)
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=color)


def build() -> Image.Image:
    canvas = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bg = vertical_gradient(S, (33, 39, 84), (8, 11, 26))
    canvas.alpha_composite(bg)

    halo = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(halo)
    hdraw.ellipse([sc(300), sc(40), sc(1120), sc(880)], fill=(88, 82, 190, 46))
    halo = halo.filter(ImageFilter.GaussianBlur(sc(150)))
    canvas.alpha_composite(halo)

    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([sc(430), sc(130), sc(900), sc(600)], fill=(255, 213, 136, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(sc(80)))
    canvas.alpha_composite(glow)

    rng = random.Random(20261117)
    stars = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(stars)
    for _ in range(34):
        x = rng.uniform(sc(70), sc(960))
        y = rng.uniform(sc(60), sc(520))
        # 让星星避开月亮主体
        if (x - sc(665)) ** 2 / sc(210) ** 2 + (y - sc(360)) ** 2 / sc(220) ** 2 < 1.15:
            continue
        r = rng.uniform(sc(1.4), sc(4.2))
        alpha = rng.randint(70, 190)
        sdraw.ellipse([x - r, y - r, x + r, y + r], fill=(255, 248, 226, alpha))
    sparkle(sdraw, (sc(250), sc(215)), sc(26), (255, 240, 200, 210))
    sparkle(sdraw, (sc(390), sc(360)), sc(12), (255, 240, 200, 150))
    sparkle(sdraw, (sc(880), sc(150)), sc(10), (255, 240, 200, 130))
    canvas.alpha_composite(stars)

    moon_mask = Image.new("L", (S, S), 0)
    mdraw = ImageDraw.Draw(moon_mask)
    mdraw.ellipse([sc(492), sc(168), sc(868), sc(544)], fill=255)
    mdraw.ellipse([sc(592), sc(96), sc(948), sc(452)], fill=0)
    moon_mask = moon_mask.filter(ImageFilter.GaussianBlur(sc(1.2)))
    gold = vertical_gradient(S, (255, 246, 207), (226, 169, 82))
    canvas.paste(gold, (0, 0), moon_mask)

    shade = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sdraw2 = ImageDraw.Draw(shade)
    sdraw2.arc([sc(500), sc(176), sc(860), sc(536)], 120, 300, fill=(196, 139, 58, 90), width=sc(10))
    shade = shade.filter(ImageFilter.GaussianBlur(sc(7)))
    canvas.alpha_composite(Image.composite(shade, Image.new("RGBA", (S, S), (0, 0, 0, 0)), moon_mask))

    tiles = [
        (238, 648, False, "grid"),
        (392, 648, True, "app"),
        (238, 802, False, "list"),
        (392, 802, False, "empty"),
    ]
    for (x, y, accent, glyph) in tiles:
        box = [sc(x), sc(y), sc(x + 128), sc(y + 128)]
        radius = sc(34)
        if accent:
            tile = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(tile)
            tdraw.rounded_rectangle(box, radius=radius, fill=(96, 108, 236, 235),
                                    outline=(158, 168, 255, 220), width=sc(3))
            canvas.alpha_composite(tile)
        elif glyph == "empty":
            tile = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(tile)
            tdraw.rounded_rectangle(box, radius=radius, fill=(255, 198, 100, 26),
                                    outline=(247, 198, 110, 170), width=sc(3))
            canvas.alpha_composite(tile)
            plus = sc(20)
            cx, cy = sc(x + 64), sc(y + 64)
            pd = ImageDraw.Draw(canvas, "RGBA")
            pd.line([cx - plus, cy, cx + plus, cy], fill=(247, 198, 110, 210), width=sc(5))
            pd.line([cx, cy - plus, cx, cy + plus], fill=(247, 198, 110, 210), width=sc(5))
            continue
        else:
            tile = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(tile)
            tdraw.rounded_rectangle(box, radius=radius, fill=(255, 255, 255, 22),
                                    outline=(255, 255, 255, 54), width=sc(2))
            canvas.alpha_composite(tile)

        draw = ImageDraw.Draw(canvas, "RGBA")
        cx, cy = sc(x + 64), sc(y + 64)
        if glyph == "app":
            sparkle(draw, (cx, cy), sc(34), (255, 252, 240, 245))
        elif glyph == "list":
            for i, width_ratio in enumerate((0.52, 0.38, 0.46)):
                ly = cy - sc(18) + i * sc(18)
                draw.rounded_rectangle(
                    [cx - sc(28), ly, cx - sc(28) + sc(56 * width_ratio), ly + sc(7)],
                    radius=sc(3.5), fill=(255, 255, 255, 120),
                )
        elif glyph == "grid":
            for dx in (-22, 2):
                for dy in (-22, 2):
                    draw.rounded_rectangle(
                        [cx + sc(dx), cy + sc(dy), cx + sc(dx + 18), cy + sc(dy + 18)],
                        radius=sc(4.5), fill=(255, 255, 255, 125),
                    )

    border = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(border)
    bdraw.rounded_rectangle([sc(2), sc(2), S - sc(2), S - sc(2)], radius=sc(232),
                            outline=(255, 255, 255, 34), width=sc(3))
    canvas.alpha_composite(border)

    mask = rounded_mask(S, sc(232))
    canvas.putalpha(mask)
    return canvas.resize((BASE, BASE), Image.LANCZOS)


def main() -> None:
    icon = build()
    icon.save(ICONS / "icon.png")
    icon.resize((256, 256), Image.LANCZOS).save(ICONS / "icon-256.png")
    icon.save(
        ICONS / "icon.ico",
        sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (96, 96), (128, 128), (256, 256)],
    )

    preview = Image.new("RGB", (760, 420), (243, 245, 251))
    light_bg = Image.new("RGB", (380, 420), (243, 245, 251))
    preview.paste(light_bg, (0, 0))
    dark_bg = Image.new("RGB", (380, 420), (12, 15, 30))
    preview.paste(dark_bg, (380, 0))
    big = icon.resize((220, 220), Image.LANCZOS)
    preview.paste(big, (80, 52), big)
    preview.paste(big, (460, 52), big)
    small = icon.resize((48, 48), Image.LANCZOS)
    for i in range(4):
        preview.paste(small, (100 + i * 62, 300), small)
        preview.paste(small, (480 + i * 62, 300), small)
    preview.save(DOCS / "06-app-icon.png")
    print("icons written:", ICONS)


if __name__ == "__main__":
    main()
