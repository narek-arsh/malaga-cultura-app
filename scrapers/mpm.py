# -*- coding: utf-8 -*-
"""
Scraper para Museo Picasso Málaga (MPM)
- Exposiciones: se extraen desde el listado (fechas DD/MM/YYYY, título, imagen).
- Actividades: se extraen desde las tarjetas del listado (rango de fechas en ES + <h2>).
Si el runner no ve actividades, se vuelca el HTML a data/debug_mpm_activities.html.
"""
from __future__ import annotations
import os, re, hashlib
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MalagaCulturalBot/1.0; +https://example.com)",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": "https://www.museopicassomalaga.org/actividades",
    "Connection": "keep-alive",
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
    r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize('NFKD', s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    s = s.replace('\xa0',' ').replace('�','-')
    s = re.sub(r'[–—]+', '-', s)   # guiones largos -> '-'
    s = re.sub(r'-{2,}', '-', s)   # '——' -> '-'
    s = re.sub(r'\s*-\s*', '-', s) # espacios alrededor del guion
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()

def _parse_spanish_date_range(text: str):
    """Devuelve (date_start, date_end, remainder_text) en YYYY-MM-DD."""
    t = _norm(text)
    # dd mes yyyy - dd mes yyyy
    m = re.search(r'(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})-(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})', t)
    if m:
        d1, mon1, y1, d2, mon2, y2 = m.groups()
        ds=f"{y1}-{MONTHS[mon1]:02d}-{int(d1):02d}"
        de=f"{y2}-{MONTHS[mon2]:02d}-{int(d2):02d}"
        return ds, de, t[m.end():].strip()
    # dd - dd mes yyyy
    m = re.search(r'(\d{1,2})-(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})', t)
    if m:
        d1, d2, mon, y = m.groups()
        ds=f"{y}-{MONTHS[mon]:02d}-{int(d1):02d}"
        de=f"{y}-{MONTHS[mon]:02d}-{int(d2):02d}"
        return ds, de, t[m.end():].strip()
    # mes - mes yyyy (aprox 1..28)
    m = re.search(r'(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)-(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})', t)
    if m:
        mon1, mon2, y = m.groups()
        ds=f"{y}-{MONTHS[mon1]:02d}-01"
        de=f"{y}-{MONTHS[mon2]:02d}-28"
        return ds, de, t[m.end():].strip()
    # 1, 8, 15, 22 y 29 octubre 2025
    m = re.search(r'(\d{1,2}(?:\s*,\s*\d{1,2})*(?:\s*y\s*\d{1,2})?)\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})', t)
    if m:
        days_list, mon, y = m.groups()
        days = [int(x.strip()) for x in re.split(r'[,\sy]+', days_list) if x.strip().isdigit()]
        if days:
            ds=f"{y}-{MONTHS[mon]:02d}-{min(days):02d}"
            de=f"{y}-{MONTHS[mon]:02d}-{max(days):02d}"
            return ds, de, t[m.end():].strip()
    # dd mes yyyy (día único)
    m = re.search(r'(\d{1,2})\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(\d{4})', t)
    if m:
        d, mon, y = m.groups()
        ds=f"{y}-{MONTHS[mon]:02d}-{int(d):02d}"
        return ds, ds, t[m.end():].strip()
    return None

def _clean_title_from_rest(rest: str) -> Optional[str]:
    if not rest:
        return None
    words = rest.strip(" -·,;").split()
    if not words:
        return None
    last = words[-1].lower()
    if last in CATEGORY_WORDS:
        words = words[:-1]
    return " ".join(words).strip(" -·,;") or None

def collect(config: dict) -> List[Dict[str, Any]]:
    institution_id = "mpm"
    institution_name = "Museo Picasso Málaga"
    events: List[Dict[str, Any]] = []

    # ── Exposiciones ──────────────────────────────────────────────────────────
    try:
        soup = _get(_abs(config["endpoints"]["exhibitions"]))
        for info in soup.select('.exhibitionCurrentFuture-info'):
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

            tnode = info.select_one('p.h1, .h1')
            title = tnode.get_text(" ", strip=True) if tnode else "Exposición"

            a = info.find('a', href=re.compile(r'/exposiciones/')) or info.find_previous('a', href=re.compile(r'/exposiciones/'))
            link = _abs(a['href']) if a and a.get('href') else _abs(config["endpoints"]["exhibitions"])

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
    except Exception as e:
        print(f"[WARN] mpm exhibitions failed: {e}")

    # ── Actividades ───────────────────────────────────────────────────────────
    try:
        soup = _get(_abs(config["endpoints"]["activities"]))
        # 1) Selector típico (tu HTML)
        cards = soup.select(".color-card-container.three-columns a.colorCard[href*='/actividades/']")
        # 2) Fallbacks por si el contenedor cambia
        if not cards:
            cards = soup.select("a.colorCard[href*='/actividades/']")
        if not cards:
            cards = [a for a in soup.find_all('a', href=True) if '/actividades/' in a['href'] and not a['href'].rstrip('/').endswith('/actividades')]

        seen = set()
        found = 0
        for a in cards:
            href = a.get('href','')
            link = _abs(href.split('#')[0])
            if link in seen:
                continue
            seen.add(link)

            # Fechas (primer <p> con nombres de mes) + título (<h2> o <h3>)
            p_dates = None
            for p in a.find_all("p"):
                txt = p.get_text(" ", strip=True)
                if re.search(r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)", txt, re.I):
                    p_dates = txt; break
            h2 = a.find(["h2","h3"])
            title = h2.get_text(" ", strip=True) if h2 else None

            base_text = p_dates or a.get_text(" ", strip=True)
            parsed = _parse_spanish_date_range(base_text)
            if not parsed:
                continue
            ds, de, rest = parsed
            if not title:
                title = _clean_title_from_rest(rest) or "Actividad"

            img = a.find("img")
            image_url = _abs(img["src"]) if img and img.get("src") else None

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
            found += 1

        if found == 0:
            # DEBUG: volcar HTML y anclas para ver qué recibe el runner
            try:
                data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
                os.makedirs(data_dir, exist_ok=True)
                with open(os.path.join(data_dir, "debug_mpm_activities.html"), "w", encoding="utf-8") as f:
                    f.write(str(soup))
                anchors = [a.get('href','') for a in soup.find_all('a', href=True) if '/actividades/' in a.get('href','')]
                with open(os.path.join(data_dir, "debug_mpm_anchors.txt"), "w", encoding="utf-8") as f:
                    f.write("\n".join(anchors))
                print("[DBG] mpm: 0 activities -> wrote data/debug_mpm_activities.html and debug_mpm_anchors.txt")
            except Exception as _e:
                print(f"[DBG] mpm: failed to write debug files: {_e}")

    except Exception as e:
        print(f"[WARN] mpm activities failed: {e}")

    return events
