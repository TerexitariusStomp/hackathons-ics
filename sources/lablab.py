"""lablab.build — /ai-hackathons index carries a JSON-LD ItemList of events;
each event page carries a schema.org Event JSON-LD with startDate/endDate."""

import re

from sources.common import fetch_text, fetch_all, jsonld_events, iso_date

INDEX = "https://lablab.build/ai-hackathons"
URL_RE = re.compile(r'"url":"(https://lablab\.build/ai-hackathons/[^"]+)"')
MAX_DETAILS = 80


def _index_urls() -> list[str]:
    html = fetch_text(INDEX)
    return sorted(set(URL_RE.findall(html)))[:MAX_DETAILS]


def _detail(url: str) -> list[dict]:
    try:
        html = fetch_text(url)
    except Exception:
        return []
    for e in jsonld_events(html):
        name = e.get("name") or ""
        if not name:
            continue
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        return [{
            "slug": f"lablab-{slug}",
            "title": name,
            "url": e.get("url") or url,
            "start": iso_date(e.get("startDate")),
            "end": iso_date(e.get("endDate")),
            "reg_deadline": None,
            "sub_deadline": None,
            "location": "Online",
            "prize": None,
            "tags": ["ai"],
            "source": "lablab",
        }]
    return []


def fetch() -> list[dict]:
    urls = _index_urls()
    return fetch_all(urls, _detail, workers=8)
