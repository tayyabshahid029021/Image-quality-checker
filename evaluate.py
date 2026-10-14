"""Run the checker on every image in sample_images/ and compare with expected.csv.

Usage:  python evaluate.py
Prints one row per image (metrics, verdict, expected) and exits with code 1
if any verdict differs from what was expected.
"""
import csv
import sys
from pathlib import Path

from PIL import Image

from quality_checker import analyze

FOLDER = Path(__file__).parent / "sample_images"


def load_expected():
    with open(FOLDER / "expected.csv", newline="") as f:
        return {row["filename"]: row["expected"] for row in csv.DictReader(f)}


def main():
    expected = load_expected()
    mismatches = 0
    print(f"{'image':30s} {'blur':>8s} {'bright':>7s} {'short px':>9s}  {'verdict':8s} {'expected':8s}")
    for name, want in expected.items():
        report = analyze(Image.open(FOLDER / name))
        blur, bright, res = (c.value for c in report.checks)
        ok = report.overall == want
        mismatches += not ok
        print(f"{name:30s} {blur:8.1f} {bright:7.1f} {res:9.0f}  {report.overall:8s} {want:8s} {'ok' if ok else 'MISMATCH'}")
    print(f"\n{len(expected) - mismatches}/{len(expected)} verdicts match the expected result.")
    sys.exit(1 if mismatches else 0)


if __name__ == "__main__":
    main()
