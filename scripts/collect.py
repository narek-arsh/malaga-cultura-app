import re, requests
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse
from mc_utils.model import Event, make_event_id, now_iso
from mc_utils.dates import parse_date_range, parse_spanish_date

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

def _fetch(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=UA, timeout=25)
        if r.status_code == 200 and r.text and len(r.text) > 500:
            return r.text
    except requests.RequestException:
        return None
    return None

def _collect_detail_links(list_url: str, must_contain: str) -> List[str]:
    """Recoge enlaces internos de un listado, filtrando por subruta (p.ej. '/exposiciones/' o '/actividades/')."""
    html = _fetch(list_url)
    if not html:
        print(f"[mpm:list] vacío: {list_url}")
        return []
    soup = BeautifulSoup(html, "html.parser")
    host = urlparse(list_url).netloc
    links: Set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        absu = urljoin(list_url, href)
        if urlparse(absu).netloc != host:
            continue
        if must_contain not in absu:
            continue
        links.add(absu)
    out = sorted(links)
    print(f"[mpm:list] {list_url} -> {len(out)} enlaces ({must_contain})")
    return out

def _parse_dates(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    """Intenta fechas por <time>, luego por texto global con nuestros parsers en español."""
    # 1) <time datetime="YYYY-MM-DD">
    dates = []
    for t in soup.find_all("time"):
        dt = (t.get("datetime") or "").strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", dt):
            dates.append(dt[:10])
        else:
            txt = t.get_text(" ", strip=True)
            d = parse_spanish_date(txt)
            if d:
                dates.append(d.isoformat())
    if len(dates) >= 2:
        return dates[0], dates[1]
    if len(dates) == 1:
        return dates[0], None

    # 2) Texto global (soporta: "del 01 de abril al 14 de septiembre de 2025", "23/05/2025 - 12/12/2025", etc.)
    txt = soup.get_text(" ", strip=True)
    s, e = parse_date_range(txt)
    if s and e:
        return s.isoformat(), e.isoformat()
    d = parse_spanish_date(txt)
    if d:
        return d.isoformat(), None
    return None, None

def _status_from_text(soup: BeautifulSoup) -> str:
    low = soup.get_text(" ", strip=True).lower()
    if any(w in low for w in ("cancelado", "cancelada", "suspendido", "suspendida")):
        return "cancelled"
    if any(w in low for w in ("aplazado", "aplazada", "pospuesto", "pospuesta")):
        return "postponed"
    return "scheduled"

def _scrape_detail(url: str, institution_id: str, institution_name: str, event_type: str, tickets_url: Optional[str]) -> Optional[Event]:
    html = _fetch(url)
    if not html:
        print(f"[mpm:detail] sin HTML: {url}")
        return None
    soup = BeautifulSoup(html, "html.parser")

    title = pick_title(soup) or "(Sin título)"
    img = pick_image(soup, url)
    desc = pick_description(soup)
    ds, de = _parse_dates(soup)
    status = _status_from_text(soup)

    eid = make_event_id(url, institution_id, title)
    now = now_iso()

    if event_type == "exhibition":
        return Event(
            id=eid, type="exhibition", institution=institution_name, institution_id=institution_id,
            title=title, description=desc, image_url=img, detail_url=url, tickets_url=tickets_url, status=status,
            date_start=ds, date_end=de, datetime_start=None, datetime_end=None, price=None,
            first_seen=now, last_seen=now, last_changed=now, source=url
        )
    else:
        # Si no hay horas claras, dejamos todo-día (00:00–23:59) en el rango detectado.
        dt_start = f"{ds}T00:00:00+02:00" if ds else None
        dt_end   = f"{de}T23:59:00+02:00" if de else None
        return Event(
            id=eid, type="activity", institution=institution_name, institution_id=institution_id,
            title=title, description=desc, image_url=img, detail_url=url, tickets_url=tickets_url, status=status,
            date_start=None, date_end=None, datetime_start=dt_start, datetime_end=dt_end, price=None,
            first_seen=now, last_seen=now, last_changed=now, source=url
        )

def scrape_mpm(base_url: str,
               exhibitions_url: str,
               activities_url: str,
               tickets_url: Optional[str],
               institution_id: str,
               institution_name: str) -> List[Event]:
    events: List[Event] = []

    # EXHIBICIONES
    if exhibitions_url:
        expo_links = _collect_detail_links(exhibitions_url, "/exposiciones/")
        ok = 0
        for link in expo_links:
            ev = _scrape_detail(link, institution_id, institution_name, "exhibition", tickets_url)
            if ev:
                events.append(ev); ok += 1
        print(f"[mpm] exposiciones: {ok}")

    # ACTIVIDADES
    if activities_url:
        act_links = _collect_detail_links(activities_url, "/actividades/")
        ok = 0
        for link in act_links:
            ev = _scrape_detail(link, institution_id, institution_name, "activity", tickets_url)
            if ev:
                events.append(ev); ok += 1
        print(f"[mpm] actividades: {ok}")

    return events
