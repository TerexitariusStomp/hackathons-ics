"""ethstars.xyz — /events is client-rendered; data loads from their backend.
Best-effort: parse any JSON-LD Event blocks or RSC-embedded entries; returns
[] when nothing parseable is present so the build never breaks."""

import re

from sources.common import fetch_text, jsonld_events, iso_date

INDEX = "https://ethstars.xyz/events"


def fetch() -> list[dict]:
    try:
        html = fetch_text(INDEX)
    except Exception:
        return []
    out = []
    for e in jsonld_events(html):
        name = e.get("name") or ""
        url = e.get("url") or INDEX
        if not name:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]
        out.append({
            "slug": f"ethstars-{slug}",
            "title": name,
            "url": url if url.startswith("http") else f"https://ethstars.xyz{url}",
            "start": iso_date(e.get("startDate")),
            "end": iso_date(e.get("endDate")),
            "reg_deadline": None,
            "sub_deadline": None,
            "location": "Online",
            "prize": None,
            "tags": ["ethereum"],
            "source": "ethstars",
        })
    return out
