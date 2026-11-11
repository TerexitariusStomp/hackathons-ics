"""Encode Club — public Supabase REST table `Encode Programmes`.

The anon key is embedded in encodeclub.com's public JS bundle (public by
design, read-only). Column names containing spaces must be %22-quoted.
"""

import os

import httpx

from sources.common import iso_date

SUPABASE = "https://bwrubpasqybdchurwjhs.supabase.co"
ANON_KEY = os.environ.get(
    "ENCODE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ3cnVicGFzcXliZGNodXJ3amhzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDA5Mzg0MjksImV4cCI6MjA1NjUxNDQyOX0.5E5e62NEjISDKFj8zP15mj-Ttg3FXxYQtGqNu1j_KmU",
)
TABLE = "Encode%20Programmes"
SELECT = (
    '"programme name","start date","end_date","registration_deadline",'
    '"project_creation_deadline",slug,location,timezone,type'
)


def fetch() -> list[dict]:
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}
    params = {
        "select": SELECT,
        "order": '"start date".desc',
        "limit": "200",
    }
    r = httpx.get(f"{SUPABASE}/rest/v1/{TABLE}", params=params,
                  headers=headers, timeout=20, follow_redirects=True)
    r.raise_for_status()
    out = []
    for p in r.json():
        ptype = (p.get("type") or "").lower()
        if "hackathon" not in ptype:
            continue
        slug = p.get("slug") or ""
        name = p.get("programme name") or ""
        if not name:
            continue
        out.append({
            "slug": f"encode-{slug or name}".lower().replace(" ", "-")[:80],
            "title": f"Encode: {name}",
            "url": f"https://www.encodeclub.com/programmes/{slug}" if slug
                   else "https://www.encodeclub.com/programmes",
            "start": iso_date(p.get("start date")),
            "end": iso_date(p.get("end_date")),
            "reg_deadline": iso_date(p.get("registration_deadline")),
            "sub_deadline": iso_date(p.get("project_creation_deadline")),
            "location": p.get("location") or "Online",
            "prize": None,
            "tags": ["web3", "education"],
            "source": "encodeclub",
        })
    return out
