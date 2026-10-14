"""Image quality checks for text extraction (OCR).

Three checks, each returning PASS, WARNING or FAIL with a plain reason:
  1. Blur        : variance of the Laplacian (higher = sharper)
  2. Brightness  : mean grey level, with a contrast guard for dark-mode images
  3. Resolution  : length of the shorter side in pixels

The overall verdict is the worst of the three.
Only Pillow and NumPy are used, so the app deploys easily on free platforms.
"""
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageFilter, ImageOps

PASS, WARNING, FAIL = "PASS", "WARNING", "FAIL"
_ORDER = {PASS: 0, WARNING: 1, FAIL: 2}

# Thresholds tuned on the 12 images in sample_images/ (see README).
THRESHOLDS = {
    # Blur: Laplacian variance, measured after scaling to at most 1000 px wide,
    # a light denoise and a contrast stretch. Higher = sharper.
    "blur_fail": 60.0,
    "blur_warn": 250.0,
    # Brightness: mean grey level (0 = black, 255 = white).
    "dark_fail": 60.0,
    "dark_warn": 100.0,
    "bright_warn": 215.0,
    # Contrast range = 99.5th minus 0.5th percentile of grey levels.
    # A wide range means text is readable even if the average is dark
    # (dark-mode screenshots), so brightness is not penalised then.
    "contrast_ok": 150.0,
    "contrast_warn": 100.0,
    "contrast_fail": 60.0,
    # Resolution: shorter side in pixels.
    "res_fail": 400,
    "res_warn": 700,
}

ANALYSIS_WIDTH = 1000  # big images are scaled down so blur scores are comparable


@dataclass
class Check:
    name: str
    status: str
    value: float
    reason: str


@dataclass
class Report:
    overall: str
    checks: list = field(default_factory=list)
    width: int = 0
    height: int = 0

    @property
    def reasons(self):
        return [c.reason for c in self.checks if c.status != PASS]


def _worst(statuses):
    return max(statuses, key=lambda s: _ORDER[s])


def _to_gray(img):
    img = ImageOps.exif_transpose(img)  # respect phone photo rotation
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, img)
    return img.convert("L")


def laplacian_variance(gray):
    """Variance of the 4-neighbour Laplacian, computed with NumPy only."""
    a = np.asarray(gray, dtype=np.float32)
    lap = (
        -4 * a[1:-1, 1:-1]
        + a[:-2, 1:-1]
        + a[2:, 1:-1]
        + a[1:-1, :-2]
        + a[1:-1, 2:]
    )
    return float(lap.var())


def check_blur(gray, t=THRESHOLDS):
    w, h = gray.size
    if w > ANALYSIS_WIDTH:
        gray = gray.resize((ANALYSIS_WIDTH, round(h * ANALYSIS_WIDTH / w)), Image.LANCZOS)
    # Light denoise first so camera noise is not mistaken for sharp edges,
    # then stretch contrast so dark or washed-out images are scored fairly.
    gray = gray.filter(ImageFilter.GaussianBlur(1.0))
    score = laplacian_variance(ImageOps.autocontrast(gray, cutoff=0.5))
    if score < t["blur_fail"]:
        return Check("Blur", FAIL, score, "The image is very blurry, so the text edges are lost.")
    if score < t["blur_warn"]:
        return Check("Blur", WARNING, score, "The image is slightly blurry and some characters may be misread.")
    return Check("Blur", PASS, score, "The image is sharp.")


def check_brightness(gray, t=THRESHOLDS):
    arr = np.asarray(gray, dtype=np.float32)
    mean = float(arr.mean())
    lo, hi = np.percentile(arr, [0.5, 99.5])
    spread = float(hi - lo)

    if spread >= t["contrast_ok"]:
        return Check("Brightness", PASS, mean, "Lighting and contrast are good.")
    if mean < t["dark_fail"]:
        return Check("Brightness", FAIL, mean, "The image is too dark to read the text.")
    if mean > t["bright_warn"] and spread < t["contrast_fail"]:
        return Check("Brightness", FAIL, mean, "The image is overexposed and the text is washed out.")
    if spread < t["contrast_fail"]:
        return Check("Brightness", FAIL, mean, "Contrast is far too low: the text barely stands out from the background.")
    if mean < t["dark_warn"]:
        return Check("Brightness", WARNING, mean, "The image is quite dark and faint text may be missed.")
    if mean > t["bright_warn"] and spread < t["contrast_warn"]:
        return Check("Brightness", WARNING, mean, "The image is very bright and thin text may fade out.")
    if spread < t["contrast_warn"]:
        return Check("Brightness", WARNING, mean, "Contrast is low, so the text may be hard to separate from the background.")
    return Check("Brightness", PASS, mean, "Lighting and contrast are good.")


def check_resolution(size, t=THRESHOLDS):
    short = min(size)
    if short < t["res_fail"]:
        return Check("Resolution", FAIL, short, f"The image is only {size[0]}x{size[1]} px, too small for reliable text extraction.")
    if short < t["res_warn"]:
        return Check("Resolution", WARNING, short, f"The image is {size[0]}x{size[1]} px, small text may not be readable.")
    return Check("Resolution", PASS, short, f"The resolution ({size[0]}x{size[1]} px) is enough.")


def analyze(img, thresholds=THRESHOLDS):
    """Run all checks on a PIL image and return a Report."""
    gray = _to_gray(img)
    checks = [
        check_blur(gray, thresholds),
        check_brightness(gray, thresholds),
        check_resolution(gray.size, thresholds),
    ]
    return Report(
        overall=_worst([c.status for c in checks]),
        checks=checks,
        width=gray.size[0],
        height=gray.size[1],
    )
