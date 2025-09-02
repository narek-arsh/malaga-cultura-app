# -*- coding: utf-8 -*-
"""
Scraper for Museo Picasso Málaga (MPM)
- Exposiciones: extrae de la propia lista (fechas DD/MM/YYYY, título, imagen de background).
- Actividades: extrae de la lista; el texto del <a> incluye fechas en español + título + categoría.
"""
from __future__ import annotations
import re, hashlib
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MalagaCulturalBot/1.0; +https://example.com)"
}
BASE = "https://www.museopicassomalaga.org"

MONTHS = {
    'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
    'julio':7,'agosto':8,'septiembre':9,'setiembre':9,'octubre':10,'noviembre':11,'diciembre':12
}
CATEGORY_WORDS = {'talleres','conferencias','musicas','músicas'}

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def _abs(url: str) -> str:
    return url if url.startswith("http") else urljoin(BASE, url)

def _get(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize('NFKD', s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    s = s.replace('\xa0',' ').replace('�','-')
    s = re.sub(r'[–—]+', '-', s)          # guiones largos -> '-'
    s = re.sub(r'-{2,}', '-', s)          # '——' -> '-'
    s = re.sub(r'\s*-\s*', '-', s)        # espacios alrededor del guion
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()

def _parse_spanish_date_range(text: str):
    """
    Devuelve (date_start, date_end, remainder_text) en YYYY-MM-DD a partir del texto en ES.
    Soporta:
      - '16 septiembre 2025 – 14 julio 2026 …'
      - '18 – 19 septiembre 2025 …'
      - '1, 8, 15, 22 y 29 octubre 2025 …'
      - 'junio – diciembre 2025 …'
      - '4 octubre 2025 …'
    """
    t = _norm(text)
    # dd mes yyyy - dd mes yyyy
    pat1 = re.compile(r'(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})-(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})')
    m = pat1.search(t)
    if m:
        d1, mon1, y1, d2, mon2, y2 = m.groups()
        ds=f"{y1}-{MONTHS[mon1]:02d}-{int(d1):02d}"
        de=f"{y2}-{MONTHS[mon2]:02d}-{int(d2):02d}"
        rest = t[m.end():].strip()
        return ds, de, rest

    # dd - dd mes yyyy
    pat2 = re.compile(r'(\d{1,2})-(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})')
    m = pat2.search(t)
    if m:
        d1, d2, mon, y = m.groups()
        ds=f"{y}-{MONTHS[mon]:02d}-{int(d1):02d}"
        de=f"{y}-{MONTHS[mon]:02d}-{int(d2):02d}"
        rest = t[m.end():].strip()
        return ds, de, rest

    # mes - mes yyyy  (aprox 1..28)
    pat3 = re.compile(r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)-(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})')
    m = pat3.search(t)
    if m:
        mon1, mon2, y = m.groups()
        ds=f"{y}-{MONTHS[mon1]:02d}-01"
        de=f"{y}-{MONTHS[mon2]:02d}-28"
        rest = t[m.end():].strip()
        return ds, de, rest

    # 1, 8, 15, 22 y 29 octubre 2025
    pat5 = re.compile(r'(\d{1,2}(?:\s*,\s*\d{1,2})*(?:\s*y\s*\d{1,2})?)\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})')
    m = pat5.search(t)
    if m:
        days_list, mon, y = m.groups()
        days = [int(x.strip()) for x in re.split(r'[,\sy]+', days_list) if x.strip().isdigit()]
        if days:
            ds=f"{y}-{MONTHS[mon]:02d}-{min(days):02d}"
            de=f"{y}-{MONTHS[mon]:02d}-{max(days):02d}"
            rest = t[m.end():].strip()
            return ds, de, rest

    # dd mes yyyy
    pat4 = re.compile(r'(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})')
    m = pat4.search(t)
    if m:
        d, mon, y = m.groups()
        ds=f"{y}-{MONTHS[mon]:02d}-{int(d):02d}"
        rest = t[m.end():].strip()
        return ds, ds, rest

    return None

def _clean_title_from_rest(rest: str) -> str:
    if not rest:
        return None
    tail = rest.strip(" -·,;")
    words = tail.split()
    if not words:
        return tail
    last = words[-1].lower()
    if last in CATEGORY_WORDS:
        words = words[:-1]
    return " ".join(words).strip(" -·,;") or None

def collect(config: dict) -> List[Dict[str, Any]]:
    institution_id = "mpm"
    institution_name = "Museo Picasso Málaga"
    events: List[Dict[str, Any]] = []

    # ── Exposiciones (desde el listado) ───────────────────────────────────────
    try:
        soup = _get(_abs(config["endpoints"]["exhibitions"]))
        for info in soup.select('.exhibitionCurrentFuture-info'):
            # Fechas DD/MM/YYYY en spans .exhibitionCurrentFuture-date
            dates = info.select('.exhibitionCurrentFuture-date')
            if not dates:
                continue
            date_start = dates[0].get_text(strip=True)
            date_end = dates[1].get_text(strip=True) if len(dates) > 1 else date_start

            def ddmmyyyy(s):
                d,m,y = s.split('/')
                return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            try:
                ds = ddmmyyyy(date_start)
                de = ddmmyyyy(date_end)
            except Exception:
                continue

            # Título
            tnode = info.select_one('p.h1, .h1')
            title = tnode.get_text(" ", strip=True) if tnode else "Exposición"

            # Link cercano a /exposiciones/<slug>
            a = info.find('a', href=re.compile(r'/exposiciones/'))
            if not a:
                a = info.find_previous('a', href=re.compile(r'/exposiciones/'))
            link = _abs(a['href']) if a and a.get('href') else _abs(config["endpoints"]["exhibitions"])

            # Imagen desde bloque background vecino
            bg = info.find_previous(class_=re.compile('exhibitionCurrentFuture-background'))
            image_url = None
            if bg:
                style = bg.get('style','')
                m = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                if m:
                    image_url = _abs(m.group(1))
                else:
                    img = bg.find('img')
                    if img and img.get('src'):
                        image_url = _abs(img['src'])

            key = f"exhibition|{institution_id}|{link}|{ds}|{de}".lower()
            events.append({
                "id": _sha1(key),
                "type": "exhibition",
                "title": title,
                "description": None,
                "image_url": image_url,
                "institution_id": institution_id,
                "institution_name": institution_name,
                "city": "Málaga",
                "url": link,
                "date_start": ds,
                "date_end": de,
                "status": "scheduled",
                "all_day": True,
                "source": "scraper",
            })
    except Exception:
        pass

    # ── Actividades (desde el listado; all-day por defecto) ───────────────────
    try:
        soup = _get(_abs(config["endpoints"]["activities"]))
        seen = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            if "/actividades/" not in href or href.rstrip('/').endswith('/actividades'):
                continue
            link = _abs(href.split('#')[0])
            if link in seen:
                continue
            seen.add(link)

            text = a.get_text(" ", strip=True)
            parsed = _parse_spanish_date_range(text)
            if not parsed:
                continue
            ds, de, rest = parsed
            title = _clean_title_from_rest(rest) or "Actividad"

            # Imagen (si el <a> incluye <img>, úsala)
            img = a.find('img')
            image_url = _abs(img['src']) if img and img.get('src') else None

            dt_start = ds + "T00:00:00+02:00"
            dt_end   = de + "T23:59:00+02:00"

            key = f"activity|{institution_id}|{link}|{dt_start}|{dt_end}".lower()
            events.append({
                "id": _sha1(key),
                "type": "activity",
                "title": title,
                "description": None,
                "image_url": image_url,
                "institution_id": institution_id,
                "institution_name": institution_name,
                "city": "Málaga",
                "url": link,
                "datetime_start": dt_start,
                "datetime_end": dt_end,
                "all_day": True,
                "status": "scheduled",
                "source": "scraper",
            })
    except Exception:
        pass

    return events
