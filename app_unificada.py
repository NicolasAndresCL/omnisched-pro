import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime, time, timedelta
from fpdf import FPDF
from io import BytesIO

# --- CONFIGURACIÓN PRO ---
st.set_page_config(page_title="Sistema Integral Horarios PRO", layout="wide", page_icon="📅")

# --- MOTOR DE BASE DE DATOS ---
def query_db(db, sql, params=(), fetch=False):
    with sqlite3.connect(db) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        if fetch:
            return cursor.fetchall()

def init_dbs():
    query_db('horario_estudios.db', 'CREATE TABLE IF NOT EXISTS clases (semana_inicio TEXT, dia TEXT, asignatura TEXT, entrada TEXT, salida TEXT, horas REAL)')
    query_db('horarios.db', 'CREATE TABLE IF NOT EXISTS registros (semana_inicio TEXT, dia TEXT, entrada TEXT, salida TEXT, bruto REAL, neto REAL, extra REAL, es_libre INTEGER)')

init_dbs()

# --- SIDEBAR MEJORADO ---
with st.sidebar:
    st.title("🚀 Panel Gemini Plus")
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

DIAS_ORDEN = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# --- HELPERS ---

def hora_a_decimal(h_str):
    """Convierte 'HH:MM' a decimal. Horas < 8 se consideran del día siguiente (ej: 01:00 → 25.0)."""
    if not h_str or h_str == "LIBRE":
        return None
    hh, mm = map(int, h_str.split(":"))
    dec = hh + mm / 60
    # Si la hora es < 8 se asume que es pasada medianoche
    if hh < 8:
        dec += 24
    return dec

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
        pdf.cell(30, 7, str(r.get('Día', r.get('dia', ''))), 1)
        pdf.cell(80, 7, str(r.get('Asignatura', r.get('asignatura', ''))), 1)
        pdf.cell(25, 7, str(r.get('Inicio', r.get('entrada', ''))), 1)
        pdf.cell(25, 7, str(r.get('Fin', r.get('salida', ''))), 1)
        pdf.cell(30, 7, f"{r.get('Horas', r.get('horas', ''))}h", 1, ln=True)

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
        dia_col = r.get('Día', r.get('dia', ''))
        ent_col = r.get('Entrada', r.get('entrada', ''))
        sal_col = r.get('Salida', r.get('salida', ''))
        bru = r.get('Bruto', r.get('bruto', 0))
        net = r.get('Neto', r.get('neto', 0))
        ext = r.get('Extra', r.get('extra', 0))
        pdf.cell(30, 7, str(dia_col), 1)
        pdf.cell(28, 7, str(ent_col), 1)
        pdf.cell(28, 7, str(sal_col), 1)
        pdf.cell(28, 7, f"{bru}h", 1)
        pdf.cell(28, 7, f"{net}h", 1)
        pdf.cell(28, 7, f"{ext}h", 1, ln=True)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    bruto_col = df.get('Bruto', df.get('bruto', pd.Series([0])))
    neto_col  = df.get('Neto',  df.get('neto',  pd.Series([0])))
    extra_col = df.get('Extra', df.get('extra', pd.Series([0])))
    pdf.cell(190, 8, f"Bruto: {round(bruto_col.sum(),2)}h  |  Neto: {round(neto_col.sum(),2)}h  |  Extras: {round(extra_col.sum(),2)}h", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

def generar_gantt(df_st, df_py, semana_label):
    """Genera figura Plotly Gantt con eje X numérico de 8.0 a 27.0 (3 AM siguiente día)."""
    fig = go.Figure()

    # ── Barras Santo Tomás (verde) ──
    for _, r in df_st.iterrows():
        ini = hora_a_decimal(r['entrada'])
        fin = hora_a_decimal(r['salida'])
        if ini is None or fin is None:
            continue
        if fin <= ini:
            fin += 24  # cruce de medianoche
        dur = fin - ini

        fig.add_trace(go.Bar(
            x=[dur],
            y=[r['dia']],
            base=[ini],
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
            text=r['asignatura'],
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(size=10, color='white'),
        ))

    # ── Barras PeYa (rojo) ──
    for _, r in df_py.iterrows():
        if r.get('es_libre', 0) == 1:
            continue
        ini = hora_a_decimal(r['entrada'])
        fin = hora_a_decimal(r['salida'])
        if ini is None or fin is None:
            continue
        if fin <= ini:
            fin += 24
        dur = fin - ini

        fig.add_trace(go.Bar(
            x=[dur],
            y=[r['dia']],
            base=[ini],
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
            text='PeYa',
            textposition='inside',
            insidetextanchor='middle',
            textfont=dict(size=10, color='white'),
        ))

    # ── Ticks del eje X: 8h → 27h con etiquetas legibles ──
    tick_horas = list(range(8, 28))  # 8, 9, ... 27
    tick_text = []
    for h in tick_horas:
        hh = h % 24
        if hh == 0:
            tick_text.append("00:00 (+1)")
        else:
            tick_text.append(f"{hh:02d}:00")

    fig.update_layout(
        title=dict(
            text=f"📊 Gantt Semanal — {semana_label}",
            font=dict(size=18),
            x=0.5
        ),
        barmode='overlay',
        xaxis=dict(
            range=[8, 28],
            tickvals=tick_horas,
            ticktext=tick_text,
            tickfont=dict(size=11),
            gridcolor='rgba(128,128,128,0.25)',
            gridwidth=1,
            title="Horario",
            showline=True,
            linecolor='rgba(128,128,128,0.4)',
        ),
        yaxis=dict(
            categoryarray=list(reversed(DIAS_ORDEN)),
            categoryorder='array',
            tickfont=dict(size=13),
            title="",
            gridcolor='rgba(128,128,128,0.15)',
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        height=430,
        margin=dict(l=10, r=10, t=60, b=40),
        legend=dict(
            orientation='h',
            yanchor='bottom', y=1.02,
            xanchor='right', x=1
        ),
        bargap=0.35,
    )

    # Línea de mediodía como referencia visual
    fig.add_vline(x=12, line_dash="dot", line_color="rgba(128,128,128,0.35)", line_width=1)

    # Leyenda manual — y con categoría válida para que funcione en dark mode
    fig.add_trace(go.Bar(x=[0], y=["Lunes"], base=[8], orientation='h',
                         marker_color='rgba(34,139,34,0.82)', name='Santo Tomás', showlegend=True))
    fig.add_trace(go.Bar(x=[0], y=["Lunes"], base=[8], orientation='h',
                         marker_color='rgba(200,30,30,0.82)', name='PeYa', showlegend=True))

    return fig

# ==========================================
# 1. REGISTRO: ESTUDIO (SANTO TOMAS)
# ==========================================
if opcion == "📝 Registro: Horario Estudio":
    st.title(":green[Horario Santo Tomas]")
    fecha_ref = st.date_input("Semana del Lunes:", datetime.now())
    inicio_sem = (fecha_ref - timedelta(days=fecha_ref.weekday())).strftime('%Y-%m-%d')
    
    with st.expander("➕ Añadir Nueva Clase", expanded=True):
        with st.form("form_st"):
            c1, c2 = st.columns(2)
            dia = c1.selectbox("Día", DIAS_ORDEN)
            materia = c2.text_input("Nombre de la Asignatura", placeholder="Ej: Anatomía")
            h_in = c1.time_input("Inicio", time(8, 30))
            h_out = c2.time_input("Fin", time(10, 0))
            
            if st.form_submit_button("Guardar"):
                dt_i = datetime.combine(datetime.today(), h_in)
                dt_o = datetime.combine(datetime.today(), h_out)
                if h_out < h_in: dt_o += timedelta(days=1)
                dur = round((dt_o - dt_i).total_seconds() / 3600, 2)
                
                query_db('horario_estudios.db', "INSERT INTO clases VALUES (?,?,?,?,?,?)", (inicio_sem, dia, materia, h_in.strftime("%H:%M"), h_out.strftime("%H:%M"), dur))
                st.success("Clase registrada con éxito.")

# ==========================================
# 2. REGISTRO: LABORAL (PEYA)
# ==========================================
elif opcion == "📝 Registro: Horario Laboral":
    st.title(":red[Horario PeYa]")
    fecha_ref = st.date_input("Selecciona semana:", datetime.now())
    inicio_sem = (fecha_ref - timedelta(days=fecha_ref.weekday())).strftime('%Y-%m-%d')
    
    conn_st = sqlite3.connect('horario_estudios.db')
    clases_semana = pd.read_sql_query("SELECT dia, entrada, salida FROM clases WHERE semana_inicio=?", conn_st, params=(inicio_sem,))
    conn_st.close()

    st.markdown("### Configura tus turnos")
    inputs = {}
    cols = st.columns(7)
    for i, d in enumerate(DIAS_ORDEN):
        with cols[i]:
            st.write(f"**{d}**")
            lib = st.checkbox("Libre", key=f"l_{d}")
            if not lib:
                ent = st.time_input("In", time(18, 0), key=f"i_{d}")
                sal = st.time_input("Out", time(0, 0), key=f"s_{d}")
                inputs[d] = {"in": ent, "out": sal, "libre": False}
                if not clases_semana.empty and d in clases_semana['dia'].values:
                    st.warning("⚠️ Hay clase")
            else:
                inputs[d] = {"libre": True}

    if st.button("💾 Guardar Semana Laboral"):
        data = []
        for d in DIAS_ORDEN:
            r = inputs[d]
            if r["libre"]: data.append((inicio_sem, d, "LIBRE", "LIBRE", 0, 0, 0, 1))
            else:
                dt_i = datetime.combine(datetime.today(), r["in"])
                dt_o = datetime.combine(datetime.today(), r["out"])
                if r["out"] < r["in"]: dt_o += timedelta(days=1)
                bruto = (dt_o - dt_i).total_seconds() / 3600
                neto = max(0, bruto - 1) if bruto > 1 else bruto
                extra = bruto if d == "Domingo" else 0
                if d == "Sábado" and r["out"] < r["in"]: extra = min(3.0, (datetime.combine(dt_o.date(), time(3,0)) - datetime.combine(dt_o.date(), time(0,0))).total_seconds()/3600)
                data.append((inicio_sem, d, r["in"].strftime("%H:%M"), r["out"].strftime("%H:%M"), round(bruto, 2), round(neto, 2), round(extra, 2), 0))
        
        with sqlite3.connect('horarios.db') as conn:
            conn.execute("DELETE FROM registros WHERE semana_inicio=?", (inicio_sem,))
            conn.executemany("INSERT INTO registros VALUES (?,?,?,?,?,?,?,?)", data)
        st.success("Horario PeYa guardado.")

# ==========================================
# 3. IMPRESIÓN: COMPLETO (SISTEMA PRO)
# ==========================================
elif opcion == "📄 Impresión: Horario Completo":
    st.title("📊 Análisis y Control Unificado")
    
    with sqlite3.connect('horario_estudios.db') as c:
        semanas = pd.read_sql_query("SELECT DISTINCT semana_inicio FROM clases ORDER BY semana_inicio DESC", c)
    
    if not semanas.empty:
        sem_sel = st.selectbox("Semana de análisis:", semanas['semana_inicio'])
        
        c1 = sqlite3.connect('horario_estudios.db'); df_st = pd.read_sql_query("SELECT * FROM clases WHERE semana_inicio=?", c1, params=(sem_sel,)); c1.close()
        c2 = sqlite3.connect('horarios.db'); df_py = pd.read_sql_query("SELECT * FROM registros WHERE semana_inicio=? AND es_libre=0", c2, params=(sem_sel,)); c2.close()

        total_h = df_st['horas'].sum() + df_py['neto'].sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("Carga Académica", f"{df_st['horas'].sum()}h")
        col2.metric("Carga Laboral (Neto)", f"{df_py['neto'].sum()}h")
        col3.metric("Ocupación Total", f"{total_h}h")

        # Gantt embebido en Completo
        st.divider()
        df_py_all = pd.read_sql_query("SELECT * FROM registros WHERE semana_inicio=?",
                                       sqlite3.connect('horarios.db'), params=(sem_sel,))
        fig = generar_gantt(df_st, df_py_all, sem_sel)
        st.plotly_chart(fig, use_container_width=True)

        st.divider()
        if st.button("🔥 Descargar Reporte Maestro PDF"):
            pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", "B", 16)
            pdf.cell(190, 10, "CONTROL DE TIEMPO UNIFICADO", ln=True, align='C')
            pdf.set_font("Arial", "", 10); pdf.cell(190, 7, f"Semana: {sem_sel}", ln=True, align='C'); pdf.ln(5)
            
            for d in DIAS_ORDEN:
                st_d = df_st[df_st['dia'] == d]; py_d = df_py[df_py['dia'] == d]
                if st_d.empty and py_d.empty: continue
                
                pdf.set_font("Arial", "B", 10); pdf.set_fill_color(230, 230, 230)
                pdf.cell(190, 8, f"--- {d.upper()} ---", 1, ln=True, fill=True)
                
                pdf.set_font("Arial", "", 9)
                for _, r in st_d.iterrows():
                    pdf.set_text_color(0, 80, 0)
                    pdf.cell(30, 7, "ESTUDIO", 1); pdf.cell(90, 7, r['asignatura'], 1); pdf.cell(20, 7, r['entrada'], 1); pdf.cell(20, 7, r['salida'], 1); pdf.cell(30, 7, f"{r['horas']}h", 1, ln=True)
                for _, r in py_d.iterrows():
                    pdf.set_text_color(180, 0, 0)
                    pdf.cell(30, 7, "TRABAJO", 1); pdf.cell(90, 7, "PeYa", 1); pdf.cell(20, 7, r['entrada'], 1); pdf.cell(20, 7, r['salida'], 1); pdf.cell(30, 7, f"{r['neto']}h", 1, ln=True)
                pdf.set_text_color(0,0,0); pdf.ln(2)
            
            st.download_button("💾 Bajar PDF Unificado", pdf.output(dest='S').encode('latin-1'), f"Master_{sem_sel}.pdf")

# ==========================================
# 4. IMPRESIÓN: HORARIO ESTUDIO
# ==========================================
elif opcion == "📄 Impresión: Horario Estudio":
    st.title(":green[Horario Santo Tomas]")
    with sqlite3.connect('horario_estudios.db') as conn:
        semanas = pd.read_sql_query("SELECT DISTINCT semana_inicio FROM clases ORDER BY semana_inicio DESC", conn)
        if not semanas.empty:
            sem = st.selectbox("Semana:", semanas['semana_inicio'])
            df = pd.read_sql_query(
                "SELECT dia as Día, asignatura as Asignatura, entrada as Inicio, salida as Fin, horas as Horas FROM clases WHERE semana_inicio=?",
                conn, params=(sem,)
            )
            st.table(df)
            st.metric("Total Semanal", f"{df['Horas'].sum()} h")

            # Gantt solo estudio
            st.divider()
            df_st_raw = pd.read_sql_query("SELECT * FROM clases WHERE semana_inicio=?",
                sqlite3.connect('horario_estudios.db'), params=(sem,))
            df_py_vacio = pd.DataFrame(columns=['dia','entrada','salida','neto','es_libre'])
            fig_est = generar_gantt(df_st_raw, df_py_vacio, sem)
            st.plotly_chart(fig_est, use_container_width=True)

            pdf_bytes = generar_pdf_estudio(df, sem)
            st.download_button(
                label="📥 Descargar PDF Horario Estudio",
                data=pdf_bytes,
                file_name=f"Estudio_{sem}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("No hay registros de clases aún.")

# ==========================================
# 5. IMPRESIÓN: HORARIO LABORAL
# ==========================================
elif opcion == "📄 Impresión: Horario Laboral":
    st.title(":red[Horario PeYa]")
    with sqlite3.connect('horarios.db') as conn:
        semanas = pd.read_sql_query("SELECT DISTINCT semana_inicio FROM registros ORDER BY semana_inicio DESC", conn)
        if not semanas.empty:
            sem = st.selectbox("Semana:", semanas['semana_inicio'])
            df = pd.read_sql_query(
                "SELECT dia as Día, entrada as Entrada, salida as Salida, bruto as Bruto, neto as Neto, extra as Extra FROM registros WHERE semana_inicio=?",
                conn, params=(sem,)
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Bruto", f"{df['Bruto'].sum()}h")
            c2.metric("Neto", f"{df['Neto'].sum()}h")
            c3.metric("Extras", f"{df['Extra'].sum()}h")

            # Gantt solo laboral
            st.divider()
            df_st_vacio = pd.DataFrame(columns=['dia','entrada','salida','horas','asignatura'])
            df_py_raw = pd.read_sql_query("SELECT * FROM registros WHERE semana_inicio=?",
                sqlite3.connect('horarios.db'), params=(sem,))
            fig_lab = generar_gantt(df_st_vacio, df_py_raw, sem)
            st.plotly_chart(fig_lab, use_container_width=True)

            pdf_bytes = generar_pdf_laboral(df, sem)
            st.download_button(
                label="📥 Descargar PDF Horario Laboral",
                data=pdf_bytes,
                file_name=f"PeYa_{sem}.pdf",
                mime="application/pdf"
            )
        else:
            st.info("No hay registros laborales aún.")

# ==========================================
# 6. GANTT: VISUALIZACIÓN SEMANAL
# ==========================================
elif opcion == "📊 Gantt: Visualización Semanal":
    st.title("📊 Gantt — Vista Semanal Integrada")
    st.markdown("Visualiza en un solo gráfico tus bloques de :green[**estudio**] y :red[**trabajo**] para la semana seleccionada.")

    # Recopilar semanas disponibles de ambas DBs
    with sqlite3.connect('horario_estudios.db') as c:
        sem_st = pd.read_sql_query("SELECT DISTINCT semana_inicio FROM clases ORDER BY semana_inicio DESC", c)
    with sqlite3.connect('horarios.db') as c:
        sem_py = pd.read_sql_query("SELECT DISTINCT semana_inicio FROM registros ORDER BY semana_inicio DESC", c)

    todas = pd.concat([sem_st, sem_py]).drop_duplicates().sort_values('semana_inicio', ascending=False)

    if todas.empty:
        st.warning("No hay datos registrados todavía. Registra clases o turnos primero.")
    else:
        sem_sel = st.selectbox("Selecciona semana:", todas['semana_inicio'])

        with sqlite3.connect('horario_estudios.db') as c:
            df_st = pd.read_sql_query("SELECT * FROM clases WHERE semana_inicio=?", c, params=(sem_sel,))
        with sqlite3.connect('horarios.db') as c:
            df_py = pd.read_sql_query("SELECT * FROM registros WHERE semana_inicio=?", c, params=(sem_sel,))

        # KPIs rápidos
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🟢 Bloques estudio", len(df_st))
        col2.metric("🔴 Turnos PeYa", len(df_py[df_py.get('es_libre', pd.Series([0]*len(df_py))) == 0]) if not df_py.empty else 0)
        col3.metric("📚 Horas académicas", f"{df_st['horas'].sum():.1f}h" if not df_st.empty else "0h")
        neto_total = df_py[df_py['es_libre'] == 0]['neto'].sum() if not df_py.empty else 0
        col4.metric("💼 Horas laborales (neto)", f"{neto_total:.1f}h")

        st.divider()

        fig = generar_gantt(df_st, df_py, sem_sel)
        st.plotly_chart(fig, use_container_width=True)

        # Leyenda explicativa
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

        # Detalle expandible
        with st.expander("📋 Ver detalle de datos"):
            t1, t2 = st.tabs(["Santo Tomás", "PeYa"])
            with t1:
                if not df_st.empty:
                    st.dataframe(df_st[['dia','asignatura','entrada','salida','horas']].rename(columns={
                        'dia':'Día','asignatura':'Asignatura','entrada':'Inicio','salida':'Fin','horas':'Horas'
                    }), use_container_width=True, hide_index=True)
                else:
                    st.info("Sin clases esta semana.")
            with t2:
                if not df_py.empty:
                    st.dataframe(df_py[df_py['es_libre']==0][['dia','entrada','salida','bruto','neto','extra']].rename(columns={
                        'dia':'Día','entrada':'Entrada','salida':'Salida','bruto':'Bruto','neto':'Neto','extra':'Extra'
                    }), use_container_width=True, hide_index=True)
                else:
                    st.info("Sin turnos esta semana.")