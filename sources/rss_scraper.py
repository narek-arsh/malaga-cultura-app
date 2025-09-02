import feedparser
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple
from mc_utils.model import Event, make_event_id, now_iso
from mc_utils.dates import parse_date_range, parse_spanish_date

def first_img_src(html: str) -> Optional[str]:
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    img = soup.find("img", src=True)
    return img["src"] if img else None

def extract_dates_from_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    s, e = parse_date_range(text)
    if s and e:
        return (s.isoformat(), e.isoformat())
    d = parse_spanish_date(text)
    if d:
        return (d.isoformat(), None)
    return (None, None)

def scrape_rss_url(url: str, event_type: str, institution_name: str, institution_id: str) -> List[Event]:
    d = feedparser.parse(url)
    events: List[Event] = []
    for entry in d.entries:
        title = entry.get("title", "").strip() or "(Sin título)"
        link = entry.get("link")
        summary_html = entry.get("summary", "") or entry.get("description", "") or ""
        text_for_dates = " ".join([title, BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True)])
        ds, de = extract_dates_from_text(text_for_dates)
        img = None
        if "media_thumbnail" in entry and entry.media_thumbnail:
            img = entry.media_thumbnail[0].get("url")
        if not img:
            img = first_img_src(summary_html)

        status = "scheduled"
        low = text_for_dates.lower()
        if any(w in low for w in ["cancelado", "cancelada", "suspendido", "suspendida"]):
            status = "cancelled"
        elif any(w in low for w in ["aplazado", "aplazada", "pospuesto", "pospuesta"]):
            status = "postponed"

        eid = make_event_id(link, institution_id, title)
        now = now_iso()
        if event_type == "exhibition":
            evt = Event(id=eid, type="exhibition", institution=institution_name, institution_id=institution_id, title=title,
                        description=BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True) or None,
                        image_url=img, detail_url=link, tickets_url=None, status=status,
                        date_start=ds, date_end=de, datetime_start=None, datetime_end=None, price=None,
                        first_seen=now, last_seen=now, last_changed=now, source=url)
        else:
            datetime_start = f"{ds}T00:00:00+02:00" if ds else None
            datetime_end = f"{de}T23:59:00+02:00" if de else None
            evt = Event(id=eid, type="activity", institution=institution_name, institution_id=institution_id, title=title,
                        description=BeautifulSoup(summary_html, "html.parser").get_text(" ", strip=True) or None,
                        image_url=img, detail_url=link, tickets_url=None, status=status,
                        date_start=None, date_end=None, datetime_start=datetime_start, datetime_end=datetime_end, price=None,
                        first_seen=now, last_seen=now, last_changed=now, source=url)
        events.append(evt)
    return events
