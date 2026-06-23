import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import datetime

# Ajustes de configuración de la interfaz gráfica
st.set_page_config(
    page_title="Gestor Comercial de Caja y Stock Elite",
    layout="wide",
    page_icon="💼"
)

# Inicialización segura de la conexión de Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# URL asignada directamente para solucionar el error de configuración de secretos
URL_DOCUMENTO = "https://docs.google.com/spreadsheets/d/1ubonT7F9SdjH5SnXHIWCLqzsccGQfMgvN_vcsoErupA/edit?gid=0#gid=0"

def inicializar_almacen_datos():
    """
    Verifica de manera defensiva la existencia de las tablas en la nube.
    Crea las estructuras iniciales si las pestañas requeridas no existen.
    """
    if not URL_DOCUMENTO:
        st.error("Error crítico: No se ha detectado la propiedad 'spreadsheet' en los secretos de la conexión.")
        return
    try:
        # Acceso directo al cliente subyacente para manipulación de estructura
        sh = conn.client._open_spreadsheet(spreadsheet=URL_DOCUMENTO)
        hojas_en_nube = [ws.title for ws in sh.worksheets()]
        
        # Validación y construcción de la hoja de Inventario
        if "Inventario" not in hojas_en_nube:
            sh.add_worksheet(title="Inventario", rows="500", cols="6")
            ws = sh.worksheet("Inventario")
            ws.append_row(["ID Producto", "Producto", "Categoría", "Precio Venta", "Stock Actual", "Stock Mínimo"])
            
        # Validación y construcción de la hoja de Movimientos de Caja
        if "Movimientos" not in hojas_en_nube:
            sh.add_worksheet(title="Movimientos", rows="1000", cols="6")
            ws = sh.worksheet("Movimientos")
            ws.append_row(["Fecha", "Tipo", "Concepto", "Monto", "Cliente", "Cantidad"])
            
        # Validación y construcción de la hoja de Clientes
        if "clientes" not in hojas_en_nube:
            sh.add_worksheet(title="clientes", rows="500", cols="5")
            ws = sh.worksheet("clientes")
            ws.append_row(["ID Cliente", "Nombre", "Correo", "Teléfono", "Saldo"])
            
    except Exception as e:
        st.error(f"Error al inicializar las hojas de cálculo: {e}. Asegúrese de que el correo de la cuenta de servicio tenga privilegios de 'Editor' y que las APIs Sheets y Drive estén activas en Google Cloud.")

# Ejecución del aprovisionamiento preventivo de las bases de datos
if URL_DOCUMENTO:
    inicializar_almacen_datos()

def guardar_datos(df, pestana):
    """
    Realiza la persistencia segura de DataFrames de forma explícita,
    especificando el recurso e invalidando la caché temporal de Streamlit.
    """
    try:
        conn.update(worksheet=pestana, data=df, spreadsheet=URL_DOCUMENTO)
        st.cache_data.clear()
        st.success(f"Pestaña '{pestana}' guardada con éxito.")
    except Exception as e:
        st.error(f"Excepción crítica al guardar en la pestaña '{pestana}': {e}. Valide la configuración de privilegios de edición en Google Sheets.")

def forzar_recarga_sistema():
    """Invalida de manera global la caché de lectura y refresca la aplicación."""
    st.cache_data.clear()
    st.rerun()

# Carga selectiva de tablas de datos con mecanismos de TTL para mitigar cuotas de la API
@st.cache_data(ttl=10)
def cargar_inventario():
    try:
        df = conn.read(worksheet="Inventario", spreadsheet=URL_DOCUMENTO, ttl="10s")
        if df.empty:
            return pd.DataFrame(columns=["ID Producto", "Producto", "Categoría", "Precio Venta", "Stock Actual", "Stock Mínimo"])
        # Formateo estricto de tipos de datos para prevenir inconsistencias algebraicas
        df["Precio Venta"] = pd.to_numeric(df["Precio Venta"], errors="coerce").fillna(0.0)
        df["Stock Actual"] = pd.to_numeric(df["Stock Actual"], errors="coerce").fillna(0).astype(int)
        df["Stock Mínimo"] = pd.to_numeric(df["Stock Mínimo"], errors="coerce").fillna(0).astype(int)
        df["ID Producto"] = df["ID Producto"].astype(str)
        return df
    except Exception:
        return pd.DataFrame(columns=["ID Producto", "Producto", "Categoría", "Precio Venta", "Stock Actual", "Stock Mínimo"])

@st.cache_data(ttl=10)
def cargar_movimientos():
    try:
        df = conn.read(worksheet="Movimientos", spreadsheet=URL_DOCUMENTO, ttl="10s")
        if df.empty:
            return pd.DataFrame(columns=["Fecha", "Tipo", "Concepto", "Monto", "Cliente", "Cantidad"])
        df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce").fillna(0.0)
        df["Cantidad"] = pd.to_numeric(df["Cantidad"], errors="coerce").fillna(0).astype(int)
        return df
    except Exception:
        return pd.DataFrame(columns=["Fecha", "Tipo", "Concepto", "Monto", "Cliente", "Cantidad"])

@st.cache_data(ttl=10)
def cargar_clientes():
    try:
        df = conn.read(worksheet="clientes", spreadsheet=URL_DOCUMENTO, ttl="10s")
        if df.empty:
            return pd.DataFrame(columns=["ID Cliente", "Nombre", "Correo", "Teléfono", "Saldo"])
        df["Saldo"] = pd.to_numeric(df["Saldo"], errors="coerce").fillna(0.0)
        df["ID Cliente"] = df["ID Cliente"].astype(str)
        return df
    except Exception:
        return pd.DataFrame(columns=["ID Cliente", "Nombre", "Correo", "Teléfono", "Saldo"])

# Asignación de variables de estado de datos
df_inventario = cargar_inventario()
df_movimientos = cargar_movimientos()
df_clientes = cargar_clientes()

# Panel de navegación y control lateral
st.sidebar.title("Sistema de Gestión Comercial")
st.sidebar.markdown("---")
modulo_activo = st.sidebar.radio(
    "Seleccione el módulo que desea operar:",
    ["Dashboard Comercial", "Punto de Venta", "Gestión de Inventario (Stock)", "Gestión de Clientes", "Control de Caja"]
)

# Cálculo dinámico de indicadores clave para la barra lateral (CORREGIDO)
ingresos_totales = df_movimientos[df_movimientos["Tipo"] == "INGRESO"]["Monto"].sum() if not df_movimientos.empty else 0.0
egresos_totales = df_movimientos[df_movimientos["Tipo"] == "EGRESO"]["Monto"].sum() if not df_movimientos.empty else 0.0
saldo_caja_vigente = ingresos_totales - egresos_totales
valor_activo_stock = (df_inventario["Stock Actual"] * df_inventario["Precio Venta"]).sum() if not df_inventario.empty else 0.0

st.sidebar.markdown("---")
st.sidebar.subheader("Indicadores de Desempeño")
st.sidebar.metric("Saldo Financiero en Caja", f"${saldo_caja_vigente:,.2f}")
st.sidebar.metric("Valor Neto de Existencias", f"${valor_activo_stock:,.2f}")

if not URL_DOCUMENTO:
    st.error("No se ha configurado la URL de Google Sheets en el archivo de secretos. Configure el sistema antes de proceder.")
    st.stop()

# ==============================================================================
# MÓDULO: DASHBOARD COMERCIAL
# ==============================================================================
if modulo_activo == "Dashboard Comercial":
    st.title("Panel de Control Comercial y Financiero")
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.metric("Total de Ventas / Ingresos", f"${ingresos_totales:,.2f}")
    with col_kpi2:
        st.metric("Total de Gastos / Egresos", f"${egresos_totales:,.2f}")
    with col_kpi3:
        st.metric("Rentabilidad de Caja", f"${saldo_caja_vigente:,.2f}", delta=f"{((saldo_caja_vigente/ingresos_totales)*100) if ingresos_totales > 0 else 0:.1f}% de Margen")
    with col_kpi4:
        alertas_criticas = df_inventario[df_inventario["Stock Actual"] <= df_inventario["Stock Mínimo"]].shape[0] if not df_inventario.empty else 0
        st.metric("Alertas de Stock Crítico", alertas_criticas, delta=-alertas_criticas if alertas_criticas > 0 else 0, delta_color="inverse")

    st.markdown("---")
    
    col_analisis_1, col_analisis_2 = st.columns(2)
    with col_analisis_1:
        st.subheader("Evolución del Flujo de Efectivo")
        if not df_movimientos.empty:
            df_grafico = df_movimientos.copy()
            df_grafico["Fecha_Visualizacion"] = pd.to_datetime(df_grafico["Fecha"]).dt.date
            df_agrupado = df_grafico.groupby(["Fecha_Visualizacion", "Tipo"])["Monto"].sum().unstack(fill_value=0.0)
            st.area_chart(df_agrupado)
        else:
            st.info("No se registran suficientes transacciones históricas para generar proyecciones.")
            
    with col_analisis_2:
        st.subheader("Estado de Existencias Frente a Stock de Seguridad")
        if not df_inventario.empty:
            df_inventario_alertas = df_inventario.copy()
            st.bar_chart(df_inventario_alertas.set_index("Producto")[["Stock Actual", "Stock Mínimo"]])
        else:
            st.info("El catálogo de existencias está vacío. Ingrese productos para habilitar el gráfico.")

# ==============================================================================
# MÓDULO: PUNTO DE VENTA (VENTAS Y DESCUENTO AUTOMÁTICO DE STOCK)
# ==============================================================================
elif modulo_activo == "Punto de Venta":
    st.title("Módulo de Facturación y Ventas Directas")
    
    if df_inventario.empty:
        st.warning("El catálogo de inventario está vacío. Ingrese mercadería para poder facturar.")
    else:
        with st.form("formulario_facturacion"):
            st.subheader("Registrar Nueva Venta")
            
            # Formateo visual de artículos para facilitar la selección de mostrador
            opciones_productos = [
                f"{row['ID Producto']} - {row['Producto']} (Disponible: {row['Stock Actual']} uds | Precio: ${row['Precio Venta']:,.2f})"
                for _, row in df_inventario.iterrows()
            ]
            producto_seleccionado = st.selectbox("Seleccione el Producto a Vender:", opciones_productos)
            
            # Selección de cliente para control de cartera y resolución de la relación de clientes
            opciones_clientes = ["Consumidor Final"]
            if not df_clientes.empty:
                opciones_clientes.extend([
                    f"{row['ID Cliente']} - {row['Nombre']}"
                    for _, row in df_clientes.iterrows()
                ])
            cliente_seleccionado = st.selectbox("Vincular con un Cliente Registrado:", opciones_clientes)
            
            cantidad_facturada = st.number_input("Cantidad a Comercializar (uds):", min_value=1, step=1, value=1)
            comentarios_venta = st.text_input("Comentarios de Facturación:", "Venta directa realizada con éxito.")
            
            confirmar_venta = st.form_submit_button("Emitir Comprobante de Venta")
            
            if confirmar_venta:
                # Recuperar clave de identificación del producto seleccionado
                id_producto_filtrado = producto_seleccionado.split(" - ")[0]
                datos_producto = df_inventario[df_inventario["ID Producto"] == id_producto_filtrado].iloc[0]
                stock_disponible = datos_producto["Stock Actual"]
                precio_unitario = datos_producto["Precio Venta"]
                nombre_articulo = datos_producto["Producto"]
                
                # Validación estricta del stock de seguridad antes de procesar transacciones
                if cantidad_facturada > stock_disponible:
                    st.error(f"Fuga de existencias evitada: La cantidad que desea comercializar ({cantidad_facturada} uds) supera el inventario físico disponible ({stock_disponible} uds).")
                else:
                    monto_total_transaccion = float(precio_unitario * cantidad_facturada)
                    marca_temporal = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    try:
                        sh = conn.client._open_spreadsheet(spreadsheet=URL_DOCUMENTO)
                        ws_movimientos = sh.worksheet("Movimientos")
                        
                        # Determinación del destinatario de la transacción comercial
                        destinatario_cliente = "Consumidor Final"
                        if cliente_seleccionado != "Consumidor Final":
                            destinatario_cliente = cliente_seleccionado.split(" - ")[1]
                        
                        # 1. Registro financiero en el Libro de Caja
                        ws_movimientos.append_row([
                            marca_temporal, "INGRESO", f"Venta: {nombre_articulo} x{cantidad_facturada} - {comentarios_venta}",
                            monto_total_transaccion, destinatario_cliente, cantidad_facturada
                        ])
                        
                        # 2. Descuento del Stock en la Hoja de Inventario
                        df_inventario_temporal = df_inventario.copy()
                        fila_indice_producto = df_inventario_temporal[df_inventario_temporal["ID Producto"] == id_producto_filtrado].index
                        df_inventario_temporal.at[fila_indice_producto[0], "Stock Actual"] = int(stock_disponible - cantidad_facturada)
                        
                        # Actualización de la hoja de inventario físico
                        guardar_datos(df_inventario_temporal, "Inventario")
                        
                        # Refresco de datos automático
                        forzar_recarga_sistema()
                        
                    except Exception as ex:
                        st.error(f"Error inesperado al persistir la transacción: {ex}")

# ==============================================================================
# MÓDULO: GESTIÓN DE INVENTARIO (CONTROL DE STOCK)
# ==============================================================================
elif modulo_activo == "Gestión de Inventario (Stock)":
    st.title("Módulo de Administración de Almacén e Inventarios")
    
    pestana_catalogo, pestana_alta_articulo = st.tabs(["Catálogo de Productos", "Alta de Producto"])
    
    with pestana_catalogo:
        st.subheader("Catálogo Vigente de Productos")
        st.write("Edite directamente sobre las celdas de la tabla interactiva y haga clic en 'Guardar Cambios de Stock' para actualizar la base de datos.")
        
        # Uso de data_editor para la edición interactiva de existencias físicas en lote
        catalogo_inventario_editado = st.data_editor(
            df_inventario,
            num_rows="dynamic",
            use_container_width=True,
            key="inventario_editor_interactivo"
        )
        
        guardar_cambios_inventario = st.button("Guardar Cambios de Stock")
        if guardar_cambios_inventario:
            try:
                # Sanitización de tipos de datos antes del volcado a Google Sheets
                catalogo_inventario_editado["Precio Venta"] = pd.to_numeric(catalogo_inventario_editado["Precio Venta"], errors="coerce").fillna(0.0)
                catalogo_inventario_editado["Stock Actual"] = pd.to_numeric(catalogo_inventario_editado["Stock Actual"], errors="coerce").fillna(0).astype(int)
                catalogo_inventario_editado["Stock Mínimo"] = pd.to_numeric(catalogo_inventario_editado["Stock Mínimo"], errors="coerce").fillna(0).astype(int)
                catalogo_inventario_editado["ID Producto"] = catalogo_inventario_editado["ID Producto"].astype(str)
                
                guardar_datos(catalogo_inventario_editado, "Inventario")
                forzar_recarga_sistema()
            except Exception as ex:
                st.error(f"Fallo al actualizar el catálogo de inventario: {ex}")
                
    with pestana_alta_articulo:
        with st.form("formulario_alta_inventario"):
            st.subheader("Alta de Producto")
            nuevo_id_prod = st.text_input("Código o ID Único de Producto:")
            nuevo_nombre_prod = st.text_input("Nombre Descriptivo del Artículo:")
            nueva_categoria_prod = st.text_input("Categoría de Almacenamiento:", "General")
            nuevo_precio_prod = st.number_input("Precio de Venta Unitario ($):", min_value=0.0, step=0.01)
            nuevo_stock_prod = st.number_input("Inventario Inicial Disponible (uds):", min_value=0, step=1)
            nuevo_minimo_prod = st.number_input("Límite Crítico (Stock Mínimo):", min_value=0, step=1, value=5)
            
            procesar_alta_prod = st.form_submit_button("Agregar Producto al Inventario")
            
            if procesar_alta_prod:
                if nuevo_id_prod in df_inventario.values:
                    st.error("Error de Clave Duplicada: El Código de Producto ingresado ya está registrado.")
                elif not nuevo_id_prod or not nuevo_nombre_prod:
                    st.error("Los campos de Código e ID de producto son obligatorios para el registro.")
                else:
                    try:
                        nueva_fila_articulo = pd.DataFrame([{
                            "ID Producto": nuevo_id_prod,
                            "Producto": nuevo_nombre_prod,
                            "Categoría": nueva_categoria_prod,
                            "Precio Venta": nuevo_precio_prod,
                            "Stock Actual": nuevo_stock_prod,
                            "Stock Mínimo": nuevo_minimo_prod
                        }])
                        
                        df_inventario_consolidado = pd.concat([df_inventario, nueva_fila_articulo], ignore_index=True)
                        guardar_datos(df_inventario_consolidado, "Inventario")
                        forzar_recarga_sistema()
                    except Exception as ex:
                        st.error(f"Error al registrar el producto: {ex}")

# ==============================================================================
# MÓDULO: GESTIÓN DE CLIENTES
# ==============================================================================
elif modulo_activo == "Gestión de Clientes":
    st.title("Módulo de Administración de Clientes y Cuentas por Cobrar")
    
    pestana_lista_clientes, pestana_alta_cliente = st.tabs(["Cartera de Clientes", "Alta de Cliente"])
    
    with pestana_lista_clientes:
        st.subheader("Clientes Registrados en la Cartera")
        st.write("Modifique directamente los campos y haga clic en el botón 'Guardar Cambios de Clientes' para actualizar la base de datos.")
        
        clientes_editados = st.data_editor(
            df_clientes,
            num_rows="dynamic",
            use_container_width=True,
            key="clientes_editor_interactivo"
        )
        
        guardar_cambios_clientes = st.button("Guardar Cambios de Clientes")
        if guardar_cambios_clientes:
            try:
                # Saneamiento de tipos de datos para prevenir inconsistencias relacionales
                clientes_editados["Saldo"] = pd.to_numeric(clientes_editados["Saldo"], errors="coerce").fillna(0.0)
                clientes_editados["ID Cliente"] = clientes_editados["ID Cliente"].astype(str)
                
                # Sincronización mediante la llamada corregida guardar_datos
                guardar_datos(clientes_editados, "clientes")
                forzar_recarga_sistema()
            except Exception as ex:
                st.error(f"Fallo al actualizar la cartera de clientes: {ex}")
                
    with pestana_alta_cliente:
        with st.form("formulario_alta_clientes"):
            st.subheader("Alta de Cliente")
            nuevo_id_cli = st.text_input("ID o RUT Único del Cliente:")
            nuevo_nombre_cli = st.text_input("Nombre Completo o Razón Social:")
            nuevo_correo_cli = st.text_input("Correo Electrónico de Contacto:")
            nuevo_telefono_cli = st.text_input("Teléfono de Contacto:")
            nuevo_saldo_cli = st.number_input("Saldo Inicial o Crédito ($):", min_value=0.0, step=0.01, value=0.0)
            
            procesar_alta_cli = st.form_submit_button("Agregar Cliente a la Cartera")
            
            if procesar_alta_cli:
                if nuevo_id_cli in df_clientes.values:
                    st.error("Error de Clave Duplicada: El ID de Cliente ingresado ya se encuentra registrado.")
                elif not nuevo_id_cli or not nuevo_nombre_cli:
                    st.error("Los campos de ID de Cliente y Nombre son obligatorios para el registro.")
                else:
                    try:
                        nueva_fila_cliente = pd.DataFrame([{
                            "ID Cliente": nuevo_id_cli,
                            "Nombre": nuevo_nombre_cli,
                            "Correo": nuevo_correo_cli,
                            "Teléfono": nuevo_telefono_cli,
                            "Saldo": nuevo_saldo_cli
                        }])
                        
                        df_clientes_consolidado = pd.concat([df_clientes, nueva_fila_cliente], ignore_index=True)
                        guardar_datos(df_clientes_consolidado, "clientes")
                        forzar_recarga_sistema()
                    except Exception as ex:
                        st.error(f"Error al registrar el cliente: {ex}")

# ==============================================================================
# MÓDULO: CONTROL DE CAJA (INGRESO Y EGRESO DIRECTO)
# ==============================================================================
elif modulo_activo == "Control de Caja":
    st.title("Módulo de Auditoría y Control del Libro de Caja")
    
    pestana_libro_diario, pestana_movimiento_manual = st.tabs(["Libro Diario", "Movimiento Manual"])
    
    with pestana_libro_diario:
        st.subheader("Auditoría Histórica de Transacciones")
        
        # Filtros de consulta para facilitar la auditoría contable
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_tipo_caja = st.multiselect("Filtrar por Tipo:", ["INGRESO", "EGRESO"], default=["INGRESO", "EGRESO"])
        with col_f2:
            filtro_concepto_caja = st.text_input("Buscar Concepto o Detalle:")
            
        df_caja_filtrado = df_movimientos.copy()
        if filtro_tipo_caja:
            df_caja_filtrado = df_caja_filtrado[df_caja_filtrado["Tipo"].isin(filtro_tipo_caja)]
        if filtro_concepto_caja:
            df_caja_filtrado = df_caja_filtrado[df_caja_filtrado["Concepto"].str.contains(filtro_concepto_caja, case=False, na=False)]
            
        if not df_caja_filtrado.empty:
            # Ordenar por fecha cronológica inversa de forma segura
            df_caja_filtrado["Fecha"] = pd.to_datetime(df_caja_filtrado["Fecha"])
            df_caja_filtrado = df_caja_filtrado.sort_values(by="Fecha", ascending=False)
            st.dataframe(df_caja_filtrado, use_container_width=True)
        else:
            st.info("No se encontraron transacciones financieras con los criterios de búsqueda especificados.")
            
    with pestana_movimiento_manual:
        with st.form("formulario_movimiento_caja"):
            st.subheader("Registrar Movimiento Manual de Caja")
            tipo_flujo_manual = st.selectbox("Seleccione el Tipo de Movimiento:", ["INGRESO", "EGRESO"])
            detalle_flujo_manual = st.text_input("Concepto (Ej: Pago de Proveedores, Retiro de Caja, Depósito de Sencillo):")
            monto_flujo_manual = st.number_input("Monto de la Operación ($):", min_value=0.01, step=0.01)
            
            procesar_flujo_manual = st.form_submit_button("Confirmar Operación de Caja")
            
            if procesar_flujo_manual:
                if not detalle_flujo_manual:
                    st.error("Debe proporcionar un concepto claro para garantizar la transparencia de la auditoría.")
                else:
                    try:
                        sh = conn.client._open_spreadsheet(spreadsheet=URL_DOCUMENTO)
                        ws_movimientos_manual = sh.worksheet("Movimientos")
                        marca_temporal_manual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Inserción de flujo de efectivo inmutable directa en Google Sheets
                        ws_movimientos_manual.append_row([
                            marca_temporal_manual, tipo_flujo_manual, detalle_flujo_manual, 
                            float(monto_flujo_manual), "Manual", 0
                        ])
                        
                        st.success("Transacción registrada con éxito en el Libro Diario.")
                        forzar_recarga_sistema()
                    except Exception as ex:
                        st.error(f"Fallo al guardar el movimiento financiero manual: {ex}")