"""Shared helpers for hackathon source adapters."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from dateutil import parser as dateutil_parser

UA = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

TIMEOUT = 20.0


def fetch_text(url: str, **kw) -> str:
    r = httpx.get(url, headers=UA, timeout=TIMEOUT, follow_redirects=True, **kw)
    r.raise_for_status()
    return r.text


def fetch_json(url: str, **kw):
    r = httpx.get(url, headers={**UA, "Accept": "application/json"},
                  timeout=TIMEOUT, follow_redirects=True, **kw)
    r.raise_for_status()
    return r.json()


def jsonld_events(html: str) -> list[dict]:
    """Extract all schema.org Event objects from application/ld+json blocks."""
    out = []
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.S,
    ):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                t = node.get("@type")
                types = t if isinstance(t, list) else [t]
                if "Event" in types:
                    out.append(node)
                stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
            elif isinstance(node, list):
                stack.extend(node)
    return out


def parse_dt(value) -> datetime | None:
    """Parse ISO-ish date/datetime to aware UTC datetime; None on failure."""
    if not value or not isinstance(value, str):
        return None
    try:
        dt = dateutil_parser.isoparse(value)
    except (ValueError, OverflowError):
        try:
            dt = dateutil_parser.parse(value, fuzzy=True)
        except (ValueError, OverflowError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def iso_date(value) -> str | None:
    """YYYY-MM-DD for all-day fields, or full ISO for timed."""
    dt = parse_dt(value)
    if dt is None:
        return None
    if dt.hour == dt.minute == dt.second == 0:
        return dt.date().isoformat()
    return dt.isoformat()


def fetch_all(urls: list[str], worker, workers: int = 8) -> list:
    """Fetch urls concurrently, returning only successful worker results."""
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(worker, urls):
            if res:
                results.extend(res if isinstance(res, list) else [res])
    return results


def abs_url(base: str, path: str) -> str:
    return urljoin(base, path)
