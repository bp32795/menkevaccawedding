"""Debug scraper output for a given URL."""
import requests
from bs4 import BeautifulSoup

url = "https://www.williams-sonoma.com/products/chefs-choice-1520-electric-knife-sharpener/?sku=8031873"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

resp = requests.get(url, headers=headers, timeout=15)
print(f"Status: {resp.status_code}")
print(f"Content length: {len(resp.text)}")

soup = BeautifulSoup(resp.content, "html.parser")

# OG tags
print("\n--- OG Tags ---")
for tag in soup.find_all("meta", attrs={"property": True}):
    prop = tag.get("property", "")
    if "og:" in prop or "product:" in prop:
        print(f"  {prop} = {tag.get('content', '')[:150]}")

# Title
title_tag = soup.find("title")
print(f"\nTitle tag: {title_tag.get_text(strip=True)[:120] if title_tag else 'NONE'}")

# H1
h1 = soup.find("h1")
print(f"H1: {h1.get_text(strip=True)[:120] if h1 else 'NONE'}")

# JSON-LD
ld_scripts = soup.find_all("script", type="application/ld+json")
print(f"\nJSON-LD scripts: {len(ld_scripts)}")
for i, s in enumerate(ld_scripts):
    print(f"  [{i}]: {str(s.string)[:300] if s.string else 'empty'}")

# Body text sample
body = soup.find("body")
body_text = body.get_text() if body else ""
print(f"\nBody text length: {len(body_text)}")
print(f"Body sample: {body_text[:500]}")
