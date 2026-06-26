#!/usr/bin/env python3
import urllib.request
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        return resp.read().decode('utf-8', errors='replace')

html = fetch('https://clash-rs.com/free-node/2026-6-26-free-clash.htm')

# Check labels
clash_label = 'clash订阅链接'
v2ray_label = 'v2ray订阅链接'

clash_pos = html.lower().find(clash_label.lower())
v2ray_pos = html.lower().find(v2ray_label.lower())

print(f'clash_label position: {clash_pos}')
print(f'v2ray_label position: {v2ray_pos}')

if clash_pos >= 0:
    tail = html[clash_pos:clash_pos+2000]
    print(f'\nAfter clash label ({len(tail)} chars):')
    print(tail[:500])
    
    # Find URLs
    url_pattern = r'https?://[^\s<>"\']+'
    urls = re.findall(url_pattern, tail)
    print(f'\nURLs found after clash label: {urls}')
    
    # Check for node.clash-rs.com URLs
    node_urls = re.findall(r'https://node\.clash-rs\.com/[^\s<>"\']+', tail)
    print(f'node.clash-rs.com URLs: {node_urls}')

if v2ray_pos >= 0:
    tail = html[v2ray_pos:v2ray_pos+2000]
    print(f'\nAfter v2ray label ({len(tail)} chars):')
    print(tail[:500])
    
    url_pattern = r'https?://[^\s<>"\']+'
    urls = re.findall(url_pattern, tail)
    print(f'\nURLs found after v2ray label: {urls}')
