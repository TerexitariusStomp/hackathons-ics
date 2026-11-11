# hackathons-ics

Self-updating [iCalendar](https://icalendar.org) feed of hackathons,
aggregated from Devpost, DoraHacks, Encode Club, lablab.build, ETHGlobal,
MLH, Devfolio, Unstop, HackerEarth and more — merged, deduplicated, with
deadline reminder events.

Built on the [`civilmonkey-ics`](https://github.com/TerexitariusStomp/civilmonkey-ics)
pattern: a Python build script fetches all sources, normalizes events, and
commits the generated `.ics` files. A GitHub Action rebuilds the feed
**4× per day**; GitHub Pages serves it.

## Subscribe

| Feed | URL |
|---|---|
| Merged (all sources) | `https://terexitariusstomp.github.io/hackathons-ics/hackathons.ics` |
| Per-source | `…/feeds/<source>.ics` (e.g. `devpost.ics`, `dorahacks.ics`) |

Each hackathon produces up to three events:

- **`<title> — build window`** — all-day event spanning start → end
- **`DEADLINE: <title> registration`** — timed reminder at the registration deadline
- **`DEADLINE: <title> submissions`** — timed reminder at the submission deadline

Events first seen within the last 7 days are prefixed `[NEW]`.
`CHANGELOG.md` records every added/removed/rescheduled event per run.

## Sources

| Source | Method |
|---|---|
| `manual` | `hackathons.json` — curated, authoritative |
| `aggregator_api` | [`0xarchit/hackathon-api`](https://github.com/0xarchit/hackathon-api) (MIT, Go) → Devfolio, Unstop, Devpost, MLH, HackerEarth, Hack2Skill, ReSkill, WhereUElevate, Devnovate |
| `dorahacks` | index → per-event schema.org JSON-LD |
| `encodeclub` | Supabase REST `Encode Programmes` (public anon key) |
| `lablab` | lablab.build JSON-LD ItemList → per-event Event JSON-LD |
| `ethglobal` | ethglobal.com/events SSR HTML cards |
| `colosseum` | landing page only — reserved, emits nothing |
| `ethstars` | best-effort JSON-LD/RSC parse |

## Adding a curated event

Edit `hackathons.json` and open a PR (or push to main — the next scheduled
run picks it up):

```json
{
  "slug": "my-hackathon",
  "title": "My Hackathon",
  "url": "https://…",
  "start": "2026-12-01",
  "end": "2026-12-15",
  "sub_deadline": "2026-12-15T23:59:00Z",
  "reg_deadline": "2026-12-01T23:59:00Z",
  "location": "Online",
  "prize": "$10,000",
  "tags": ["ai"]
}
```

## Development

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# aggregator source (optional locally):
git clone https://github.com/0xarchit/hackathon-api /tmp/hoa
(cd /tmp/hoa && go run ./cmd/server/main.go &)   # serves :8080

python3 hackathons_ics.py build
```

## License

MIT — see [LICENSE](LICENSE). Aggregator core is
[`0xarchit/hackathon-api`](https://github.com/0xarchit/hackathon-api) (MIT).
See `vendor/NOTICE` for attributions.
