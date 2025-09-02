import os, yaml
from typing import List, Dict
from mc_utils.model import Event, now_iso
from mc_utils.storage import load_json, save_json_local
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
    # Solo dejamos activadas las que estén en el YAML y enabled != false
    allowed_ids = {i["id"] for i in institutions if i.get("enabled", True)}

    all_events: List[Event] = []

    for inst in institutions:
        name = inst["name"]
        iid = inst["id"]
        tickets_url = inst.get("tickets_url")
        base_url = inst.get("base_url") or ""
        ex_url = inst.get("exhibitions_url") or ""
        ac_url = inst.get("activities_url") or ""

        if iid == "mpm":
            all_events += scrape_mpm(base_url, ex_url, ac_url, tickets_url, iid, name)
        elif iid == "thyssen":
            all_events += scrape_thyssen(ex_url, ac_url, tickets_url, iid, name)
        # No hay más scrapers aquí a propósito

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

    # PRUNE: elimina cualquier evento de instituciones no permitidas
    tmp_map = {k: v for k, v in tmp_map.items() if v.get("institution_id") in allowed_ids}

    out_list = sorted(list(tmp_map.values()), key=event_sort_key)

    save_json_local(build_path, out_list)
    print(f"Saved {len(out_list)} events to build/events.json")

if __name__ == "__main__":
    main()
