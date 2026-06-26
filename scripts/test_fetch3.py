#!/usr/bin/env python3
import urllib.request
import re

def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')

# Test clash-rs.com article - get subscription URLs after labels
print("=== clash-rs.com article ===")
html = fetch('https://clash-rs.com/free-node/2026-6-26-free-clash.htm')

# Find URLs after "clash订阅链接" and "v2ray订阅链接"
clash_label_pos = html.find('clash订阅链接')
if clash_label_pos > 0:
    tail = html[clash_label_pos:clash_label_pos+500]
    urls = re.findall(r'https?://[^\s<>"\']+', tail)
    print(f"After 'clash订阅链接': {urls[:5]}")

v2ray_label_pos = html.find('v2ray订阅链接')
if v2ray_label_pos > 0:
    tail = html[v2ray_label_pos:v2ray_label_pos+500]
    urls = re.findall(r'https?://[^\s<>"\']+', tail)
    print(f"After 'v2ray订阅链接': {urls[:5]}")

# Find node.clash-rs.com URLs
node_urls = re.findall(r'https://node\.clash-rs\.com/[^\s<>"\']+', html)
print(f"\nnode.clash-rs.com URLs ({len(node_urls)}):")
for u in node_urls:
    print(f"  {u}")

# Test clashbest.github.io article
print("\n=== clashbest.github.io article ===")
html2 = fetch('https://clashbest.github.io/free-nodes/2026-6-25-node-share-links.htm')
# Find all URLs
url_pattern = r'https?://[^\s<>"\']+'
urls2 = re.findall(url_pattern, html2)
sub_urls2 = [u for u in urls2 if any(k in u.lower() for k in ['clash', 'v2ray', 'sub', 'yaml', 'txt', 'freenode', 'node', 'vpn', 'subscribe'])]
print(f"Subscription-like URLs ({len(sub_urls2)}):")
for u in sub_urls2[:20]:
    print(f"  {u}")

# Find strong labels
strongs2 = re.findall(r'<strong[^>]*>(.*?)</strong>', html2, re.DOTALL)
print(f"\nStrong labels ({len(strongs2)}):")
for s in strongs2[:20]:
    clean = re.sub(r'<[^>]+>', '', s).strip()
    if clean:
        print(f"  {clean[:100]}")

# Find labels with 订阅
sub_labels = re.findall(r'[^<]{0,30}订阅[^<]{0,30}', html2)
print(f"\n订阅 labels ({len(sub_labels)}):")
for s in sub_labels[:10]:
    print(f"  {s.strip()[:100]}")
