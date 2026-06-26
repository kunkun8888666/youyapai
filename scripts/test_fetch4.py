#!/usr/bin/env python3
import urllib.request
import re
import ssl
import datetime as dt

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

today = dt.date(2026, 6, 26)
target_dates = [today - dt.timedelta(days=i) for i in range(3)]
print(f"Target dates: {target_dates}")

for href in links:
    if "/free-node/" not in href or href == "/free-node/":
        continue
    print(f"  Link: {href}")
    match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", href)
    if match:
        d = dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        print(f"    Parsed date: {d}, in targets: {d in target_dates}")
