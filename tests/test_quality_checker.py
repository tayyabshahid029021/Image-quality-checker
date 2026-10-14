import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from quality_checker import FAIL, PASS, WARNING, analyze  # noqa: E402
from evaluate import FOLDER, load_expected  # noqa: E402


def text_image(width=1000, height=1250, bg=255, fg=20):
    """A simple synthetic page: many short bars standing in for text lines."""
    img = Image.new("L", (width, height), bg)
    d = ImageDraw.Draw(img)
    for row in range(30):
        y = 80 + row * 32
        for col in range(12):
            x = 60 + col * 70
            d.rectangle([x, y, x + 50, y + 14], fill=fg)
    return img.convert("RGB")


def check_by_name(report, name):
    return next(c for c in report.checks if c.name == name)


def test_sharp_page_passes():
    assert analyze(text_image()).overall == PASS


def test_heavy_blur_fails_with_reason():
    report = analyze(text_image().filter(ImageFilter.GaussianBlur(8)))
    assert check_by_name(report, "Blur").status == FAIL
    assert report.overall == FAIL
    assert any("blurry" in r for r in report.reasons)


def test_very_dark_image_fails():
    dark = Image.fromarray((np.asarray(text_image()) * 0.15).astype(np.uint8))
    assert check_by_name(analyze(dark), "Brightness").status == FAIL


def test_dark_mode_screenshot_is_not_penalised():
    report = analyze(text_image(bg=15, fg=230))
    assert check_by_name(report, "Brightness").status == PASS


def test_tiny_image_fails_resolution():
    report = analyze(text_image(200, 250))
    assert check_by_name(report, "Resolution").status == FAIL


def test_small_image_warns_resolution():
    report = analyze(text_image(560, 700))
    assert check_by_name(report, "Resolution").status == WARNING


def test_overall_is_worst_check():
    report = analyze(text_image(200, 250))
    order = [PASS, WARNING, FAIL]
    assert report.overall == max((c.status for c in report.checks), key=order.index)


def test_transparent_png_is_handled():
    assert analyze(text_image().convert("RGBA")).overall == PASS


def test_greyscale_and_palette_modes_work():
    base = text_image()
    assert analyze(base.convert("L")).overall == PASS
    assert analyze(base.convert("P")).overall in (PASS, WARNING)


@pytest.mark.parametrize("name,expected", sorted(load_expected().items()))
def test_sample_images_match_expected(name, expected):
    report = analyze(Image.open(FOLDER / name))
    assert report.overall == expected, report.reasons
