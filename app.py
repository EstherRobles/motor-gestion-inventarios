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

# El motor arranca únicamente cuando las 3 fuentes están presentes
if file_catalogo and file_teorico and file_fisico:
    
    # 1. Lectura de archivos
    df_cat = pd.read_csv(file_catalogo) if file_catalogo.name.endswith('.csv') else pd.read_excel(file_catalogo)
    df_teo = pd.read_csv(file_teorico) if file_teorico.name.endswith('.csv') else pd.read_excel(file_teorico)
    df_fis = pd.read_csv(file_fisico) if file_fisico.name.endswith('.csv') else pd.read_excel(file_fisico)
    
    st.info("📊 Inicializando cruce relacional y análisis de consistencia de inventario...")

    # 2. Normalización de Encabezados (Elimina tildes, espacios y fuerza mayúsculas)
    for df in [df_cat, df_teo, df_fis]:
        df.columns = df.columns.astype(str).str.strip().str.upper()
        df.rename(columns={'UBICACIÓN': 'LOCALIZADOR', 'UNIT_COST': 'COSTO_UNITARIO'}, inplace=True)

    # 3. Validación de columnas mínimas requeridas por tabla
    cols_cat_ok = {'SKU', 'DESCRIPCION', 'COSTO_UNITARIO'}.issubset(df_cat.columns)
    cols_teo_ok = {'SKU', 'LOCALIZADOR', 'CANTIDAD'}.issubset(df_teo.columns)
    cols_fis_ok = {'SKU', 'LOCALIZADOR', 'CONTEO'}.issubset(df_fis.columns)

    if cols_cat_ok and cols_teo_ok and cols_fis_ok:
        
        # 4. Limpieza absoluta de llaves de texto primarias
        df_cat['SKU'] = df_cat['SKU'].fillna('').astype(str).str.strip().str.upper()
        
        for df in [df_teo, df_fis]:
            df['SKU'] = df['SKU'].fillna('').astype(str).str.strip().str.upper()
            df['LOCALIZADOR'] = df['LOCALIZADOR'].fillna('').astype(str).str.strip().str.upper()

        # 5. Forzar tipos numéricos para cálculos matemáticos seguros
        df_cat['COSTO_UNITARIO'] = pd.to_numeric(df_cat['COSTO_UNITARIO'], errors='coerce').fillna(0)
        df_teo['CANTIDAD'] = pd.to_numeric(df_teo['CANTIDAD'], errors='coerce').fillna(0)
        df_fis['CONTEO'] = pd.to_numeric(df_fis['CONTEO'], errors='coerce').fillna(0)

        # --- MOTOR LOGÍSTICO AVANZADO ---
        
        # Paso A: Consolidación total neta por SKU para evaluar desvíos globales reales (Independiente de la ubicación)
        neto_teo = df_teo.groupby('SKU')['CANTIDAD'].sum().to_dict()
        neto_fis = df_fis.groupby('SKU')['CONTEO'].sum().to_dict()
        
        # Paso B: Cruzar Registro Lógico (ERP) vs Auditoría Física por llave compuesta [SKU + LOCALIZADOR]
        df_cruce = pd.merge(
            df_teo, 
            df_fis, 
            on=['SKU', 'LOCALIZADOR'], 
            how='outer', 
            suffixes=('_teo', '_fis')
        )
        
        # Rellenar nulos de cantidades producidos por el merge outer
        df_cruce['CANTIDAD'] = df_cruce['CANTIDAD'].fillna(0)
        df_cruce['CONTEO'] = df_cruce['CONTEO'].fillna(0)
        
        # Paso C: Enriquecer la matriz trayendo los datos maestros del CATÁLOGO por SKU
        df_cruce = pd.merge(df_cruce, df_cat[['SKU', 'DESCRIPCION', 'COSTO_UNITARIO']], on='SKU', how='left')
        
        # Paso D: Análisis de desviaciones por línea
        df_cruce['DIFERENCIA_UNIDADES'] = df_cruce['CONTEO'] - df_cruce['CANTIDAD']
        
        # Paso E: Algoritmo de clasificación de condiciones operativas
        resultados = []
        catalogo_lista = set(df_cat['SKU']) # Optimizar búsqueda
        
        for idx, row in df_cruce.iterrows():
            sku = row['SKU']
            dif_linea = row['DIFERENCIA_UNIDADES']
            
            # Validación de existencia en catálogo maestro
            if sku not in catalogo_lista and sku != '':
                resultados.append("SKU NO CATALOGADO")
                continue
                
            stk_teorico_global = neto_teo.get(sku, 0)
            stk_fisico_global = neto_fis.get(sku, 0)
            dif_global = stk_fisico_global - stk_teorico_global
            
            if sku == '':
                resultados.append("FILA VACÍA")
            elif dif_linea == 0:
                resultados.append("OK")
            elif dif_linea != 0 and dif_global == 0:
                resultados.append("MAL UBICADO")
            elif dif_global < 0:
                resultados.append("FALTANTE NETO")
            else:
                resultados.append("SOBRANTE NETO")
                
        df_cruce['RESULTADO'] = resultados
        
        # Completar datos para ítems que aparecieron en el piso pero no estaban en el ERP actual
        df_cruce['DESCRIPCION'] = df_cruce['DESCRIPCION'].fillna("No figura en Catálogo")
        df_cruce['COSTO_UNITARIO'] = df_cruce['COSTO_UNITARIO'].fillna(0)
        
        # Calcular el desvío monetario final por línea
        df_cruce['VALOR_DESVIO'] = df_cruce['DIFERENCIA_UNIDADES'] * df_cruce['COSTO_UNITARIO']
        
        # Filtrar filas vacías remanentes
        df_cruce = df_cruce[df_cruce['SKU'] != '']

        # --- PANEL DE CONTROL (MÉTRICAS) ---
        st.markdown("### 📊 Indicadores Operativos Gerenciales")
        m1, m2, m3, m4 = st.columns(4)
        
        lineas_ok = len(df_cruce[df_cruce['RESULTADO'] == "OK"])
        lineas_mal = len(df_cruce[df_cruce['RESULTADO'] == "MAL UBICADO"])
        lineas_no_cat = len(df_cruce[df_cruce['RESULTADO'] == "SKU NO CATALOGADO"])
        
        m1.metric("Posiciones Correctas", f"{lineas_ok} líneas")
        m2.metric("Errores de Ubicación", f"{lineas_mal} líneas", delta="Revisar Ordenamiento", delta_color="off")
        m3.metric("Alertas de Catálogo", f"{lineas_no_cat} ítems", delta="Crítico", delta_color="inverse")
        m4.metric("Impacto Financiero Total", f"${df_cruce['VALOR_DESVIO'].sum():,.2f}")

        # --- MATRIZ INTERACTIVA ---
        st.markdown("### 📋 Matriz Detallada de Conciliación Multifocal")
        
        df_mostrar = df_cruce[[
            'SKU', 'DESCRIPCION', 'LOCALIZADOR', 'CANTIDAD', 'CONTEO', 
            'DIFERENCIA_UNIDADES', 'COSTO_UNITARIO', 'VALOR_DESVIO', 'RESULTADO'
        ]].rename(columns={'CANTIDAD': 'STOCK_TEORICO', 'CONTEO': 'STOCK_FISICO'})
        
        st.dataframe(df_mostrar, use_container_width=True)
        
    else:
        st.error("❌ Error de estructura: Revisá que el Catálogo tenga [SKU, DESCRIPCION, UNIT_COST], el ERP tenga [SKU, LOCALIZADOR, CANTIDAD] y el Conteo tenga [SKU, LOCALIZADOR, CONTEO].")