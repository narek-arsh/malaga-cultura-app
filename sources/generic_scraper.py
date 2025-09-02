import re, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Optional, Tuple, Set
from mc_utils.model import Event, make_event_id, now_iso
from mc_utils.dates import parse_date_range, parse_spanish_date
from .common import pick_title, pick_description, pick_image

# UA "real" para evitar bloqueos
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

def fetch(url: str) -> Optional[str]:
    try:
        r = requests.get(url, headers=UA, timeout=25)
        if r.status_code == 200 and r.text and len(r.text) > 500:
            return r.text
    except requests.RequestException:
        return None
    return None

def collect_detail_links(list_url: str, domain_host: str, hint: str = "") -> List[str]:
    html = fetch(list_url)
    if not html: 
        print(f"[collect] vacío: {list_url}")
        return []
    soup = BeautifulSoup(html, "html.parser")
    links: Set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        absu = urljoin(list_url, href)
        if urlparse(absu).netloc != domain_host:
            continue
        # Si se indica hint (p.ej. "/expos"), lo exigimos
        if hint and hint not in absu:
            continue
        links.add(absu)
    out = list(links)[:60]  # cota de seguridad
    print(f"[collect] {list_url} -> {len(out)} enlaces (hint={hint})")
    return out

def parse_dates_from_time_tags(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    # 1) <time datetime="YYYY-MM-DD">
    times = soup.find_all("time")
    dates = []
    for t in times:
        dt = (t.get("datetime") or "").strip()
        if re.match(r"^\d{4}-\d{2}-\d{2}", dt):
            dates.append(dt[:10])
        else:
            # 2) Contenido legible "10/10/2025" o "10 octubre 2025"
            txt = t.get_text(" ", strip=True)
            d = parse_spanish_date(txt)
            if d:
                dates.append(d.isoformat())
    if len(dates) >= 2:
        return (dates[0], dates[1])
    if len(dates) == 1:
        return (dates[0], None)
    return (None, None)

def parse_dates_from_text(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    # Primero probamos <time>, luego texto global
    ds, de = parse_dates_from_time_tags(soup)
    if ds or de:
        return (ds, de)
    txt = soup.get_text(" ", strip=True)
    s, e = parse_date_range(txt)
    if s and e:
        return (s.isoformat(), e.isoformat())
    d = parse_spanish_date(txt)
    if d:
        return (d.isoformat(), None)
    return (None, None)

def scrape_detail(url: str, institution_name: str, institution_id: str, event_type: str, tickets_url: Optional[str]) -> Optional[Event]:
    html = fetch(url)
    if not html: 
        print(f"[detail] sin HTML: {url}")
        return None
    soup = BeautifulSoup(html, "html.parser")
    title = pick_title(soup) or "(Sin título)"
    img = pick_image(soup, url)
    desc = pick_description(soup)
    ds, de = parse_dates_from_text(soup)

    status = "scheduled"
    low = soup.get_text(" ", strip=True).lower()
    if any(w in low for w in ["cancelado","cancelada","suspendido","suspendida"]):
        status = "cancelled"
    elif any(w in low for w in ["aplazado","aplazada","pospuesto","pospuesta"]):
        status = "postponed"

    eid = make_event_id(url, institution_id, title)
    now = now_iso()
    if event_type == "exhibition":
        return Event(id=eid, type="exhibition", institution=institution_name, institution_id=institution_id,
                     title=title, description=desc, image_url=img, detail_url=url, tickets_url=tickets_url, status=status,
                     date_start=ds, date_end=de, datetime_start=None, datetime_end=None, price=None,
                     first_seen=now, last_seen=now, last_changed=now, source=url)
    else:
        # Actividades: si no hay hora en la ficha, dejamos 00:00 (editable manual)
        dt_start = f"{ds}T00:00:00+02:00" if ds else None
        dt_end = f"{de}T23:59:00+02:00" if de else None
        return Event(id=eid, type="activity", institution=institution_name, institution_id=institution_id, title=title,
                     description=desc, image_url=img, detail_url=url, tickets_url=tickets_url, status=status,
                     date_start=None, date_end=None, datetime_start=dt_start, datetime_end=dt_end, price=None,
                     first_seen=now, last_seen=now, last_changed=now, source=url)

def scrape_from_listing(list_url: str, event_type: str, institution_name: str, institution_id: str, tickets_url: Optional[str], hint: str = "") -> List[Event]:
    from urllib.parse import urlparse
    host = urlparse(list_url).netloc
    details = collect_detail_links(list_url, host, hint=hint)
    out: List[Event] = []
    ok = 0
    for link in details:
        ev = scrape_detail(link, institution_name, institution_id, event_type, tickets_url)
        if ev:
            out.append(ev)
            ok += 1
    print(f"[scrape] {institution_id}:{event_type} -> {ok} eventos")
    return out
