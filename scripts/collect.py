# -*- coding: utf-8 -*-
"""
Collector orchestrator.
- Loads config/institutions.yaml
- Runs enabled scrapers
- Merges with manual_events.json (manual > scraper)
- Writes data/events.json and data/meta.json
"""
import json, os, hashlib, time, importlib, yaml, sys
from copy import deepcopy
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(__file__))

# Asegura que el paquete 'scrapers' se pueda importar
import sys
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# Ensure project root is on PYTHONPATH for 'scrapers' imports
import sys
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
CONFIG_PATH = os.path.join(ROOT, "config", "institutions.yaml")
DATA_DIR = os.path.join(ROOT, "data")
EVENTS_PATH = os.path.join(DATA_DIR, "events.json")
MANUAL_PATH = os.path.join(DATA_DIR, "manual_events.json")
META_PATH = os.path.join(DATA_DIR, "meta.json")

def sha1(s: str) -> str:
    import hashlib
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(MANUAL_PATH):
        with open(MANUAL_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    if not os.path.exists(EVENTS_PATH):
        with open(EVENTS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def key_for_event(e: dict) -> str:
    parts = [e.get("type",""), e.get("institution_id","")]
    if e.get("url"):
        parts.append(e["url"])
    else:
        parts.append(e.get("title",""))
    # date or datetime
    if e.get("type") == "exhibition":
        parts.append(e.get("date_start",""))
        parts.append(e.get("date_end",""))
    else:
        parts.append(e.get("datetime_start",""))
        parts.append(e.get("datetime_end",""))
    return "|".join(parts).lower()

def normalize_event(e: dict) -> dict:
    e = deepcopy(e)
    e.setdefault("status", "scheduled")
    e.setdefault("source", "scraper")
    e.setdefault("last_seen_at", datetime.now(timezone.utc).isoformat())
    e.setdefault("city", "Málaga")
    # Keep schema_version for future migrations
    e.setdefault("schema_version", "1")
    # Ensure id
    if not e.get("id"):
        e["id"] = sha1(key_for_event(e))
    return e

def merge_events(scraped: list, manual: list) -> list:
    by_id = {}
    for e in scraped:
        ne = normalize_event(e)
        by_id[ne["id"]] = ne
    for m in manual:
        nm = normalize_event(m)
        # manual overrides scraper
        if nm["id"] in by_id:
            by_id[nm["id"]].update({k:v for k,v in nm.items() if k not in ("source","schema_version")})
        else:
            by_id[nm["id"]] = nm
    return sorted(by_id.values(), key=lambda x: (
        x.get("date_start") or x.get("datetime_start") or "9999",
        x.get("title","")
    ))

def main():
    ensure_data_files()
    cfg = load_yaml(CONFIG_PATH)
    scraped = []
    active = 0

    for inst in cfg.get("institutions", []):
        if not inst.get("enabled"):
            continue
        active += 1
        scraper_mod = f"scrapers.{inst['id']}"
        try:
            mod = importlib.import_module(scraper_mod)
        except Exception as e:
            print(f"[WARN] Cannot import {scraper_mod}: {e}")
            continue
        try:
            res = mod.collect(inst)
scraped.extend(res)
by_type = {}
for e in res:
    by_type[e.get('type','?')] = by_type.get(e.get('type','?'), 0) + 1
print(f"[OK] {inst['id']} -> {len(res)} events (by type: {by_type})")
        except Exception as e:
            print(f"[ERROR] {inst['id']} scraper failed: {e}")

    # Load manual
    try:
        with open(MANUAL_PATH, "r", encoding="utf-8") as f:
            manual = json.load(f)
    except Exception:
        manual = []

    merged = merge_events(scraped, manual)

    # Write events.json
    with open(EVENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_institutions": active,
        "counts": {
            "total": len(merged),
            "scraped": len(scraped),
            "manual": len(merged) - len(scraped) # rough
        }
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    sys.exit(main())
