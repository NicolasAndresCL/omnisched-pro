# OmniSched v2.1 — Sistema de Inteligencia Horaria

Aplicación web desarrollada con **Streamlit** para la autogestión profesional del tiempo. Coordina actividades académicas en **IP Santo Tomás** y turnos laborales en **PedidosYa**, con reportes unificados, cálculos automáticos y visualización Gantt interactiva.

## Características Principales

- **Gestión Dual de Datos:** Bases de datos independientes en SQLite para la carga académica y la laboral.
- **Cálculos Automáticos de Tiempo:**
  - Horas **Bruto** y **Neto** (descuento automático de 1h de colación en turnos largos).
  - **Horas Extras** para domingos y trasnoches de madrugada de sábado (00:00–03:00).
- **Validación de Conflictos:** Alerta visual en tiempo real si un turno PeYa se solapa con una clase.
- **Gantt Interactivo:** Visualización semanal integrada con Plotly, con soporte de dark mode.
- **Módulo de Impresión PDF:** Reportes con formato profesional y distinción de actividades por color (verde para estudios, rojo para trabajo).

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.x |
| Framework Web | [Streamlit](https://streamlit.io/) |
| Base de Datos | SQLite3 |
| Procesamiento | Pandas |
| Visualización | Plotly |
| Exportación | FPDF / Openpyxl |

## Estructura del Proyecto

```text
.
├── app_unificada.py         # Aplicación principal
├── Lanzar_App.bat           # Script de ejecución rápida (Windows)
├── env/                     # Entorno virtual de Python
├── horario_estudios.db      # Base de datos de clases (autogenerada)
└── horarios.db              # Base de datos de turnos PeYa (autogenerada)
```

## Instalación y Configuración

**1. Crear y activar entorno virtual:**

```bash
python -m venv env

# Windows
env\Scripts\activate
```

**2. Instalar dependencias:**

```bash
pip install streamlit pandas fpdf openpyxl plotly
```

## Ejecución

En Windows, doble clic en `Lanzar_App.bat`.

O desde terminal con el entorno activo:

```bash
streamlit run app_unificada.py
```

---

## Módulos del Sistema

| Módulo | Descripción |
|---|---|
| 📝 Registro Estudio | Ingreso de asignaturas, días y bloques horarios |
| 📝 Registro Laboral | Configuración semanal de turnos con detección de trasnoches |
| 📄 Impresión Completo | Reporte maestro que unifica ambas agendas en un solo cronograma |
| 📄 Impresión Estudio | Reporte específico de carga académica semanal |
| 📄 Impresión Laboral | Reporte de horas brutas, netas y extras para control de pagos |
| 📊 Gantt Semanal | Vista gráfica integrada de estudio y trabajo sobre eje temporal |

---

## Autoría y Desarrollo

Diseñado y codificado por:

**Nicolás Andrés Cano Leal** — *BizOps & LiveOps | Python Developer | Backend · Data · Automation*

- **Rol Actual:** Live Performance Agent en **PedidosYa**
- **Formación:** Ingeniería en Informática (IP Santo Tomás)
- **Especialidad:** Automatización de procesos (VBA/Python), Análisis de Datos y Desarrollo Backend

### Conectemos:

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/nicolas-andres-cano-leal)
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/NicolasAndresCL)
[![Portfolio](https://img.shields.io/badge/Portfolio-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://nicolasandrescl.pythonanywhere.com/)

---
*Desarrollado con precisión técnica en Rancagua, Chile.*
