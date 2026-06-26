#!/usr/bin/env python3
import urllib.request
import ssl
import re

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

req = urllib.request.Request('https://clash-rs.com/free-node/', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    html = resp.read().decode('utf-8', errors='replace')

print('=== First 2000 chars ===')
print(html[:2000])
print('\n=== Full HTML length ===')
print(f'Total length: {len(html)}')

print('\n=== Looking for links ===')
links = re.findall(r'href="([^"]*)"', html)
print(f'Total links found: {len(links)}')
for href in links[:20]:
    print(f'  {href}')

print('\n=== Looking for /free-node/ in links ===')
for href in links:
    if '/free-node/' in href:
        print(f'  Found: {href}')
