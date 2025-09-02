import re
import dateparser
from datetime import datetime, date
from typing import Optional, Tuple

def parse_spanish_date(text: str) -> Optional[date]:
    dt = dateparser.parse(text, languages=['es'])
    return dt.date() if dt else None

def parse_date_range(text: str) -> Tuple[Optional[date], Optional[date]]:
    """
    Devuelve (inicio, fin) si detecta un rango en español.
    Soporta:
      - 10/10/2025 - 17/11/2025  (o sin año en alguno)
      - Del 01 de abril al 14 de septiembre de 2025
      - Del 16 de julio de 2025 al 13 de octubre de 2025
      - Del 01 al 12 de septiembre de 2025
    """
    if not text:
        return (None, None)

    t = " ".join(text.split()).lower()
    t = t.replace('–', '-').replace('—', '-')

    # 1) Formato numérico: dd/mm[/yyyy] - dd/mm[/yyyy]
    m = re.search(
        r'(\d{1,2})[\/\.\-](\d{1,2})(?:[\/\.\-](\d{2,4}))?\s*-\s*'
        r'(\d{1,2})[\/\.\-](\d{1,2})(?:[\/\.\-](\d{2,4}))?',
        t
    )
    if m:
        y_now = datetime.now().year
        d1 = f"{m.group(1)}/{m.group(2)}/{m.group(3) if m.group(3) else y_now}"
        d2 = f"{m.group(4)}/{m.group(5)}/{m.group(6) if m.group(6) else y_now}"
        s = dateparser.parse(d1, languages=['es'])
        e = dateparser.parse(d2, languages=['es'])
        return (s.date() if s else None, e.date() if e else None)

    # 2) "del 16 de julio [de 2025] al 13 de octubre [de 2025]"
    m = re.search(
        r'del?\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)(?:\s+de\s+(\d{4}))?\s+'
        r'al?\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)(?:\s+de\s+(\d{4}))?',
        t, flags=re.I
    )
    if m:
        y_now = str(datetime.now().year)
        y1 = m.group(3) or m.group(6) or y_now
        y2 = m.group(6) or m.group(3) or y_now
        s_txt = f"{m.group(1)} {m.group(2)} {y1}"
        e_txt = f"{m.group(4)} {m.group(5)} {y2}"
        s = dateparser.parse(s_txt, languages=['es'])
        e = dateparser.parse(e_txt, languages=['es'])
        if s and e:
            return (s.date(), e.date())

    # 3) "del 01 al 12 de septiembre [de 2025]"
    m = re.search(
        r'del?\s+(\d{1,2})\s+al?\s+(\d{1,2})\s+de\s+([a-záéíóúñ]+)(?:\s+de\s+(\d{4}))?',
        t, flags=re.I
    )
    if m:
        y = m.group(4) or str(datetime.now().year)
        s_txt = f"{m.group(1)} {m.group(3)} {y}"
        e_txt = f"{m.group(2)} {m.group(3)} {y}"
        s = dateparser.parse(s_txt, languages=['es'])
        e = dateparser.parse(e_txt, languages=['es'])
        if s and e:
            return (s.date(), e.date())

    # 4) Heurística final: separar por guiones y probar parseo suelto
    parts = re.split(r'\s*-\s*', t)
    if len(parts) == 2:
        s = dateparser.parse(parts[0], languages=['es'])
        e = dateparser.parse(parts[1], languages=['es'])
        if s and e:
            return (s.date(), e.date())

    return (None, None)

def overlap_day_range(event_start: Optional[date], event_end: Optional[date], q_start: date, q_end: date) -> bool:
    if not event_start and not event_end:
        return False
    s = event_start or event_end
    e = event_end or event_start
    return (s <= q_end) and (e >= q_start)
