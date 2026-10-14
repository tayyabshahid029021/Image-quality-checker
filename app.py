from pathlib import Path

import streamlit as st
from PIL import Image

from quality_checker import FAIL, PASS, THRESHOLDS, WARNING, analyze

SAMPLES = Path(__file__).parent / "sample_images"

st.set_page_config(page_title="Image Quality Checker", page_icon="🔍", layout="centered")

st.markdown(
    """
    <style>
    .block-container { max-width: 880px; padding-top: 2.2rem; }
    .badge { display: inline-block; padding: 0.3rem 0.9rem; border-radius: 999px;
             font-weight: 700; font-size: 1rem; }
    .badge-PASS { background: #DCFCE7; color: #166534; }
    .badge-WARNING { background: #FEF3C7; color: #92400E; }
    .badge-FAIL { background: #FEE2E2; color: #991B1B; }
    .reason { margin: 0.35rem 0 0 0; color: #334155; }
    .metric-row { display: flex; justify-content: space-between; padding: 0.4rem 0;
                  border-bottom: 1px solid #E2E8F0; font-size: 0.95rem; }
    .metric-row span:last-child { color: #475569; }
    </style>
    """,
    unsafe_allow_html=True,
)

ICON = {PASS: "✅", WARNING: "⚠️", FAIL: "❌"}
VERDICT_TEXT = {
    PASS: "Good to go. This image should work for text extraction.",
    WARNING: "Usable, but results may be poor. Consider a better image.",
    FAIL: "Too poor for text extraction. Please retake or rescan the image.",
}


def show_result(name, img):
    report = analyze(img)
    left, right = st.columns([1, 1.2], gap="large")
    with left:
        st.image(img, caption=name, width="stretch")
    with right:
        st.markdown(
            f'<span class="badge badge-{report.overall}">{ICON[report.overall]} {report.overall}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<p class="reason">{VERDICT_TEXT[report.overall]}</p>', unsafe_allow_html=True)
        for reason in report.reasons:
            st.markdown(f"- {reason}")
        st.write("")
        rows = ""
        units = {"Blur": "sharpness score", "Brightness": "average brightness (0 to 255)", "Resolution": "shorter side in px"}
        for c in report.checks:
            rows += (
                f'<div class="metric-row"><span>{ICON[c.status]} {c.name}</span>'
                f'<span>{c.value:.0f} <small>{units[c.name]}</small></span></div>'
            )
        st.markdown(rows, unsafe_allow_html=True)


st.title("Image Quality Checker")
st.write("Check if an image is good enough for text extraction (OCR) before you run it. "
         "It tests blur, brightness and resolution, and tells you why an image fails.")

files = st.file_uploader(
    "Upload one or more images",
    type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
    accept_multiple_files=True,
)

sample_names = sorted(p.name for p in SAMPLES.glob("*") if p.suffix.lower() in {".jpg", ".png"})
sample = None
if not files and sample_names:
    sample = st.selectbox("Or try a sample image", ["None"] + sample_names)

if files:
    for f in files:
        try:
            img = Image.open(f)
            img.load()
        except Exception:
            st.error(f"{f.name} could not be opened. Please upload a valid image file.")
            continue
        show_result(f.name, img)
        st.divider()
elif sample and sample != "None":
    show_result(sample, Image.open(SAMPLES / sample))

with st.expander("How the checks work"):
    t = THRESHOLDS
    st.markdown(
        f"""
**Blur.** The image is scaled to at most 1000 px wide, lightly denoised and contrast-stretched. Then the variance of the Laplacian (an edge detector) is measured. Below **{t['blur_fail']:.0f}** fails, below **{t['blur_warn']:.0f}** warns.

**Brightness.** Average grey level and contrast range. Average below **{t['dark_fail']:.0f}** fails and below **{t['dark_warn']:.0f}** warns. Washed-out or low contrast images are flagged too. Images with a wide contrast range (like dark mode screenshots) are not penalised for being dark.

**Resolution.** Shorter side below **{t['res_fail']} px** fails and below **{t['res_warn']} px** warns.

The overall result is the worst of the three checks. Thresholds were tuned on 12 test images (see the README).
"""
    )
