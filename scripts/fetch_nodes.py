#!/usr/bin/env python3
"""Fetch, parse, merge, and deduplicate free node subscriptions.

Fetches the latest 3 days of free node subscription content from:
  - yoyapai.com
  - clash-rs.com
  - clashbest.github.io

Parses the nodes, deduplicates by (server, port, protocol), and outputs
standard-format config files for Clash/Mihomo and V2Ray clients.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import re
import ssl
import sys
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

import yaml


BEIJING_TZ = dt.timezone(dt.timedelta(hours=8))
RETENTION_DAYS = 3

YOYAPAI_LIST_URL = "https://yoyapai.com/category/mianfeijiedian"
YOYAPAI_CLASH_LABEL = "<strong>Clash（Clash Meta/Mihomo）免费节点订阅地址：</strong>"
YOYAPAI_V2RAY_LABEL = "<strong>V2Ray免费节点订阅地址：</strong>"

CLASHRS_LIST_URL = "https://clash-rs.com/free-node/"
CLASHRS_CLASH_LABEL = "clash订阅链接"
CLASHRS_V2RAY_LABEL = "v2ray订阅链接"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.check_hostname = False
SSL_CONTEXT.verify_mode = ssl.CERT_NONE


@dataclass(frozen=True)
class Candidate:
    title: str
    url: str
    date: dt.date


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href_stack: list[str | None] = []
        self._current_href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href")
        self._href_stack.append(self._current_href)
        self._current_href = href
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current_href is None:
            return
        text = " ".join("".join(self._text).split())
        if text:
            self.links.append((text, self._current_href))
        self._current_href = self._href_stack.pop() if self._href_stack else None
        self._text = []


def log(message: str) -> None:
    print(f"[fetch] {message}", flush=True)


def fetch_text(url: str, timeout: int = 30, retries: int = 3, referer: str = "") -> str | None:
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    for attempt in range(1, retries + 1):
        try:
            request = Request(url, headers=headers)
            with urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
                raw = response.read()
                return decode_html(raw, response.headers.get_content_charset())
        except (HTTPError, URLError, TimeoutError, ConnectionResetError, OSError) as exc:
            log(f"fetch failed ({attempt}/{retries}) {url}: {exc}")
            if attempt < retries:
                time.sleep(attempt * 2)
    return None


def decode_html(raw: bytes, header_charset: str | None) -> str:
    head = raw[:4096].decode("ascii", errors="ignore")
    meta_match = re.search(r"charset=[\"']?([\w.-]+)", head, flags=re.IGNORECASE)
    candidates = dedupe_strings([
        meta_match.group(1) if meta_match else None,
        header_charset,
        "utf-8-sig",
        "utf-8",
        "gb18030",
        "gbk",
        "big5",
    ])

    decoded: list[tuple[int, str]] = []

    for charset in candidates:
        try:
            text = raw.decode(charset)
        except (LookupError, UnicodeDecodeError):
            continue
        decoded.append((decode_quality(text), text))

    if decoded:
        return max(decoded, key=lambda item: item[1])[1]

    return raw.decode("utf-8", errors="replace")


def dedupe_strings(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        normalized = value.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


def decode_quality(text: str) -> int:
    score = 0
    score -= text.count("\ufffd") * 100
    score -= sum(text.count(marker) for marker in ["銆", "涓", "绔", "鏂", "犳", "婧", "€"]) * 8
    score += sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
    score += text.count("://") * 5
    score += text.count("proxies:") * 20
    score += text.count("vless://") * 20
    return score


def unwrap_redirect_url(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    target = query.get("target")
    if target and target[0]:
        return unquote(target[0])
    return url


def normalize_url(url: str, base_url: str) -> str:
    return unwrap_redirect_url(urljoin(base_url, html.unescape(url)))


def parse_title_date(title: str, today: dt.date) -> dt.date | None:
    match = re.search(r"(?:(20\d{2})\D+)?(\d{1,2})月(\d{1,2})日\s*$", title)
    if not match:
        return None
    year = int(match.group(1) or today.year)
    month = int(match.group(2))
    day = int(match.group(3))
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def parse_url_date(url: str, today: dt.date) -> dt.date | None:
    match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", url)
    if not match:
        match = re.search(r"/(\d{4})/(\d{2})/(\d{2})", url)
    if not match:
        return None
    try:
        return dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def append_cache_buster(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["_t"] = [str(int(time.time()))]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))


# ---------------------------------------------------------------------------
# YoYaPai source
# ---------------------------------------------------------------------------

def fetch_yoyapai(today: dt.date, target_dates: list[dt.date]) -> tuple[list[str], list[str]]:
    log("fetching from yoyapai.com ...")
    clash_contents: list[str] = []
    v2ray_contents: list[str] = []

    list_html = fetch_text(append_cache_buster(YOYAPAI_LIST_URL), referer="https://yoyapai.com/")
    if not list_html:
        log("yoyapai list page unavailable; trying fallback subscription url patterns")
        for target_date in target_dates:
            clash_url, v2ray_url = yoyapai_fallback_subscription_urls(target_date)
            cc = fetch_text(clash_url, referer="https://yoyapai.com/")
            vc = fetch_text(v2ray_url, referer="https://yoyapai.com/")
            if cc:
                clash_contents.append(cc)
            if vc:
                v2ray_contents.append(vc)
        return clash_contents, v2ray_contents

    child_pages = yoyapai_find_child_pages(list_html, today)
    for target_date in target_dates:
        candidate = child_pages.get(target_date)
        fallback_clash_url, fallback_v2ray_url = yoyapai_fallback_subscription_urls(target_date)

        if not candidate:
            log(f"yoyapai: child page not found for {target_date.isoformat()}; using fallback")
            cc = fetch_text(fallback_clash_url, referer="https://yoyapai.com/")
            vc = fetch_text(fallback_v2ray_url, referer="https://yoyapai.com/")
            if cc:
                clash_contents.append(cc)
            if vc:
                v2ray_contents.append(vc)
            continue

        log(f"yoyapai: child page for {target_date.isoformat()}: {candidate.url}")
        page_html = fetch_text(candidate.url, referer="https://yoyapai.com/")
        if not page_html:
            log(f"yoyapai: child page unavailable for {target_date.isoformat()}; using fallback")
            cc = fetch_text(fallback_clash_url, referer="https://yoyapai.com/")
            vc = fetch_text(fallback_v2ray_url, referer="https://yoyapai.com/")
            if cc:
                clash_contents.append(cc)
            if vc:
                v2ray_contents.append(vc)
            continue

        clash_url = extract_after_label(page_html, YOYAPAI_CLASH_LABEL, candidate.url) or fallback_clash_url
        v2ray_url = extract_after_label(page_html, YOYAPAI_V2RAY_LABEL, candidate.url) or fallback_v2ray_url
        log(f"yoyapai: Clash sub for {target_date.isoformat()}: {clash_url}")
        log(f"yoyapai: V2Ray sub for {target_date.isoformat()}: {v2ray_url}")

        cc = fetch_text(clash_url, referer="https://yoyapai.com/")
        vc = fetch_text(v2ray_url, referer="https://yoyapai.com/")
        if cc:
            clash_contents.append(cc)
        if vc:
            v2ray_contents.append(vc)

    return clash_contents, v2ray_contents


def yoyapai_find_child_pages(list_html: str, today: dt.date) -> dict[dt.date, Candidate]:
    parser = LinkParser()
    parser.feed(list_html)

    candidates_by_date: dict[dt.date, Candidate] = {}
    for title, href in parser.links:
        if "免费节点分享" not in title or "Clash/V2Ray/SSR" not in title:
            continue
        page_date = parse_title_date(title, today)
        if not page_date:
            continue
        candidate = Candidate(title=title, url=normalize_url(href, YOYAPAI_LIST_URL), date=page_date)
        existing = candidates_by_date.get(page_date)
        if not existing or candidate.url > existing.url:
            candidates_by_date[page_date] = candidate

    return candidates_by_date


def yoyapai_fallback_subscription_urls(target_date: dt.date) -> tuple[str, str]:
    date_path = target_date.strftime("%Y/%m")
    day = target_date.strftime("%d")
    base = f"https://freenode.yoyapai.com/{date_path}/{day}-yoyapai.com"
    return (
        f"{base}-clashvpn-mianfeijiedian.yaml",
        f"{base}-ssrv2ray-vpn-mianfeijiedian.txt",
    )


# ---------------------------------------------------------------------------
# Clash-RS source
# ---------------------------------------------------------------------------

def fetch_clashrs(today: dt.date, target_dates: list[dt.date]) -> tuple[list[str], list[str]]:
    log("fetching from clash-rs.com ...")
    clash_contents: list[str] = []
    v2ray_contents: list[str] = []

    list_html = fetch_text(CLASHRS_LIST_URL, referer="https://clash-rs.com/")
    if not list_html:
        log("clash-rs: list page unavailable")
        return clash_contents, v2ray_contents

    log(f"clash-rs: list page length: {len(list_html)}")
    article_links = clashrs_find_articles(list_html, target_dates)
    for target_date in target_dates:
        article_url = article_links.get(target_date)
        if not article_url:
            log(f"clash-rs: no article found for {target_date.isoformat()}")
            continue

        log(f"clash-rs: article for {target_date.isoformat()}: {article_url}")
        page_html = fetch_text(article_url, referer="https://clash-rs.com/")
        if not page_html:
            log(f"clash-rs: article unavailable for {target_date.isoformat()}")
            continue

        clash_urls = clashrs_extract_sub_urls(page_html, CLASHRS_CLASH_LABEL, article_url)
        v2ray_urls = clashrs_extract_sub_urls(page_html, CLASHRS_V2RAY_LABEL, article_url)

        log(f"clash-rs: found {len(clash_urls)} Clash URLs, {len(v2ray_urls)} V2Ray URLs for {target_date.isoformat()}")

        for url in clash_urls:
            cc = fetch_text(url, referer="https://clash-rs.com/")
            if cc:
                clash_contents.append(cc)

        for url in v2ray_urls:
            vc = fetch_text(url, referer="https://clash-rs.com/")
            if vc:
                v2ray_contents.append(vc)

    return clash_contents, v2ray_contents


def clashrs_find_articles(list_html: str, target_dates: list[dt.date]) -> dict[dt.date, str]:
    links = re.findall(r'href="([^"]*)"', list_html)
    articles: dict[dt.date, str] = {}
    for href in links:
        if "/free-node/" not in href:
            continue
        if href == "/free-node/" or href == CLASHRS_LIST_URL:
            continue
        full_url = normalize_url(href, CLASHRS_LIST_URL)
        page_date = parse_url_date(full_url, target_dates[0])
        if page_date and page_date in target_dates and page_date not in articles:
            articles[page_date] = full_url
    log(f"clash-rs: found {len(articles)} articles")
    return articles


def clashrs_extract_sub_urls(page_html: str, label: str, base_url: str) -> list[str]:
    result = []
    url_pattern = r'https?://[^\s<>"\']+'
    all_urls = re.findall(url_pattern, page_html)

    if "clash" in label.lower():
        for url in all_urls:
            if url.endswith(".yaml") or url.endswith(".yml"):
                if "node.clash-rs.com" in url and "clash-rs.com/go/" not in url:
                    result.append(url)
    elif "v2ray" in label.lower():
        for url in all_urls:
            if url.endswith(".txt"):
                if "node.clash-rs.com" in url and "clash-rs.com/go/" not in url:
                    result.append(url)

    return result


# ---------------------------------------------------------------------------
# Shared extraction helpers
# ---------------------------------------------------------------------------

def extract_after_label(page_html: str, label: str, base_url: str) -> str | None:
    label_pos = page_html.find(label)
    if label_pos < 0:
        label_pos = html.unescape(page_html).find(html.unescape(label))
        searchable = html.unescape(page_html)
    else:
        searchable = page_html

    if label_pos < 0:
        return None

    tail = searchable[label_pos + len(html.unescape(label)) :]
    next_strong = tail.find("<strong>")
    if next_strong >= 0:
        tail = tail[:next_strong]
    tail = html.unescape(tail)

    href_match = re.search(r'href=["\']([^"\']+)["\']', tail, flags=re.IGNORECASE)
    if href_match:
        return normalize_url(href_match.group(1), base_url)

    url_match = re.search(r"https?://[^\s<>'\"]+", tail)
    if url_match:
        return normalize_url(url_match.group(0), base_url)

    return None


# ---------------------------------------------------------------------------
# Clash parsing and config generation
# ---------------------------------------------------------------------------

def parse_clash_proxies(content: str) -> list[dict]:
    content = re.sub(r'!<\w+>\s*', '', content)
    try:
        config = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        log(f"failed to parse Clash YAML: {exc}")
        return []
    if not isinstance(config, dict):
        return []
    proxies = config.get("proxies")
    if not isinstance(proxies, list):
        return []
    return [p for p in proxies if isinstance(p, dict)]


def dedup_clash_proxies(all_proxies: list[list[dict]]) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    result: list[dict] = []
    for proxies in all_proxies:
        for proxy in proxies:
            server = str(proxy.get("server", "")).strip().lower()
            port = str(proxy.get("port", "")).strip()
            ptype = str(proxy.get("type", "")).strip().lower()
            if not server or not port or not ptype:
                continue
            key = (server, port, ptype)
            if key in seen:
                continue
            seen.add(key)
            result.append(proxy)
    return result


def ensure_unique_names(proxies: list[dict]) -> list[dict]:
    used: set[str] = set()
    for proxy in proxies:
        name = proxy.get("name", "")
        if not name:
            name = f"{proxy.get('type', 'unknown')}-{proxy.get('server', 'unknown')}:{proxy.get('port', '0')}"
        if name not in used:
            used.add(name)
            continue
        suffix = 2
        while f"{name} ({suffix})" in used:
            suffix += 1
        new_name = f"{name} ({suffix})"
        proxy["name"] = new_name
        used.add(new_name)
    return proxies


def generate_clash_config(proxies: list[dict], sources: list[str]) -> str:
    proxy_names = [p["name"] for p in proxies]

    proxy_groups: list[dict] = []
    if proxy_names:
        proxy_groups.append(
            {
                "name": "PROXY",
                "type": "select",
                "proxies": ["AUTO"] + proxy_names + ["DIRECT", "REJECT"],
            }
        )
        proxy_groups.append(
            {
                "name": "AUTO",
                "type": "url-test",
                "url": "http://www.gstatic.com/generate_204",
                "interval": 300,
                "tolerance": 50,
                "proxies": list(proxy_names),
            }
        )

    config = {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "proxies": proxies,
        "proxy-groups": proxy_groups,
        "rules": ["GEOIP,CN,DIRECT", "MATCH,PROXY"],
    }

    header = (
        "# Auto-generated by fetch_nodes.py\n"
        f"# Sources: {', '.join(sources)}\n"
        f"# Total nodes: {len(proxies)}\n"
        "# This is a complete Clash/Mihomo config. Import directly into Clash/Mihomo.\n"
    )

    body = yaml.dump(
        config,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=10000,
    )
    return header + "\n" + body


# ---------------------------------------------------------------------------
# V2Ray/SSR/SS URL parsing and subscription generation
# ---------------------------------------------------------------------------

def _b64_decode(text: str) -> str:
    text = text.strip()
    padding = 4 - len(text) % 4
    if padding != 4:
        text += "=" * padding
    for decoder in (base64.b64decode, base64.urlsafe_b64decode):
        try:
            return decoder(text).decode("utf-8", errors="replace")
        except Exception:
            continue
    raise ValueError("base64 decode failed")


def _parse_standard_url(url: str) -> tuple[str, str, str] | None:
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port
    if not host or not port:
        return None
    return (parsed.scheme, host.lower(), str(port))


def _parse_vmess_url(url: str) -> tuple[str, str, str] | None:
    payload = url[len("vmess://") :]
    try:
        decoded = _b64_decode(payload)
        info = json.loads(decoded)
    except (ValueError, json.JSONDecodeError) as exc:
        log(f"failed to parse vmess URL: {exc}")
        return None
    server = info.get("add") or info.get("address") or info.get("host")
    port = info.get("port")
    if not server or not port:
        return None
    return ("vmess", str(server).lower(), str(port))


def _parse_ss_url(url: str) -> tuple[str, str, str] | None:
    parsed = urlparse(url)
    if parsed.hostname and parsed.port:
        return ("ss", parsed.hostname.lower(), str(parsed.port))

    payload = url[len("ss://") :]
    if "#" in payload:
        payload = payload[: payload.index("#")]
    try:
        decoded = _b64_decode(payload)
    except ValueError as exc:
        log(f"failed to parse ss URL: {exc}")
        return None

    if "@" not in decoded:
        return None
    _, host_port = decoded.rsplit("@", 1)
    if ":" not in host_port:
        return None
    host, port = host_port.rsplit(":", 1)
    if not host or not port:
        return None
    return ("ss", host.lower(), port)


def _parse_ssr_url(url: str) -> tuple[str, str, str] | None:
    payload = url[len("ssr://") :]
    try:
        decoded = _b64_decode(payload)
    except ValueError as exc:
        log(f"failed to parse ssr URL: {exc}")
        return None
    main = decoded.split("/?")[0]
    parts = main.split(":")
    if len(parts) < 2:
        return None
    host, port = parts[0], parts[1]
    if not host or not port:
        return None
    return ("ssr", host.lower(), port)


def parse_v2ray_url(url: str) -> tuple[str, str, str] | None:
    url = url.strip()
    if url.startswith("vless://") or url.startswith("trojan://"):
        return _parse_standard_url(url)
    if url.startswith("vmess://"):
        return _parse_vmess_url(url)
    if url.startswith("ss://"):
        return _parse_ss_url(url)
    if url.startswith("ssr://"):
        return _parse_ssr_url(url)
    return None


def parse_v2ray_urls(content: str) -> list[str]:
    urls: list[str] = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        if parse_v2ray_url(line):
            urls.append(line)
    return urls


def dedup_v2ray_urls(all_urls: list[list[str]]) -> list[str]:
    seen: set[tuple[str, str, str]] = set()
    result: list[str] = []
    for urls in all_urls:
        for url in urls:
            key = parse_v2ray_url(url)
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            result.append(url)
    return result


def generate_v2ray_subscription(urls: list[str], sources: list[str]) -> str:
    header = (
        "# Auto-generated by fetch_nodes.py\n"
        f"# Sources: {', '.join(sources)}\n"
        f"# Total nodes: {len(urls)}\n"
        "# This is a V2Ray subscription file. Import into V2RayN/V2RayNG/Shadowrocket.\n"
    )
    if urls:
        return header + "\n" + "\n".join(urls) + "\n"
    return header + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", help="repository root path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    today = dt.datetime.now(BEIJING_TZ).date()
    target_dates = [today - dt.timedelta(days=offset) for offset in range(RETENTION_DAYS)]
    log(f"fetch date: {today.isoformat()} (Asia/Shanghai)")
    log(f"target dates: {', '.join(d.isoformat() for d in target_dates)}")

    all_clash_contents: list[str] = []
    all_v2ray_contents: list[str] = []
    active_sources: list[str] = []

    # Source 1: yoyapai.com
    yoyapai_clash, yoyapai_v2ray = fetch_yoyapai(today, target_dates)
    if yoyapai_clash or yoyapai_v2ray:
        all_clash_contents.extend(yoyapai_clash)
        all_v2ray_contents.extend(yoyapai_v2ray)
        active_sources.append("yoyapai.com")
        log(f"yoyapai: {len(yoyapai_clash)} Clash, {len(yoyapai_v2ray)} V2Ray contents")

    # Source 2: clash-rs.com
    clashrs_clash, clashrs_v2ray = fetch_clashrs(today, target_dates)
    if clashrs_clash or clashrs_v2ray:
        all_clash_contents.extend(clashrs_clash)
        all_v2ray_contents.extend(clashrs_v2ray)
        active_sources.append("clash-rs.com")
        log(f"clash-rs: {len(clashrs_clash)} Clash, {len(clashrs_v2ray)} V2Ray contents")

    if not active_sources:
        log("no subscription content fetched from any source")
        return 1

    log(f"active sources: {', '.join(active_sources)}")

    # Parse nodes
    all_clash_proxies = [parse_clash_proxies(c) for c in all_clash_contents]
    all_v2ray_urls = [parse_v2ray_urls(c) for c in all_v2ray_contents]
    raw_clash = sum(len(p) for p in all_clash_proxies)
    raw_v2ray = sum(len(u) for u in all_v2ray_urls)
    log(f"parsed Clash proxies: {raw_clash} (before dedup)")
    log(f"parsed V2Ray URLs: {raw_v2ray} (before dedup)")

    # Deduplicate
    clash_proxies = dedup_clash_proxies(all_clash_proxies)
    clash_proxies = ensure_unique_names(clash_proxies)
    v2ray_urls = dedup_v2ray_urls(all_v2ray_urls)
    log(f"Clash proxies after dedup: {len(clash_proxies)}")
    log(f"V2Ray URLs after dedup: {len(v2ray_urls)}")

    # Generate standard-format config files
    clash_output = generate_clash_config(clash_proxies, active_sources)
    v2ray_output = generate_v2ray_subscription(v2ray_urls, active_sources)

    clash_path = repo_root / "output" / "clash.yaml"
    v2ray_path = repo_root / "output" / "v2ray.yaml"
    stats_path = repo_root / "output" / "stats.json"

    clash_path.write_text(clash_output, encoding="utf-8")
    v2ray_path.write_text(v2ray_output, encoding="utf-8")

    stats_data = {
        "clash_nodes": len(clash_proxies),
        "v2ray_nodes": len(v2ray_urls),
        "update_date": today.isoformat(),
        "sources": active_sources,
    }
    stats_path.write_text(json.dumps(stats_data, ensure_ascii=False, indent=2), encoding="utf-8")

    log(f"wrote {clash_path.name} ({len(clash_proxies)} proxies)")
    log(f"wrote {v2ray_path.name} ({len(v2ray_urls)} urls)")
    log(f"wrote {stats_path.name} with stats")
    return 0


if __name__ == "__main__":
    sys.exit(main())
