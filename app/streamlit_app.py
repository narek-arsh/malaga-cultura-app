# -*- coding: utf-8 -*-
import os, json, hashlib
from datetime import datetime, date, time
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(__file__))
EVENTS_PATH = os.path.join(ROOT, "data", "events.json")
MANUAL_PATH = os.path.join(ROOT, "data", "manual_events.json")

st.set_page_config(page_title="Agenda cultural · Málaga", page_icon="🖼️", layout="wide")

st.title("Agenda cultural · Málaga (MVP)")
st.caption("Fuente inicial: Museo Picasso Málaga. Próximamente: Thyssen, Pompidou…")

# --- Utilities ---------------------------------------------------------------
MESES = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"]
DIAS  = ["lun","mar","mié","jue","vie","sáb","dom"]

def fmt_fecha_rango(d1: str, d2: str) -> str:
    y1, m1, d_1 = d1.split("-")
    y2, m2, d_2 = d2.split("-")
    m1n, m2n = int(m1), int(m2)
    if d1 == d2:
        return f"{int(d_1)} {MESES[m1n-1]} {y1}"
    if y1 == y2 and m1 == m2:
        return f"{int(d_1)}–{int(d_2)} {MESES[m1n-1]} {y1}"
    if y1 == y2:
        return f"{int(d_1)} {MESES[m1n-1]} – {int(d_2)} {MESES[m2n-1]} {y1}"
    return f"{int(d_1)} {MESES[m1n-1]} {y1} – {int(d_2)} {MESES[m2n-1]} {y2}"

def fmt_horario(dt1: str, dt2: str, all_day: bool) -> str:
    # dt in ISO with TZ e.g., 2025-09-20T11:00:00+02:00
    d1 = datetime.fromisoformat(dt1.replace("Z","+00:00"))
    d2 = datetime.fromisoformat(dt2.replace("Z","+00:00"))
    dia = DIAS[d1.weekday()]
    if all_day:
        return f"{dia} {d1.day} {MESES[d1.month-1]} {d1.year} · todo el día"
    if d1.date() == d2.date():
        return f"{dia} {d1.day} {MESES[d1.month-1]} {d1.year} · {d1.strftime('%H:%M')}–{d2.strftime('%H:%M')}"
    return f"{dia} {d1.day} {MESES[d1.month-1]} {d1.year} · {d1.strftime('%H:%M')} → {d2.day} {MESES[d2.month-1]} {d2.year} {d2.strftime('%H:%M')}"

@st.cache_data(ttl=0, show_spinner=False)
def load_events():
    try:
        with open(EVENTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

events = load_events()

# --- Controls (filters off for now) -----------------------------------------
cols = st.columns([1,1,1,1,1])
with cols[0]:
    if st.button("🔄 Recargar datos", use_container_width=True):
        st.cache_data.clear()
        st.experimental_rerun()
with cols[1]:
    show_past = st.toggle("Mostrar pasados", value=False)

st.divider()

# --- List (cards) ------------------------------------------------------------
def is_past(e: dict) -> bool:
    if e.get("type") == "exhibition":
        return e.get("date_end","9999") < datetime.now().strftime("%Y-%m-%d")
    else:
        return e.get("datetime_end","9999") < datetime.now().isoformat()

shown = 0
for e in sorted(events, key=lambda x: (x.get("date_start") or x.get("datetime_start") or "9999", x.get("title",""))):
    if not show_past and is_past(e):
        continue
    with st.container():
        cols = st.columns([1,3])
        with cols[0]:
            if e.get("image_url"):
                st.image(e["image_url"], use_column_width=True)
        with cols[1]:
            st.subheader(e.get("title","(sin título)"))
            st.caption(e.get("institution_name",""))
            # date line
            if e.get("type") == "exhibition":
                line = fmt_fecha_rango(e["date_start"], e["date_end"])
                # badge en curso
                today = datetime.now().strftime("%Y-%m-%d")
                if e["date_start"] <= today <= e["date_end"]:
                    st.markdown(f"**{line}** · 🟢 *En curso*")
                else:
                    st.markdown(f"**{line}**")
            else:
                st.markdown(f"**{fmt_horario(e['datetime_start'], e['datetime_end'], e.get('all_day', False))}**")
            if e.get("description"):
                st.write(e["description"])
            if e.get("url"):
                st.link_button("Ficha oficial", e["url"], use_container_width=False)
        st.divider()
        shown += 1

if shown == 0:
    st.info("De momento no hay eventos para mostrar. Prueba a activar 'Mostrar pasados' o vuelve más tarde.")

# --- Manual editor (optional) -----------------------------------------------
with st.expander("✍️ Alta/edición manual (avanzado)"):
    try:
        with open(MANUAL_PATH, "r", encoding="utf-8") as f:
            manual = json.load(f)
    except Exception:
        manual = []
    edited = st.data_editor(manual, num_rows="dynamic", use_container_width=True)
    if st.button("💾 Guardar manual_events.json"):
        try:
            with open(MANUAL_PATH, "w", encoding="utf-8") as f:
                json.dump(edited, f, ensure_ascii=False, indent=2)
            st.success("Guardado. (Si estás en Streamlit Cloud, recuerda *commit* para persistir cambios.)")
        except Exception as ex:
            st.error(f"No se pudo guardar: {ex}")
