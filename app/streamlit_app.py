import os, sys, json
import streamlit as st
from datetime import date, datetime, timedelta, time
from typing import List, Dict, Any
import yaml

ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mc_utils.storage import load_json, save_json_local, github_upsert_file
from mc_utils.model import make_event_id, now_iso

APP_TITLE = "Málaga · Agenda cultural"
BUILD_PATH = os.path.join(ROOT, "build", "events.json")
MANUAL_PATH = os.path.join(ROOT, "data", "manual.json")
CFG_PATH = os.path.join(ROOT, "config", "institutions.yaml")

# ✅ Interruptor: desactivar filtros (True = filtros activados; False = desactivados)
FILTERS_ENABLED = False

st.set_page_config(page_title=APP_TITLE, layout="wide")

@st.cache_data
def load_cfg():
    with open(CFG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg

@st.cache_data
def load_events() -> List[Dict[str, Any]]:
    return load_json(BUILD_PATH, [])

def ensure_session_state():
    if "page_size" not in st.session_state:
        st.session_state.page_size = 24
    if "offset" not in st.session_state:
        st.session_state.offset = 0
    if "inst_filter" not in st.session_state:
        st.session_state.inst_filter = "Todas"
    if "show_nodate" not in st.session_state:
        st.session_state.show_nodate = True  # solo útil cuando activemos filtros

def human_date(ev: Dict) -> str:
    if ev["type"] == "exhibition":
        ds = ev.get("date_start")
        de = ev.get("date_end")
        if ds and de:
            d1 = datetime.fromisoformat(ds).strftime("%d/%m")
            d2 = datetime.fromisoformat(de).strftime("%d/%m")
            return f"{d1} – {d2}"
        elif ds:
            return datetime.fromisoformat(ds).strftime("%d/%m")
        elif de:
            return datetime.fromisoformat(de).strftime("%d/%m")
        return ""
    else:
        ds = ev.get("datetime_start")
        de = ev.get("datetime_end")
        if ds and de:
            d1 = datetime.fromisoformat(ds.replace("Z",""))
            d2 = datetime.fromisoformat(de.replace("Z",""))
            if d1.date() == d2.date():
                return f"{d1.strftime('%d/%m · %H:%M')}–{d2.strftime('%H:%M')}"
            return f"{d1.strftime('%d/%m · %H:%M')} – {d2.strftime('%d/%m · %H:%M')}"
        elif ds:
            d1 = datetime.fromisoformat(ds.replace("Z",""))
            return f"{d1.strftime('%d/%m · %H:%M')}"
        d2 = ev.get("date_start")
        if d2:
            d = datetime.fromisoformat(d2)
            return d.strftime("%d/%m")
        return ""

def render_card(ev: Dict, col):
    with col:
        if ev.get("image_url"):
            st.image(ev["image_url"], use_column_width=True)
        title = ev.get("title","(Sin título)")
        inst = ev.get("institution")
        date_txt = human_date(ev)
        status = ev.get("status","scheduled")
        badge = ""
        if status in ["cancelled","postponed"]:
            badge = f" · **{status.upper()}**"
        st.markdown(f"**{title}**")
        if ev.get("description"):
            st.caption(ev["description"])
        st.markdown(f"**{date_txt}** · {inst}{badge}")
        links = []
        if ev.get("detail_url"):
            links.append(f"[Más info]({ev['detail_url']})")
        if ev.get("tickets_url"):
            links.append(f"[Entradas y horarios]({ev['tickets_url']})")
        if ev.get("price"):
            links.append(f"💶 {ev['price']}")
        if links:
            st.markdown(" · ".join(links))

def manual_form(institutions: List[str]):
    st.subheader("Añadir / editar evento (entrada manual)")
    with st.form("manual_form", clear_on_submit=False):
        ev_type = st.selectbox("Tipo", ["exhibition", "activity", "permanent"])
        inst = st.selectbox("Institución", institutions)
        title = st.text_input("Título")
        description = st.text_area("Descripción", height=100)
        image_url = st.text_input("Imagen (URL)")
        detail_url = st.text_input("Enlace detalle")
        tickets_url = st.text_input("Entradas y horarios (URL)")
        status = st.selectbox("Estado", ["scheduled", "ongoing", "cancelled", "postponed"])
        price = st.text_input("Precio (texto libre)")

        col1, col2, col3 = st.columns(3)
        date_start = None; date_end = None
        datetime_start = None; datetime_end = None

        if ev_type == "exhibition":
            ds = col1.date_input("Fecha inicio", value=date.today())
            has_end = col2.toggle("Añadir fecha fin", value=True)
            de = None
            if has_end:
                de = col3.date_input("Fecha fin", value=date.today())
            date_start = ds.isoformat() if ds else None
            date_end = de.isoformat() if de else None

        elif ev_type == "activity":
            ds = col1.date_input("Fecha (actividad)", value=date.today())
            tstart = col2.time_input("Hora inicio", value=time(19,0))
            has_tend = col3.toggle("Añadir hora fin", value=False)
            tend = None
            if has_tend:
                tend = st.time_input("Hora fin", value=time(21,0), step=300)
            offset = "+02:00"
            if ds and tstart:
                datetime_start = f"{ds.isoformat()}T{tstart.strftime('%H:%M')}:00{offset}"
            if ds and tend:
                datetime_end = f"{ds.isoformat()}T{tend.strftime('%H:%M')}:00{offset}"

        submitted = st.form_submit_button("Guardar / Actualizar")
        if submitted:
            cfg = load_cfg()
            inst_id = next((i["id"] for i in cfg["institutions"] if i["name"] == inst), "custom")
            eid = make_event_id(detail_url if detail_url else None, inst_id, title or "")
            item = {
                "id": eid,
                "type": ev_type,
                "institution": inst,
                "institution_id": inst_id,
                "title": title or "(Sin título)",
                "description": description or None,
                "image_url": image_url or None,
                "detail_url": detail_url or None,
                "tickets_url": tickets_url or None,
                "status": status,
                "date_start": date_start,
                "date_end": date_end,
                "datetime_start": datetime_start,
                "datetime_end": datetime_end,
                "price": price or None,
                "first_seen": now_iso(),
                "last_seen": now_iso(),
                "last_changed": now_iso(),
                "source": "manual"
            }
            manual = load_json(MANUAL_PATH, [])
            found = False
            for i, e in enumerate(manual):
                if e["id"] == eid:
                    manual[i] = item
                    found = True
                    break
            if not found:
                manual.append(item)

            token = os.getenv("GITHUB_TOKEN", "")
            repo_owner = os.getenv("REPO_OWNER", "")
            repo_name = os.getenv("REPO_NAME", "")
            branch = os.getenv("BRANCH", "main")
            if token and repo_owner and repo_name:
                ok = github_upsert_file(
                    repo_owner=repo_owner,
                    repo_name=repo_name,
                    branch=branch,
                    path="data/manual.json",
                    content_str=json.dumps(manual, ensure_ascii=False, indent=2),
                    message=f"chore: manual upsert {eid}",
                    token=token
                )
                if ok:
                    st.success("Guardado en el repositorio (manual.json actualizado).")
                else:
                    save_json_local(MANUAL_PATH, manual)
                    st.warning("No se pudo subir a GitHub. Se guardó localmente en el contenedor.")
            else:
                save_json_local(MANUAL_PATH, manual)
                st.info("No hay credenciales de GitHub. Descarga manual.json y súbelo por PR.")
                st.download_button(
                    "Descargar manual.json",
                    data=json.dumps(manual, ensure_ascii=False, indent=2),
                    file_name="manual.json",
                    mime="application/json"
                )

def primary_date_str(e: Dict) -> str:
    """
    Fecha principal para ordenar:
    - Exhibiciones: date_start > date_end > datetime_start > datetime_end
    - Actividades: datetime_start > date_start > datetime_end > date_end
    Fallback: '9999-12-31' (empuja al final)
    """
    def pick(*keys):
        for k in keys:
            v = e.get(k)
            if v:
                return v[:10] if "datetime" in k else v
        return None

    if e.get("type") == "exhibition":
        d = pick("date_start", "date_end", "datetime_start", "datetime_end")
    else:
        d = pick("datetime_start", "date_start", "datetime_end", "date_end")
    return d or "9999-12-31"

def main():
    st.title(APP_TITLE)
    cfg = load_cfg()
    ensure_session_state()

    # Sidebar: sin filtros (solo administración/paginación)
    inst_names = [i["name"] for i in cfg["institutions"]]
    with st.sidebar:
        st.header("Administración")
        if not FILTERS_ENABLED:
            st.caption("Filtros desactivados temporalmente.")
        st.number_input("Tamaño de página", 8, 60, key="page_size")
        st.divider()
        manual_form(inst_names)

    # Datos
    events = load_events()

    # ✅ Sin filtros: mostramos TODO, solo ordenamos por fecha y título
    shown = sorted(
        events,
        key=lambda e: (primary_date_str(e), e.get("title", ""))
    )

    # Diagnóstico simple
    total = len(events)
    con_fecha = sum(1 for e in events if (e.get("date_start") or e.get("date_end") or e.get("datetime_start") or e.get("datetime_end")))
    st.caption(f"Eventos capturados: {total} · Con fecha: {con_fecha} · Sin fecha: {total - con_fecha} · (Filtros: OFF)")

    # Paginación
    start = st.session_state.offset
    end = start + st.session_state.page_size
    page = shown[start:end]

    st.subheader(f"Resultados ({len(shown)})")
    if not page:
        st.info("No hay eventos cargados todavía.")
    else:
        row_cols = st.columns(4)
        for idx, ev in enumerate(page):
            if idx % 4 == 0 and idx != 0:
                row_cols = st.columns(4)
            render_card(ev, row_cols[idx % 4])

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.session_state.offset > 0 and st.button("⬅️ Anteriores"):
                st.session_state.offset = max(0, st.session_state.offset - st.session_state.page_size)
                st.rerun()
        with c2:
            if end < len(shown) and st.button("Cargar más ⬇️"):
                st.session_state.offset = end
                st.rerun()
        with c3:
            if st.session_state.offset > 0 and st.button("🔝 Volver al inicio"):
                st.session_state.offset = 0
                st.rerun()

if __name__ == "__main__":
    main()
