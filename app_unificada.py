import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
from fpdf import FPDF

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Sistema Integral Horarios PRO", layout="wide", page_icon="📅")

DB_ESTUDIOS = 'horario_estudios.db'
DB_LABORAL  = 'horarios.db'

DIAS_ORDEN = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# --- BASE DE DATOS ---

def query_db(db, sql, params=(), fetch=False):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        if fetch:
            return cursor.fetchall()

def read_df(db, sql, params=()):
    with sqlite3.connect(db) as conn:
        return pd.read_sql_query(sql, conn, params=params)

def init_dbs():
    query_db(DB_ESTUDIOS,
        'CREATE TABLE IF NOT EXISTS clases '
        '(semana_inicio TEXT, dia TEXT, asignatura TEXT, entrada TEXT, salida TEXT, horas REAL)')
    query_db(DB_LABORAL,
        'CREATE TABLE IF NOT EXISTS registros '
        '(semana_inicio TEXT, dia TEXT, entrada TEXT, salida TEXT, '
        'bruto REAL, neto REAL, extra REAL, es_libre INTEGER)')

init_dbs()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🚀 Panel de Control")
    opcion = st.radio("Módulos Disponibles:", [
        "📝 Registro: Horario Estudio",
        "📝 Registro: Horario Laboral",
        "📄 Impresión: Horario Completo",
        "📄 Impresión: Horario Estudio",
        "📄 Impresión: Horario Laboral",
        "📊 Gantt: Visualización Semanal",
    ])
    st.divider()
    if st.button("🧹 Limpiar Cache"):
        st.cache_data.clear()
        st.rerun()

# --- HELPERS ---

def get_semana_inicio(fecha):
    return (fecha - timedelta(days=fecha.weekday())).strftime('%Y-%m-%d')

def hora_a_decimal(h_str):
    """Convierte 'HH:MM' a decimal. Horas < 8 se consideran del día siguiente (ej: 01:00 → 25.0)."""
    if not h_str or h_str == "LIBRE":
        return None
    hh, mm = map(int, h_str.split(":"))
    dec = hh + mm / 60
    if hh < 8:
        dec += 24
    return dec

def calcular_horas_turno(dia, hora_in, hora_out):
    """Devuelve (bruto, neto, extra) para un turno dado."""
    dt_i = datetime.combine(datetime.today(), hora_in)
    dt_o = datetime.combine(datetime.today(), hora_out)
    if hora_out < hora_in:
        dt_o += timedelta(days=1)
    bruto = (dt_o - dt_i).total_seconds() / 3600
    neto  = max(0, bruto - 1) if bruto > 1 else bruto
    if dia == "Domingo":
        extra = bruto
    elif dia == "Sábado" and hora_out < hora_in:
        # Cuenta solo las horas entre medianoche y las 03:00 como extras de trasnoche
        medianoche = datetime.combine(dt_o.date(), time(0, 0))
        limite_03  = datetime.combine(dt_o.date(), time(3, 0))
        extra = min(3.0, (min(dt_o, limite_03) - medianoche).total_seconds() / 3600)
    else:
        extra = 0
    return round(bruto, 2), round(neto, 2), round(extra, 2)

# --- PDF ---

def generar_pdf_estudio(df, sem):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(0, 100, 0)
    pdf.cell(190, 10, "HORARIO SANTO TOMÁS", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 7, f"Semana: {sem}", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(200, 230, 200)
    for col, w in [("Día", 30), ("Asignatura", 80), ("Inicio", 25), ("Fin", 25), ("Horas", 30)]:
        pdf.cell(w, 8, col, 1, fill=True)
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    for _, r in df.iterrows():
        pdf.set_text_color(0, 80, 0)
        pdf.cell(30, 7, str(r.get('Día',        r.get('dia',       ''))), 1)
        pdf.cell(80, 7, str(r.get('Asignatura', r.get('asignatura',''))), 1)
        pdf.cell(25, 7, str(r.get('Inicio',     r.get('entrada',   ''))), 1)
        pdf.cell(25, 7, str(r.get('Fin',        r.get('salida',    ''))), 1)
        pdf.cell(30, 7, f"{r.get('Horas',       r.get('horas',     ''))}h", 1, ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    total = df.get('Horas', df.get('horas', pd.Series([0]))).sum()
    pdf.cell(190, 8, f"Total Semanal: {round(total, 2)} h", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

def generar_pdf_laboral(df, sem):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.set_text_color(160, 0, 0)
    pdf.cell(190, 10, "HORARIO PEDIDOSYA", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.cell(190, 7, f"Semana: {sem}", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(255, 210, 210)
    for col, w in [("Día", 30), ("Entrada", 28), ("Salida", 28), ("Bruto", 28), ("Neto", 28), ("Extra", 28)]:
        pdf.cell(w, 8, col, 1, fill=True)
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    for _, r in df.iterrows():
        pdf.set_text_color(160, 0, 0)
        pdf.cell(30, 7, str(r.get('Día',    r.get('dia',    ''))), 1)
        pdf.cell(28, 7, str(r.get('Entrada',r.get('entrada',''))), 1)
        pdf.cell(28, 7, str(r.get('Salida', r.get('salida', ''))), 1)
        pdf.cell(28, 7, f"{r.get('Bruto',   r.get('bruto',  0))}h", 1)
        pdf.cell(28, 7, f"{r.get('Neto',    r.get('neto',   0))}h", 1)
        pdf.cell(28, 7, f"{r.get('Extra',   r.get('extra',  0))}h", 1, ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    bruto_col = df.get('Bruto', df.get('bruto', pd.Series([0])))
    neto_col  = df.get('Neto',  df.get('neto',  pd.Series([0])))
    extra_col = df.get('Extra', df.get('extra', pd.Series([0])))
    pdf.cell(190, 8,
        f"Bruto: {round(bruto_col.sum(),2)}h  |  "
        f"Neto: {round(neto_col.sum(),2)}h  |  "
        f"Extras: {round(extra_col.sum(),2)}h",
        ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- GANTT ---

def generar_gantt(df_st, df_py, semana_label):
    fig = go.Figure()

    for _, r in df_st.iterrows():
        ini = hora_a_decimal(r['entrada'])
        fin = hora_a_decimal(r['salida'])
        if ini is None or fin is None:
            continue
        if fin <= ini:
            fin += 24
        fig.add_trace(go.Bar(
            x=[fin - ini], y=[r['dia']], base=[ini],
            orientation='h',
            marker_color='rgba(34, 139, 34, 0.82)',
            marker_line=dict(color='rgba(0,100,0,1)', width=1.5),
            name='Santo Tomás',
            hovertemplate=(
                f"<b>Santo Tomás</b><br>"
                f"Asignatura: {r['asignatura']}<br>"
                f"Día: {r['dia']}<br>"
                f"Horario: {r['entrada']} – {r['salida']}<br>"
                f"Duración: {r['horas']}h<extra></extra>"
            ),
            showlegend=False,
            text=r['asignatura'], textposition='inside',
            insidetextanchor='middle',
            textfont=dict(size=10, color='white'),
        ))

    for _, r in df_py.iterrows():
        if r.get('es_libre', 0) == 1:
            continue
        ini = hora_a_decimal(r['entrada'])
        fin = hora_a_decimal(r['salida'])
        if ini is None or fin is None:
            continue
        if fin <= ini:
            fin += 24
        fig.add_trace(go.Bar(
            x=[fin - ini], y=[r['dia']], base=[ini],
            orientation='h',
            marker_color='rgba(200, 30, 30, 0.82)',
            marker_line=dict(color='rgba(140,0,0,1)', width=1.5),
            name='PeYa',
            hovertemplate=(
                f"<b>PedidosYa</b><br>"
                f"Día: {r['dia']}<br>"
                f"Turno: {r['entrada']} – {r['salida']}<br>"
                f"Neto: {r['neto']}h<extra></extra>"
            ),
            showlegend=False,
            text='PeYa', textposition='inside',
            insidetextanchor='middle',
            textfont=dict(size=10, color='white'),
        ))

    tick_horas = list(range(8, 28))
    tick_text  = [("00:00 (+1)" if h % 24 == 0 else f"{h % 24:02d}:00") for h in tick_horas]

    fig.update_layout(
        title=dict(text=f"📊 Gantt Semanal — {semana_label}", font=dict(size=18), x=0.5),
        barmode='overlay',
        xaxis=dict(
            range=[8, 28], tickvals=tick_horas, ticktext=tick_text,
            tickfont=dict(size=11), gridcolor='rgba(128,128,128,0.25)', gridwidth=1,
            title="Horario", showline=True, linecolor='rgba(128,128,128,0.4)',
        ),
        yaxis=dict(
            categoryarray=list(reversed(DIAS_ORDEN)), categoryorder='array',
            tickfont=dict(size=13), title="", gridcolor='rgba(128,128,128,0.15)',
        ),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        height=430, margin=dict(l=10, r=10, t=60, b=40),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        bargap=0.35,
    )
    fig.add_vline(x=12, line_dash="dot", line_color="rgba(128,128,128,0.35)", line_width=1)
    # Leyenda manual con categoría válida para que funcione en dark mode
    fig.add_trace(go.Bar(x=[0], y=["Lunes"], base=[8], orientation='h',
                         marker_color='rgba(34,139,34,0.82)', name='Santo Tomás', showlegend=True))
    fig.add_trace(go.Bar(x=[0], y=["Lunes"], base=[8], orientation='h',
                         marker_color='rgba(200,30,30,0.82)', name='PeYa', showlegend=True))
    return fig

# ==========================================
# 1. REGISTRO: ESTUDIO
# ==========================================
if opcion == "📝 Registro: Horario Estudio":
    st.title(":green[Horario Santo Tomas]")
    fecha_ref  = st.date_input("Semana del Lunes:", datetime.now())
    inicio_sem = get_semana_inicio(fecha_ref)

    with st.expander("➕ Añadir Nueva Clase", expanded=True):
        with st.form("form_st"):
            c1, c2  = st.columns(2)
            dia     = c1.selectbox("Día", DIAS_ORDEN)
            materia = c2.text_input("Nombre de la Asignatura", placeholder="Ej: Anatomía")
            h_in    = c1.time_input("Inicio", time(8, 30))
            h_out   = c2.time_input("Fin",    time(10, 0))

            if st.form_submit_button("Guardar"):
                dt_i = datetime.combine(datetime.today(), h_in)
                dt_o = datetime.combine(datetime.today(), h_out)
                if h_out < h_in:
                    dt_o += timedelta(days=1)
                dur = round((dt_o - dt_i).total_seconds() / 3600, 2)
                query_db(DB_ESTUDIOS,
                    "INSERT INTO clases VALUES (?,?,?,?,?,?)",
                    (inicio_sem, dia, materia, h_in.strftime("%H:%M"), h_out.strftime("%H:%M"), dur))
                st.success("Clase registrada con éxito.")

# ==========================================
# 2. REGISTRO: LABORAL
# ==========================================
elif opcion == "📝 Registro: Horario Laboral":
    st.title(":red[Horario PeYa]")
    fecha_ref     = st.date_input("Selecciona semana:", datetime.now())
    inicio_sem    = get_semana_inicio(fecha_ref)
    clases_semana = read_df(DB_ESTUDIOS,
        "SELECT dia, entrada, salida FROM clases WHERE semana_inicio=?", (inicio_sem,))

    st.markdown("### Configura tus turnos")
    inputs = {}
    cols   = st.columns(7)
    for i, d in enumerate(DIAS_ORDEN):
        with cols[i]:
            st.write(f"**{d}**")
            lib = st.checkbox("Libre", key=f"l_{d}")
            if not lib:
                ent = st.time_input("In",  time(18, 0), key=f"i_{d}")
                sal = st.time_input("Out", time(0, 0),  key=f"s_{d}")
                inputs[d] = {"in": ent, "out": sal, "libre": False}
                if not clases_semana.empty and d in clases_semana['dia'].values:
                    st.warning("⚠️ Hay clase")
            else:
                inputs[d] = {"libre": True}

    if st.button("💾 Guardar Semana Laboral"):
        data = []
        for d in DIAS_ORDEN:
            r = inputs[d]
            if r["libre"]:
                data.append((inicio_sem, d, "LIBRE", "LIBRE", 0, 0, 0, 1))
            else:
                bruto, neto, extra = calcular_horas_turno(d, r["in"], r["out"])
                data.append((inicio_sem, d,
                              r["in"].strftime("%H:%M"), r["out"].strftime("%H:%M"),
                              bruto, neto, extra, 0))

        with sqlite3.connect(DB_LABORAL) as conn:
            conn.execute("DELETE FROM registros WHERE semana_inicio=?", (inicio_sem,))
            conn.executemany("INSERT INTO registros VALUES (?,?,?,?,?,?,?,?)", data)
        st.success("Horario PeYa guardado.")

# ==========================================
# 3. IMPRESIÓN: COMPLETO
# ==========================================
elif opcion == "📄 Impresión: Horario Completo":
    st.title("📊 Análisis y Control Unificado")

    semanas = read_df(DB_ESTUDIOS, "SELECT DISTINCT semana_inicio FROM clases ORDER BY semana_inicio DESC")

    if not semanas.empty:
        sem_sel   = st.selectbox("Semana de análisis:", semanas['semana_inicio'])
        df_st     = read_df(DB_ESTUDIOS, "SELECT * FROM clases WHERE semana_inicio=?", (sem_sel,))
        df_py     = read_df(DB_LABORAL,
            "SELECT * FROM registros WHERE semana_inicio=? AND es_libre=0", (sem_sel,))
        df_py_all = read_df(DB_LABORAL,
            "SELECT * FROM registros WHERE semana_inicio=?", (sem_sel,))

        col1, col2, col3 = st.columns(3)
        col1.metric("Carga Académica",      f"{df_st['horas'].sum()}h")
        col2.metric("Carga Laboral (Neto)", f"{df_py['neto'].sum()}h")
        col3.metric("Ocupación Total",      f"{df_st['horas'].sum() + df_py['neto'].sum()}h")

        st.divider()
        st.plotly_chart(generar_gantt(df_st, df_py_all, sem_sel), use_container_width=True)
        st.divider()

        if st.button("🔥 Descargar Reporte Maestro PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, "CONTROL DE TIEMPO UNIFICADO", ln=True, align='C')
            pdf.set_font("Arial", "", 10)
            pdf.cell(190, 7, f"Semana: {sem_sel}", ln=True, align='C')
            pdf.ln(5)

            for d in DIAS_ORDEN:
                st_d = df_st[df_st['dia'] == d]
                py_d = df_py[df_py['dia'] == d]
                if st_d.empty and py_d.empty:
                    continue

                pdf.set_font("Arial", "B", 10)
                pdf.set_fill_color(230, 230, 230)
                pdf.cell(190, 8, f"--- {d.upper()} ---", 1, ln=True, fill=True)

                pdf.set_font("Arial", "", 9)
                for _, r in st_d.iterrows():
                    pdf.set_text_color(0, 80, 0)
                    pdf.cell(30, 7, "ESTUDIO", 1)
                    pdf.cell(90, 7, r['asignatura'], 1)
                    pdf.cell(20, 7, r['entrada'], 1)
                    pdf.cell(20, 7, r['salida'], 1)
                    pdf.cell(30, 7, f"{r['horas']}h", 1, ln=True)
                for _, r in py_d.iterrows():
                    pdf.set_text_color(180, 0, 0)
                    pdf.cell(30, 7, "TRABAJO", 1)
                    pdf.cell(90, 7, "PeYa", 1)
                    pdf.cell(20, 7, r['entrada'], 1)
                    pdf.cell(20, 7, r['salida'], 1)
                    pdf.cell(30, 7, f"{r['neto']}h", 1, ln=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln(2)

            st.download_button("💾 Bajar PDF Unificado",
                               pdf.output(dest='S').encode('latin-1'),
                               f"Master_{sem_sel}.pdf")

# ==========================================
# 4. IMPRESIÓN: HORARIO ESTUDIO
# ==========================================
elif opcion == "📄 Impresión: Horario Estudio":
    st.title(":green[Horario Santo Tomas]")
    semanas = read_df(DB_ESTUDIOS, "SELECT DISTINCT semana_inicio FROM clases ORDER BY semana_inicio DESC")

    if not semanas.empty:
        sem = st.selectbox("Semana:", semanas['semana_inicio'])
        df  = read_df(DB_ESTUDIOS,
            "SELECT dia as Día, asignatura as Asignatura, entrada as Inicio, "
            "salida as Fin, horas as Horas FROM clases WHERE semana_inicio=?", (sem,))
        st.table(df)
        st.metric("Total Semanal", f"{df['Horas'].sum()} h")

        st.divider()
        df_st_raw   = read_df(DB_ESTUDIOS, "SELECT * FROM clases WHERE semana_inicio=?", (sem,))
        df_py_vacio = pd.DataFrame(columns=['dia', 'entrada', 'salida', 'neto', 'es_libre'])
        st.plotly_chart(generar_gantt(df_st_raw, df_py_vacio, sem), use_container_width=True)

        st.download_button(
            label="📥 Descargar PDF Horario Estudio",
            data=generar_pdf_estudio(df, sem),
            file_name=f"Estudio_{sem}.pdf",
            mime="application/pdf",
        )
    else:
        st.info("No hay registros de clases aún.")

# ==========================================
# 5. IMPRESIÓN: HORARIO LABORAL
# ==========================================
elif opcion == "📄 Impresión: Horario Laboral":
    st.title(":red[Horario PeYa]")
    semanas = read_df(DB_LABORAL, "SELECT DISTINCT semana_inicio FROM registros ORDER BY semana_inicio DESC")

    if not semanas.empty:
        sem = st.selectbox("Semana:", semanas['semana_inicio'])
        df  = read_df(DB_LABORAL,
            "SELECT dia as Día, entrada as Entrada, salida as Salida, "
            "bruto as Bruto, neto as Neto, extra as Extra "
            "FROM registros WHERE semana_inicio=?", (sem,))
        st.dataframe(df, use_container_width=True, hide_index=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Bruto",  f"{df['Bruto'].sum()}h")
        c2.metric("Neto",   f"{df['Neto'].sum()}h")
        c3.metric("Extras", f"{df['Extra'].sum()}h")

        st.divider()
        df_st_vacio = pd.DataFrame(columns=['dia', 'entrada', 'salida', 'horas', 'asignatura'])
        df_py_raw   = read_df(DB_LABORAL, "SELECT * FROM registros WHERE semana_inicio=?", (sem,))
        st.plotly_chart(generar_gantt(df_st_vacio, df_py_raw, sem), use_container_width=True)

        st.download_button(
            label="📥 Descargar PDF Horario Laboral",
            data=generar_pdf_laboral(df, sem),
            file_name=f"PeYa_{sem}.pdf",
            mime="application/pdf",
        )
    else:
        st.info("No hay registros laborales aún.")

# ==========================================
# 6. GANTT: VISUALIZACIÓN SEMANAL
# ==========================================
elif opcion == "📊 Gantt: Visualización Semanal":
    st.title("📊 Gantt — Vista Semanal Integrada")
    st.markdown("Visualiza en un solo gráfico tus bloques de :green[**estudio**] y :red[**trabajo**] para la semana seleccionada.")

    sem_st = read_df(DB_ESTUDIOS, "SELECT DISTINCT semana_inicio FROM clases    ORDER BY semana_inicio DESC")
    sem_py = read_df(DB_LABORAL,  "SELECT DISTINCT semana_inicio FROM registros ORDER BY semana_inicio DESC")
    todas  = pd.concat([sem_st, sem_py]).drop_duplicates().sort_values('semana_inicio', ascending=False)

    if todas.empty:
        st.warning("No hay datos registrados todavía. Registra clases o turnos primero.")
    else:
        sem_sel = st.selectbox("Selecciona semana:", todas['semana_inicio'])

        df_st = read_df(DB_ESTUDIOS, "SELECT * FROM clases    WHERE semana_inicio=?", (sem_sel,))
        df_py = read_df(DB_LABORAL,  "SELECT * FROM registros WHERE semana_inicio=?", (sem_sel,))

        turnos_activos = df_py[df_py['es_libre'] == 0] if not df_py.empty else pd.DataFrame()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🟢 Bloques estudio",        len(df_st))
        col2.metric("🔴 Turnos PeYa",             len(turnos_activos))
        col3.metric("📚 Horas académicas",         f"{df_st['horas'].sum():.1f}h" if not df_st.empty else "0h")
        col4.metric("💼 Horas laborales (neto)",   f"{turnos_activos['neto'].sum():.1f}h" if not turnos_activos.empty else "0h")

        st.divider()
        st.plotly_chart(generar_gantt(df_st, df_py, sem_sel), use_container_width=True)

        st.markdown("""
        <div style='display:flex; gap:24px; margin-top:8px;'>
            <div style='display:flex; align-items:center; gap:8px;'>
                <div style='width:18px; height:18px; background:rgba(34,139,34,0.80); border-radius:3px;'></div>
                <span style='font-size:14px;'>Santo Tomás (Clases)</span>
            </div>
            <div style='display:flex; align-items:center; gap:8px;'>
                <div style='width:18px; height:18px; background:rgba(200,30,30,0.80); border-radius:3px;'></div>
                <span style='font-size:14px;'>PedidosYa (Turno laboral)</span>
            </div>
            <div style='font-size:13px; color:#888; margin-left:auto;'>⏰ El eje X cubre desde las 08:00 hasta las 03:00 del día siguiente</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📋 Ver detalle de datos"):
            t1, t2 = st.tabs(["Santo Tomás", "PeYa"])
            with t1:
                if not df_st.empty:
                    st.dataframe(
                        df_st[['dia','asignatura','entrada','salida','horas']].rename(columns={
                            'dia':'Día', 'asignatura':'Asignatura',
                            'entrada':'Inicio', 'salida':'Fin', 'horas':'Horas'
                        }), use_container_width=True, hide_index=True)
                else:
                    st.info("Sin clases esta semana.")
            with t2:
                if not turnos_activos.empty:
                    st.dataframe(
                        turnos_activos[['dia','entrada','salida','bruto','neto','extra']].rename(columns={
                            'dia':'Día', 'entrada':'Entrada', 'salida':'Salida',
                            'bruto':'Bruto', 'neto':'Neto', 'extra':'Extra'
                        }), use_container_width=True, hide_index=True)
                else:
                    st.info("Sin turnos esta semana.")
