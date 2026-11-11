#!/usr/bin/env python3
"""Build hackathons.ics (+ per-source feeds) from all registered sources.

Usage:
    python3 hackathons_ics.py build [--quiet]

Pipeline: fetch all sources -> normalize -> dedupe -> diff state ->
emit ICS (merged + feeds/<source>.ics) -> update .hackathons_state.json
and CHANGELOG.md.
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from icalendar import Calendar, Event
from rapidfuzz import fuzz

from sources import all_sources
from sources.common import parse_dt

ROOT = Path(__file__).resolve().parent
ICS_PATH = ROOT / "hackathons.ics"
FEEDS_DIR = ROOT / "feeds"
STATE_PATH = ROOT / ".hackathons_state.json"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"

CAL_NAME = "Hackathon Megaplan"
PRODID = "-//hackathons-ics//hackathon-megaplan//EN"
NEW_DAYS = 7
PRUNE_DAYS = 30
DEDUP_THRESHOLD = 85
SOURCE_PRIORITY = ["manual", "aggregator_api", "devpost", "dorahacks",
                   "encodeclub", "lablab", "ethglobal", "mlh", "devfolio",
                   "colosseum", "ethstars"]


def log(msg, quiet=False):
    if not quiet:
        print(msg, file=sys.stderr)


# ---------- fetch / normalize ----------

def fetch_all_events(quiet=False):
    events, health = [], {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(mod.fetch): name for name, mod in all_sources()}
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                res = fut.result()
                events.extend(res or [])
                health[name] = {"count": len(res or []), "ok": True}
                log(f"[source] {name}: {len(res or [])} events", quiet)
            except Exception as e:
                health[name] = {"count": 0, "ok": False, "error": str(e)[:200]}
                log(f"[source] {name}: FAILED {e}", quiet)
    return events, health


def norm_title(t: str) -> str:
    t = re.sub(r"^(encode|ethglobal|dorahacks|lablab)[:\-–]?\s*", "", t.lower())
    t = re.sub(r"\b(hackathon|buidlathon|buildathon|hackathon \d{4}|\d{4})\b", " ", t)
    return re.sub(r"[^a-z0-9 ]", " ", t)


def _date_only(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def event_sort_key(e):
    return (e.get("start") or "9999", e.get("title", ""))


def latest_dt(e):
    cands = [parse_dt(e.get(k)) for k in
             ("end", "sub_deadline", "reg_deadline", "start")]
    cands = [c for c in cands if c]
    return max(cands) if cands else None


def dedupe(events):
    """Merge cross-source duplicates: similar title + nearby dates."""
    events = sorted(events, key=lambda e: SOURCE_PRIORITY.index(e["source"])
                    if e["source"] in SOURCE_PRIORITY else 99)
    kept = []
    for e in events:
        dup = False
        for k in kept:
            if norm_title(e["title"]) == norm_title(k["title"]):
                dup = True
                break
            if fuzz.token_set_ratio(norm_title(e["title"]),
                                    norm_title(k["title"])) >= DEDUP_THRESHOLD:
                ed, kd = _date_only(e.get("start")), _date_only(k.get("start"))
                if ed and kd and abs((ed - kd).days) <= 10:
                    dup = True
                    break
                if not ed or not kd:
                    dup = True
                    break
        if not dup:
            kept.append(e)
    return kept


def prune(events):
    cutoff = datetime.now(timezone.utc) - timedelta(days=PRUNE_DAYS)
    return [e for e in events
            if (latest_dt(e) or datetime.max.replace(tzinfo=timezone.utc)) > cutoff]


# ---------- state / changelog ----------

def load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"events": {}, "health": {}}


def diff_state(events, state):
    """Return (added, removed, changed) slug lists."""
    old = state.get("events", {})
    new_slugs = {e["slug"] for e in events}
    added = sorted(new_slugs - set(old))
    removed = sorted(set(old) - new_slugs)
    changed = []
    by_slug = {e["slug"]: e for e in events}
    for s in new_slugs & set(old):
        o = old[s]
        n = by_slug[s]
        if (o.get("start"), o.get("end")) != (n.get("start"), n.get("end")):
            changed.append(s)
    return added, removed, changed


def update_state(events, health, state):
    now = datetime.now(timezone.utc).date().isoformat()
    old = state.get("events", {})
    new_events = {}
    for e in events:
        prev = old.get(e["slug"], {})
        new_events[e["slug"]] = {
            "first_seen": prev.get("first_seen", now),
            "last_seen": now,
            "title": e["title"],
            "source": e["source"],
            "start": e.get("start"),
            "end": e.get("end"),
        }
    state["events"] = new_events
    state["health"] = health
    return state


def write_changelog(added, removed, changed, health, quiet=False):
    today = date.today().isoformat()
    lines = [f"## {today}", ""]
    if added:
        lines.append(f"### Added ({len(added)})")
        lines += [f"- {s}" for s in added[:50]]
        lines.append("")
    if removed:
        lines.append(f"### Removed ({len(removed)})")
        lines += [f"- {s}" for s in removed[:50]]
        lines.append("")
    if changed:
        lines.append(f"### Rescheduled ({len(changed)})")
        lines += [f"- {s}" for s in changed[:50]]
        lines.append("")
    bad = [n for n, h in health.items() if not h.get("ok")]
    zero = [n for n, h in health.items() if h.get("ok") and h.get("count") == 0]
    if bad or zero:
        lines.append("### Source health")
        lines += [f"- FAIL {n}: {health[n].get('error', '?')}" for n in bad]
        lines += [f"- EMPTY {n} (0 events)" for n in zero]
        lines.append("")
    if len(lines) <= 2:
        return  # nothing worth recording
    block = "\n".join(lines) + "\n"
    if CHANGELOG_PATH.exists():
        old = CHANGELOG_PATH.read_text()
        CHANGELOG_PATH.write_text(block + "\n" + old)
    else:
        CHANGELOG_PATH.write_text("# Hackathons ICS — change log\n\n" + block)
    log(f"[changelog] +{len(added)} -{len(removed)} ~{len(changed)}", quiet)


# ---------- ICS ----------

def esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace(";", "\\;") \
        .replace(",", "\\,").replace("\n", "\\n")


def dt_param(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def is_all_day(s: str | None) -> bool:
    return bool(s) and len(s) == 10


def make_vevent(uid, summary, description, url, location,
                dtstart, dtend=None, all_day=False):
    ev = Event()
    ev.add("uid", uid)
    ev.add("summary", esc(summary))
    if description:
        ev.add("description", esc(description))
    if url:
        ev.add("url", url)
    if location:
        ev.add("location", esc(location))
    if all_day:
        d1 = _date_only(dtstart)
        d2 = _date_only(dtend) or d1
        ev.add("dtstart", d1)
        ev.add("dtend", d2 + timedelta(days=1))
    else:
        s = parse_dt(dtstart)
        e = parse_dt(dtend) if dtend else s + timedelta(hours=1)
        if e <= s:
            e = s + timedelta(hours=1)
        ev.add("dtstart", s)
        ev.add("dtend", e)
    return ev


def build_calendar(events, cal_name=CAL_NAME, state=None):
    cal = Calendar()
    cal.add("prodid", PRODID)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", cal_name)
    for e in sorted(events, key=event_sort_key):
        slug = e["slug"]
        title = e["title"]
        prefix = "[NEW] " if state and is_new(e, state) else ""
        disp = f"{prefix}{title}"
        desc_bits = [e.get("prize") and f"Prize: {e['prize']}",
                     e.get("tags") and "Tags: " + ", ".join(e["tags"]),
                     f"Source: {e['source']}"]
        description = " · ".join(b for b in desc_bits if b)
        # build window (all-day)
        if e.get("start") or e.get("end"):
            cal.add_component(make_vevent(
                f"hack-{slug}-window@hackathons-ics",
                f"{disp} — build window",
                description, e.get("url"), e.get("location"),
                e.get("start") or e.get("end"),
                e.get("end") or e.get("start"),
                all_day=is_all_day(e.get("start") or e.get("end"))))
        # deadline reminders
        for key, label in (("reg_deadline", "registration"),
                           ("sub_deadline", "submissions")):
            if e.get(key):
                cal.add_component(make_vevent(
                    f"hack-{slug}-{key.split('_')[0]}@hackathons-ics",
                    f"{prefix}DEADLINE: {title} {label}",
                    description, e.get("url"), e.get("location"),
                    e[key], all_day=is_all_day(e[key])))
    return cal


def is_new(e, state):
    fs = state.get("events", {}).get(e["slug"], {}).get("first_seen")
    if not fs:
        return True
    try:
        return (date.today() - date.fromisoformat(fs)).days < NEW_DAYS
    except ValueError:
        return True


def emit(events, state, quiet=False):
    FEEDS_DIR.mkdir(exist_ok=True)
    # merged feed
    cal = build_calendar(events, state=state)
    ICS_PATH.write_bytes(cal.to_ical())
    # per-source feeds
    sources = sorted({e["source"] for e in events})
    for src in sources:
        sub = [e for e in events if e["source"] == src]
        (FEEDS_DIR / f"{src}.ics").write_bytes(
            build_calendar(sub, f"{CAL_NAME} — {src}", state=state).to_ical())
    # prune stale per-source files
    for f in FEEDS_DIR.glob("*.ics"):
        if f.stem not in sources:
            f.unlink()
    n_events = sum(len(cal.walk("VEVENT")) for cal in [cal])
    log(f"[emit] {ICS_PATH.name}: {len(events)} hackathons "
        f"({len(sources)} sources), {n_events} VEVENTs", quiet)


# ---------- main ----------

def build(quiet=False):
    events, health = fetch_all_events(quiet)
    log(f"[fetch] {len(events)} raw events", quiet)
    events = prune(dedupe([e for e in events if e.get("title") and
                           (e.get("start") or e.get("end"))]))
    log(f"[norm]  {len(events)} after dedupe+prune", quiet)
    state = load_state()
    added, removed, changed = diff_state(events, state)
    state = update_state(events, health, state)
    STATE_PATH.write_text(json.dumps(state, indent=1, sort_keys=True))
    write_changelog(added, removed, changed, health, quiet)
    emit(events, state, quiet)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="build",
                    choices=["build"])
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    return build(args.quiet)


if __name__ == "__main__":
    sys.exit(main())
