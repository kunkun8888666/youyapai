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

# Search for all .yaml and .txt URLs
yaml_urls = re.findall(r'https?://[^\s<>"\']+\.ya?ml[^\s<>"\']*', html)
txt_urls = re.findall(r'https?://[^\s<>"\']+\.txt[^\s<>"\']*', html)

print(f'YAML URLs: {yaml_urls}')
print(f'TXT URLs: {txt_urls}')

# Search for node.clash-rs.com URLs
node_urls = re.findall(r'https://node\.clash-rs\.com/[^\s<>"\']+', html)
print(f'\nnode.clash-rs.com URLs: {node_urls}')

# Search for uploads URLs
upload_urls = re.findall(r'https?://[^\s<>"\']+/uploads/[^\s<>"\']+', html)
print(f'\nuploads URLs: {upload_urls}')

# Look for subscription URLs with date pattern
date_pattern = re.findall(r'https?://[^\s<>"\']+20260626[^\s<>"\']*', html)
print(f'\nURLs with 20260626: {date_pattern}')
