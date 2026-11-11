"""ETHGlobal — /events is server-rendered. Each card is
<a href="/events/slug"> containing: a date block (month name + day <span>s),
an <h2> name, a location span, a type badge, and an "Apply to Attend" CTA.
We keep cards whose type badge mentions a hackathon."""

import re
from datetime import date, timedelta

from selectolax.lexbor import LexborHTMLParser as HTMLParser

from sources.common import fetch_text

INDEX = "https://ethglobal.com/events"
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
HACK_TYPES = ("hackathon", "buidlathon")
TYPE_RE = re.compile(
    r"(Conference|Hackathon|Buidlathon|Meetup|Workshop|Event|Other)"
    r"\s+Apply to Attend\s*$")
LOC_RE = re.compile(r"^(.+?,\s*[A-Z][A-Za-z ]+|Online|Virtual)$")


def _ymd(mon_name: str, day: int) -> str | None:
    month = MONTHS.get(mon_name[:3].lower())
    if not month:
        return None
    today = date.today()
    try:
        d = date(today.year, month, day)
    except ValueError:
        return None
    if d < today - timedelta(days=60):
        d = date(today.year + 1, month, day)
    return d.isoformat()


def _card_date(tree) -> tuple[str | None, str | None]:
    month_el = tree.css_first(".uppercase.text-xs")
    if not month_el:
        return None, None
    mon = (month_el.text() or "").strip()
    # day numbers are <span> digits inside the same date block
    days = []
    block = month_el.parent
    if block:
        for sp in block.css("span"):
            t = (sp.text() or "").strip()
            if t.isdigit():
                days.append(int(t))
    if not days:
        return None, None
    return _ymd(mon, days[0]), (_ymd(mon, days[-1]) if len(days) > 1 else None)


def fetch() -> list[dict]:
    try:
        html = fetch_text(INDEX)
    except Exception:
        return []
    tree = HTMLParser(html)
    out = []
    for a in tree.css('a[href^="/events/"]'):
        href = a.attributes.get("href", "")
        slug = href.rstrip("/").rsplit("/", 1)[-1]
        if not slug or slug in {"agents", "aggregation-day"}:
            continue
        h2 = a.css_first("h2")
        name = (h2.text() if h2 else "").strip()
        if not name:
            continue
        # type badge: last badge text before the Apply CTA
        cta = None
        for div in a.css("div"):
            t = (div.text() or "").strip()
            if t == "Apply to Attend":
                cta = div
                break
        etype = ""
        if cta is not None and cta.parent:
            badges = cta.parent.css("span")
            for sp in reversed(badges):
                t = (sp.text() or "").strip()
                if t and t != "Apply to Attend":
                    etype = t
                    break
        if not any(t in etype.lower() for t in HACK_TYPES):
            continue
        # location: span text matching "City, Country" or Online
        location = "Online"
        for sp in a.css("span"):
            t = re.sub(r"\s+", " ", (sp.text() or "")).strip()
            if LOC_RE.match(t) and len(t) < 60:
                location = t
                break
        start, end = _card_date(a)
        out.append({
            "slug": f"ethglobal-{slug}",
            "title": f"ETHGlobal: {name}",
            "url": f"https://ethglobal.com{href}",
            "start": start,
            "end": end,
            "reg_deadline": None,
            "sub_deadline": None,
            "location": location,
            "prize": None,
            "tags": ["web3"],
            "source": "ethglobal",
        })
    return out
