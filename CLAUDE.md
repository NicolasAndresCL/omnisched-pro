# CLAUDE.md — OmniSched v2.1

Guía de arquitectura para desarrollo asistido por IA en este proyecto.

## Descripción del proyecto

Aplicación Streamlit de archivo único (`app_unificada.py`) para gestión de horarios personales: clases en IP Santo Tomás y turnos laborales en PedidosYa. Sin backend separado; todo vive en el script principal más dos archivos SQLite autogenerados.

## Estructura del código

`app_unificada.py` está organizado en secciones en este orden:

1. **Imports y configuración** — `st.set_page_config`, constantes globales, inicialización de session state
2. **Capa de base de datos** — `query_db`, `read_df`, `init_dbs`
3. **Sidebar** — navegación con `st.radio`
4. **Helpers de negocio** — `get_semana_inicio`, `hora_a_decimal`, `calcular_horas_turno`
5. **Generadores PDF** — `generar_pdf_estudio`, `generar_pdf_laboral`
6. **Generador Gantt** — `generar_gantt` (Plotly)
7. **Módulos UI** — bloques `if/elif` según `opcion` del sidebar

## Bases de datos

| Constante | Archivo | Tabla | Columnas |
|---|---|---|---|
| `DB_ESTUDIOS` | `horario_estudios.db` | `clases` | `semana_inicio, dia, asignatura, entrada, salida, horas` |
| `DB_LABORAL` | `horarios.db` | `registros` | `semana_inicio, dia, entrada, salida, bruto, neto, extra, es_libre` |

- `semana_inicio` es siempre el lunes de la semana en formato `YYYY-MM-DD` (calculado por `get_semana_inicio`).
- `es_libre INTEGER` actúa como booleano (0/1). Filas con `es_libre=1` tienen `entrada='LIBRE'` y horas en 0.
- Las tablas se crean automáticamente en `init_dbs()` al arrancar la app.

## Patrones clave

### Leer datos
Usar siempre `read_df(db, sql, params)` — nunca abrir conexiones raw dentro de `pd.read_sql_query`.

```python
df = read_df(DB_ESTUDIOS, "SELECT * FROM clases WHERE semana_inicio=?", (sem,))
```

### Escribir datos
`query_db` para operaciones simples; context manager `with sqlite3.connect(DB) as conn` para transacciones multi-sentencia (ej: DELETE + executemany).

### Semana de inicio
```python
inicio_sem = get_semana_inicio(fecha_ref)  # fecha_ref es un date de st.date_input
```

### Horas de turno
```python
bruto, neto, extra = calcular_horas_turno(dia, hora_in, hora_out)
```
`hora_in` y `hora_out` son objetos `datetime.time`. La función maneja turnos que cruzan medianoche.

### Limpiar campo de texto tras guardar (formulario de estudio)
Se rota la clave del formulario vía `st.session_state.form_key`. Incrementar `form_key` en el handler de submit hace que Streamlit cree un formulario nuevo en el siguiente render, devolviendo todos los inputs a sus valores por defecto.

### Pre-rellenar formulario laboral desde otra semana
Escribir directamente en `st.session_state` con las claves `f"l_{dia}"`, `f"i_{dia}"`, `f"s_{dia}"` antes de llamar `st.rerun()`. Streamlit usa esos valores como valor inicial de cada widget en el siguiente render.

## Dependencias

```
streamlit
pandas
fpdf
plotly
openpyxl
sqlite3  # stdlib
```

## Ejecución local

```bash
env\Scripts\activate       # Windows
streamlit run app_unificada.py
```

## Convenciones de desarrollo

- No crear módulos adicionales salvo que la app supere ~700 líneas; por ahora todo en `app_unificada.py` es suficiente.
- Los PDFs usan `fpdf` (FPDF2) con fuente Arial y encoding `latin-1` en el output.
- El Gantt usa eje X numérico (horas decimales) desde 8.0 hasta 28.0; horas < 8 se suman 24 para representar turnos de trasnoche en el mismo eje continuo.
- No agregar dependencias nuevas sin actualizar `readme.md` y el bloque de pip install.
