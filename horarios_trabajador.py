import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
from fpdf import FPDF
from io import BytesIO

# ─────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────
TRABAJADORES = ["Manu", "Jorge", "Babi", "Nico"]
DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

COLORES_TRABAJADOR = {
    "Manu":  "#378ADD",
    "Jorge": "#1D9E75",
    "Babi":  "#D4537E",
    "Nico":  "#BA7517",
}

# ─────────────────────────────────────────────
# BASE DE DATOS
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("horarios_trabajador.db")
    c = conn.cursor()

    # Crear tabla si no existe (esquema nuevo con trabajador)
    c.execute("""
        CREATE TABLE IF NOT EXISTS registros (
            semana_inicio TEXT,
            trabajador    TEXT,
            dia           TEXT,
            entrada       TEXT,
            salida        TEXT,
            bruto         REAL,
            neto          REAL,
            extra         REAL,
            es_libre      INTEGER,
            PRIMARY KEY (semana_inicio, trabajador, dia)
        )
    """)

    # ── Migración: agregar columna 'trabajador' si la BD es del esquema viejo ──
    columnas_existentes = [row[1] for row in c.execute("PRAGMA table_info(registros)")]
    if "trabajador" not in columnas_existentes:
        # 1. Agregar la columna con valor por defecto temporal
        c.execute("ALTER TABLE registros ADD COLUMN trabajador TEXT DEFAULT 'Nico'")
        # 2. Reconstruir la tabla para aplicar la PRIMARY KEY correcta
        c.execute("""
            CREATE TABLE registros_nuevo (
                semana_inicio TEXT,
                trabajador    TEXT,
                dia           TEXT,
                entrada       TEXT,
                salida        TEXT,
                bruto         REAL,
                neto          REAL,
                extra         REAL,
                es_libre      INTEGER,
                PRIMARY KEY (semana_inicio, trabajador, dia)
            )
        """)
        c.execute("""
            INSERT OR IGNORE INTO registros_nuevo
            SELECT semana_inicio, trabajador, dia, entrada, salida,
                   bruto, neto, extra, es_libre
            FROM registros
        """)
        c.execute("DROP TABLE registros")
        c.execute("ALTER TABLE registros_nuevo RENAME TO registros")

    conn.commit()
    conn.close()


def guardar_semana(df: pd.DataFrame, semana: str, trabajador: str):
    conn = sqlite3.connect("horarios_trabajador.db")
    c = conn.cursor()
    c.execute(
        "DELETE FROM registros WHERE semana_inicio = ? AND trabajador = ?",
        (semana, trabajador),
    )
    for _, row in df.iterrows():
        c.execute(
            "INSERT OR REPLACE INTO registros VALUES (?,?,?,?,?,?,?,?,?)",
            (
                semana,
                trabajador,
                row["Día"],
                row["Entrada"],
                row["Salida"],
                row["Bruto (h)"],
                row["Neto (h)"],
                row["Extras (h)"],
                1 if row["Entrada"] == "LIBRE" else 0,
            ),
        )
    conn.commit()
    conn.close()


def cargar_semana(semana: str, trabajador: str) -> pd.DataFrame:
    conn = sqlite3.connect("horarios_trabajador.db")
    df = pd.read_sql_query(
        """SELECT dia as 'Día', entrada as 'Entrada', salida as 'Salida',
                  bruto as 'Bruto (h)', neto as 'Neto (h)', extra as 'Extras (h)'
           FROM registros
           WHERE semana_inicio = ? AND trabajador = ?
           ORDER BY rowid""",
        conn,
        params=(semana, trabajador),
    )
    conn.close()
    return df


def semanas_disponibles() -> list[str]:
    conn = sqlite3.connect("horarios_trabajador.db")
    df = pd.read_sql_query(
        "SELECT DISTINCT semana_inicio FROM registros ORDER BY semana_inicio DESC", conn
    )
    conn.close()
    return df["semana_inicio"].tolist()


def cargar_semana_todos(semana: str) -> pd.DataFrame:
    conn = sqlite3.connect("horarios_trabajador.db")
    df = pd.read_sql_query(
        """SELECT trabajador as 'Trabajador', dia as 'Día',
                  entrada as 'Entrada', salida as 'Salida',
                  bruto as 'Bruto (h)', neto as 'Neto (h)', extra as 'Extras (h)',
                  es_libre
           FROM registros
           WHERE semana_inicio = ?
           ORDER BY trabajador, rowid""",
        conn,
        params=(semana,),
    )
    conn.close()
    return df


init_db()

# ─────────────────────────────────────────────
# LÓGICA DE CÁLCULO
# ─────────────────────────────────────────────
def calcular_turno(dia: str, ent: time, sal: time) -> dict:
    dt_in = datetime.combine(datetime.today(), ent)
    dt_out = datetime.combine(datetime.today(), sal)
    if sal < ent:
        dt_out += timedelta(days=1)

    dur = (dt_out - dt_in).total_seconds() / 3600
    ext = 0.0

    if dia == "Domingo":
        ext = dur
    elif dia == "Sábado":
        if sal < ent:  # turno que cruza medianoche Sáb→Dom
            mediana = datetime.combine(dt_out.date(), time(0, 0))
            lim = datetime.combine(dt_out.date(), time(3, 0))
            ext = (min(dt_out, lim) - mediana).total_seconds() / 3600 if dt_out > mediana else 0.0
        elif ent < time(3, 0):  # madrugada Vie→Sáb
            lim = datetime.combine(dt_in.date(), time(3, 0))
            ext = (min(dt_out, lim) - dt_in).total_seconds() / 3600

    neto = max(0.0, dur - 1) if dur > 1 else dur
    return {
        "bruto": round(dur, 2),
        "neto": round(neto, 2),
        "extras": round(ext, 2),
    }


def construir_df(registros_inputs: dict) -> pd.DataFrame:
    filas = []
    for dia in DIAS:
        reg = registros_inputs[dia]
        if reg["libre"]:
            filas.append(
                {"Día": dia, "Entrada": "LIBRE", "Salida": "LIBRE",
                 "Bruto (h)": 0.0, "Neto (h)": 0.0, "Extras (h)": 0.0}
            )
        else:
            calc = calcular_turno(dia, reg["in"], reg["out"])
            filas.append(
                {"Día": dia,
                 "Entrada": reg["in"].strftime("%H:%M"),
                 "Salida": reg["out"].strftime("%H:%M"),
                 "Bruto (h)": calc["bruto"],
                 "Neto (h)": calc["neto"],
                 "Extras (h)": calc["extras"]}
            )
    return pd.DataFrame(filas)


# ─────────────────────────────────────────────
# EXPORTACIÓN
# ─────────────────────────────────────────────
def generar_pdf(df: pd.DataFrame, titulo: str, totales: pd.Series) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, titulo, ln=True, align="C")
    pdf.ln(4)

    columnas = df.columns.tolist()
    ancho_col = 190 // len(columnas)

    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(220, 220, 220)
    for col in columnas:
        pdf.cell(ancho_col, 9, col, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        for val in row:
            pdf.cell(ancho_col, 8, str(val), border=1)
        pdf.ln()

    pdf.ln(4)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(
        0, 9,
        f"Total Neto: {totales['Neto (h)']:.2f} h  |  Total Extras: {totales['Extras (h)']:.2f} h",
        ln=True,
    )
    return pdf.output(dest="S").encode("latin-1")


def generar_excel(df: pd.DataFrame, sheet: str = "Horarios") -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet)
    return buf.getvalue()


# ─────────────────────────────────────────────
# GRÁFICO GANTT
# ─────────────────────────────────────────────
def tiempo_a_horas(t_str: str) -> float | None:
    """Convierte 'HH:MM' a horas decimales. Retorna None si es LIBRE."""
    if t_str == "LIBRE":
        return None
    h, m = map(int, t_str.split(":"))
    return h + m / 60


def gantt_semanal(semana: str):
    df_todos = cargar_semana_todos(semana)
    if df_todos.empty:
        st.info("No hay datos para esta semana.")
        return

    # Eje X: 9.0 → 27.0 (= 03:00 del día siguiente)
    X_MIN, X_MAX = 9.0, 27.0

    fig = go.Figure()

    # Invertir orden de días para que Lunes quede arriba
    dias_orden = list(reversed(DIAS))

    for trabajador in TRABAJADORES:
        df_w = df_todos[df_todos["Trabajador"] == trabajador]
        if df_w.empty:
            continue

        x_starts, x_ends, hover_texts = [], [], []

        for dia in dias_orden:
            fila = df_w[df_w["Día"] == dia]
            if fila.empty or fila.iloc[0]["es_libre"] == 1:
                x_starts.append(None)
                x_ends.append(None)
                hover_texts.append(f"{dia} — libre")
                continue

            row = fila.iloc[0]
            hi = tiempo_a_horas(row["Entrada"])
            ho = tiempo_a_horas(row["Salida"])

            # Turno nocturno cruza medianoche
            if ho is not None and hi is not None and ho <= hi:
                ho += 24

            # Clamp al rango del eje
            hi_clamped = max(hi, X_MIN) if hi else X_MIN
            ho_clamped = min(ho, X_MAX) if ho else X_MIN

            x_starts.append(hi_clamped)
            x_ends.append(ho_clamped)
            hover_texts.append(
                f"<b>{trabajador}</b> — {dia}<br>"
                f"Entrada: {row['Entrada']}  Salida: {row['Salida']}<br>"
                f"Neto: {row['Neto (h)']:.1f} h  Extras: {row['Extras (h)']:.1f} h"
            )

        # Barras flotantes: base = x_start, width = x_end - x_start
        widths = [
            (e - s) if (s is not None and e is not None) else 0
            for s, e in zip(x_starts, x_ends)
        ]
        bases = [s if s is not None else X_MIN for s in x_starts]

        fig.add_trace(
            go.Bar(
                name=trabajador,
                y=dias_orden,
                x=widths,
                base=bases,
                orientation="h",
                marker_color=COLORES_TRABAJADOR[trabajador],
                marker_line_color="rgba(0,0,0,0.25)",
                marker_line_width=0.8,
                text=[f"{w:.1f}h" if w > 0 else "" for w in widths],
                textposition="inside",
                insidetextanchor="middle",
                hovertemplate="%{customdata}<extra></extra>",
                customdata=hover_texts,
            )
        )

    # Ticks eje X: 09:00 → 03:00
    tick_vals = list(range(int(X_MIN), int(X_MAX) + 1))
    tick_labels = [
        f"{h:02d}:00" if h < 24 else f"{h - 24:02d}:00"
        for h in tick_vals
    ]

    fig.update_layout(
        barmode="group",
        bargap=0.25,
        bargroupgap=0.08,
        height=420,
        margin=dict(l=90, r=20, t=30, b=50),
        xaxis=dict(
            range=[X_MIN, X_MAX],
            tickvals=tick_vals,
            ticktext=tick_labels,
            title="Hora del día",
            gridcolor="rgba(120,120,120,0.15)",
            zeroline=False,
        ),
        yaxis=dict(
            title="",
            gridcolor="rgba(120,120,120,0.08)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
    )

    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────
# INTERFAZ STREAMLIT
# ─────────────────────────────────────────────
st.set_page_config(page_title="LiveOps · Horarios", layout="wide")
st.title("LiveOps — Gestor de Horarios")

tab_reg, tab_hist, tab_gantt = st.tabs(
    ["📝 Registro", "📊 Historial y Exportación", "📈 Gráfico Semanal"]
)

# ═══════════════════════════════════════════════
# TAB 1 — REGISTRO
# ═══════════════════════════════════════════════
with tab_reg:
    col_fecha, col_trab = st.columns([2, 2])
    with col_fecha:
        fecha_ref = st.date_input("Semana:", datetime.now(), key="reg_fecha")
    with col_trab:
        trabajador_sel = st.selectbox("Trabajador:", TRABAJADORES, key="reg_trab")

    inicio_sem = (fecha_ref - timedelta(days=fecha_ref.weekday())).strftime("%Y-%m-%d")
    st.caption(f"Semana del {inicio_sem}")

    registros_inputs: dict = {}
    cols_input = st.columns(7)

    for i, dia in enumerate(DIAS):
        with cols_input[i]:
            st.markdown(f"**{dia[:3]}**")
            libre = st.checkbox("Libre", key=f"l_{dia}_{trabajador_sel}")
            if libre:
                registros_inputs[dia] = {"in": None, "out": None, "libre": True}
            else:
                ent = st.time_input("In", time(9, 0), key=f"i_{dia}_{trabajador_sel}")
                sal = st.time_input("Out", time(15, 0), key=f"s_{dia}_{trabajador_sel}")
                registros_inputs[dia] = {"in": ent, "out": sal, "libre": False}

    df_actual = construir_df(registros_inputs)

    # Métricas resumen
    totales_act = df_actual[["Bruto (h)", "Neto (h)", "Extras (h)"]].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("Horas brutas", f"{totales_act['Bruto (h)']:.2f} h")
    m2.metric("Horas netas", f"{totales_act['Neto (h)']:.2f} h")
    m3.metric("Horas extra", f"{totales_act['Extras (h)']:.2f} h")

    st.table(df_actual)

    if st.button(f"💾 Guardar turno de {trabajador_sel}"):
        guardar_semana(df_actual, inicio_sem, trabajador_sel)
        st.success(f"Turno de **{trabajador_sel}** para la semana {inicio_sem} guardado.")

# ═══════════════════════════════════════════════
# TAB 2 — HISTORIAL Y EXPORTACIÓN
# ═══════════════════════════════════════════════
with tab_hist:
    semanas = semanas_disponibles()

    if not semanas:
        st.info("No hay datos históricos. Ve a Registro para guardar la primera semana.")
    else:
        col_s, col_t = st.columns([2, 2])
        with col_s:
            semana_sel = st.selectbox("Semana:", semanas, key="hist_sem")
        with col_t:
            trab_sel = st.selectbox(
                "Trabajador:", ["Todos"] + TRABAJADORES, key="hist_trab"
            )

        if trab_sel == "Todos":
            df_hist = cargar_semana_todos(semana_sel).drop(columns=["es_libre"], errors="ignore")
        else:
            df_hist = cargar_semana(semana_sel, trab_sel)

        if df_hist.empty:
            st.warning("Sin datos para esta combinación.")
        else:
            st.dataframe(df_hist, use_container_width=True, hide_index=True)

            totales_h = df_hist[["Bruto (h)", "Neto (h)", "Extras (h)"]].sum()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Bruto", f"{totales_h['Bruto (h)']:.2f} h")
            m2.metric("Total Neto", f"{totales_h['Neto (h)']:.2f} h")
            m3.metric("Total Extras", f"{totales_h['Extras (h)']:.2f} h")

            st.divider()
            st.subheader("📥 Descargar reporte")
            col_pdf, col_xl = st.columns(2)

            titulo_pdf = (
                f"Horarios semana {semana_sel}"
                if trab_sel == "Todos"
                else f"Horarios {trab_sel} — semana {semana_sel}"
            )
            nombre_base = f"Reporte_{semana_sel}_{trab_sel}"

            with col_pdf:
                pdf_bytes = generar_pdf(df_hist, titulo_pdf, totales_h)
                st.download_button(
                    "⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=f"{nombre_base}.pdf",
                    mime="application/pdf",
                )

            with col_xl:
                xl_bytes = generar_excel(df_hist)
                st.download_button(
                    "⬇️ Descargar Excel",
                    data=xl_bytes,
                    file_name=f"{nombre_base}.xlsx",
                )

# ═══════════════════════════════════════════════
# TAB 3 — GRÁFICO GANTT
# ═══════════════════════════════════════════════
with tab_gantt:
    semanas_g = semanas_disponibles()
    if not semanas_g:
        st.info("Guarda al menos una semana para ver el gráfico.")
    else:
        semana_g = st.selectbox("Semana a visualizar:", semanas_g, key="gantt_sem")
        st.caption(
            "Eje X: horas del día (09:00 → 03:00). "
            "Cada barra es el turno de un trabajador. Los días libres no aparecen."
        )
        gantt_semanal(semana_g)