"""Generate the 12 test images used to tune and test the checker.

Every image starts from the same rendered "document" (a fake invoice with
text), then one problem is applied: blur, darkness, low resolution and so on.
Run once:  python make_samples.py
"""
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

OUT = Path(__file__).parent / "sample_images"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

LINES = [
    "Item                      Qty     Price     Total",
    "Wireless keyboard          2      29.99     59.98",
    "USB-C charging cable       5       9.50     47.50",
    "Laptop stand               1      34.00     34.00",
    "Screen cleaning kit        3       6.25     18.75",
    "Notebook A5 (ruled)       10       2.40     24.00",
    "HDMI adapter               2      12.80     25.60",
    "Desk lamp                  1      27.45     27.45",
    "Subtotal                                   237.28",
    "Tax (8%)                                    18.98",
    "Total due                                  256.26",
]


def font(size, bold=False):
    """DejaVu fonts on Linux, Arial on macOS, Pillow's built-in font otherwise."""
    for path in (FONT_BOLD if bold else FONT_REG,
                 "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def render_document(width=1000, height=1250, dark_mode=False):
    """Draw a simple invoice page with black text on white (or the reverse)."""
    if dark_mode:
        bg, fg = (18, 20, 26), (225, 228, 235)
    else:
        bg, fg = (255, 255, 255), (20, 20, 20)
    img = Image.new("RGB", (width, height), bg)
    d = ImageDraw.Draw(img)
    d.text((60, 60), "INVOICE  #20418", font=font(44, True), fill=fg)
    d.text((60, 125), "Northgate Office Supplies, 14 Mill Road", font=font(24), fill=fg)
    d.text((60, 160), "Date: 12 October 2026", font=font(24), fill=fg)
    y = 260
    for i, line in enumerate(LINES):
        d.text((60, y), line, font=font(26, bold=(i in (0, 10))), fill=fg)
        y += 52
    y += 40
    for para in range(4):
        d.text((60, y), "Thank you for your order. Payment is due within 14 days.", font=font(22), fill=fg)
        y += 36
        d.text((60, y), "Questions about this invoice? Contact accounts@northgate.example", font=font(22), fill=fg)
        y += 60
    return img


def add_camera_noise(img, sigma=4, seed=1):
    rng = np.random.default_rng(seed)
    arr = np.asarray(img).astype(np.float32)
    arr += rng.normal(0, sigma, arr.shape)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def darken(img, factor):
    return ImageEnhance.Brightness(img).enhance(factor)


def wash_out(img):
    """Simulate overexposure: push everything towards white."""
    arr = np.asarray(img).astype(np.float32)
    arr = 255 - (255 - arr) * 0.18
    return Image.fromarray(arr.astype(np.uint8))


def low_contrast(img):
    arr = np.asarray(img).astype(np.float32)
    arr = 150 + (arr - 128) * 0.12
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def main():
    OUT.mkdir(exist_ok=True)
    random.seed(1)
    base = render_document()

    samples = {
        "01_sharp_good.jpg": add_camera_noise(base),
        "02_sharp_high_res.jpg": add_camera_noise(render_document(2000, 2500)),
        "03_slight_blur.jpg": add_camera_noise(base.filter(ImageFilter.GaussianBlur(1.2))),
        "04_medium_blur.jpg": add_camera_noise(base.filter(ImageFilter.GaussianBlur(2.5))),
        "05_heavy_blur.jpg": add_camera_noise(base.filter(ImageFilter.GaussianBlur(6))),
        "06_slightly_dark.jpg": add_camera_noise(darken(base, 0.38)),
        "07_very_dark.jpg": add_camera_noise(darken(base, 0.18)),
        "08_overexposed.jpg": add_camera_noise(wash_out(base)),
        "09_tiny_resolution.jpg": base.resize((220, 275), Image.LANCZOS),
        "10_borderline_resolution.jpg": base.resize((560, 700), Image.LANCZOS),
        "11_low_contrast.jpg": add_camera_noise(low_contrast(base)),
        "12_dark_mode_screenshot.png": render_document(dark_mode=True),
    }
    for name, img in samples.items():
        path = OUT / name
        if path.suffix == ".jpg":
            img.save(path, quality=88)
        else:
            img.save(path)
        print("saved", path.name, img.size)


if __name__ == "__main__":
    main()
