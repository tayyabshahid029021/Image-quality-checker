# Image Quality Checker

A small Streamlit tool that warns when an image is too poor for text extraction (OCR). Built for aiTransform (task ZR-26-00755).

Upload an image and the tool checks **blur**, **brightness** and **resolution**. Each check gives a **PASS**, **WARNING** or **FAIL** with a plain reason, and the overall result is the worst of the three.

**Live app:** https://your-app-name.streamlit.app

## What it does

| Check | How it is measured | WARNING | FAIL |
|---|---|---|---|
| Blur | Variance of the Laplacian (an edge detector) after scaling to at most 1000 px wide, a light denoise and a contrast stretch | below 250 | below 60 |
| Brightness | Average grey level (0 to 255) plus contrast range (99.5th minus 0.5th percentile) | mean below 100, or low contrast | mean below 60, or very low contrast / washed out |
| Resolution | Shorter side of the image in pixels | below 700 px | below 400 px |

Images with a wide contrast range (for example dark mode screenshots) are not penalised for a low average brightness, because their text is still readable.

Only Pillow and NumPy are used for the checks (no OpenCV), so the app installs fast on free hosting.

## Setup

```
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at http://localhost:8501. You can upload your own images or pick one of the 12 samples from the dropdown.

No API keys or secrets are needed.

## How I tested it

I made 12 test images with `make_samples.py`. They all start from the same rendered invoice page, and one problem is applied to each (blur, darkness, low resolution and so on). The expected verdict for each is stored in `sample_images/expected.csv`.

Run the comparison:

```
python evaluate.py
```

Run the automated tests (21 tests, including one per sample image):

```
python -m pytest -q
```

Final results with the tuned thresholds:

| Image | Blur score | Mean brightness | Shorter side (px) | Verdict | Expected |
|---|---:|---:|---:|---|---|
| 01_sharp_good | 476.6 | 242.8 | 1000 | PASS | PASS |
| 02_sharp_high_res | 313.6 | 250.6 | 2000 | PASS | PASS |
| 03_slight_blur | 140.9 | 243.1 | 1000 | WARNING | WARNING |
| 04_medium_blur | 30.1 | 243.2 | 1000 | FAIL | FAIL |
| 05_heavy_blur | 29.0 | 243.4 | 1000 | FAIL | FAIL |
| 06_slightly_dark | 499.8 | 91.6 | 1000 | WARNING | WARNING |
| 07_very_dark | 655.7 | 42.7 | 1000 | FAIL | FAIL |
| 08_overexposed | 596.8 | 251.3 | 1000 | FAIL | FAIL |
| 09_tiny_resolution | 606.6 | 243.6 | 220 | FAIL | FAIL |
| 10_borderline_resolution | 637.3 | 243.8 | 560 | WARNING | WARNING |
| 11_low_contrast | 867.8 | 163.3 | 1000 | FAIL | FAIL |
| 12_dark_mode_screenshot | 490.5 | 29.1 | 1000 | PASS | PASS |

### How the thresholds were tuned

My first version did not work, and tuning fixed three problems:

1. **Contrast was measured with the 5th to 95th percentile.** A page of text has very few dark pixels (well under 5%), so this range looked tiny and every clean page failed. I changed it to the 0.5th to 99.5th percentile.
2. **Brightness alone cannot find overexposure on documents.** A normal white page already has a mean brightness around 243, so a high-brightness rule flagged good pages. Overexposure is now detected as high brightness together with low contrast.
3. **The raw blur score was unreliable.** Dark and low contrast images looked blurry, and camera noise made a heavily blurred image look sharper than a medium one. Adding a light denoise and a contrast stretch before measuring fixed this. The sharp images now score 313 or more, the slight blur scores 141, and the medium and heavy blur score about 30, so the thresholds sit in the gaps (60 and 250).

## Limitations

- **The test images are synthetic.** They are generated from one invoice layout, so they do not cover the full variety of real photos (shadows, curved paper, mixed lighting, handwriting). The thresholds should be re-checked on real phone photos and scans before relying on them.
- **The blur threshold is the least robust.** The sharpest realistic image (02, a large image scaled down) scores 313, which is close to the warning line of 250. Images with very little text, or very large fonts, can score lower even when sharp.
- **Motion blur or blur in only part of the image** is averaged over the whole picture, so it can be missed.
- **Heavy compression noise** can look like sharpness and hide some blur.
- **It does not check skew, text size, or whether the image contains text at all.** A sharp photo of a landscape will pass.
- Resolution is judged by pixels only. DPI metadata is ignored.

## Project structure

```
app.py                 Streamlit interface
quality_checker.py     The three checks and the thresholds
make_samples.py        Generates the 12 test images
evaluate.py            Compares verdicts with sample_images/expected.csv
sample_images/         12 test images and expected.csv
tests/                 Pytest tests
requirements.txt       Python dependencies
```

## Tech used

Python, Streamlit, Pillow, NumPy, Pytest, Git and GitHub, deployed on Streamlit Community Cloud.
