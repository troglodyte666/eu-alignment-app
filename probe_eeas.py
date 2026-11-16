"""Temporary diagnostic: print what EEAS serves to this machine."""
import re
import sys
import urllib.error
import urllib.request

from eu_alignment_scraper import HEADERS

BASE = "https://www.eeas.europa.eu"


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status, r.geturl(), body
    except urllib.error.HTTPError as e:
        return e.code, url, e.read().decode("utf-8", errors="replace")[:600]
    except Exception as e:
        return None, url, f"{type(e).__name__}: {e}"


def show(label, url, head=600):
    status, final, body = get(url)
    print(f"\n=== {label}\n    {url}\n    status={status} final={final} len={len(body)}")
    print("    head:", re.sub(r"\s+", " ", body[:head]))
    return status, body


status, body = show("sitemap root", f"{BASE}/sitemap.xml", 1500)
if status == 403:
    print("BLOCKED on this runner")
    sys.exit(0)
print("    <sitemap> count:", body.count("<sitemap>"), " <url> count:", body.count("<url>"))
for loc in re.findall(r"<loc>([^<]+)</loc>", body)[:60]:
    print("    loc:", loc)

for pg in (1, 2, 3):
    status, body = show(f"sitemap page {pg}", f"{BASE}/sitemap.xml?page={pg}", 400)
    entries = re.findall(r"<url>(.*?)</url>", body, re.DOTALL)
    locs = [(re.search(r"<loc>([^<]+)", e), re.search(r"<lastmod>([^<]+)", e)) for e in entries]
    locs = [(l.group(1) if l else "", m.group(1) if m else "") for l, m in locs]
    ny = [x for x in locs if "/delegations/un-new-york/" in x[0]]
    print(f"    urls={len(locs)} un-new-york={len(ny)} max_lastmod={max((m for _, m in locs), default='')}")
    for l, m in locs[:5] + locs[-5:]:
        print("     ", m, l)
    for l, m in sorted(ny, key=lambda x: x[1])[-15:]:
        print("      NY", m, l)

status, body = show("robots", f"{BASE}/robots.txt", 200)
for line in body.splitlines():
    if "sitemap" in line.lower():
        print("   ", line)

candidates = [
    f"{BASE}/delegations/un-new-york_en",
    f"{BASE}/delegations/un-new-york_en?s=63",
    f"{BASE}/delegations/un-new-york/press-material_en",
    f"{BASE}/filter-page/press-material_en",
    f"{BASE}/delegations/un-new-york/rss_en",
    f"{BASE}/delegations/un-new-york/sitemap.xml",
]
for url in candidates:
    status, body = show("candidate", url, 200)
    hrefs = list(dict.fromkeys(re.findall(r'href="([^"]+)"', body)))
    ny = [h for h in hrefs if "/delegations/un-new-york/" in h]
    nav = [h for h in hrefs if re.search(r"filter|press-material|page=|rss|feed|\?s=|search", h)]
    print(f"    hrefs={len(hrefs)} un-new-york={len(ny)}")
    for h in ny[:40]:
        print("      NY", h)
    for h in nav[:40]:
        print("      NAV", h)
