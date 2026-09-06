"""Generate deterministic PNG and ICO files from WaterBuddy's icon geometry."""

from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "windows_app"


def make_icon(size: int = 512) -> Image.Image:
    image = Image.new("RGBA", (size, size), "#071A3A")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=116, fill="#071A3A")
    draw.ellipse((66, 66, 446, 446), fill="#0B2C61")
    drop = [(256, 68), (220, 137), (142, 220), (142, 304), (142, 378), (193, 428), (256, 428), (319, 428), (370, 378), (370, 304), (370, 220), (292, 137)]
    draw.polygon(drop, fill="#20B6EB")
    draw.ellipse((195, 260, 233, 310), fill="#061E52"); draw.ellipse((279, 260, 317, 310), fill="#061E52")
    draw.ellipse((201, 270, 215, 284), fill="white"); draw.ellipse((285, 270, 299, 284), fill="white")
    draw.arc((220, 307, 292, 355), start=20, end=160, fill="#061E52", width=12)
    draw.ellipse((157, 313, 203, 333), fill="#FC8ABE"); draw.ellipse((309, 313, 355, 333), fill="#FC8ABE")
    draw.line((190, 174, 267, 102), fill=(255, 255, 255, 100), width=18)
    return image


if __name__ == "__main__":
    OUTPUT.mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    icon.save(OUTPUT / "waterbuddy-icon.png", optimize=True)
    icon.save(OUTPUT / "WaterBuddy.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
