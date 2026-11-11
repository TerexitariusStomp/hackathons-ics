"""0xarchit/hackathon-api aggregator (MIT) — covers Devfolio, Unstop,
Devpost, MLH, HackerEarth, Hack2Skill, ReSkill, WhereUElevate, Devnovate.

The Go server is started by the workflow (or manually) and exposed at
AGGREGATOR_URL (default http://localhost:8080/api/v1/hackathons).
"""

import os

from sources.common import fetch_json, iso_date

URL = os.environ.get("AGGREGATOR_URL", "http://localhost:8080/api/v1/hackathons")


def fetch() -> list[dict]:
    data = fetch_json(URL)
    items = data if isinstance(data, list) else data.get("hackathons", data.get("data", []))
    out = []
    for h in items:
        platform = (h.get("platform") or "aggregator").lower().replace(" ", "-")
        out.append({
            "slug": f"{platform}-{(h.get('id') or h['title'])}".lower().replace(" ", "-")[:80],
            "title": h.get("title", "Untitled hackathon"),
            "url": h.get("url", ""),
            "start": iso_date(h.get("start_date")),
            "end": iso_date(h.get("end_date")),
            "reg_deadline": iso_date(h.get("registration_end")),
            "sub_deadline": None,
            "location": h.get("location") or h.get("mode") or "Online",
            "prize": h.get("prize_pool"),
            "tags": h.get("tags") or [],
            "source": platform,
        })
    return out
