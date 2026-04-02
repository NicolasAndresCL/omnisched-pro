import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time, timedelta
from fpdf import FPDF
from io import BytesIO

# --- CONFIGURACIÓN DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('horarios.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS registros 
                (semana_inicio TEXT, dia TEXT, entrada TEXT, salida TEXT, 
                bruto REAL, neto REAL, extra REAL, es_libre INTEGER)''')
    conn.commit()
    conn.close()

def guardar_semana(df_datos, fecha_inicio):
    conn = sqlite3.connect('horarios.db')
    c = conn.cursor()
    # Borrar si ya existe esa semana para no duplicar al re-guardar
    c.execute("DELETE FROM registros WHERE semana_inicio = ?", (fecha_inicio,))
    for _, row in df_datos.iterrows():
        c.execute("INSERT INTO registros VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (fecha_inicio, row['Día'], row['Entrada'], row['Salida'], 
                row['Bruto (h)'], row['Neto (h)'], row['Extras (h)'], 
                1 if row['Entrada'] == "LIBRE" else 0))
    conn.commit()
    conn.close()

init_db()

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Gestor de Horarios SQL", layout="wide")
tab1, tab2 = st.tabs(["📝 Registro de Horario", "📊 Historial por Semana"])

# --- TAB 1: REGISTRO ---
with tab1:
    st.header("Entrada de Horarios")
    fecha_ref = st.date_input("Selecciona la semana:", datetime.now(), key="reg_fecha")
    inicio_sem = (fecha_ref - timedelta(days=fecha_ref.weekday())).strftime('%Y-%m-%d')
    
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    registros_inputs = {}

    cols_input = st.columns(7)
    for i, dia in enumerate(dias):
        with cols_input[i]:
            st.markdown(f"**{dia}**")
            libre = st.checkbox("Libre", key=f"l_{dia}")
            if not libre:
                ent = st.time_input("In", time(9, 0), key=f"i_{dia}")
                sal = st.time_input("Out", time(15, 0), key=f"s_{dia}")
                registros_inputs[dia] = {"in": ent, "out": sal, "libre": False}
            else:
                registros_inputs[dia] = {"in": None, "out": None, "libre": True}

    # Lógica de cálculos (IDÉNTICA A LA ANTERIOR)
    lista_final = []
    for dia in dias:
        reg = registros_inputs[dia]
        if reg["libre"]:
            res = {"Día": dia, "Entrada": "LIBRE", "Salida": "LIBRE", "Bruto (h)": 0.0, "Neto (h)": 0.0, "Extras (h)": 0.0}
        else:
            dt_in = datetime.combine(datetime.today(), reg["in"])
            dt_out = datetime.combine(datetime.today(), reg["out"])
            if reg["out"] < reg["in"]: dt_out += timedelta(days=1)
            
            dur = (dt_out - dt_in).total_seconds() / 3600
            ext = 0
            if dia == "Domingo": ext = dur
            elif dia == "Sábado":
                # Lógica madrugada Sábado -> Domingo
                if reg["out"] < reg["in"]:
                    mediana = datetime.combine(dt_out.date(), time(0,0))
                    lim = datetime.combine(dt_out.date(), time(3,0))
                    ext = (min(dt_out, lim) - mediana).total_seconds() / 3600 if dt_out > mediana else 0
                # Lógica madrugada Viernes -> Sábado
                elif reg["in"] < time(3,0):
                    lim = datetime.combine(dt_in.date(), time(3,0))
                    ext = (min(dt_out, lim) - dt_in).total_seconds() / 3600

            res = {
                "Día": dia, "Entrada": reg["in"].strftime("%H:%M"), "Salida": reg["out"].strftime("%H:%M"),
                "Bruto (h)": round(dur, 2), "Neto (h)": round(max(0, dur-1) if dur > 1 else dur, 2), "Extras (h)": round(ext, 2)
            }
        lista_final.append(res)

    df_actual = pd.DataFrame(lista_final)
    st.table(df_actual)
    
    if st.button("💾 Guardar Semana en Base de Datos"):
        guardar_semana(df_actual, inicio_sem)
        st.success(f"Datos de la semana {inicio_sem} guardados correctamente.")

# --- TAB 2: HISTORIAL ---
with tab2:
    st.header("Consulta y Exportación de Historial")
    conn = sqlite3.connect('horarios.db')
    
    # Obtener semanas únicas guardadas
    semanas_df = pd.read_sql_query("SELECT DISTINCT semana_inicio FROM registros ORDER BY semana_inicio DESC", conn)
    
    if not semanas_df.empty:
        semana_sel = st.selectbox("Selecciona la semana para consultar o exportar:", semanas_df['semana_inicio'])
        
        # Cargar datos de esa semana específica
        query = "SELECT dia as Día, entrada as Entrada, salida as Salida, bruto as 'Bruto (h)', neto as 'Neto (h)', extra as 'Extras (h)' FROM registros WHERE semana_inicio = ?"
        datos_historial = pd.read_sql_query(query, conn, params=(semana_sel,))
        
        # Mostrar tabla en pantalla
        st.dataframe(datos_historial, use_container_width=True, hide_index=True)
        
        # Métricas de resumen
        totales = datos_historial[['Bruto (h)', 'Neto (h)', 'Extras (h)']].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Bruto", f"{totales['Bruto (h)']:.2f} h")
        m2.metric("Total Neto", f"{totales['Neto (h)']:.2f} h")
        m3.metric("Total Extras", f"{totales['Extras (h)']:.2f} h")

        st.divider()
        st.subheader("📥 Descargar Reporte Seleccionado")
        col_pdf, col_xl = st.columns(2)

        # --- EXPORTAR A PDF ---
        with col_pdf:
            if st.button("Generar PDF de esta semana"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", "B", 14)
                pdf.cell(190, 10, f"Reporte de Horarios - Semana {semana_sel}", ln=True, align='C')
                pdf.ln(5)
                
                # Encabezados
                pdf.set_font("Arial", "B", 10)
                pdf.set_fill_color(230, 230, 230)
                columnas = datos_historial.columns.tolist()
                for col in columnas:
                    pdf.cell(31, 10, col, 1, 0, 'C', True)
                pdf.ln()
                
                # Datos de la tabla
                pdf.set_font("Arial", "", 10)
                for _, row in datos_historial.iterrows():
                    for item in row:
                        pdf.cell(31, 10, str(item), 1)
                    pdf.ln()
                
                # Totales al final del PDF
                pdf.ln(5)
                pdf.set_font("Arial", "B", 10)
                pdf.cell(190, 10, f"Total Neto Semanal: {totales['Neto (h)']:.2f} h | Total Extras: {totales['Extras (h)']:.2f} h", ln=True)

                pdf_bytes = pdf.output(dest='S').encode('latin-1')
                st.download_button("⬇️ Descargar PDF", data=pdf_bytes, file_name=f"Reporte_{semana_sel}.pdf", mime="application/pdf")

        # --- EXPORTAR A EXCEL ---
        with col_xl:
            output_xl = BytesIO()
            with pd.ExcelWriter(output_xl, engine='openpyxl') as writer:
                datos_historial.to_excel(writer, index=False, sheet_name='Horarios')
            
            st.download_button("⬇️ Descargar Excel", data=output_xl.getvalue(), file_name=f"Reporte_{semana_sel}.xlsx")
            
    else:
        st.info("No hay datos históricos. Ve a la pestaña de Registro para guardar tu primera semana.")
    
    conn.close()