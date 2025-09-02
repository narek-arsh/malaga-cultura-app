import re
import dateparser
from datetime import datetime, date
from typing import Optional, Tuple

def parse_spanish_date(text: str) -> Optional[date]:
    dt = dateparser.parse(text, languages=['es'])
    return dt.date() if dt else None

def parse_date_range(text: str) -> Tuple[Optional[date], Optional[date]]:
    t = text.replace('–', '-').replace('—', '-').replace(' a ', ' - ').replace(' al ', ' - ')
    m = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})(?:[\/\-\.](\d{2,4}))?\s*-\s*(\d{1,2})[\/\-\.](\d{1,2})(?:[\/\-\.](\d{2,4}))?', t)
    if m:
        d1 = '/'.join([m.group(1), m.group(2), m.group(3) if m.group(3) else str(datetime.now().year)])
        d2 = '/'.join([m.group(4), m.group(5), m.group(6) if m.group(6) else str(datetime.now().year)])
        s = dateparser.parse(d1, languages=['es'])
        e = dateparser.parse(d2, languages=['es'])
        return (s.date() if s else None, e.date() if e else None)

    parts = re.split(r'\s*-\s*|\s*–\s*|\s*—\s*', t)
    if len(parts) == 2:
        s = dateparser.parse(parts[0], languages=['es'])
        e = dateparser.parse(parts[1], languages=['es'])
        if s and e:
            return (s.date(), e.date())

    m = re.search(r'del?\s+(\d{1,2})\s+al?\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)', t, flags=re.I)
    if m:
        year = datetime.now().year
        s_txt = f"{m.group(1)} {m.group(3)} {year}"
        e_txt = f"{m.group(2)} {m.group(3)} {year}"
        s = dateparser.parse(s_txt, languages=['es'])
        e = dateparser.parse(e_txt, languages=['es'])
        if s and e:
            return (s.date(), e.date())

    return (None, None)

def overlap_day_range(event_start: Optional[date], event_end: Optional[date], q_start: date, q_end: date) -> bool:
    if not event_start and not event_end:
        return False
    s = event_start or event_end
    e = event_end or event_start
    return (s <= q_end) and (e >= q_start)
