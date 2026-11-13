import streamlit as st
import pandas as pd
from io import BytesIO

# Configuración de página ancha para mejor lectura de la matriz
st.set_page_config(page_title="Conciliador Inteligente 3T+", layout="wide")

st.title("🔄 Motor de Conciliación Avanzado (Catálogo + ERP + Físico + Cut-Off)")
st.subheader("Integración de Catálogo Maestro, Registro Lógico (ERP), Auditoría Física y Transacciones")
st.markdown("---")

# Interfaz de carga para los archivos (3 obligatorios + 1 opcional de transacciones)
st.markdown("### 📂 Carga de Fuentes de Datos")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.subheader("📔 1. Catálogo Maestro")
    file_catalogo = st.file_uploader("Subir Maestro de Artículos", type=["csv", "xlsx"])

with col2:
    st.subheader("💻 2. Stock Teórico (ERP)")
    file_teorico = st.file_uploader("Subir Saldo del Sistema", type=["csv", "xlsx"])

with col3:
    st.subheader("📋 3. Conteo Físico")
    file_fisico = st.file_uploader("Subir Auditoría de Depósito", type=["csv", "xlsx"])

with col4:
    st.subheader("⏱️ 4. Transacciones (Opcional)")
    file_trx = st.file_uploader("Subir Movimientos (Cut-Off)", type=["csv", "xlsx"])

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

# Función para convertir DataFrame a Excel en memoria
def convertir_a_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Conciliacion_3T')
    return output.getvalue()

# El motor arranca cuando las 3 fuentes principales están presentes
if file_catalogo and file_teorico and file_fisico:
    
    # 1. Lectura de archivos obligatorios
    df_cat = pd.read_csv(file_catalogo) if file_catalogo.name.endswith('.csv') else pd.read_excel(file_catalogo)
    df_teo = pd.read_csv(file_teorico) if file_teorico.name.endswith('.csv') else pd.read_excel(file_teorico)
    df_fis = pd.read_csv(file_fisico) if file_fisico.name.endswith('.csv') else pd.read_excel(file_fisico)
    
    st.info("📊 Inicializando cruce relacional sobre el universo del Conteo Físico...")

    # 2. Normalización de Encabezados (Todas las claves en MAYÚSCULAS)
    renombres = {
        'CODIGO': 'SKU',
        'CÓDIGO': 'SKU',
        'ITEM': 'SKU',
        'ITEM NAME': 'SKU',
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
        'UDM': 'UNIDAD_DE_MEDIDA',
        'SERIAL NUMBER': 'SERIAL_NUMBER',
        'LOTE': 'LOT',
        'ORGANIZACIÓN': 'ORGANIZACION',
        'ORG': 'ORGANIZACION',
        'INVENTORY ORGANIZATION CODE': 'ORGANIZACION',
        'SUBINVENTORY': 'SUBINVENTARIO',
        'COUNTED BY': 'CONTADO_POR',
        'RECUENTO REALIZADO POR': 'CONTADO_POR',
        'FECHA': 'FECHA_CONTEO',
        'FECHA DE CONTEO': 'FECHA_CONTEO',
        'COUNT DATE': 'FECHA_CONTEO',
        'TRANSACTION DATE': 'FECHA_TRX',
        'QUANTITY': 'CANTIDAD_TRX',
        'TRANSACTION TYPE': 'TIPO_TRX',
        'CAT. TRANSACCION': 'CAT_TRX',
        'TRANSACTION SOURCE REFERENCE': 'REF_ORIGEN_TRX',
        'DESCRIPCION': 'DESCRIPCION_ARCHIVO',
        'ITEM DESCRIPTION': 'DESCRIPCION_ARCHIVO'
    }
    
    for df in [df_cat, df_teo, df_fis]:
        df.columns = df.columns.astype(str).str.strip().str.upper()
        df.rename(columns=renombres, inplace=True)

    # Restaurar nombre DESCRIPCION específicamente en el Catálogo Maestro
    if 'DESCRIPCION_ARCHIVO' in df_cat.columns:
        df_cat.rename(columns={'DESCRIPCION_ARCHIVO': 'DESCRIPCION'}, inplace=True)

    # Asegurar columnas opcionales en Conteo Físico
    for col_opt in ['CONTADO_POR', 'SECUENCIA', 'UNIDAD_DE_MEDIDA']:
        if col_opt not in df_fis.columns:
            df_fis[col_opt] = ''

    # Parsear Fecha de Conteo si existe en la planilla de Conteo
    tiene_fecha_conteo = 'FECHA_CONTEO' in df_fis.columns
    if tiene_fecha_conteo:
        df_fis['FECHA_CONTEO_DT'] = pd.to_datetime(df_fis['FECHA_CONTEO'], dayfirst=True, errors='coerce')
    else:
        df_fis['FECHA_CONTEO_DT'] = pd.NaT

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
        
        neto_teo = df_teo.groupby('SKU')['CANTIDAD'].sum().to_dict()
        neto_fis = df_fis.groupby('SKU')['CONTEO'].sum().to_dict()
        
        llaves_cruce = ['ORGANIZACION', 'SUBINVENTARIO', 'SKU', 'LOCALIZADOR']

        # Consolidar ERP por llave completa
        df_teo_agrupado = df_teo.groupby(llaves_cruce, as_index=False).agg({
            'CANTIDAD': 'sum',
            'UNIDAD_DE_MEDIDA': agrupar_textos,
            'PROYECTO': agrupar_textos,
            'TAREA': agrupar_textos,
            'LOT': agrupar_textos,
            'SERIAL_NUMBER': agrupar_textos
        })

        # Consolidar Físico por llave completa (conservando la fecha más temprana del conteo en esa posición)
        df_fis_agrupado = df_fis.groupby(llaves_cruce, as_index=False).agg({
            'CONTEO': 'sum',
            'UNIDAD_DE_MEDIDA': agrupar_textos,
            'CONTADO_POR': agrupar_textos,
            'SECUENCIA': agrupar_textos,
            'FECHA_CONTEO_DT': 'min'
        })

        # Cruzar CONTEO FÍSICO (izquierda) contra STOCK TEÓRICO (derecha)
        df_cruce = pd.merge(
            df_fis_agrupado,
            df_teo_agrupado,
            on=llaves_cruce,
            how='left',
            suffixes=('_CONTEO', '_ERP')
        )
        
        # Unificar Unidad de Medida
        df_cruce['UNIDAD_DE_MEDIDA'] = df_cruce['UNIDAD_DE_MEDIDA_ERP'].replace('', pd.NA).fillna(df_cruce['UNIDAD_DE_MEDIDA_CONTEO']).fillna('')

        # Rellenar nulos
        df_cruce['CANTIDAD'] = df_cruce['CANTIDAD'].fillna(0)
        df_cruce['CONTEO'] = df_cruce['CONTEO'].fillna(0)
        for col in ['PROYECTO', 'TAREA', 'LOT', 'SERIAL_NUMBER', 'CONTADO_POR', 'SECUENCIA']:
            df_cruce[col] = df_cruce[col].fillna('')
        
        # Enriquecer con Catálogo Maestro
        df_cruce = pd.merge(df_cruce, df_cat_unico[['SKU', 'DESCRIPCION', 'COSTO_UNITARIO']], on='SKU', how='left')
        
        # Desviación de unidades (Foto Conteo vs Foto ERP)
        df_cruce['DIFERENCIA_UNIDADES'] = df_cruce['CONTEO'] - df_cruce['CANTIDAD']

        # --- ANÁLISIS DE CUT-OFF (TRANSACCIONES POST-CONTEO) ---
        df_cruce['CANT_MOV_POST_CONTEO'] = 0
        df_cruce['NETO_TRX_POST_CONTEO'] = 0.0
        df_cruce['DETALLE_TRX_POST_CONTEO'] = ''

        if file_trx is not None:
            df_trx = pd.read_csv(file_trx) if file_trx.name.endswith('.csv') else pd.read_excel(file_trx)
            df_trx.columns = df_trx.columns.astype(str).str.strip().str.upper()
            df_trx.rename(columns=renombres, inplace=True)
            # Renombre exclusivo para Transacciones si viene como 'CANTIDAD'
            df_trx.rename(columns={'CANTIDAD': 'CANTIDAD_TRX'}, inplace=True)

            cols_trx_req = {'ORGANIZACION', 'SUBINVENTARIO', 'SKU', 'LOCALIZADOR', 'FECHA_TRX', 'CANTIDAD_TRX'}
            if cols_trx_req.issubset(df_trx.columns):
                if not tiene_fecha_conteo:
                    st.warning("⚠️ Subiste el archivo de Transacciones, pero el Conteo Físico no tiene columna 'FECHA_CONTEO' (o 'FECHA'). Agregala para filtrar movimientos posteriores.")
                else:
                    for col_llave in llaves_cruce:
                        df_trx[col_llave] = df_trx[col_llave].fillna('').astype(str).str.strip().str.upper()
                    
                    df_trx['CANTIDAD_TRX'] = limpiar_numero(df_trx['CANTIDAD_TRX'])
                    df_trx['FECHA_TRX_DT'] = pd.to_datetime(df_trx['FECHA_TRX'], dayfirst=True, errors='coerce')
                    
                    if 'TIPO_TRX' not in df_trx.columns:
                        df_trx['TIPO_TRX'] = 'MOVIMIENTO'
                    df_trx['TIPO_TRX'] = df_trx['TIPO_TRX'].fillna('MOVIMIENTO').astype(str).str.strip()

                    # Etiqueta descriptiva por cada transacción (ej: "Subinventory Transfer (-9) [05/11 14:05]")
                    df_trx['RESUMEN_LINEA'] = (
                        df_trx['TIPO_TRX'] + " (" + 
                        df_trx['CANTIDAD_TRX'].apply(lambda x: f"{x:+g}") + ") [" +
                        df_trx['FECHA_TRX_DT'].dt.strftime('%d/%m %H:%M').fillna('') + "]"
                    )

                    # Cruzar transacciones contra las posiciones contadas que tienen fecha válida
                    df_pos_con_fecha = df_cruce[llaves_cruce + ['FECHA_CONTEO_DT']].dropna(subset=['FECHA_CONTEO_DT'])
                    df_trx_cruce = pd.merge(df_trx, df_pos_con_fecha, on=llaves_cruce, how='inner')

                    # Filtrar SOLO transacciones ocurridas DESPUÉS (o en el mismo instante) del conteo
                    df_trx_post = df_trx_cruce[df_trx_cruce['FECHA_TRX_DT'] >= df_trx_cruce['FECHA_CONTEO_DT']]

                    if not df_trx_post.empty:
                        df_trx_resumen = df_trx_post.groupby(llaves_cruce, as_index=False).agg(
                            CANT_MOV_POST_CONTEO=('CANTIDAD_TRX', 'count'),
                            NETO_TRX_POST_CONTEO=('CANTIDAD_TRX', 'sum'),
                            DETALLE_TRX_POST_CONTEO=('RESUMEN_LINEA', agrupar_textos)
                        )
                        df_cruce.drop(columns=['CANT_MOV_POST_CONTEO', 'NETO_TRX_POST_CONTEO', 'DETALLE_TRX_POST_CONTEO'], inplace=True)
                        df_cruce = pd.merge(df_cruce, df_trx_resumen, on=llaves_cruce, how='left')
                        df_cruce['CANT_MOV_POST_CONTEO'] = df_cruce['CANT_MOV_POST_CONTEO'].fillna(0).astype(int)
                        df_cruce['NETO_TRX_POST_CONTEO'] = df_cruce['NETO_TRX_POST_CONTEO'].fillna(0.0)
                        df_cruce['DETALLE_TRX_POST_CONTEO'] = df_cruce['DETALLE_TRX_POST_CONTEO'].fillna('')
            else:
                faltantes_trx = cols_trx_req - set(df_trx.columns)
                st.warning(f"⚠️ No se pudo procesar Transacciones. Faltan columnas: {list(faltantes_trx)}")

        # --- ALGORITMO DE CLASIFICACIÓN CONSERVADOR (CON DETECCIÓN DE LOTES Y CUT-OFF) ---
        resultados = []
        catalogo_lista = set(df_cat_unico['SKU'])
        
        for idx, row in df_cruce.iterrows():
            sku = row['SKU']
            dif_linea = row['DIFERENCIA_UNIDADES']
            cant_movs = row['CANT_MOV_POST_CONTEO']
            neto_trx = row['NETO_TRX_POST_CONTEO']
            
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
                resultados.append("SOBRANTE TOTAL")
                continue
                
            stk_teorico_global = neto_teo.get(sku, 0)
            stk_fisico_global = neto_fis.get(sku, 0)
            dif_global = stk_fisico_global - stk_teorico_global
            
            # 1. Evaluar primero si hubo transacciones posteriores que expliquen el desvío
            if cant_movs > 0:
                if dif_linea != 0 and round(dif_linea + neto_trx, 4) == 0:
                    resultados.append("CONCILIADO POR MOV. POST-CONTEO")
                    continue
                elif dif_linea != 0:
                    resultados.append("REVISAR MOV. POST-CONTEO (DIF. PARCIAL)")
                    continue
                elif dif_linea == 0 and neto_trx != 0:
                    resultados.append("ALERTA: MOV. POST-CONTEO CON DIF. 0")
                    continue

            # 2. Clasificación estándar (sin movimientos posteriores que alteren el saldo)
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
        
        # Formatear Fecha de Conteo para visualización limpia
        df_cruce['FECHA_CONTEO_STR'] = df_cruce['FECHA_CONTEO_DT'].dt.strftime('%d/%m/%Y %H:%M').fillna('')

        # Completar datos faltantes de catálogo
        df_cruce['DESCRIPCION'] = df_cruce['DESCRIPCION'].fillna("No figura en Catálogo")
        df_cruce['COSTO_UNITARIO'] = df_cruce['COSTO_UNITARIO'].fillna(0)
        
        # Calcular el desvío monetario final por línea
        df_cruce['VALOR_DESVIO'] = df_cruce['DIFERENCIA_UNIDADES'] * df_cruce['COSTO_UNITARIO']
        
        # Filtrar filas vacías remanentes
        df_cruce = df_cruce[df_cruce['SKU'] != '']

        # --- PANEL DE CONTROL (MÉTRICAS) ---
        st.markdown("### 📊 Indicadores Operativos (Sobre Posiciones Contadas)")
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        
        lineas_ok = len(df_cruce[df_cruce['RESULTADO'] == "OK"])
        lineas_revisar = len(df_cruce[df_cruce['RESULTADO'].str.contains("REVISAR LOTES")])
        lineas_mov_post = len(df_cruce[df_cruce['RESULTADO'].str.contains("POST-CONTEO")])
        lineas_mal = len(df_cruce[df_cruce['RESULTADO'].str.contains("MAL UBICADO")])
        lineas_no_cat = len(df_cruce[df_cruce['RESULTADO'] == "SOBRANTE TOTAL"])
        
        m1.metric("Posiciones OK", f"{lineas_ok}")
        m2.metric("Revisar Lotes/Proy.", f"{lineas_revisar}")
        m3.metric("Con Mov. Post-Conteo", f"{lineas_mov_post}", delta="Cut-Off")
        m4.metric("Mal Ubicados", f"{lineas_mal}")
        m5.metric("Sin Catálogo", f"{lineas_no_cat}")
        m6.metric("Impacto Financiero", f"${df_cruce['VALOR_DESVIO'].sum():,.2f}")

        # --- MATRIZ INTERACTIVA CON FILTRO ---
        st.markdown("### 📋 Matriz Detallada de Conciliación (Universo Contado)")
        
        opciones_filtro = ["TODOS"] + sorted(df_cruce['RESULTADO'].unique().tolist())
        filtro_sel = st.selectbox("🔍 Filtrar por Estado / Resultado:", opciones_filtro)
        
        df_filtrado = df_cruce if filtro_sel == "TODOS" else df_cruce[df_cruce['RESULTADO'] == filtro_sel]
        
        columnas_ordenadas = [
            'ORGANIZACION', 'SUBINVENTARIO', 'LOCALIZADOR', 'SKU', 'DESCRIPCION',
            'UNIDAD_DE_MEDIDA', 'FECHA_CONTEO_STR', 'CANTIDAD', 'CONTEO', 'DIFERENCIA_UNIDADES', 
            'RESULTADO', 'CANT_MOV_POST_CONTEO', 'NETO_TRX_POST_CONTEO', 'DETALLE_TRX_POST_CONTEO',
            'LOT', 'SERIAL_NUMBER', 'PROYECTO', 'TAREA',
            'SECUENCIA', 'CONTADO_POR', 'COSTO_UNITARIO', 'VALOR_DESVIO'
        ]
        
        df_mostrar = df_filtrado[columnas_ordenadas].rename(columns={
            'CANTIDAD': 'STOCK_TEORICO',
            'CONTEO': 'STOCK_FISICO',
            'FECHA_CONTEO_STR': 'FECHA_CONTEO',
            'CANT_MOV_POST_CONTEO': 'MOVS_POST_CONTEO',
            'NETO_TRX_POST_CONTEO': 'NETO_MOVS_POST',
            'DETALLE_TRX_POST_CONTEO': 'DETALLE_MOVIMIENTOS'
        })
        
        st.dataframe(df_mostrar, use_container_width=True)

        # --- BOTONES DE DESCARGA (EXCEL Y CSV) ---
        st.markdown("### 📥 Exportar Resultados")
        btn1, btn2, _ = st.columns([1, 1, 2])
        
        nombre_base = f"conciliacion_3T_{filtro_sel.lower().replace(' ', '_').replace('/', '_')}"
        
        with btn1:
            st.download_button(
                label="📗 Descargar Excel (.xlsx)",
                data=convertir_a_excel(df_mostrar),
                file_name=f"{nombre_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        with btn2:
            csv_data = df_mostrar.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button(
                label="📄 Descargar CSV (.csv)",
                data=csv_data,
                file_name=f"{nombre_base}.csv",
                mime="text/csv"
            )
        
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
