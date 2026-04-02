# 📅 OmniSched v2.1 — Sistema de Inteligencia Horaria

Este proyecto es una aplicación web robusta desarrollada con **Streamlit**, diseñada para la autogestión profesional del tiempo. Permite coordinar de manera eficiente las actividades académicas en **IP Santo Tomás** y los turnos laborales en **PedidosYa**, ofreciendo un control exhaustivo mediante reportes unificados y automatización de cálculos.

## 🚀 Características Principales

* **Gestión Dual de Datos:** Bases de datos independientes en **SQLite** para separar la carga académica de la laboral de forma íntegra.
* **Cálculos Automáticos de Tiempo:**
    * Cálculo de horas **Bruto** y **Neto** (descuento automático de 1h de colación en turnos largos).
    * Lógica avanzada para **Horas Extras** (domingos y trasnoches de madrugada de viernes/sábado).
* **Validación de Conflictos:** Alerta visual en tiempo real en el registro laboral si un turno de PeYa se solapa con una clase programada.
* **Módulo de Impresión PRO:** Generación de reportes en **PDF** con formato profesional y distinción de actividades por colores (Verde para Estudios, Rojo para Trabajo).
* **Interfaz Optimizada:** Panel de navegación con 5 módulos especializados para registro, consulta y exportación.

## 🛠️ Stack Tecnológico

* **Lenguaje:** Python 3.x
* **Framework Web:** [Streamlit](https://streamlit.io/)
* **Base de Datos:** SQLite3
* **Procesamiento de Datos:** Pandas
* **Generación de Reportes:** FPDF / Openpyxl

## 📋 Estructura del Proyecto

```text
.
├── app_unificada.py         # Código principal de la aplicación
├── Lanzar_App.bat           # Script de ejecución rápida para Windows
├── env/                     # Entorno virtual de Python
├── horario_estudios.db      # Base de Datos de Clases (Autogenerada)
└── horarios_laboral.db      # Base de Datos de Turnos PeYa (Autogenerada)
```

## ⚙️ Instalación y Configuración
Clonar o copiar los archivos del proyecto.

Crear y activar el entorno virtual:

```
Bash
python -m venv env
# En Windows:
env\Scripts\activate
Instalar dependencias necesarias:
```
```
Bash
pip install streamlit pandas fpdf openpyxl
🖥️ Ejecución
Para usuarios de Windows, simplemente haz doble clic en el archivo Lanzar_App.bat.
```
Alternativamente, desde la terminal con el entorno activo:
```
Bash
streamlit run app_unificada.py
```
---
## 📊 Módulos del Sistema
- 📝 Registro Estudio: Ingreso de asignaturas, días y bloques horarios para la universidad.

- 📝 Registro Laboral: Configuración semanal de turnos con detección inteligente de trasnoches.

- 📄 Impresión Horario Completo: El "Master Report" que unifica ambos mundos en un solo cronograma cronológico.

- 📄 Impresión Horario Estudio: Reporte específico de carga académica semanal.

- 📄 Impresión Horario Laboral: Reporte detallado de horas brutas, netas y extras para control de pagos.
---
Nota de Desarrollo: Este sistema fue optimizado utilizando capacidades de Gemini Plus para garantizar la integridad de las bases de datos y la precisión quirúrgica en los cálculos de tiempo laboral.

---

## 👨‍💻 Autoría y Desarrollo

Este ecosistema de gestión fue diseñado y codificado por:

**Nicolás Andrés Cano Leal** *BizOps & LiveOps | Python Developer | Backend · Data · Automation*

* **Rol Actual:** Live Performance Agent en **PedidosYa**.
* **Formación:** Ingeniería en Informática (IP Santo Tomás).
* **Especialidad:** Automatización de procesos (VBA/Python), Análisis de Datos y Desarrollo Backend.

### 📬 Conectemos:
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/nicolas-andres-cano-leal) 
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/NicolasAndresCL)
[![Portfolio](https://img.shields.io/badge/Portfolio-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://[tu-portfolio.streamlit.app](https://nicolasandrescl.pythonanywhere.com/))

---
*Desarrollado con ❤️ y precisión técnica en Rancagua, Chile.*