"""Hackathon source adapters. Each module exposes fetch() -> list[dict].

Record shape:
  slug, title, url, start, end, reg_deadline, sub_deadline,
  location, prize, tags (list), source
Dates are ISO strings (YYYY-MM-DD for all-day, full ISO for timed).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str):
    import importlib
    return importlib.import_module(f"sources.{name}")


def all_sources():
    """Ordered source registry: (name, module)."""
    names = [
        "manual",
        "aggregator_api",
        "dorahacks",
        "encodeclub",
        "lablab",
        "ethglobal",
        "colosseum",
        "ethstars",
    ]
    return [(n, _load(n)) for n in names]


def load_curated() -> list[dict]:
    path = ROOT / "hackathons.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text())
    return data.get("hackathons", data if isinstance(data, list) else [])
