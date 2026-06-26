#!/usr/bin/env python3
import urllib.request
import re
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        return resp.read().decode('utf-8', errors='replace')

html = fetch('https://clash-rs.com/free-node/')
links = re.findall(r'href="([^"]*)"', html)

for href in links:
    if "/free-node/" not in href:
        continue
    # Check the filter condition
    is_list_page = href == "/free-node/" or href == "https://clash-rs.com/free-node/" or href.endswith("/free-node/")
    print(f"  Link: {href!r}  is_list_page: {is_list_page}")
