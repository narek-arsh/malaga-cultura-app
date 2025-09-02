import os, yaml
from typing import List, Dict
from mc_utils.model import Event, now_iso
from mc_utils.storage import load_json, save_json_local
from sources.generic_scraper import scrape_from_listing
from sources.rss_scraper import scrape_rss_url
from sources.museo_picasso import scrape_mpm
from sources.thyssen import scrape_thyssen

ROOT = os.path.dirname(os.path.dirname(__file__))

def merge_events(existing: Dict[str, Dict], new_events: List[Dict]) -> Dict[str, Dict]:
    out = dict(existing)
    now = now_iso()
    for ev in new_events:
        eid = ev["id"]
        if eid in out:
            changed = False
            for k, v in ev.items():
                if k in ["first_seen", "last_seen", "last_changed"]:
                    continue
                if out[eid].get(k) != v:
                    changed = True
                    out[eid][k] = v
            out[eid]["last_seen"] = now
            if changed:
                out[eid]["last_changed"] = now
        else:
            ev["first_seen"] = now
            ev["last_seen"] = now
            ev["last_changed"] = now
            out[eid] = ev
    return out

def main():
    cfg_path = os.path.join(ROOT, "config", "institutions.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    institutions = cfg.get("institutions", [])
    all_events: List[Event] = []

    for inst in institutions:
        name = inst["name"]
        iid = inst["id"]
        tickets_url = inst.get("tickets_url")
        base_url = inst.get("base_url") or ""
        ex_url = inst.get("exhibitions_url") or ""
        ac_url = inst.get("activities_url") or ""
        rss_ex = inst.get("rss_exhibitions_url") or ""
        rss_ac = inst.get("rss_activities_url") or ""

        # 1) Specific scrapers
        if iid == "mpm":
            all_events += scrape_mpm(base_url, ex_url, ac_url, tickets_url, iid, name)
            # continue to RSS/generic for extra, just in case (no 'continue')
        elif iid == "thyssen":
            all_events += scrape_thyssen(ex_url, ac_url, tickets_url, iid, name)

        # 2) RSS
        if rss_ex:
            all_events += [e for e in scrape_rss_url(rss_ex, "exhibition", name, iid)]
        if rss_ac:
            all_events += [e for e in scrape_rss_url(rss_ac, "activity", name, iid)]

        # 3) Generic fallback
        if ex_url:
            all_events += scrape_from_listing(ex_url, "exhibition", name, iid, tickets_url, hint="/expos")
        if ac_url:
            all_events += scrape_from_listing(ac_url, "activity", name, iid, tickets_url, hint="/activ")

    scraped = [e.to_dict() for e in all_events]

    manual_path = os.path.join(ROOT, "data", "manual.json")
    manual_list = load_json(manual_path, [])

    build_path = os.path.join(ROOT, "build", "events.json")
    existing_list = load_json(build_path, [])
    existing_map = {e["id"]: e for e in existing_list}

    def event_sort_key(e):
        d = e.get("date_start") or (e.get("datetime_start") or "")[:10] or "9999-12-31"
        return (d, e.get("title", ""))

    tmp_map = merge_events(existing_map, scraped)
    tmp_map = merge_events(tmp_map, manual_list)

    out_list = sorted(list(tmp_map.values()), key=event_sort_key)

    save_json_local(build_path, out_list)
    print(f"Saved {len(out_list)} events to build/events.json")

if __name__ == "__main__":
    main()
