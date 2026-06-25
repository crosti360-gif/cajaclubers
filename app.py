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

# ==============================================================================
# SISTEMA DE AUTENTICACIÓN (CONTRASEÑA AL ABRIR)
# ==============================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso Restringido")
    st.markdown("Por favor, ingrese la contraseña para acceder al sistema.")
    
    pwd = st.text_input("Contraseña:", type="password")
    
    if st.button("Ingresar al Sistema"):
        # CAMBIAR "admin123" POR LA CONTRASEÑA QUE DESEES
        if pwd == "admin123":
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta. Intente nuevamente.")
    st.stop() # Detiene la ejecución del resto del código si no está logueado

# ==============================================================================
# INICIALIZACIÓN Y BASE DE DATOS
# ==============================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

URL_DOCUMENTO = "https://docs.google.com/spreadsheets/d/1ubonT7F9SdjH5SnXHIWCLqzsccGQfMgvN_vcsoErupA/edit?gid=0#gid=0"

CODIGO_EDITOR_CAJA = "caja2026"  # Clave requerida para corregir registros

def inicializar_almacen_datos():
    if not URL_DOCUMENTO:
        st.error("Error crítico: No se ha detectado la propiedad 'spreadsheet' en los secretos.")
        return
    try:
        sh = conn.client._open_spreadsheet(spreadsheet=URL_DOCUMENTO)
        hojas_en_nube = [ws.title for ws in sh.worksheets()]
        
        if "Inventario" not in hojas_en_nube:
            sh.add_worksheet(title="Inventario", rows="500", cols="6")
            ws = sh.worksheet("Inventario")
            ws.append_row(["ID Producto", "Producto", "Categoría", "Precio Venta", "Stock Actual", "Stock Mínimo"])
            
        if "Movimientos" not in hojas_en_nube:
            sh.add_worksheet(title="Movimientos", rows="1000", cols="6")
            ws = sh.worksheet("Movimientos")
            ws.append_row(["Fecha", "Tipo", "Concepto", "Monto", "Cliente", "Cantidad"])
            
        if "clientes" not in hojas_en_nube:
            sh.add_worksheet(title="clientes", rows="500", cols="5")
            ws = sh.worksheet("clientes")
            ws.append_row(["ID Cliente", "Nombre", "Correo", "Teléfono", "Saldo"])
            
    except Exception as e:
        st.error(f"Error al inicializar las hojas de cálculo: {e}")

if URL_DOCUMENTO:
    inicializar_almacen_datos()

def guardar_datos(df, pestana):
    try:
        conn.update(worksheet=pestana, data=df, spreadsheet=URL_DOCUMENTO)
        st.cache_data.clear()
        st.success(f"Base de datos '{pestana}' actualizada con éxito.")
    except Exception as e:
        st.error(f"Excepción crítica al guardar en la pestaña '{pestana}': {e}")

def forzar_recarga_sistema():
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=10)
def cargar_inventario():
    try:
        df = conn.read(worksheet="Inventario", spreadsheet=URL_DOCUMENTO, ttl="10s")
        if df.empty:
            return pd.DataFrame(columns=["ID Producto", "Producto", "Categoría", "Precio Venta", "Stock Actual", "Stock Mínimo"])
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

df_inventario = cargar_inventario()
df_movimientos = cargar_movimientos()
df_clientes = cargar_clientes()

st.sidebar.title("Gestión Comercial")
st.sidebar.markdown("---")
modulo_activo = st.sidebar.radio(
    "Seleccione el módulo:",
    ["Dashboard Comercial", "Punto de Venta", "Gestión de Inventario", "Socios y Deudas", "Control de Caja"]
)

ingresos_totales = df_movimientos[df_movimientos["Tipo"] == "INGRESO"]["Monto"].sum() if not df_movimientos.empty else 0.0
egresos_totales = df_movimientos[df_movimientos["Tipo"] == "EGRESO"]["Monto"].sum() if not df_movimientos.empty else 0.0
saldo_caja_vigente = ingresos_totales - egresos_totales
valor_activo_stock = (df_inventario["Stock Actual"] * df_inventario["Precio Venta"]).sum() if not df_inventario.empty else 0.0

st.sidebar.markdown("---")
st.sidebar.subheader("Indicadores")
st.sidebar.metric("Efectivo en Caja", f"${saldo_caja_vigente:,.2f}")
st.sidebar.metric("Valor en Stock", f"${valor_activo_stock:,.2f}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

# ==============================================================================
# MÓDULO: DASHBOARD COMERCIAL
# ==============================================================================
if modulo_activo == "Dashboard Comercial":
    st.title("Panel de Control Comercial y Financiero")
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    with col_kpi1:
        st.metric("Total Ingresos", f"${ingresos_totales:,.2f}")
    with col_kpi2:
        st.metric("Total Egresos", f"${egresos_totales:,.2f}")
    with col_kpi3:
        st.metric("Saldo Real Caja", f"${saldo_caja_vigente:,.2f}")
    with col_kpi4:
        deuda_total_socios = df_clientes["Saldo"].sum() if not df_clientes.empty else 0.0
        st.metric("Deuda a Cobrar (Socios)", f"${deuda_total_socios:,.2f}", delta_color="off")

    st.markdown("---")
    
    col_analisis_1, col_analisis_2 = st.columns(2)
    with col_analisis_1:
        st.subheader("Flujo de Efectivo")
        if not df_movimientos.empty:
            df_grafico = df_movimientos.copy()
            df_grafico["Fecha_Visualizacion"] = pd.to_datetime(df_grafico["Fecha"]).dt.date
            df_agrupado = df_grafico.groupby(["Fecha_Visualizacion", "Tipo"])["Monto"].sum().unstack(fill_value=0.0)
            st.area_chart(df_agrupado)
            
    with col_analisis_2:
        st.subheader("Estado de Existencias")
        if not df_inventario.empty:
            st.bar_chart(df_inventario.set_index("Producto")[["Stock Actual", "Stock Mínimo"]])

# ==============================================================================
# MÓDULO: PUNTO DE VENTA (VENTAS Y DEUDAS)
# ==============================================================================
elif modulo_activo == "Punto de Venta":
    st.title("Punto de Venta y Facturación")
    
    if df_inventario.empty:
        st.warning("El catálogo está vacío. Ingrese productos en Inventario.")
    else:
        with st.form("formulario_facturacion"):
            opciones_productos = [f"{row['ID Producto']} - {row['Producto']} (Stock: {row['Stock Actual']} | ${row['Precio Venta']:,.2f})" for _, row in df_inventario.iterrows()]
            producto_seleccionado = st.selectbox("Seleccione el Producto:", opciones_productos)
            
            opciones_clientes = ["Consumidor Final"]
            if not df_clientes.empty:
                opciones_clientes.extend([f"{row['ID Cliente']} - {row['Nombre']}" for _, row in df_clientes.iterrows()])
            cliente_seleccionado = st.selectbox("Vincular con Socio/Cliente:", opciones_clientes)
            
            cantidad_facturada = st.number_input("Cantidad:", min_value=1, step=1, value=1)
            
            # Cálculo de totales
            id_producto_filtrado = producto_seleccionado.split(" - ")[0]
            datos_producto = df_inventario[df_inventario["ID Producto"] == id_producto_filtrado].iloc[0]
            precio_unitario = datos_producto["Precio Venta"]
            monto_total = float(precio_unitario * cantidad_facturada)
            
            st.markdown(f"### **Total a Pagar: ${monto_total:,.2f}**")
            
            # INPUT DE MONTO ABONADO PARA GENERAR RESTO/DEUDA
            monto_abonado = st.number_input("Monto Abonado (Deje el total si paga todo completo):", min_value=0.0, step=0.01, value=monto_total)
            comentarios_venta = st.text_input("Comentarios:", "Venta directa")
            
            confirmar_venta = st.form_submit_button("Confirmar Venta")
            
            if confirmar_venta:
                stock_disponible = datos_producto["Stock Actual"]
                
                if cantidad_facturada > stock_disponible:
                    st.error(f"Stock insuficiente. Disponible: {stock_disponible} uds.")
                elif monto_abonado < monto_total and cliente_seleccionado == "Consumidor Final":
                    st.error("Para dejar saldo pendiente (deuda), debe seleccionar un Socio/Cliente registrado, no Consumidor Final.")
                else:
                    marca_temporal = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    deuda_generada = monto_total - monto_abonado
                    
                    try:
                        sh = conn.client._open_spreadsheet(spreadsheet=URL_DOCUMENTO)
                        ws_movimientos = sh.worksheet("Movimientos")
                        
                        destinatario = cliente_seleccionado.split(" - ")[1] if cliente_seleccionado != "Consumidor Final" else "Consumidor Final"
                        
                        # 1. Movimiento de caja SOLO por lo abonado
                        concepto_mov = f"Venta: {datos_producto['Producto']} x{cantidad_facturada} (Total: ${monto_total})"
                        ws_movimientos.append_row([marca_temporal, "INGRESO", concepto_mov, monto_abonado, destinatario, cantidad_facturada])
                        
                        # 2. Descuento de Stock
                        df_inventario_temp = df_inventario.copy()
                        idx_prod = df_inventario_temp[df_inventario_temp["ID Producto"] == id_producto_filtrado].index
                        df_inventario_temp.at[idx_prod[0], "Stock Actual"] = int(stock_disponible - cantidad_facturada)
                        guardar_datos(df_inventario_temp, "Inventario")
                        
                        # 3. Sumar deuda a la planilla del socio si hay resto
                        if deuda_generada > 0:
                            id_cliente = cliente_seleccionado.split(" - ")[0]
                            df_clientes_temp = df_clientes.copy()
                            idx_cli = df_clientes_temp[df_clientes_temp["ID Cliente"] == id_cliente].index
                            saldo_actual = float(df_clientes_temp.at[idx_cli[0], "Saldo"])
                            df_clientes_temp.at[idx_cli[0], "Saldo"] = saldo_actual + deuda_generada
                            guardar_datos(df_clientes_temp, "clientes")
                            st.warning(f"Se generó una deuda de ${deuda_generada:,.2f} en la cuenta de {destinatario}.")
                        
                        forzar_recarga_sistema()
                    except Exception as ex:
                        st.error(f"Error al procesar: {ex}")

# ==============================================================================
# MÓDULO: GESTIÓN DE INVENTARIO
# ==============================================================================
elif modulo_activo == "Gestión de Inventario":
    st.title("Administración de Almacén")
    pestana_catalogo, pestana_alta = st.tabs(["Catálogo Editable", "Alta de Producto"])
    
    with pestana_catalogo:
        st.write("Edite directamente las celdas y guarde los cambios.")
        catalogo_editado = st.data_editor(df_inventario, num_rows="dynamic", use_container_width=True)
        if st.button("Guardar Cambios de Stock"):
            catalogo_editado["Precio Venta"] = pd.to_numeric(catalogo_editado["Precio Venta"], errors="coerce").fillna(0.0)
            catalogo_editado["Stock Actual"] = pd.to_numeric(catalogo_editado["Stock Actual"], errors="coerce").fillna(0).astype(int)
            catalogo_editado["Stock Mínimo"] = pd.to_numeric(catalogo_editado["Stock Mínimo"], errors="coerce").fillna(0).astype(int)
            catalogo_editado["ID Producto"] = catalogo_editado["ID Producto"].astype(str)
            guardar_datos(catalogo_editado, "Inventario")
            forzar_recarga_sistema()
                
    with pestana_alta:
        with st.form("form_alta_inv"):
            id_prod = st.text_input("Código de Producto:")
            nombre_prod = st.text_input("Nombre:")
            cat_prod = st.text_input("Categoría:", "General")
            precio_prod = st.number_input("Precio Venta ($):", min_value=0.0, step=0.01)
            stock_prod = st.number_input("Stock Inicial:", min_value=0, step=1)
            min_prod = st.number_input("Stock Mínimo:", min_value=0, step=1, value=5)
            
            if st.form_submit_button("Agregar Producto"):
                if id_prod in df_inventario["ID Producto"].values:
                    st.error("El Código ya existe.")
                elif not id_prod or not nombre_prod:
                    st.error("Código y Nombre son obligatorios.")
                else:
                    nueva_fila = pd.DataFrame([{"ID Producto": id_prod, "Producto": nombre_prod, "Categoría": cat_prod, "Precio Venta": precio_prod, "Stock Actual": stock_prod, "Stock Mínimo": min_prod}])
                    guardar_datos(pd.concat([df_inventario, nueva_fila], ignore_index=True), "Inventario")
                    forzar_recarga_sistema()

# ==============================================================================
# MÓDULO: SOCIOS Y DEUDAS
# ==============================================================================
elif modulo_activo == "Socios y Deudas":
    st.title("Gestión de Socios y Cobro de Deudas")
    
    tab_socios, tab_alta, tab_cobros = st.tabs(["Cartera Editable", "Alta de Socio", "Cobrar Deuda"])
    
    with tab_socios:
        st.write("Edite los datos de los socios directamente en la tabla.")
        clientes_editados = st.data_editor(df_clientes, num_rows="dynamic", use_container_width=True)
        if st.button("Guardar Cambios de Socios"):
            clientes_editados["Saldo"] = pd.to_numeric(clientes_editados["Saldo"], errors="coerce").fillna(0.0)
            clientes_editados["ID Cliente"] = clientes_editados["ID Cliente"].astype(str)
            guardar_datos(clientes_editados, "clientes")
            forzar_recarga_sistema()
                
    with tab_alta:
        with st.form("form_alta_cli"):
            id_cli = st.text_input("ID/RUT Socio:")
            nom_cli = st.text_input("Nombre Completo:")
            cor_cli = st.text_input("Correo:")
            tel_cli = st.text_input("Teléfono:")
            sal_cli = st.number_input("Deuda Inicial ($):", min_value=0.0, step=0.01, value=0.0)
            
            if st.form_submit_button("Agregar Socio"):
                if id_cli in df_clientes["ID Cliente"].values:
                    st.error("El ID ya está registrado.")
                elif not id_cli or not nom_cli:
                    st.error("ID y Nombre son obligatorios.")
                else:
                    nueva_fila = pd.DataFrame([{"ID Cliente": id_cli, "Nombre": nom_cli, "Correo": cor_cli, "Teléfono": tel_cli, "Saldo": sal_cli}])
                    guardar_datos(pd.concat([df_clientes, nueva_fila], ignore_index=True), "clientes")
                    forzar_recarga_sistema()
                    
    with tab_cobros:
        st.subheader("Registrar Pago de Deuda")
        socios_con_deuda = df_clientes[df_clientes["Saldo"] > 0]
        if socios_con_deuda.empty:
            st.success("No hay socios con deudas pendientes en este momento.")
        else:
            with st.form("form_cobro"):
                opciones_deudores = [f"{r['ID Cliente']} - {r['Nombre']} (Deuda: ${r['Saldo']:,.2f})" for _, r in socios_con_deuda.iterrows()]
                socio_cobro = st.selectbox("Seleccione el Socio que abonará:", opciones_deudores)
                monto_pagar = st.number_input("Monto a Abonar ($):", min_value=0.01, step=0.01)
                
                if st.form_submit_button("Procesar Pago"):
                    id_socio = socio_cobro.split(" - ")[0]
                    nombre_socio = socio_cobro.split(" - ")[1].split(" (")[0]
                    
                    idx = df_clientes[df_clientes["ID Cliente"] == id_socio].index
                    deuda_actual = float(df_clientes.at[idx[0], "Saldo"])
                    
                    if monto_pagar > deuda_actual:
                        st.error(f"El monto a pagar (${monto_pagar}) no puede ser mayor que la deuda actual (${deuda_actual}).")
                    else:
                        try:
                            # 1. Registrar el ingreso en la caja
                            sh = conn.client._open_spreadsheet(spreadsheet=URL_DOCUMENTO)
                            ws_movimientos = sh.worksheet("Movimientos")
                            marca_t = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ws_movimientos.append_row([marca_t, "INGRESO", f"Cobro de Deuda Pendiente", monto_pagar, nombre_socio, 0])
                            
                            # 2. Restar la deuda en la planilla
                            df_clientes_actualizado = df_clientes.copy()
                            df_clientes_actualizado.at[idx[0], "Saldo"] = deuda_actual - monto_pagar
                            guardar_datos(df_clientes_actualizado, "clientes")
                            
                            forzar_recarga_sistema()
                        except Exception as e:
                            st.error(f"Error procesando cobro: {e}")

# ==============================================================================
# MÓDULO: CONTROL DE CAJA Y CIERRES
# ==============================================================================
elif modulo_activo == "Control de Caja":
    st.title("Auditoría, Libro de Caja y Cierres")
    
    tab_diario, tab_manual, tab_cierres = st.tabs(["Libro Diario", "Movimiento Manual", "Cierres de Caja"])
    
    with tab_diario:
        f1, f2 = st.columns(2)
        tipo = f1.multiselect("Filtrar Tipo:", ["INGRESO", "EGRESO"], default=["INGRESO", "EGRESO"])
        concepto = f2.text_input("Buscar Concepto:")
            
        df_filt = df_movimientos.copy()
        if tipo:
            df_filt = df_filt[df_filt["Tipo"].isin(tipo)]
        if concepto:
            df_filt = df_filt[df_filt["Concepto"].str.contains(concepto, case=False, na=False)]
            
        if not df_filt.empty:
            df_filt["Fecha"] = pd.to_datetime(df_filt["Fecha"])
            st.dataframe(df_filt.sort_values(by="Fecha", ascending=False), use_container_width=True)
            
        # -------------------------------------------------------------
        # HERRAMIENTA: EDITOR DE CAJA CON CÓDIGO DE ACCESO
        # -------------------------------------------------------------
        st.write("---")
        with st.expander("🛠️ Corrector de Movimientos por Errores de Tipeo"):
            st.write("Utiliza esta sección para modificar los montos o conceptos mal ingresados del Libro Diario.")
            
            codigo_ingresado = st.text_input("Ingrese el código de seguridad para habilitar la edición:", type="password", key="codigo_seg_caja")
            
            if codigo_ingresado == CODIGO_EDITOR_CAJA:
                st.success("🔓 Acceso Concedido")
                
                if df_movimientos.empty:
                    st.info("No hay registros en el Libro Diario para editar.")
                else:
                    # Mostrar selector basado en el índice de la tabla de movimientos
                    opciones_filas = [f"Índice {idx} | {row['Fecha']} | {row['Tipo']} | {row['Concepto']} | ${row['Monto']}" for idx, row in df_movimientos.iterrows()]
                    fila_seleccionada = st.selectbox("Seleccione exactamente el registro que desea corregir:", opciones_filas)
                    
                    # Extraer el índice original numérico
                    idx_original = int(fila_seleccionada.split(" ")[1])
                    datos_fila = df_movimientos.iloc[idx_original]
                    
                    with st.form("formulario_edicion_caja"):
                        st.markdown(f"**Modificando el registro de índice:** {idx_original}")
                        nuevo_concepto_mov = st.text_input("Concepto / Descripción:", value=str(datos_fila["Concepto"]))
                        nuevo_monto_mov = st.number_input("Monto ($):", value=float(datos_fila["Monto"]), min_value=0.0, step=0.01)
                        
                        btn_aplicar_cambio = st.form_submit_button("Guardar Corrección")
                        if btn_aplicar_cambio:
                            df_movimientos_copia = df_movimientos.copy()
                            df_movimientos_copia.at[idx_original, "Concepto"] = nuevo_concepto_mov
                            df_movimientos_copia.at[idx_original, "Monto"] = nuevo_monto_mov
                            
                            # Volver a guardar los tipos correctos antes de empujar a Google Sheets
                            df_movimientos_copia["Monto"] = pd.to_numeric(df_movimientos_copia["Monto"], errors="coerce").fillna(0.0)
                            df_movimientos_copia["Cantidad"] = pd.to_numeric(df_movimientos_copia["Cantidad"], errors="coerce").fillna(0).astype(int)
                            
                            guardar_datos(df_movimientos_copia, "Movimientos")
                            forzar_recarga_sistema()
            elif codigo_ingresado != "":
                st.error("❌ Código de seguridad inválido.")
            
    with tab_manual:
        with st.form("form_caja"):
            t_mov = st.selectbox("Tipo:", ["INGRESO", "EGRESO"])
            det_mov = st.text_input("Concepto:")
            monto_mov = st.number_input("Monto ($):", min_value=0.01, step=0.01)
            
            if st.form_submit_button("Confirmar Operación"):
                if not det_mov:
                    st.error("Proporcione un concepto válido.")
                else:
                    try:
                        sh = conn.client._open_spreadsheet(spreadsheet=URL_DOCUMENTO)
                        ws = sh.worksheet("Movimientos")
                        mt = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ws.append_row([mt, t_mov, det_mov, float(monto_mov), "Manual", 0])
                        st.success("Operación registrada.")
                        forzar_recarga_sistema()
                    except Exception as ex:
                        st.error(f"Fallo al guardar: {ex}")
                        
    with tab_cierres:
        st.subheader("Cierres de Caja Automatizados")
        
        if not df_movimientos.empty:
            df_movimientos["Fecha_dt"] = pd.to_datetime(df_movimientos["Fecha"])
            hoy = datetime.datetime.now().date()
            
            # Datos Hoy
            df_hoy = df_movimientos[df_movimientos["Fecha_dt"].dt.date == hoy]
            ing_hoy = df_hoy[df_hoy["Tipo"] == "INGRESO"]["Monto"].sum()
            egr_hoy = df_hoy[df_hoy["Tipo"] == "EGRESO"]["Monto"].sum()
            
            # Datos Semana (Lunes a Domingo actual)
            inicio_semana = hoy - datetime.timedelta(days=hoy.weekday())
            df_sem = df_movimientos[df_movimientos["Fecha_dt"].dt.date >= inicio_semana]
            ing_sem = df_sem[df_sem["Tipo"] == "INGRESO"]["Monto"].sum()
            egr_sem = df_sem[df_sem["Tipo"] == "EGRESO"]["Monto"].sum()
            
            # Datos Año
            df_ano = df_movimientos[df_movimientos["Fecha_dt"].dt.year == hoy.year]
            ing_ano = df_ano[df_ano["Tipo"] == "INGRESO"]["Monto"].sum()
            egr_ano = df_ano[df_ano["Tipo"] == "EGRESO"]["Monto"].sum()
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.info(f"### Cierre Diario\n**Fecha:** {hoy.strftime('%d/%m/%Y')}")
                st.write(f"🟢 **Ingresos:** ${ing_hoy:,.2f}")
                st.write(f"🔴 **Egresos:** ${egr_hoy:,.2f}")
                st.markdown(f"#### Saldo: ${(ing_hoy - egr_hoy):,.2f}")
                
            with c2:
                st.success(f"### Cierre Semanal\n**Desde:** {inicio_semana.strftime('%d/%m/%Y')}")
                st.write(f"🟢 **Ingresos:** ${ing_sem:,.2f}")
                st.write(f"🔴 **Egresos:** ${egr_sem:,.2f}")
                st.markdown(f"#### Saldo: ${(ing_sem - egr_sem):,.2f}")
                
            with c3:
                st.warning(f"### Cierre Anual\n**Año:** {hoy.year}")
                st.write(f"🟢 **Ingresos:** ${ing_ano:,.2f}")
                st.write(f"🔴 **Egresos:** ${egr_ano:,.2f}")
                st.markdown(f"#### Saldo: ${(ing_ano - egr_ano):,.2f}")
        else:
            st.write("No hay movimientos registrados para calcular los cierres.")