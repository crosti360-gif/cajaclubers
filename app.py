import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="SIEMBRA CAJA - ERP", layout="wide", page_icon="🌱")

# CÓDIGO DE SEGURIDAD PARA EDITAR LA CAJA
CODIGO_ADMIN = "1234"  # Puedes cambiar este código por el que tú quieras

def recargar_app():
    if hasattr(st, 'rerun'):
        st.rerun()
    else:
        st.experimental_rerun()

# --- CONEXIÓN AUTOMÁTICA A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(pestana):
    try:
        return conn.read(worksheet=pestana, ttl="0d")
    except Exception:
        return pd.DataFrame()

def guardar_datos(df, pestana):
    conn.update(worksheet=pestana, data=df)

# --- CARGA DE DATOS DESDE LA NUBE ---
df_clientes = cargar_datos("clientes")
df_productos = cargar_datos("productos")
df_ventas = cargar_datos("ventas")
df_cobranzas = cargar_datos("cobranzas")
df_compras = cargar_datos("compras")
df_retiros = cargar_datos("retiros")

# Asegurar estructuras mínimas por si las pestañas están vacías
if df_clientes.empty:
    df_clientes = pd.DataFrame(columns=["ID", "Cédula", "Nombre", "Teléfono", "Correo", "Dirección", "Fecha de Nacimiento", "Estado", "Saldo"])
if df_productos.empty:
    df_productos = pd.DataFrame(columns=["Código", "Variedad", "Familia", "Stock"])
if df_ventas.empty:
    df_ventas = pd.DataFrame(columns=["Fecha", "Recibo", "Cliente", "Variedad", "Gramos", "Precio/g", "Total", "Condición"])
if df_cobranzas.empty:
    df_cobranzas = pd.DataFrame(columns=["Fecha", "Cliente", "Monto Abonado"])
if df_compras.empty:
    df_compras = pd.DataFrame(columns=["Fecha", "Concepto", "Proveedor", "Monto"])
if df_retiros.empty:
    df_retiros = pd.DataFrame(columns=["Fecha", "Usuario", "Monto"])

# Sanitización estricta de tipos de datos para evitar fallos de cálculo
df_clientes["ID"] = pd.to_numeric(df_clientes["ID"], errors='coerce').fillna(0).astype(int)
df_clientes["Saldo"] = pd.to_numeric(df_clientes["Saldo"], errors='coerce').fillna(0).astype(float)
df_productos["Stock"] = pd.to_numeric(df_productos["Stock"], errors='coerce').fillna(0).astype(float)
df_ventas["Total"] = pd.to_numeric(df_ventas["Total"], errors='coerce').fillna(0).astype(float)
df_cobranzas["Monto Abonado"] = pd.to_numeric(df_cobranzas["Monto Abonado"], errors='coerce').fillna(0).astype(float)
df_compras["Monto"] = pd.to_numeric(df_compras["Monto"], errors='coerce').fillna(0).astype(float)
df_retiros["Monto"] = pd.to_numeric(df_retiros["Monto"], errors='coerce').fillna(0).astype(float)

# --- MENÚ DE NAVEGACIÓN ---
st.sidebar.title("🌱 SIEMBRA CAJA")
st.sidebar.write("Sistema de Gestión Comercial")
menu = st.sidebar.radio("Ir a:", [
    "📊 Dashboard", 
    "👥 Clientes y Cobranzas", 
    "🌿 Inventario y Variedades", 
    "🛍️ Registrar Venta", 
    "💸 Compras y Retiros", 
    "💰 Caja y Finanzas"
])

# ==========================================
# --- MODULO 1: DASHBOARD ---
# ==========================================
if menu == "📊 Dashboard":
    st.title("📊 Panel de Control General")
    st.write("Resumen automatizado en tiempo real sincronizado con Google Sheets.")
    
    total_ventas = df_ventas["Total"].sum()
    deuda_total = df_clientes["Saldo"].sum()
    total_clientes = len(df_clientes[df_clientes["Estado"] == "Activo"])
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Ventas Totales Históricas ($)", f"${total_ventas:,.2f}")
    col2.metric("Deuda Pendiente a Cobrar ($)", f"${deuda_total:,.2f}", delta="- Activa", delta_color="inverse")
    col3.metric("Socios Activos", total_clientes)

# ==========================================
# --- MODULO 2: CLIENTES Y COBRANZAS ---
# ==========================================
elif menu == "👥 Clientes y Cobranzas":
    st.title("👥 Base de Datos y Cobros")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Listado de Socios", "➕ Nuevo Socio", "✏️ Editar Socio", "💳 Cobrar Deuda", "🗑️ Eliminar Socio"])
    
    with tab1:
        st.dataframe(df_clientes, use_container_width=True)
        
    with tab2:
        with st.form("nuevo_cliente"):
            st.subheader("Registrar Nuevo Socio")
            col1, col2 = st.columns(2)
            with col1:
                cedula = st.text_input("Cédula de Identidad")
                nombre = st.text_input("Nombre Completo")
                tel = st.text_input("Teléfono")
            with col2:
                correo = st.text_input("Correo Electrónico")
                direccion = st.text_input("Dirección")
                fecha_nac = st.text_input("Fecha de Nacimiento (DD/MM/AAAA)")
            
            enviar = st.form_submit_button("Guardar Socio")
            if enviar and nombre:
                nuevo_id = int(df_clientes["ID"].max() + 1) if not df_clientes.empty else 1
                nueva_fila = {"ID": nuevo_id, "Cédula": cedula, "Nombre": nombre, "Teléfono": tel, "Correo": correo, "Dirección": direccion, "Fecha de Nacimiento": fecha_nac, "Estado": "Activo", "Saldo": 0.0}
                df_clientes = pd.concat([df_clientes, pd.DataFrame([nueva_fila])], ignore_index=True)
                guardar_datos(df_clientes, "clientes")
                st.success("Socio guardado en la nube con éxito.")
                recargar_app()

    with tab3:
        st.subheader("Modificar Datos de un Socio Existente")
        if not df_clientes.empty:
            opciones_clientes = {row["ID"]: f"{row['Nombre']} (ID: {row['ID']})" for _, row in df_clientes.iterrows()}
            id_a_editar = st.selectbox("Seleccione el Socio a editar", options=list(opciones_clientes.keys()), format_func=lambda x: opciones_clientes[x])
            
            idx_editar = df_clientes.index[df_clientes["ID"] == id_a_editar].tolist()[0]
            datos_actuales = df_clientes.iloc[idx_editar]
            
            with st.form("editar_cliente"):
                colA, colB = st.columns(2)
                with colA:
                    edit_cedula = st.text_input("Cédula de Identidad", value=str(datos_actuales.get("Cédula", "")))
                    edit_nombre = st.text_input("Nombre Completo", value=str(datos_actuales.get("Nombre", "")))
                    edit_tel = st.text_input("Teléfono", value=str(datos_actuales.get("Teléfono", "")))
                    edit_estado = st.selectbox("Estado", ["Activo", "Inactivo"], index=0 if datos_actuales.get("Estado", "Activo") == "Activo" else 1)
                with colB:
                    edit_correo = st.text_input("Correo Electrónico", value=str(datos_actuales.get("Correo", "")))
                    edit_direccion = st.text_input("Dirección", value=str(datos_actuales.get("Dirección", "")))
                    edit_fecha_nac = st.text_input("Fecha de Nacimiento (DD/MM/AAAA)", value=str(datos_actuales.get("Fecha de Nacimiento", "")))
                
                btn_guardar_cambios = st.form_submit_button("Guardar Cambios")
                if btn_guardar_cambios and edit_nombre:
                    viejo_nombre = datos_actuales["Nombre"]
                    df_clientes.at[idx_editar, "Cédula"] = edit_cedula
                    df_clientes.at[idx_editar, "Nombre"] = edit_nombre
                    df_clientes.at[idx_editar, "Teléfono"] = edit_tel
                    df_clientes.at[idx_editar, "Correo"] = edit_correo
                    df_clientes.at[idx_editar, "Dirección"] = edit_direccion
                    df_clientes.at[idx_editar, "Fecha de Nacimiento"] = edit_fecha_nac
                    df_clientes.at[idx_editar, "Estado"] = edit_estado
                    
                    if viejo_nombre != edit_nombre:
                        if not df_ventas.empty:
                            df_ventas.loc[df_ventas["Cliente"] == viejo_nombre, "Cliente"] = edit_nombre
                            guardar_datos(df_ventas, "ventas")
                        if not df_cobranzas.empty:
                            df_cobranzas.loc[df_cobranzas["Cliente"] == viejo_nombre, "Cliente"] = edit_nombre
                            guardar_datos(df_cobranzas, "cobranzas")
                            
                    guardar_datos(df_clientes, "clientes")
                    st.success("Datos actualizados correctamente.")
                    recargar_app()
        else:
            st.info("No hay socios registrados para editar.")

    with tab4:
        st.subheader("Cobrar deuda a cliente")
        deudores = df_clientes[df_clientes["Saldo"] > 0]
        if deudores.empty:
            st.info("No hay clientes con deudas pendientes actualmente.")
        else:
            opciones_deudores = {row["ID"]: f"{row['Nombre']} (Debe: ${row['Saldo']:,.2f})" for _, row in deudores.iterrows()}
            id_cobro = st.selectbox("Seleccionar Socio Deudor", options=list(opciones_deudores.keys()), format_func=lambda x: opciones_deudores[x])
            
            idx_cli = df_clientes.index[df_clientes["ID"] == id_cobro].tolist()[0]
            cliente_cobro = df_clientes.at[idx_cli, "Nombre"]
            deuda_actual = df_clientes.at[idx_cli, "Saldo"]
            
            with st.form("cobrar_deuda"):
                monto_pago = st.number_input("Monto a entregar ($)", min_value=1.0, max_value=float(deuda_actual), step=50.0)
                btn_cobrar = st.form_submit_button("Registrar Cobranza")
                
                if btn_cobrar:
                    nueva_cobranza = {"Fecha": str(datetime.date.today()), "Cliente": cliente_cobro, "Monto Abonado": monto_pago}
                    df_cobranzas = pd.concat([df_cobranzas, pd.DataFrame([nueva_cobranza])], ignore_index=True)
                    guardar_datos(df_cobranzas, "cobranzas")
                    
                    df_clientes.at[idx_cli, "Saldo"] -= monto_pago
                    guardar_datos(df_clientes, "clientes")
                    st.success(f"Cobranza guardada con éxito.")
                    recargar_app()

    with tab5:
        st.subheader("🗑️ Eliminar Socio")
        if not df_clientes.empty:
            opciones_borrar = {row["ID"]: f"{row['Nombre']} (ID: {row['ID']})" for _, row in df_clientes.iterrows()}
            id_a_borrar = st.selectbox("Seleccione el Socio a eliminar", options=list(opciones_borrar.keys()), format_func=lambda x: opciones_borrar[x])
            
            with st.form("eliminar_cliente"):
                btn_eliminar = st.form_submit_button("Eliminar Permanentemente", type="primary")
                if btn_eliminar:
                    df_clientes = df_clientes[df_clientes["ID"] != id_a_borrar].reset_index(drop=True)
                    guardar_datos(df_clientes, "clientes")
                    st.success(f"Socio eliminado.")
                    recargar_app()

# ==========================================
# --- MODULO 3: PRODUCTOS Y STOCK ---
# ==========================================
elif menu == "🌿 Inventario y Variedades":
    st.title("🌿 Gestión de Inventario y Catálogo")
    tab1, tab2 = st.tabs(["Inventario y Ajustes", "Agregar/Quitar Variedades"])
    
    with tab1:
        st.dataframe(df_productos, use_container_width=True)
        st.subheader("🔄 Ingreso / Egreso Manual")
        if not df_productos.empty:
            with st.form("modificar_stock"):
                var_seleccionada = st.selectbox("Seleccionar Variedad", df_productos["Variedad"].tolist())
                tipo_mov = st.radio("Tipo de Movimiento", ["Entrada (+)", "Salida (-)"])
                cantidad = st.number_input("Cantidad (Gramos)", min_value=1.0, step=1.0)
                btn_actualizar = st.form_submit_button("Actualizar Inventario")
                if btn_actualizar:
                    idx = df_productos.index[df_productos['Variedad'] == var_seleccionada].tolist()[0]
                    if "Entrada" in tipo_mov:
                        df_productos.at[idx, "Stock"] += cantidad
                    else:
                        df_productos.at[idx, "Stock"] -= cantidad
                    guardar_datos(df_productos, "productos")
                    st.success("Stock sincronizado en Google Sheets.")
                    recargar_app()

    with tab2:
        colA, colB = st.columns(2)
        with colA:
            with st.form("nueva_variedad"):
                st.subheader("➕ Agregar Variedad")
                nuevo_cod = st.text_input("Código")
                nueva_var = st.text_input("Nombre de la Variedad")
                nueva_fam = st.selectbox("Familia", ["Flores", "Extractos", "Comestibles", "Otros"])
                btn_crear = st.form_submit_button("Agregar")
                if btn_crear and nueva_var:
                    nueva_fila = {"Código": nuevo_cod, "Variedad": nueva_var, "Familia": nueva_fam, "Stock": 0.0}
                    df_productos = pd.concat([df_productos, pd.DataFrame([nueva_fila])], ignore_index=True)
                    guardar_datos(df_productos, "productos")
                    st.success("Variedad agregada de forma permanente.")
                    recargar_app()
        with colB:
            with st.form("eliminar_variedad"):
                st.subheader("🗑️ Eliminar Variedad")
                if not df_productos.empty:
                    var_a_borrar = st.selectbox("Seleccionar para eliminar", df_productos["Variedad"].tolist())
                    btn_borrar = st.form_submit_button("Eliminar Permanentemente")
                    if btn_borrar:
                        df_productos = df_productos[df_productos["Variedad"] != var_a_borrar].reset_index(drop=True)
                        guardar_datos(df_productos, "productos")
                        st.success("Variedad removida.")
                        recargar_app()

# ==========================================
# --- MODULO 4: REGISTRAR VENTA ---
# ==========================================
elif menu == "🛍️ Registrar Venta":
    st.title("🛍️ Nueva Transacción")
    if df_productos.empty or df_clientes.empty:
        st.warning("Debes registrar al menos un cliente y una variedad antes de operar.")
    else:
        socios_activos = df_clientes[df_clientes["Estado"] == "Activo"]
        
        with st.form("formulario_venta"):
            cliente_sel = st.selectbox("Seleccionar Socio", socios_activos["Nombre"].tolist())
            producto_sel = st.selectbox("Seleccionar Variedad", df_productos["Variedad"].tolist())
            gramos = st.number_input("Cantidad (Gramos)", min_value=1.0, step=1.0)
            precio = st.number_input("Precio por Gramo ($)", min_value=1.0, step=10.0)
            condicion = st.radio("Condición de Pago", ["Paga en el momento", "Debe"])
            
            procesar = st.form_submit_button("Procesar Venta 🚀")
            if procesar:
                idx_prod = df_productos.index[df_productos["Variedad"] == producto_sel].tolist()[0]
                stock_actual = df_productos.at[idx_prod, "Stock"]
                
                if gramos > stock_actual:
                    st.error(f"❌ Error: Stock insuficiente. Solo quedan {stock_actual}g disponibles de {producto_sel}.")
                else:
                    total = gramos * precio
                    nro_recibo = f"V-{len(df_ventas) + 1:03d}"
                    nueva_venta = {"Fecha": str(datetime.date.today()), "Recibo": nro_recibo, "Cliente": cliente_sel, "Variedad": producto_sel, "Gramos": gramos, "Precio/g": price, "Total": total, "Condición": condicion}
                    
                    df_ventas = pd.concat([df_ventas, pd.DataFrame([nueva_venta])], ignore_index=True)
                    guardar_datos(df_ventas, "ventas")
                    
                    df_productos.at[idx_prod, "Stock"] -= gramos
                    guardar_datos(df_productos, "productos")
                    
                    if condicion == "Debe":
                        idx_cli = df_clientes.index[df_clientes["Nombre"] == cliente_sel].tolist()[0]
                        df_clientes.at[idx_cli, "Saldo"] += total
                        guardar_datos(df_clientes, "clientes")
                        
                    st.success(f"Venta grabada en la nube. Total: ${total:,.2f}")
                    recargar_app()

# ==========================================
# --- MODULO 5: COMPRAS Y RETIROS ---
# ==========================================
elif menu == "💸 Compras y Retiros":
    st.title("💸 Registro de Salidas de Dinero")
    tab1, tab2 = st.tabs(["🛒 Compras y Gastos", "🏧 Retiros de Dinero"])
    
    with tab1:
        with st.form("registro_compra"):
            st.subheader("Registrar Compra/Gasto Operativo")
            concepto = st.text_input("Concepto")
            proveedor = st.text_input("Proveedor")
            monto_compra = st.number_input("Monto del Gasto ($)", min_value=1.0, step=100.0)
            btn_compra = st.form_submit_button("Registrar Gasto")
            if btn_compra and concepto:
                nueva_compra = {"Fecha": str(datetime.date.today()), "Concepto": concepto, "Proveedor": proveedor, "Monto": monto_compra}
                df_compras = pd.concat([df_compras, pd.DataFrame([nueva_compra])], ignore_index=True)
                guardar_datos(df_compras, "compras")
                st.success("Gasto guardado.")
                recargar_app()
        st.dataframe(df_compras, use_container_width=True)
        
    with tab2:
        st.subheader("📊 Resumen de Retiros por Usuario")
        if not df_retiros.empty:
            resumen_usuarios = df_retiros.groupby("Usuario")["Monto"].sum().reset_index()
            cols_resumen = st.columns(len(resumen_usuarios) if len(resumen_usuarios) > 0 else 1)
            for i, row in resumen_usuarios.iterrows():
                with cols_resumen[i]:
                    st.metric(f"Total {row['Usuario']}", f"${row['Monto']:,.2f}")
        
        with st.form("registro_retiro"):
            st.subheader("Registrar Nuevo Retiro")
            usuario = st.selectbox("Usuario que realiza el retiro", ["Usuario 1", "Usuario 2"])
            monto_retiro = st.number_input("Monto a retirar ($)", min_value=1.0, step=100.0)
            btn_retiro = st.form_submit_button("Registrar Retiro")
            if btn_retiro:
                nuevo_retiro = {"Fecha": str(datetime.date.today()), "Usuario": usuario, "Monto": monto_retiro}
                df_retiros = pd.concat([df_retiros, pd.DataFrame([nuevo_retiro])], ignore_index=True)
                guardar_datos(df_retiros, "retiros")
                st.success("Retiro registrado con éxito.")
                recargar_app()
        st.dataframe(df_retiros, use_container_width=True)

# ==========================================
# --- MODULO 6: CAJA Y FINANZAS ---
# ==========================================
elif menu == "💰 Caja y Finanzas":
    st.title("💰 Flujo de Fondos y Resultados")
    
    ventas_efectivo = df_ventas[df_ventas["Condición"] == "Paga en el momento"]["Total"].sum() if not df_ventas.empty else 0
    cobranzas = df_cobranzas["Monto Abonado"].sum() if not df_cobranzas.empty else 0
    total_ingresos = ventas_efectivo + cobranzas
    
    compras = df_compras["Monto"].sum() if not df_compras.empty else 0
    retiros = df_retiros["Monto"].sum() if not df_retiros.empty else 0
    total_egresos = compras + retiros
    
    caja_neta = total_ingresos - total_egresos
    
    st.markdown("### Estado de Flujo de Caja")
    st.markdown("""
    | Concepto | Monto |
    | :--- | :--- |
    | **(+) Ventas al Contado** |  ${:,.2f} |
    | **(+) Cobro de Deudas (Atrasadas)** |  ${:,.2f} |
    | --- | --- |
    | **TOTAL INGRESOS CAJA** | **${:,.2f}** |
    | | |
    | **(-) Compras y Gastos Operativos** | -${:,.2f} |
    | **(-) Retiros de Socios** | -${:,.2f} |
    | --- | --- |
    | **TOTAL EGRESOS CAJA** | **-${:,.2f}** |
    | | |
    | **(=) SALDO NETO EN CAJA HOY** | **${:,.2f}** |
    """.format(ventas_efectivo, cobranzas, total_ingresos, compras, retiros, total_egresos, caja_neta))
    
    if caja_neta < 0:
        st.error("⚠️ Atención: La caja está en negativo. Hay más salidas registradas que ingresos de efectivo.")

    # -------------------------------------------------------------
    # NUEVA SECCIÓN: EDITOR DE CAJA PROTEGIDO CON CÓDIGO
    # -------------------------------------------------------------
    st.write("---")
    with st.expander("🛠️ Editor de Caja Avanzado (Solo Administrador)"):
        st.write("Utiliza esta herramienta para corregir registros individuales de ventas, cobranzas, compras o retiros que se hayan ingresado incorrectamente.")
        
        codigo_ingresado = st.text_input("Introduce el código de acceso:", type="password")
        
        if codigo_ingresado == CODIGO_ADMIN:
            st.success("🔓 Acceso Concedido")
            
            opcion_editar = st.selectbox("¿Qué deseas corregir?", [
                "Seleccionar...", 
                "Ver/Editar Ventas", 
                "Ver/Editar Cobranzas", 
                "Ver/Editar Compras/Gastos", 
                "Ver/Editar Retiros"
            ])
            
            # --- SUB-EDITOR VENTAS ---
            if opcion_editar == "Ver/Editar Ventas" and not df_ventas.empty:
                st.write("### Listado de Ventas Registradas")
                st.dataframe(df_ventas)
                idx_v = st.number_input("Selecciona el Índice (Nro de fila de la izquierda) a modificar:", min_value=0, max_value=len(df_ventas)-1, step=1)
                
                with st.form("form_edit_venta"):
                    st.write(f"Modificando registro número {idx_v}")
                    nuevo_total = st.number_input("Nuevo Total ($):", value=float(df_ventas.at[idx_v, "Total"]))
                    btn_save_v = st.form_submit_button("Actualizar Registro de Venta")
                    if btn_save_v:
                        df_ventas.at[idx_v, "Total"] = nuevo_total
                        guardar_datos(df_ventas, "ventas")
                        st.success("Cambio aplicado e indexado en la nube.")
                        recargar_app()

            # --- SUB-EDITOR COBRANZAS ---
            elif opcion_editar == "Ver/Editar Cobranzas" and not df_cobranzas.empty:
                st.write("### Listado de Cobranzas")
                st.dataframe(df_cobranzas)
                idx_cob = st.number_input("Selecciona el Índice a modificar:", min_value=0, max_value=len(df_cobranzas)-1, step=1)
                
                with st.form("form_edit_cob"):
                    nuevo_monto_cob = st.number_input("Nuevo Monto Abonado ($):", value=float(df_cobranzas.at[idx_cob, "Monto Abonado"]))
                    btn_save_cob = st.form_submit_button("Actualizar Cobranza")
                    if btn_save_cob:
                        df_cobranzas.at[idx_cob, "Monto Abonado"] = nuevo_monto_cob
                        guardar_datos(df_cobranzas, "cobranzas")
                        st.success("Monto de cobranza actualizado.")
                        recargar_app()

            # --- SUB-EDITOR COMPRAS ---
            elif opcion_editar == "Ver/Editar Compras/Gastos" and not df_compras.empty:
                st.write("### Listado de Compras/Gastos")
                st.dataframe(df_compras)
                idx_com = st.number_input("Selecciona el Índice a modificar:", min_value=0, max_value=len(df_compras)-1, step=1)
                
                with st.form("form_edit_com"):
                    nuevo_monto_com = st.number_input("Nuevo Monto del Gasto ($):", value=float(df_compras.at[idx_com, "Monto"]))
                    btn_save_com = st.form_submit_button("Actualizar Gasto")
                    if btn_save_com:
                        df_compras.at[idx_com, "Monto"] = nuevo_monto_com
                        guardar_datos(df_compras, "compras")
                        st.success("Gasto modificado de forma correcta.")
                        recargar_app()

            # --- SUB-EDITOR RETIROS ---
            elif opcion_editar == "Ver/Editar Retiros" and not df_retiros.empty:
                st.write("### Listado de Retiros")
                st.dataframe(df_retiros)
                idx_ret = st.number_input("Selecciona el Índice a modificar:", min_value=0, max_value=len(df_retiros)-1, step=1)
                
                with st.form("form_edit_ret"):
                    nuevo_monto_ret = st.number_input("Nuevo Monto Retirado ($):", value=float(df_retiros.at[idx_ret, "Monto"]))
                    btn_save_ret = st.form_submit_button("Actualizar Retiro")
                    if btn_save_ret:
                        df_retiros.at[idx_ret, "Monto"] = nuevo_monto_ret
                        guardar_datos(df_retiros, "retiros")
                        st.success("Retiro modificado de manera permanente.")
                        recargar_app()
            
            elif opcion_editar != "Seleccionar...":
                st.info("No hay registros en esta sección para editar.")
                
        elif codigo_ingresado != "":
            st.error("❌ Código incorrecto. Acceso denegado.")