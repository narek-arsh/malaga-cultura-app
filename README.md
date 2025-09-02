# Agenda Cultural Málaga (MVP)

App de Streamlit + recolector automático para exposiciones y actividades.
Empezamos con **Museo Picasso Málaga** y luego iremos sumando sedes sin romper lo anterior.

## Estructura
```
config/
  institutions.yaml      # activar/desactivar sedes
scrapers/
  __init__.py
  mpm.py                 # scraper Picasso
data/
  events.json            # generado por el workflow
  manual_events.json     # entradas manuales (editar si hace falta)
  meta.json              # info del último build
app/
  streamlit_app.py       # interfaz Streamlit
.github/workflows/
  collect.yml            # ejecuta el recolector a diario y a botón
scripts/
  collect.py             # orquestador
requirements.txt
README.md
```

## Cómo usar (rápido)
1. **Sube este repo a GitHub.**
2. Abre la pestaña **Actions** del repo y pulsa **Run workflow** (esto genera `data/events.json`).
3. Lanza la app localmente:
   ```bash
   pip install -r requirements.txt
   streamlit run app/streamlit_app.py
   ```
   o despliega en Streamlit Cloud apuntando a `app/streamlit_app.py`.
4. Para añadir/eliminar sedes, edita `config/institutions.yaml` (solo `enabled: true/false`).

## Manual events
- Edita `data/manual_events.json` o usa el editor dentro de la app (expansor).
- Las entradas manuales tienen prioridad sobre las del scraper si coinciden en el mismo `id`.

## Notas
- El scraper de MPM se apoya en el HTML público; si la web cambia, solo hay que tocar `scrapers/mpm.py`.
- La app muestra **todo** (filtros desactivados por ahora), ordenado por fecha y, a igualdad, por título.
- Horario europeo: `Europe/Madrid`.
