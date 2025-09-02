import re, requests
from bs4 import BeautifulSoup
from typing import List, Optional
from urllib.parse import urljoin
from mc_utils.model import Event, make_event_id, now_iso

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

def _fetch(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=UA, timeout=25)
        if r.status_code == 200 and len(r.text) > 500:
            return r.text
    except requests.RequestException:
        return None
    return None

def _iso(d: str) -> Optional[str]:
    # dd/mm/yyyy -> yyyy-mm-dd
    m = re.match(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$", d or "")
    if not m: 
        return None
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"

def scrape_mpm(base_url: str, exhibitions_url: str, activities_url: str, tickets_url: Optional[str], institution_id: str, institution_name: str) -> List[Event]:
    html = _fetch(base_url)
    out: List[Event] = []
    if not html:
        print("[mpm] home vacío")
        return out
    soup = BeautifulSoup(html, "html.parser")

    # Tarjetas destacadas del home: .homeFeaturedHero[.is-half]
    cards = soup.select(".homeFeaturedHero, .homeFeaturedHero.is-half")
    print(f"[mpm] hero cards: {len(cards)}")
    for div in cards:
        a = div.find("a", href=True)
        if not a:
            continue
        href = urljoin(base_url, a["href"])
        title = a.get_text(" ", strip=True) or "(Sin título)"
        date_spans = [x.get_text(strip=True) for x in div.select(".homeFeaturedHero-date") if x.get_text(strip=True)]
        img = None
        pic = div.find("img", src=True)
        if pic:
            img = urljoin(base_url, pic["src"])
        else:
            styled = div.find(style=True)
            if styled and "background-image" in styled.get("style",""):
                m = re.search(r"url\\(([^)]+)\\)", styled["style"])
                if m: 
                    img = urljoin(base_url, m.group(1).strip("'\""))

        # Tipo por URL
        typ = "exhibition" if "/exposiciones/" in href else ("activity" if "/actividades/" in href else "exhibition")

        ds = _iso(date_spans[0]) if len(date_spans) >= 1 else None
        de = _iso(date_spans[1]) if len(date_spans) >= 2 else None

        eid = make_event_id(href, institution_id, title)
        now = now_iso()
        if typ == "exhibition":
            ev = Event(
                id=eid, type="exhibition", institution=institution_name, institution_id=institution_id,
                title=title, description=None, image_url=img, detail_url=href, tickets_url=tickets_url, status="scheduled",
                date_start=ds, date_end=de, datetime_start=None, datetime_end=None, price=None,
                first_seen=now, last_seen=now, last_changed=now, source="mpm:home"
            )
        else:
            ev = Event(
                id=eid, type="activity", institution=institution_name, institution_id=institution_id,
                title=title, description=None, image_url=img, detail_url=href, tickets_url=tickets_url, status="scheduled",
                date_start=None, date_end=None,
                datetime_start=f"{ds}T00:00:00+02:00" if ds else None,
                datetime_end=f"{de}T23:59:00+02:00" if de else None,
                price=None, first_seen=now, last_seen=now, last_changed=now, source="mpm:home"
            )
        out.append(ev)

    print(f"[mpm] total eventos: {len(out)}")
    return out
