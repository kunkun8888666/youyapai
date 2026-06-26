#!/usr/bin/env python3
import urllib.request
import re

def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')

# Test clash-rs.com article page
print("=== clash-rs.com article ===")
html = fetch('https://clash-rs.com/free-node/2026-6-26-free-clash.htm')
# Find all URLs
url_pattern = r'https?://[^\s<>"\']+'
urls = re.findall(url_pattern, html)
sub_urls = [u for u in urls if any(k in u.lower() for k in ['clash', 'v2ray', 'sub', 'yaml', 'txt', 'freenode', 'node', 'vpn'])]
print(f"Subscription-like URLs ({len(sub_urls)}):")
for u in sub_urls[:20]:
    print(f"  {u}")

# Also find strong labels
strong_pattern = r'<strong[^>]*>(.*?)</strong>'
strongs = re.findall(strong_pattern, html, re.DOTALL)
print(f"\nStrong labels ({len(strongs)}):")
for s in strongs[:20]:
    clean = re.sub(r'<[^>]+>', '', s).strip()
    if clean:
        print(f"  {clean[:100]}")

# Test clashbest.github.io
print("\n=== clashbest.github.io ===")
try:
    html2 = fetch('https://clashbest.github.io/free-nodes/')
    url_pattern = r'https?://[^\s<>"\']+'
    urls2 = re.findall(url_pattern, html2)
    sub_urls2 = [u for u in urls2 if any(k in u.lower() for k in ['clash', 'v2ray', 'sub', 'yaml', 'txt', 'freenode', 'node', 'vpn'])]
    print(f"Subscription-like URLs ({len(sub_urls2)}):")
    for u in sub_urls2[:20]:
        print(f"  {u}")
    
    # Find article links
    links2 = re.findall(r'href="([^"]+)"', html2)
    article_links = [l for l in links2 if '/free-nodes/' in l and l != '/free-nodes/']
    print(f"\nArticle links ({len(article_links)}):")
    for l in article_links[:10]:
        print(f"  {l}")
    
    # Get first article
    if article_links:
        first = article_links[0]
        if not first.startswith('http'):
            first = 'https://clashbest.github.io' + first
        print(f"\nFirst article: {first}")
        article2 = fetch(first)
        urls3 = re.findall(url_pattern, article2)
        sub_urls3 = [u for u in urls3 if any(k in u.lower() for k in ['clash', 'v2ray', 'sub', 'yaml', 'txt', 'freenode', 'node', 'vpn'])]
        print(f"Subscription-like URLs in article ({len(sub_urls3)}):")
        for u in sub_urls3[:20]:
            print(f"  {u}")
        
        strongs2 = re.findall(r'<strong[^>]*>(.*?)</strong>', article2, re.DOTALL)
        print(f"\nStrong labels ({len(strongs2)}):")
        for s in strongs2[:20]:
            clean = re.sub(r'<[^>]+>', '', s).strip()
            if clean:
                print(f"  {clean[:100]}")
except Exception as e:
    print(f"Error: {e}")
