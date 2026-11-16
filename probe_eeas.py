"""Temporary diagnostic: print what EEAS serves to this machine."""
import re
import time
import urllib.error
import urllib.request

import eu_alignment_scraper as s

BASE = "https://www.eeas.europa.eu"


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=s.HEADERS)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", errors="replace")
            return r.status, body, time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:600], time.time() - t0
    except Exception as e:
        return None, f"{type(e).__name__}: {e}", time.time() - t0


print("##### A. sitemap pages exactly as production fetches them (1.5s apart, timeout 15)")
known = set(open("scraped_results.csv", encoding="utf-8").read().split(","))
new_from_sitemap = {}
for pg in range(1, 26):
    status, body, dt = get(f"{BASE}/sitemap.xml?page={pg}", timeout=15)
    entries = re.findall(r"<url>(.*?)</url>", body, re.DOTALL)
    ny_new = []
    for e in entries:
        loc = re.search(r"<loc>([^<]+)", e)
        mod = re.search(r"<lastmod>([^<]+)", e)
        if not loc or "/delegations/un-new-york/" not in loc.group(1) or not loc.group(1).endswith("_en"):
            continue
        if mod and mod.group(1)[:10] >= "2026-10-15" and loc.group(1) not in known:
            ny_new.append((mod.group(1)[:10], loc.group(1)))
    print(f"  page {pg:2d}: status={status} len={len(body)} urls={len(entries)} "
          f"new_ny={len(ny_new)} {dt:.1f}s head={body[:60]!r}" if not entries else
          f"  page {pg:2d}: status={status} len={len(body)} urls={len(entries)} new_ny={len(ny_new)} {dt:.1f}s")
    for m, l in ny_new:
        new_from_sitemap[l] = m
    time.sleep(1.5)
print(f"  NEW un-new-york URLs (lastmod >= 2026-10-15, not in CSV): {len(new_from_sitemap)}")
for l, m in sorted(new_from_sitemap.items(), key=lambda x: x[1]):
    print("   ", m, l)

print("\n##### B. press-material listing for UN New York")
listing = f"{BASE}/filter-page/press-material_en?f%5B0%5D=press_site%3AUN%20New%20York"
seen_listing = []
for suffix in ("", "&page=1", "&page=2"):
    status, body, dt = get(listing + suffix)
    hrefs = list(dict.fromkeys(re.findall(r'href="([^"]+)"', body)))
    ny = [h for h in hrefs if "/delegations/un-new-york/" in h and "global-gateway" not in h]
    pager = [h for h in hrefs if "page=" in h]
    print(f"\n  {suffix or '(first page)'}: status={status} len={len(body)} hrefs={len(hrefs)} ny={len(ny)} {dt:.1f}s")
    for h in ny:
        full = (BASE + h if h.startswith("/") else h).split("?")[0]
        print("     NY", full, "" if full in known else "<-- NOT IN CSV")
    for h in pager[:8]:
        print("     PAGER", h)
    seen_listing += ny
    if suffix == "" and ny:
        i = body.find(ny[0])
        print("     CONTEXT:", re.sub(r"\s+", " ", body[max(0, i - 700): i + 500]))

print("\n##### C. one statement page")
if seen_listing:
    u = seen_listing[0]
    u = u if u.startswith("http") else BASE + u
    status, body, dt = get(u.split("?")[0])
    print(f"  {u}\n  status={status} len={len(body)} date={s.parse_date(body) if status == 200 else None} "
          f"title={s.extract_title(body)[:90] if status == 200 else None!r}")
