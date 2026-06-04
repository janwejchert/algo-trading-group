"""Temporary diagnostic: locate the NAAIM exposure-index data source.

The exposure-index page renders its numbers with a JavaScript members-widget
(members.naaim.org / GrowthZone), so there is no .xlsx to scrape. This script
fetches the page and the widget scripts it loads and prints any data endpoints,
JSON URLs, iframes, and widget/account ids it can find, plus short snippets of
the widget JS around any fetch/ajax/url calls.

Run from the repo root:  python diag_naaim.py
Then paste the entire output back.
"""
import re

import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
PAGE = "https://www.naaim.org/programs/naaim-exposure-index/"
HINT = re.compile(
    r"(members\.naaim|gzcontent|publicwidget|exposure|indicator|/api|\.json|"
    r"growthzone|widget|chart|sentiment|/data)",
    re.I,
)


def fetch(url):
    return requests.get(url, timeout=30, headers=HEADERS)


def urls_in(text):
    return sorted(set(re.findall(r"https?://[^\s'\"<>()]+", text)))


print(f"== page {PAGE}")
page = fetch(PAGE)
html = page.text
print(f"   status={page.status_code} length={len(html)} chars\n")

scripts = re.findall(r"<script[^>]+src=[\"']([^\"']+)[\"']", html, re.I)
iframes = re.findall(r"<iframe[^>]+src=[\"']([^\"']+)[\"']", html, re.I)
print(f"== {len(scripts)} <script src> total; iframes: {iframes or 'none'}")
for s in scripts:
    if HINT.search(s):
        print("   script:", s)

page_urls = [u for u in urls_in(html) if HINT.search(u)]
print(f"\n== {len(page_urls)} data-hint URLs in page HTML:")
for u in page_urls:
    print("   ", u)

print("\n== inline config hints (widget/org/account/api ids):")
hints = re.findall(
    r"(?:data-[\w-]*|organization|account|widget|org|api)[\w-]*[\"']?\s*[:=]\s*[\"']?[\w-]{4,}",
    html,
    re.I,
)
for h in sorted(set(hints))[:30]:
    print("   ", h.strip())

candidates = [s for s in scripts if s.startswith("http") and HINT.search(s)]
for extra in ["https://members.naaim.org/GZContent/PublicWidgets/Subscriptions.js"]:
    if extra not in candidates:
        candidates.append(extra)

print(f"\n== scanning {len(candidates)} widget scripts for endpoints:")
for c in candidates:
    try:
        j = fetch(c)
        text = j.text
        inside = [u for u in urls_in(text) if HINT.search(u)]
        paths = sorted(set(re.findall(
            r"[\"'](/[A-Za-z0-9_./-]*(?:api|data|widget|exposure|indicator)"
            r"[A-Za-z0-9_./-]*)[\"']",
            text,
            re.I,
        )))
        print(f"\n   -- {c}  (status {j.status_code}, {len(text)} chars)")
        for u in inside[:30]:
            print("       url :", u)
        for p in paths[:30]:
            print("       path:", p)
        for m in re.finditer(r"(fetch\(|\.ajax\(|\.get\(|xhr|open\(\s*[\"']GET)", text, re.I):
            lo, hi = max(0, m.start() - 60), min(len(text), m.start() + 120)
            snippet = text[lo:hi].replace("\n", " ")
            print("       call:", snippet)
    except Exception as e:
        print(f"   -- {c}  ERROR {e}")

print("\n== done. Paste everything above back.")
