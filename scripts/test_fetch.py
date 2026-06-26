#!/usr/bin/env python3
import urllib.request
import re

def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')

# Test clash-rs.com
print("=== clash-rs.com ===")
html = fetch('https://clash-rs.com/free-node/')
links = re.findall(r'href="([^"]+)"', html)
for link in links:
    if '/free-node/' in link and link != '/free-node/':
        print(link)

# Get first article
article_links = [l for l in links if '/free-node/' in l and l != '/free-node/']
if article_links:
    print("\n=== First article ===")
    first = article_links[0]
    if not first.startswith('http'):
        first = 'https://clash-rs.com' + first
    print(f"URL: {first}")
    article = fetch(first)
    # Find subscription URLs
    clash_matches = re.findall(r'Clash[^<]*订阅[^<]*', article)
    v2ray_matches = re.findall(r'V2Ray[^<]*订阅[^<]*', article)
    print(f"Clash labels: {clash_matches[:3]}")
    print(f"V2Ray labels: {v2ray_matches[:3]}")
    
    # Find URLs after labels
    url_pattern = r'https?://[^\s<>"\']+'
    urls = re.findall(url_pattern, article)
    sub_urls = [u for u in urls if any(k in u.lower() for k in ['clash', 'v2ray', 'sub', 'yaml', 'txt', 'freenode', 'node'])]
    print(f"Subscription-like URLs: {sub_urls[:10]}")

# Test clashbest.github.io
print("\n=== clashbest.github.io ===")
try:
    html2 = fetch('https://clashbest.github.io/')
    links2 = re.findall(r'href="([^"]+)"', html2)
    for link in links2[:20]:
        print(link)
except Exception as e:
    print(f"Error: {e}")
