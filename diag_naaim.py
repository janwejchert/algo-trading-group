"""Temporary diagnostic: extract the NAAIM exposure-index widget config.

The exposure-index numbers come from a GrowthZone members-widget configured
inline (an ApiUrl plus data-script-id widgets), not a downloadable file. This
prints the full ApiUrl, the GrowthZone/members URLs, the data-script-id widgets
with context, the inline script blocks that configure the widget, and the HTML
around any 'exposure' mention, so the live data API can be reconstructed.

Run from the repo root:  python diag_naaim.py
Paste the entire output back.
"""
import html as ihtml
import re

import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
PAGE = "https://www.naaim.org/programs/naaim-exposure-index/"

page = requests.get(PAGE, timeout=30, headers=HEADERS)
text = page.text
print(f"== page status={page.status_code} length={len(text)}\n")

print("== ApiUrl / GrowthZone / members URLs:")
for m in sorted(set(re.findall(r'"?[Aa]pi_?[Uu]rl"?\s*[:=]\s*"([^"]+)"', text))):
    print("   ApiUrl :", ihtml.unescape(m))
for m in sorted(set(re.findall(r"https?://[^\s\"'<>]*growthzone[^\s\"'<>]*", text, re.I))):
    print("   gz-url :", ihtml.unescape(m))
for m in sorted(set(re.findall(r"https?://members\.naaim\.org[^\s\"'<>]*", text, re.I))):
    print("   members:", ihtml.unescape(m))

print("\n== data-script-id widgets (with context):")
for m in re.finditer(r'data-script-id="([^"]+)"', text):
    lo, hi = max(0, m.start() - 130), min(len(text), m.end() + 130)
    print(f"   id={m.group(1)}  ::  {text[lo:hi].strip()[:280]!r}")

print("\n== inline <script> blocks mentioning ApiUrl/growthzone/widget/exposure:")
for blk in re.findall(r"<script\b[^>]*>(.*?)</script>", text, re.S | re.I):
    if re.search(r"(apiurl|growthzone|publicwidget|exposure|scriptid|widget)", blk, re.I):
        print("   ----- script block (first 1500 chars) -----")
        print(blk.strip()[:1500])

print("\n== 'exposure' contexts in HTML:")
for m in list(re.finditer(r"exposure", text, re.I))[:6]:
    lo, hi = max(0, m.start() - 100), min(len(text), m.start() + 170)
    print("   ...", text[lo:hi].replace("\n", " ").strip())

print("\n== done. Paste everything above.")
