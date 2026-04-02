import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, time, timedelta
from io import BytesIO

# --- 1. BASE DE DATOS ADAPTADA ---
def init_db_estudios():
    conn = sqlite3.connect('horario_estudios.db')
    c = conn.cursor()
    # Agregamos 'asignatura' a la tabla
    c.execute('''CREATE TABLE IF NOT EXISTS clases 
                 (semana_inicio TEXT, dia TEXT, asignatura TEXT, 
                  entrada TEXT, salida TEXT, horas REAL)''')
    conn.commit()
    conn.close()

init_db_estudios()

# --- 2. CONFIGURACIÓN UI ---
st.set_page_config(page_title="Horario Santo Tomas", layout="wide")
st.title(":green[Horario Santo Tomas]")

tab1, tab2 = st.tabs(["📝 Registrar Clases", "📚 Mi Horario Semanal"])

# --- TAB 1: REGISTRO DE BLOQUES ---
with tab1:
    fecha_ref = st.date_input("Semana del:", datetime.now())
    inicio_sem = (fecha_ref - timedelta(days=fecha_ref.weekday())).strftime('%Y-%m-%d')
    
    st.info(f"Registrando bloques para la semana del lunes {inicio_sem}")

    # Usaremos un formulario para agregar bloques uno por uno
    with st.expander("➕ Agregar Nuevo Bloque / Asignatura", expanded=True):
        with st.form("form_clase"):
            col1, col2 = st.columns(2)
            dia = col1.selectbox("Día", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"])
            nombre_materia = col2.text_input("Nombre de la Asignatura", placeholder="Ej: Cálculo I")
            
            c_in, c_out = st.columns(2)
            h_in = c_in.time_input("Hora Inicio", time(8, 30))
            h_out = c_out.time_input("Hora Fin", time(10, 0))
            
            btn_guardar = st.form_submit_button("Añadir al Horario")

            if btn_guardar:
                # Calcular duración del bloque
                dt_i = datetime.combine(datetime.today(), h_in)
                dt_o = datetime.combine(datetime.today(), h_out)
                if h_out < h_in: dt_o += timedelta(days=1)
                duracion = (dt_o - dt_i).total_seconds() / 3600

                conn = sqlite3.connect('horario_estudios.db')
                c = conn.cursor()
                c.execute("INSERT INTO clases VALUES (?, ?, ?, ?, ?, ?)",
                          (inicio_sem, dia, nombre_materia, h_in.strftime("%H:%M"), h_out.strftime("%H:%M"), round(duracion, 2)))
                conn.commit()
                conn.close()
                st.success(f"¡{nombre_materia} guardado para el {dia}!")

# --- TAB 2: VISUALIZACIÓN Y TOTALES ---
# --- TAB 2: VISUALIZACIÓN Y EXPORTACIÓN ---
with tab2:
    conn = sqlite3.connect('horario_estudios.db')
    semanas = pd.read_sql_query("SELECT DISTINCT semana_inicio FROM clases ORDER BY semana_inicio DESC", conn)
    
    if not semanas.empty:
        sem_sel = st.selectbox("Ver semana:", semanas['semana_inicio'])
        
        # Cargar datos filtrados por semana
        query = "SELECT dia as Día, asignatura as Asignatura, entrada as Inicio, salida as Fin, horas as Horas FROM clases WHERE semana_inicio = ?"
        df = pd.read_sql_query(query, conn, params=(sem_sel,))
        
        # Orden lógico de los días para la tabla
        orden_dias = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5, "Domingo":6}
        df['orden'] = df['Día'].map(orden_dias)
        df = df.sort_values(['orden', 'Inicio']).drop(columns=['orden'])

        st.dataframe(df, use_container_width=True, hide_index=True)

        # Cálculos de resumen
        total_semanal = df["Horas"].sum()
        st.metric("Total Horas de Clase en la Semana", f"{total_semanal:.2f} h")

        st.divider()
        st.subheader("📥 Exportar mi Horario")
        c_pdf, c_xl = st.columns(2)

        # --- GENERAR PDF  ---
        with c_pdf:
            if st.button("Generar PDF"):
                from fpdf import FPDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_auto_page_break(auto=True, margin=15)
                
                # Título
                pdf.set_font("Arial", "B", 16)
                pdf.set_text_color(0, 128, 0)
                pdf.cell(190, 10, f"Horario Santo Tomas - Semana {sem_sel}", ln=True, align='C')
                pdf.ln(10)
                
                # Configuración de anchos: Total 190
                w = [25, 85, 25, 25, 30]
                headers = ["Dia", "Asignatura", "Inicio", "Fin", "Horas"]
                
                # Encabezados
                pdf.set_font("Arial", "B", 10)
                pdf.set_fill_color(200, 230, 201)
                pdf.set_text_color(0, 0, 0)
                for i in range(len(headers)):
                    pdf.cell(w[i], 10, headers[i], 1, 0, 'C', True)
                pdf.ln()
                
                # Datos de la tabla
                pdf.set_font("Arial", "", 9)
                for _, row in df.iterrows():
                    # 1. Calcular altura necesaria para esta fila
                    # Dividimos el ancho de la asignatura por un factor aproximado de caracteres
                    texto_asignatura = str(row['Asignatura'])
                    # Calculamos cuántas líneas ocupará (estimación de 50 caracteres por línea en 85mm)
                    num_lineas = (len(texto_asignatura) // 50) + 1
                    h_fila = max(10, num_lineas * 7) # Altura mínima de 10, o 7 por cada línea

                    # Guardar posición inicial de la fila
                    x, y = pdf.get_x(), pdf.get_y()

                    # 2. Dibujar celdas (todas con la misma h_fila para cerrar el cuadro)
                    pdf.rect(x, y, w[0], h_fila) # Recuadro Dia
                    pdf.cell(w[0], h_fila, str(row['Día']), 0, 0, 'C')
                    
                    # Celda de Asignatura (MultiCell)
                    pdf.rect(x + w[0], y, w[1], h_fila) # Recuadro Asignatura
                    pdf.set_xy(x + w[0], y + 2) # Margen interno pequeño
                    pdf.multi_cell(w[1], 5, texto_asignatura, 0, 'L')
                    
                    # Volver a la derecha para las demás columnas
                    pdf.set_xy(x + w[0] + w[1], y)
                    pdf.cell(w[2], h_fila, str(row['Inicio']), 1, 0, 'C')
                    pdf.cell(w[3], h_fila, str(row['Fin']), 1, 0, 'C')
                    pdf.cell(w[4], h_fila, str(row['Horas']), 1, 1, 'C')

                pdf.ln(5)
                pdf.set_font("Arial", "B", 11)
                pdf.cell(190, 10, f"Carga Horaria Total: {total_semanal:.2f} horas", ln=True, align='R')

                pdf_out = pdf.output(dest='S').encode('latin-1')
                st.download_button("⬇️ Descargar PDF", data=pdf_out, file_name=f"Horario_ST_{sem_sel}.pdf", mime="application/pdf")
        # --- GENERAR EXCEL ---
        with c_xl:
            from io import BytesIO
            output_xl = BytesIO()
            with pd.ExcelWriter(output_xl, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='MiHorario')
            
            st.download_button("⬇️ Descargar Excel", data=output_xl.getvalue(), file_name=f"Horario_ST_{sem_sel}.xlsx")
            
        st.divider()
        if st.button("🗑️ Borrar toda esta semana", type="secondary"):
            c = conn.cursor()
            c.execute("DELETE FROM clases WHERE semana_inicio = ?", (sem_sel,))
            conn.commit()
            st.rerun()
            
    else:
        st.info("No hay clases registradas aún. Ve a la pestaña 'Registrar Clases'.")
    conn.close()