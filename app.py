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

# Función blindada para limpiar números (soporta Excel nativo y CSV con miles '.' y decimal ',')
def limpiar_numero(serie):
    if pd.api.types.is_numeric_dtype(serie):
        return serie.fillna(0)
    
    def parsear(val):
        if pd.isna(val):
            return 0.0
        s = str(val).strip().replace('$', '').replace(' ', '')
        if s == '':
            return 0.0
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        try:
            return float(s)
        except ValueError:
            return 0.0

    return serie.apply(parsear)

# El motor arranca únicamente cuando las 3 fuentes están presentes
if file_catalogo and file_teorico and file_fisico:
    
    # 1. Lectura de archivos
    df_cat = pd.read_csv(file_catalogo) if file_catalogo.name.endswith('.csv') else pd.read_excel(file_catalogo)
    df_teo = pd.read_csv(file_teorico) if file_teorico.name.endswith('.csv') else pd.read_excel(file_teorico)
    df_fis = pd.read_csv(file_fisico) if file_fisico.name.endswith('.csv') else pd.read_excel(file_fisico)
    
    st.info("📊 Inicializando cruce relacional sobre el universo del Conteo Físico...")

    # 2. Normalización de Encabezados
    renombres = {
        'CODIGO': 'SKU',
        'CÓDIGO': 'SKU',
        'ITEM': 'SKU',
        'UBICACIÓN': 'LOCALIZADOR',
        'UBICACION': 'LOCALIZADOR',
        'LOCALIZACION': 'LOCALIZADOR',
        'LOCALIZACIÓN': 'LOCALIZADOR',
        'LOCATOR': 'LOCALIZADOR',
        'UNIT_COST': 'COSTO_UNITARIO',
        'UNIDAD DE MEDIDA': 'UNIDAD_DE_MEDIDA',
        'UNIDAD_MEDIDA': 'UNIDAD_DE_MEDIDA',
        'UOM': 'UNIDAD_DE_MEDIDA',
        'UMD': 'UNIDAD_DE_MEDIDA',
        'SERIAL NUMBER': 'SERIAL_NUMBER',
        'LOTE': 'LOT',
        'ORGANIZACIÓN': 'ORGANIZACION',
        'ORG': 'ORGANIZACION',
        'INVENTORY ORGANIZATION CODE': 'ORGANIZACION',
        'SUBINVENTORY': 'SUBINVENTARIO',
        'COUNTED BY': 'CONTADO_POR',
        'DESCRIPCION': 'DESCRIPCION_ARCHIVO'
    }
    
    for df in [df_cat, df_teo, df_fis]:
        df.columns = df.columns.astype(str).str.strip().str.upper()
        df.rename(columns=renombres, inplace=True)

    # Restaurar nombre DESCRIPCION específicamente en el Catálogo Maestro
    if 'DESCRIPCION_ARCHIVO' in df_cat.columns:
        df_cat.rename(columns={'DESCRIPCION_ARCHIVO': 'DESCRIPCION'}, inplace=True)

    # Asegurar columnas opcionales de auditoría en Conteo Físico
    for col_opt in ['CONTADO_POR', 'SECUENCIA', 'UNIDAD_DE_MEDIDA']:
        if col_opt not in df_fis.columns:
            df_fis[col_opt] = ''

    # 3. Validación de columnas mínimas requeridas por tabla
    cols_cat_req = {'SKU', 'DESCRIPCION', 'COSTO_UNITARIO'}
    cols_teo_req = {
        'SKU', 'LOCALIZADOR', 'CANTIDAD', 'PROYECTO', 'TAREA', 
        'ORGANIZACION', 'SUBINVENTARIO', 'UNIDAD_DE_MEDIDA', 'SERIAL_NUMBER', 'LOT'
    }
    cols_fis_req = {'ORGANIZACION', 'SUBINVENTARIO', 'SKU', 'LOCALIZADOR', 'CONTEO'}

    cols_cat_ok = cols_cat_req.issubset(df_cat.columns)
    cols_teo_ok = cols_teo_req.issubset(df_teo.columns)
    cols_fis_ok = cols_fis_req.issubset(df_fis.columns)

    if cols_cat_ok and cols_teo_ok and cols_fis_ok:
        
        # 4. Limpieza absoluta de llaves de texto primarias
        df_cat['SKU'] = df_cat['SKU'].fillna('').astype(str).str.strip().str.upper()
        
        for df in [df_teo, df_fis]:
            for col_llave in ['ORGANIZACION', 'SUBINVENTARIO', 'SKU', 'LOCALIZADOR']:
                df[col_llave] = df[col_llave].fillna('').astype(str).str.strip().str.upper()

        cols_extra_teo = ['PROYECTO', 'TAREA', 'UNIDAD_DE_MEDIDA', 'SERIAL_NUMBER', 'LOT']
        for col in cols_extra_teo:
            df_teo[col] = df_teo[col].fillna('').astype(str).str.strip().str.upper()

        for col in ['CONTADO_POR', 'SECUENCIA', 'UNIDAD_DE_MEDIDA']:
            df_fis[col] = df_fis[col].fillna('').astype(str).str.strip().str.upper()

        # 5. Forzar tipos numéricos
        df_cat['COSTO_UNITARIO'] = limpiar_numero(df_cat['COSTO_UNITARIO'])
        df_teo['CANTIDAD'] = limpiar_numero(df_teo['CANTIDAD'])
        df_fis['CONTEO'] = limpiar_numero(df_fis['CONTEO'])

        # Deduplicar Catálogo por SKU
        df_cat_unico = df_cat.drop_duplicates(subset=['SKU'], keep='first')

        # --- MOTOR LOGÍSTICO ENFOCADO EN EL CONTEO FÍSICO ---
        
        # Paso A: Consolidación total neta por SKU (Global)
        neto_teo = df_teo.groupby('SKU')['CANTIDAD'].sum().to_dict()
        neto_fis = df_fis.groupby('SKU')['CONTEO'].sum().to_dict()
        
        llaves_cruce = ['ORGANIZACION', 'SUBINVENTARIO', 'SKU', 'LOCALIZADOR']

        # Paso B1: Consolidar ERP por llave completa (evita duplicar filas cuando hay lotes/proyectos)
        df_teo_agrupado = df_teo.groupby(llaves_cruce, as_index=False).agg({
            'CANTIDAD': 'sum',
            'UNIDAD_DE_MEDIDA': agrupar_textos,
            'PROYECTO': agrupar_textos,
            'TAREA': agrupar_textos,
            'LOT': agrupar_textos,
            'SERIAL_NUMBER': agrupar_textos
        })

        # Consolidar Físico por llave completa (universo base de análisis)
        df_fis_agrupado = df_fis.groupby(llaves_cruce, as_index=False).agg({
            'CONTEO': 'sum',
            'UNIDAD_DE_MEDIDA': agrupar_textos,
            'CONTADO_POR': agrupar_textos,
            'SECUENCIA': agrupar_textos
        })

        # Paso B2: Cruzar CONTEO FÍSICO (izquierda) contra STOCK TEÓRICO (derecha) -> Solo trae lo contado
        df_cruce = pd.merge(
            df_fis_agrupado,
            df_teo_agrupado,
            on=llaves_cruce,
            how='left',
            suffixes=('_CONTEO', '_ERP')
        )
        
        # Unificar Unidad de Medida (prioriza ERP y si no está en ERP toma la del Conteo)
        df_cruce['UNIDAD_DE_MEDIDA'] = df_cruce['UNIDAD_DE_MEDIDA_ERP'].replace('', pd.NA).fillna(df_cruce['UNIDAD_DE_MEDIDA_CONTEO']).fillna('')

        # Rellenar nulos para ítems contados que tenían 0 en el ERP
        df_cruce['CANTIDAD'] = df_cruce['CANTIDAD'].fillna(0)
        df_cruce['CONTEO'] = df_cruce['CONTEO'].fillna(0)
        for col in ['PROYECTO', 'TAREA', 'LOT', 'SERIAL_NUMBER', 'CONTADO_POR', 'SECUENCIA']:
            df_cruce[col] = df_cruce[col].fillna('')
        
        # Paso C: Enriquecer la matriz trayendo los datos maestros del CATÁLOGO por SKU
        df_cruce = pd.merge(df_cruce, df_cat_unico[['SKU', 'DESCRIPCION', 'COSTO_UNITARIO']], on='SKU', how='left')
        
        # Paso D: Análisis de desviaciones por línea
        df_cruce['DIFERENCIA_UNIDADES'] = df_cruce['CONTEO'] - df_cruce['CANTIDAD']
        
        # Paso E: Algoritmo de clasificación de condiciones operativas
        resultados = []
        catalogo_lista = set(df_cat_unico['SKU'])
        
        for idx, row in df_cruce.iterrows():
            sku = row['SKU']
            dif_linea = row['DIFERENCIA_UNIDADES']
            
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
            
            if dif_linea == 0:
                if tiene_atributos:
                    resultados.append("REVISAR LOTES Y PROYECTOS")
                else:
                    resultados.append("OK")
            elif dif_linea != 0 and dif_global == 0:
                resultados.append("MAL UBICADO (CON LOTES/PROY)" if tiene_atributos else "MAL UBICADO")
            elif dif_linea < 0:
                resultados.append("FALTANTE EN POSICIÓN (CON LOTES/PROY)" if tiene_atributos else "FALTANTE EN POSICIÓN")
            else:
                resultados.append("SOBRANTE EN POSICIÓN (CON LOTES/PROY)" if tiene_atributos else "SOBRANTE EN POSICIÓN")
                
        df_cruce['RESULTADO'] = resultados
        
        # Completar datos faltantes de catálogo
        df_cruce['DESCRIPCION'] = df_cruce['DESCRIPCION'].fillna("No figura en Catálogo")
        df_cruce['COSTO_UNITARIO'] = df_cruce['COSTO_UNITARIO'].fillna(0)
        
        # Calcular el desvío monetario final por línea
        df_cruce['VALOR_DESVIO'] = df_cruce['DIFERENCIA_UNIDADES'] * df_cruce['COSTO_UNITARIO']
        
        # Filtrar filas vacías remanentes
        df_cruce = df_cruce[df_cruce['SKU'] != '']

        # --- PANEL DE CONTROL (MÉTRICAS) ---
        st.markdown("### 📊 Indicadores Operativos (Sobre Posiciones Contadas)")
        m1, m2, m3, m4, m5 = st.columns(5)
        
        lineas_ok = len(df_cruce[df_cruce['RESULTADO'] == "OK"])
        lineas_revisar = len(df_cruce[df_cruce['RESULTADO'].str.contains("REVISAR LOTES")])
        lineas_mal = len(df_cruce[df_cruce['RESULTADO'].str.contains("MAL UBICADO")])
        lineas_no_cat = len(df_cruce[df_cruce['RESULTADO'] == "SKU NO CATALOGADO"])
        
        m1.metric("Posiciones OK (Directas)", f"{lineas_ok}")
        m2.metric("Revisar Lotes/Proy.", f"{lineas_revisar}", delta="Requiere desglose", delta_color="off")
        m3.metric("Errores de Ubicación", f"{lineas_mal}")
        m4.metric("Alertas de Catálogo", f"{lineas_no_cat}", delta="Crítico", delta_color="inverse")
        m5.metric("Impacto Financiero Contado", f"${df_cruce['VALOR_DESVIO'].sum():,.2f}")

        # --- MATRIZ INTERACTIVA CON FILTRO ---
        st.markdown("### 📋 Matriz Detallada de Conciliación (Universo Contado)")
        
        opciones_filtro = ["TODOS"] + sorted(df_cruce['RESULTADO'].unique().tolist())
        filtro_sel = st.selectbox("🔍 Filtrar por Estado / Resultado:", opciones_filtro)
        
        df_filtrado = df_cruce if filtro_sel == "TODOS" else df_cruce[df_cruce['RESULTADO'] == filtro_sel]
        
        columnas_ordenadas = [
            'ORGANIZACION', 'SUBINVENTARIO', 'LOCALIZADOR', 'SKU', 'DESCRIPCION',
            'UNIDAD_DE_MEDIDA', 'CANTIDAD', 'CONTEO', 'DIFERENCIA_UNIDADES', 
            'RESULTADO', 'LOT', 'SERIAL_NUMBER', 'PROYECTO', 'TAREA',
            'SECUENCIA', 'CONTADO_POR', 'COSTO_UNITARIO', 'VALOR_DESVIO'
        ]
        
        df_mostrar = df_filtrado[columnas_ordenadas].rename(
            columns={'CANTIDAD': 'STOCK_TEORICO', 'CONTEO': 'STOCK_FISICO'}
        )
        
        st.dataframe(df_mostrar, use_container_width=True)
        
    else:
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
