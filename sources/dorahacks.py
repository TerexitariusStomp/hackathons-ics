"""DoraHacks — index page gives featured /hackathon/<slug>/ links; each
detail page carries a schema.org Event JSON-LD block."""

import re

from sources.common import fetch_text, fetch_all, jsonld_events, iso_date, abs_url

INDEX = "https://dorahacks.io/hackathon"
BASE = "https://dorahacks.io"
SLUG_RE = re.compile(r'"(/hackathon/[a-z0-9-]+/)"')


def _detail(slug_path: str) -> list[dict]:
    url = abs_url(BASE, slug_path)
    try:
        html = fetch_text(url)
    except Exception:
        return []
    events = [e for e in jsonld_events(html)
              if "hackathon" in (e.get("url") or url).lower()
              or True]
    out = []
    for e in events[:1]:  # first Event block is the hackathon itself
        name = e.get("name") or ""
        if not name:
            continue
        slug = slug_path.strip("/").split("/")[-1]
        out.append({
            "slug": f"dorahacks-{slug}",
            "title": name,
            "url": e.get("url") or url,
            "start": iso_date(e.get("startDate")),
            "end": iso_date(e.get("endDate")),
            "reg_deadline": None,
            "sub_deadline": None,
            "location": "Online",
            "prize": None,
            "tags": ["web3"],
            "source": "dorahacks",
        })
    return out


def fetch() -> list[dict]:
    try:
        html = fetch_text(INDEX)
    except Exception:
        return []
    slugs = sorted(set(SLUG_RE.findall(html)))
    return fetch_all(slugs, _detail, workers=4)
