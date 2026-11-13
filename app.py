import streamlit as st
import pandas as pd

# Configuración de página ancha para mejor lectura de la matriz
st.set_page_config(page_title="Conciliador Inteligente 3T", layout="wide")

st.title("🔄 Motor de Conciliación Avanzado de Tres Capas (3T)")
st.subheader("Integración de Catálogo Maestro, Registro Lógico (ERP) y Auditoría Física")
st.markdown("---")

# Interfaz de carga para los 3 archivos requeridos
st.markdown("### 📂 Carga de Fuentes de Datos")
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("📔 1. Catálogo Maestro")
    file_catalogo = st.file_uploader("Subir Maestro de Artículos", type=["csv", "xlsx"])

with col2:
    st.subheader("💻 2. Stock Teórico (ERP)")
    file_teorico = st.file_uploader("Subir Saldo del Sistema", type=["csv", "xlsx"])

with col3:
    st.subheader("📋 3. Conteo Físico")
    file_fisico = st.file_uploader("Subir Auditoría de Depósito", type=["csv", "xlsx"])

# Función auxiliar para concatenar valores únicos sin repetir ni mostrar vacíos
def agrupar_textos(serie):
    vals = [str(x).strip() for x in serie if pd.notna(x) and str(x).strip() not in ['', 'NAN', 'NONE', 'NAT']]
    unicos = list(dict.fromkeys(vals))
    return " | ".join(unicos) if unicos else ""

# El motor arranca únicamente cuando las 3 fuentes están presentes
if file_catalogo and file_teorico and file_fisico:
    
    # 1. Lectura de archivos
    df_cat = pd.read_csv(file_catalogo) if file_catalogo.name.endswith('.csv') else pd.read_excel(file_catalogo)
    df_teo = pd.read_csv(file_teorico) if file_teorico.name.endswith('.csv') else pd.read_excel(file_teorico)
    df_fis = pd.read_csv(file_fisico) if file_fisico.name.endswith('.csv') else pd.read_excel(file_fisico)
    
    st.info("📊 Inicializando cruce relacional y análisis de consistencia de inventario...")

    # 2. Normalización de Encabezados (Elimina espacios, fuerza mayúsculas y unifica variantes)
    renombres = {
        'UBICACIÓN': 'LOCALIZADOR',
        'UBICACION': 'LOCALIZADOR',
        'UNIT_COST': 'COSTO_UNITARIO',
        'UNIDAD DE MEDIDA': 'UNIDAD_DE_MEDIDA',
        'UOM': 'UNIDAD_DE_MEDIDA',
        'SERIAL NUMBER': 'SERIAL_NUMBER',
        'LOTE': 'LOT',
        'ORGANIZACIÓN': 'ORGANIZACION'
    }
    
    for df in [df_cat, df_teo, df_fis]:
        df.columns = df.columns.astype(str).str.strip().str.upper()
        df.rename(columns=renombres, inplace=True)

    # 3. Validación de columnas mínimas requeridas por tabla
    cols_cat_req = {'SKU', 'DESCRIPCION', 'COSTO_UNITARIO'}
    cols_teo_req = {
        'SKU', 'LOCALIZADOR', 'CANTIDAD', 'PROYECTO', 'TAREA', 
        'ORGANIZACION', 'SUBINVENTARIO', 'UNIDAD_DE_MEDIDA', 'SERIAL_NUMBER', 'LOT'
    }
    cols_fis_req = {'SKU', 'LOCALIZADOR', 'CONTEO'}

    cols_cat_ok = cols_cat_req.issubset(df_cat.columns)
    cols_teo_ok = cols_teo_req.issubset(df_teo.columns)
    cols_fis_ok = cols_fis_req.issubset(df_fis.columns)

    if cols_cat_ok and cols_teo_ok and cols_fis_ok:
        
        # 4. Limpieza absoluta de llaves de texto primarias
        df_cat['SKU'] = df_cat['SKU'].fillna('').astype(str).str.strip().str.upper()
        
        for df in [df_teo, df_fis]:
            df['SKU'] = df['SKU'].fillna('').astype(str).str.strip().str.upper()
            df['LOCALIZADOR'] = df['LOCALIZADOR'].fillna('').astype(str).str.strip().str.upper()

        # Limpieza de las nuevas columnas de texto en ERP
        cols_extra_teo = ['PROYECTO', 'TAREA', 'ORGANIZACION', 'SUBINVENTARIO', 'UNIDAD_DE_MEDIDA', 'SERIAL_NUMBER', 'LOT']
        for col in cols_extra_teo:
            df_teo[col] = df_teo[col].fillna('').astype(str).str.strip().str.upper()

        # 5. Forzar tipos numéricos para cálculos matemáticos seguros
        df_cat['COSTO_UNITARIO'] = pd.to_numeric(df_cat['COSTO_UNITARIO'], errors='coerce').fillna(0)
        df_teo['CANTIDAD'] = pd.to_numeric(df_teo['CANTIDAD'], errors='coerce').fillna(0)
        df_fis['CONTEO'] = pd.to_numeric(df_fis['CONTEO'], errors='coerce').fillna(0)

        # --- MOTOR LOGÍSTICO AVANZADO ---
        
        # Paso A: Consolidación total neta por SKU (Global)
        neto_teo = df_teo.groupby('SKU')['CANTIDAD'].sum().to_dict()
        neto_fis = df_fis.groupby('SKU')['CONTEO'].sum().to_dict()
        
        # Paso B1: Consolidar ERP por [SKU + LOCALIZADOR] para evitar duplicados cuando hay múltiples lotes/proyectos
        df_teo_agrupado = df_teo.groupby(['SKU', 'LOCALIZADOR'], as_index=False).agg({
            'CANTIDAD': 'sum',
            'ORGANIZACION': agrupar_textos,
            'SUBINVENTARIO': agrupar_textos,
            'UNIDAD_DE_MEDIDA': agrupar_textos,
            'PROYECTO': agrupar_textos,
            'TAREA': agrupar_textos,
            'LOT': agrupar_textos,
            'SERIAL_NUMBER': agrupar_textos
        })

        # Consolidar Físico por [SKU + LOCALIZADOR] por seguridad si hubiera más de una toma en el mismo lugar
        df_fis_agrupado = df_fis.groupby(['SKU', 'LOCALIZADOR'], as_index=False).agg({
            'CONTEO': 'sum'
        })

        # Paso B2: Cruzar Registro Lógico (ERP) vs Auditoría Física por llave compuesta [SKU + LOCALIZADOR]
        df_cruce = pd.merge(
            df_teo_agrupado, 
            df_fis_agrupado, 
            on=['SKU', 'LOCALIZADOR'], 
            how='outer'
        )
        
        # Rellenar nulos producidos por el merge outer
        df_cruce['CANTIDAD'] = df_cruce['CANTIDAD'].fillna(0)
        df_cruce['CONTEO'] = df_cruce['CONTEO'].fillna(0)
        for col in cols_extra_teo:
            df_cruce[col] = df_cruce[col].fillna('')
        
        # Paso C: Enriquecer la matriz trayendo los datos maestros del CATÁLOGO por SKU
        df_cruce = pd.merge(df_cruce, df_cat[['SKU', 'DESCRIPCION', 'COSTO_UNITARIO']], on='SKU', how='left')
        
        # Paso D: Análisis de desviaciones por línea
        df_cruce['DIFERENCIA_UNIDADES'] = df_cruce['CONTEO'] - df_cruce['CANTIDAD']
        
        # Paso E: Algoritmo de clasificación de condiciones operativas
        resultados = []
        catalogo_lista = set(df_cat['SKU'])
        
        for idx, row in df_cruce.iterrows():
            sku = row['SKU']
            dif_linea = row['DIFERENCIA_UNIDADES']
            
            # Detectar si la posición tiene atributos de trazabilidad (Lote, Serie, Proyecto o Tarea)
            tiene_atributos = any([
                row['LOT'] != '',
                row['SERIAL_NUMBER'] != '',
                row['PROYECTO'] != '',
                row['TAREA'] != ''
            ])
            
            if sku == '':
                resultados.append("FILA VACÍA")
                continue

            if sku not in catalogo_lista:
                resultados.append("SKU NO CATALOGADO")
                continue
                
            stk_teorico_global = neto_teo.get(sku, 0)
            stk_fisico_global = neto_fis.get(sku, 0)
            dif_global = stk_fisico_global - stk_teorico_global
            
            # Clasificación con detección de Lotes / Proyectos
            if dif_linea == 0:
                if tiene_atributos:
                    resultados.append("REVISAR LOTES Y PROYECTOS")
                else:
                    resultados.append("OK")
            elif dif_linea != 0 and dif_global == 0:
                resultados.append("MAL UBICADO (CON LOTES/PROY)" if tiene_atributos else "MAL UBICADO")
            elif dif_global < 0:
                resultados.append("FALTANTE NETO (CON LOTES/PROY)" if tiene_atributos else "FALTANTE NETO")
            else:
                resultados.append("SOBRANTE NETO (CON LOTES/PROY)" if tiene_atributos else "SOBRANTE NETO")
                
        df_cruce['RESULTADO'] = resultados
        
        # Completar datos faltantes de catálogo
        df_cruce['DESCRIPCION'] = df_cruce['DESCRIPCION'].fillna("No figura en Catálogo")
        df_cruce['COSTO_UNITARIO'] = df_cruce['COSTO_UNITARIO'].fillna(0)
        
        # Calcular el desvío monetario final por línea
        df_cruce['VALOR_DESVIO'] = df_cruce['DIFERENCIA_UNIDADES'] * df_cruce['COSTO_UNITARIO']
        
        # Filtrar filas vacías remanentes
        df_cruce = df_cruce[df_cruce['SKU'] != '']

        # --- PANEL DE CONTROL (MÉTRICAS) ---
        st.markdown("### 📊 Indicadores Operativos Gerenciales")
        m1, m2, m3, m4, m5 = st.columns(5)
        
        lineas_ok = len(df_cruce[df_cruce['RESULTADO'] == "OK"])
        lineas_revisar = len(df_cruce[df_cruce['RESULTADO'].str.contains("REVISAR LOTES")])
        lineas_mal = len(df_cruce[df_cruce['RESULTADO'].str.contains("MAL UBICADO")])
        lineas_no_cat = len(df_cruce[df_cruce['RESULTADO'] == "SKU NO CATALOGADO"])
        
        m1.metric("Posiciones OK (Directas)", f"{lineas_ok}")
        m2.metric("Revisar Lotes/Proy.", f"{lineas_revisar}", delta="Requiere desglose", delta_color="off")
        m3.metric("Errores de Ubicación", f"{lineas_mal}")
        m4.metric("Alertas de Catálogo", f"{lineas_no_cat}", delta="Crítico", delta_color="inverse")
        m5.metric("Impacto Financiero Total", f"${df_cruce['VALOR_DESVIO'].sum():,.2f}")

        # --- MATRIZ INTERACTIVA CON FILTRO ---
        st.markdown("### 📋 Matriz Detallada de Conciliación Multifocal")
        
        # Filtro rápido por Resultado para aislar los ~300 ítems al instante
        opciones_filtro = ["TODOS"] + sorted(df_cruce['RESULTADO'].unique().tolist())
        filtro_sel = st.selectbox("🔍 Filtrar por Estado / Resultado:", opciones_filtro)
        
        df_filtrado = df_cruce if filtro_sel == "TODOS" else df_cruce[df_cruce['RESULTADO'] == filtro_sel]
        
        columnas_ordenadas = [
            'SKU', 'DESCRIPCION', 'ORGANIZACION', 'SUBINVENTARIO', 'LOCALIZADOR', 
            'UNIDAD_DE_MEDIDA', 'CANTIDAD', 'CONTEO', 'DIFERENCIA_UNIDADES', 
            'RESULTADO', 'LOT', 'SERIAL_NUMBER', 'PROYECTO', 'TAREA', 
            'COSTO_UNITARIO', 'VALOR_DESVIO'
        ]
        
        df_mostrar = df_filtrado[columnas_ordenadas].rename(
            columns={'CANTIDAD': 'STOCK_TEORICO', 'CONTEO': 'STOCK_FISICO'}
        )
        
        st.dataframe(df_mostrar, use_container_width=True)
        
    else:
        # Mensaje detallado indicando exactamente qué columna falta si hay error
        faltantes_cat = cols_cat_req - set(df_cat.columns)
        faltantes_teo = cols_teo_req - set(df_teo.columns)
        faltantes_fis = cols_fis_req - set(df_fis.columns)
        
        st.error("❌ Error de estructura en los archivos cargados:")
        if faltantes_cat:
            st.warning(f"Faltan en Catálogo: {list(faltantes_cat)}")
        if faltantes_teo:
            st.warning(f"Faltan en Stock Teórico (ERP): {list(faltantes_teo)}")
        if faltantes_fis:
            st.warning(f"Faltan en Conteo Físico: {list(faltantes_fis)}")
