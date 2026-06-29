# motor-gestion-inventarios
Sistema de gestión de inventario bajo la metodología «Lean Manufacturing», gestionado a través de un motor analítico en Python y Streamlit para la conciliación en tiempo real de tres capas (Catálogo, ERP y Conteo Físico). Optimiza la disciplina operativa mediante la clasificación automática de desvíos y stock mal ubicado.  

## 🎯 Enfoque Metodológico (Lean Manufacturing)
El motor analítico se alinea directamente con los principios de la manufactura esbelta, actuando como una herramienta de control visual y resolución de problemas enfocado en:
* 📉 **Reducción de Desperdicios:** Identifica con precisión materiales mal ubicados, reduciendo los tiempos muertos y los movimientos innecesarios de operarios y autoelevadores.
* 🧼 **Disciplina Operativa (5S):** Promueve el pilar de *Seiton* (Orden) al contrastar dinámicamente dónde debería estar físicamente el stock versus dónde fue registrado.
* 👁️ **Transparencia y Control Visual:** Expone visualmente los desvíos financieros y de cantidades, permitiendo tomar acciones correctivas inmediatas sobre las inconsistencias del inventario.

---

## 🧠 Arquitectura de Conciliación en Tres Capas (3T)
El núcleo del algoritmo procesa y cruza de manera simultánea tres fuentes de datos críticas para la operación logística:
1. 📑 **Catálogo Maestro:** Base de datos de ingeniería que valida la existencia oficial de los códigos (SKU), descripciones y costos unitarios estándar.
2. 💻 **Registro Lógico (ERP):** El inventario teórico o contable que el sistema informático declara tener en cada posición y localizador.
3. 📋 **Conteo Físico (Auditoría):** Los datos reales relevados en el **GEMBA** por el equipo de almacén durante los inventarios cíclicos o generales.

---

## 📊 Estructura de Datos Requerida (Campos y Tipos)
Para que el motor ejecute la conciliación de forma correcta, los archivos de entrada (`.csv` o `.xlsx`) deben contener las siguientes columnas y formatos específicos:

### 1. Archivo: Catálogo Maestro
 | Campo | Tipo de Dato | Descripción
**SKU** | Texto (String) | Identificador único del artículo o material.
**DESCRIPCION** | Texto (String) | Nombre o detalle comercial del componente.
**COSTO_UNITARIO** | Numérico (Float) | Costo estándar del material.

### 2. Archivo: Registro Lógico (ERP)
 | Campo | Tipo de Dato | Descripción 
**SKU** | Texto (String) | Identificador único del artículo.
**LOCALIZADOR** | Texto (String) | Posición o rack asignado en el sistema.
**CANTIDAD** | Numérico (Entero/Float) | Stock teórico registrado en el sistema contable. 

### 3. Archivo: Conteo Físico (Auditoría)
 | Campo | Tipo de Dato | Descripción
**SKU** | Texto (String) | Identificador único del artículo relevado.
**LOCALIZADOR** | Texto (String) | Posición física real donde se encontró el material.
**CONTEO** | Numérico (Entero/Float) | Unidades físicas reales contadas por el auditor.

💡💡 **Nota de robustez:** El motor cuenta con un módulo de preprocesamiento automático que limpia espacios en blanco, estandariza a mayúsculas y convierte textos a formatos numéricos seguros para evitar caídas del sistema por inconsistencias de tipeo.

---
## 📊 Funcionalidades Clave y Agilización de la Auditoría

Conciliación Automatizada: Centraliza y cruza las tres fuentes de datos en segundos, eliminando el uso de buscarv/vlookup complejos y propensos a error en Excel. 
Agilización del Resultado: Reduce el tiempo de emisión del reporte final de auditoría, permitiendo al equipo de almacén realizar re-conteos inmediatos mientras la operación sigue en caliente. 
Clasificación Automática de Desvíos: Separa inconsistencias administrativas (errores de sistema) de diferencias físicas reales (faltantes o sobrantes).
Detección de Stock Mal Ubicado: Alerta si un SKU se encuentra físicamente en un localizador diferente al asignado por el sistema ERP. 
Impacto Financiero: Traduce las diferencias físicas a valores monetarios para priorizar el análisis de los desvíos con mayor criticidad económica.

---
## 🛠️ Tecnologías Utilizadas

* **Python: Para la lógica del motor analítico y el procesamiento de estructuras de datos complejas. 
* **Streamlit: Framework utilizado para el diseño de la interfaz de usuario y el despliegue de la aplicación web en la nube. 
* **Pandas: Biblioteca encargada de la manipulación, limpieza, mapeo y transformación de los dataframes de inventario. 
* **Openpyxl: Motor de lectura de datos para la integración nativa con planillas de cálculo operativas de Excel.

