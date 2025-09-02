from typing import Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def text(soup: BeautifulSoup) -> str:
    return soup.get_text(" ", strip=True)

def pick_title(soup: BeautifulSoup) -> Optional[str]:
    h1 = soup.find(["h1","h2"], string=True)
    if h1: return h1.get_text(" ", strip=True)
    og = soup.find("meta", property="og:title")
    if og and og.get("content"): return og["content"].strip()
    if soup.title and soup.title.string: return soup.title.string.strip()
    return None

def pick_description(soup: BeautifulSoup) -> Optional[str]:
    og = soup.find("meta", property="og:description")
    if og and og.get("content"): return og["content"].strip()
    p = soup.find("article") or soup.find("main") or soup
    fp = p.find("p")
    if fp: return fp.get_text(" ", strip=True)
    return None

def pick_image(soup: BeautifulSoup, base: str) -> Optional[str]:
    og = soup.find("meta", property="og:image")
    if og and og.get("content"): return urljoin(base, og["content"])
    img = soup.find("article").find("img", src=True) if soup.find("article") else soup.find("img", src=True)
    if img: return urljoin(base, img["src"])
    return None
