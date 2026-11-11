"""Curated hackathons.json — authoritative seed for events we care about."""

import re

from sources import ROOT, load_curated


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s or "event"


def fetch() -> list[dict]:
    out = []
    for h in load_curated():
        out.append({
            "slug": h.get("slug") or _slug(h["title"]),
            "title": h["title"],
            "url": h.get("url", ""),
            "start": h.get("start"),
            "end": h.get("end"),
            "reg_deadline": h.get("reg_deadline") or h.get("registration_deadline"),
            "sub_deadline": h.get("sub_deadline") or h.get("submission_deadline"),
            "location": h.get("location", "Online"),
            "prize": h.get("prize"),
            "tags": h.get("tags", []),
            "source": "manual",
        })
    return out
