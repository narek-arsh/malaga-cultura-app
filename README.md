# Málaga · Agenda cultural — Scrapers por sede

Incluye scrapers **individuales** por web:

- `sources/museo_picasso.py` → Museo Picasso Málaga (home + actividades tickets).
- `sources/thyssen.py` → Museo Carmen Thyssen Málaga (listados propios).
- `sources/generic_scraper.py` → Fallback: extrae enlaces del listado y parsea la **ficha de detalle** (título, imagen, fechas).
- `sources/rss_scraper.py` → Si hay feed, úsalo primero.

`config/institutions.yaml` define URLs por sede.  
El colector `scripts/collect.py` intenta: **scraper específico → RSS → genérico**.

## Ejecutar
```
PYTHONPATH=. python scripts/collect.py
```
o en **GitHub Actions** (workflow incluido).

## Notas
- Para **actividades**, si no hay hora clara en la ficha, se deja la fecha con `00:00` (editables en la app).
- Detección de **cancelado/aplazado** por texto.
