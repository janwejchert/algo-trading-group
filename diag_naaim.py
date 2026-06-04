"""Temporary diagnostic: dump the NAAIM exposure-index display section.

Prints the raw HTML around the "Average exposure" content block, any
image/iframe/canvas/embed near it, any URLs mentioning exposure/chart, and any
inline <script> or inline numeric data arrays tied to that section, so we can
see how the current value and the historical series are rendered.

Run from the repo root:  python diag_naaim.py
Paste the entire output back.
"""
import re

import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
PAGE = "https://www.naaim.org/programs/naaim-exposure-index/"

text = requests.get(PAGE, timeout=30, headers=HEADERS).text
print(f"== page length={len(text)}")

i = text.find("Average exposure")
if i == -1:
    i = text.rfind("NAAIM Exposure Index")
print(f"\n== raw HTML around exposure section (idx={i}), 400 before / 6000 after ==")
print(text[max(0, i - 400): i + 6000])

print("\n== img/iframe/canvas/embed tags with data hints ==")
for tag in re.findall(r"<(?:img|iframe|canvas|embed|object|svg)[^>]*>", text, re.I):
    if re.search(r"(exposure|chart|graph|members\.naaim|growthzone|/uploads/)", tag, re.I):
        print("   ", tag[:320])

print("\n== URLs mentioning exposure/chart/graph ==")
for u in sorted(set(re.findall(r"https?://[^\s\"'<>()]+", text))):
    if re.search(r"(exposure|chart|graph)", u, re.I):
        print("   ", u)

print("\n== inline <script> blocks mentioning exposure or the section ids ==")
for blk in re.findall(r"<script\b[^>]*>(.*?)</script>", text, re.S | re.I):
    if re.search(r"(exposure|brxe-uyrwco|brxe-wchvig|brxe-yyntpa|brxe-wbfput)", blk, re.I):
        print("   ----- script block (first 2500 chars) -----")
        print(blk.strip()[:2500])

print("\n== long numeric arrays on the page (possible embedded series) ==")
for arr in re.findall(r"\[(?:\s*-?\d+(?:\.\d+)?\s*,){6,}\s*-?\d+(?:\.\d+)?\s*\]", text):
    print("   ", arr[:300])

print("\n== done. Paste everything above.")
