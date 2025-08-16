import streamlit as st
from io import BytesIO
import pandas as pd
import plotly.express as px
from utils.db import guardar_venta, leer_ventas, leer_transacciones, guardar_transaccion, leer_clientes, leer_productos, \
    actualizar_producto_por_clave


# Helper function to convert DataFrame to Excel
def to_excel(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Ventas')
    writer.close()
    processed_data = output.getvalue()
    return processed_data


def render():
    st.title("💸 Ventas")

    # --- Definir columnas numéricas al principio para asegurar su disponibilidad ---
    numeric_cols_ventas = ["Cantidad", "Precio Unitario", "Total", "Monto Crédito", "Monto Contado",
                           "Anticipo Aplicado"]

    # Validar clientes y productos cargados en sesión
    if "clientes" not in st.session_state or st.session_state.clientes.empty:
        st.session_state.clientes = leer_clientes()
        if st.session_state.clientes.empty:
            st.warning("⚠️ No hay clientes registrados. Agrega alguno en 'Clientes'.")
            st.stop()

    if "productos" not in st.session_state or st.session_state.productos.empty:
        st.session_state.productos = leer_productos()
        if st.session_state.productos.empty:
            st.warning("⚠️ No hay productos registrados. Agrega uno en 'Productos'.")
            st.stop()

    # Cargar ventas y transacciones si no están o recargarlas para asegurar tipos de datos
    # Mantenemos esto fuera del if submitted para que la UI siempre muestre datos frescos
    st.session_state.ventas = leer_ventas()
    for col in numeric_cols_ventas:
        if col in st.session_state.ventas.columns:
            st.session_state.ventas[col] = pd.to_numeric(st.session_state.ventas[col], errors='coerce').fillna(0.0)

    st.session_state.transacciones_data = leer_transacciones()
    if "Monto" in st.session_state.transacciones_data.columns:
        st.session_state.transacciones_data["Monto"] = pd.to_numeric(st.session_state.transacciones_data["Monto"],
                                                                     errors='coerce').fillna(0.0)

    # --- Sincronizar ventas con transacciones ---
    ventas_df = st.session_state.ventas
    transacciones_df = st.session_state.transacciones_data

    ventas_data = ventas_df.to_dict(orient="records")
    transacciones_data = transacciones_df.to_dict(orient="records")

    # Creamos un set clave para buscar rápido: (Fecha, Cliente, Monto)
    transacciones_claves = {
        (t.get("Fecha"), t.get("Cliente"), round(float(t.get("Monto", 0)), 2))
        for t in transacciones_data
    }

    transacciones_creadas = 0
    for venta in ventas_data:
        fecha = venta.get("Fecha")
        cliente = venta.get("Cliente")
        monto_contado = float(venta.get("Monto Contado", 0) or 0)
        monto_credito = float(venta.get("Monto Crédito", 0) or 0)
        anticipo = float(venta.get("Anticipo Aplicado", 0) or 0)

        # Contado
        if monto_contado > 0:
            clave = (fecha, cliente, round(monto_contado, 2))
            if clave not in transacciones_claves:
                guardar_transaccion({
                    "Fecha": fecha,
                    "Descripción": f"Pago de contado por venta a {cliente}",
                    "Categoría": "Ventas",
                    "Tipo": "Ingreso",
                    "Monto": monto_contado,
                    "Cliente": cliente,
                    "Método de pago": venta.get("Método de pago", "Contado")
                })
                transacciones_creadas += 1

        # Anticipo
        if anticipo > 0:
            clave = (fecha, cliente, round(anticipo, 2))
            if clave not in transacciones_claves:
                guardar_transaccion({
                    "Fecha": fecha,
                    "Descripción": f"Anticipo aplicado a venta de {cliente}",
                    "Categoría": "Anticipo Aplicado",
                    "Tipo": "Egreso",
                    "Monto": anticipo,
                    "Cliente": cliente,
                    "Método de pago": "Anticipo"
                })
                transacciones_creadas += 1

        # Crédito
        if monto_credito > 0:
            clave = (fecha, cliente, round(monto_credito, 2))
            if clave not in transacciones_claves:
                guardar_transaccion({
                    "Fecha": fecha,
                    "Descripción": f"Venta a crédito para {cliente}",
                    "Categoría": "Ventas a Crédito",
                    "Tipo": "Ingreso",
                    "Monto": monto_credito,
                    "Cliente": cliente,
                    "Método de pago": "Crédito"
                })
                transacciones_creadas += 1

    if transacciones_creadas > 0:
        st.success(f"🔄 {transacciones_creadas} transacciones faltantes fueron agregadas automáticamente.")
        st.session_state.transacciones_data = leer_transacciones()  # Recargar las transacciones después de la sincronización

    # --- Resto del código de la aplicación de ventas ---
    st.subheader("Registrar nueva venta")

    # --- CAMPOS QUE DEBEN ACTUALIZARSE AL CAMBIAR SU VALOR (FUERA DEL FORM) ---
    fecha = st.date_input("Fecha", key="venta_fecha")
    cliente = st.selectbox("Cliente", st.session_state.clientes["Nombre"].tolist(), key="venta_cliente")


    # --- CAMBIOS AQUÍ para mostrar la existencia con selección extendida ---
    df_productos = st.session_state.productos.copy()

    # Crear columna combinada para mostrar en el selectbox
    df_productos["Etiqueta"] = df_productos.apply(
        lambda row: f"{row['Nombre']} | {row['Clave']} | {row['Marca_Tipo']}", axis=1
    )

    # Mostrar el selectbox con la etiqueta combinada
    producto_seleccionado = st.selectbox(
        "Producto/Servicio",
        df_productos["Etiqueta"].tolist(),
        key="venta_producto"
    )

    # Inicializar valores
    existencia_actual = 0
    producto_info_selected = pd.DataFrame()

    # Buscar el producto original por la etiqueta seleccionada
    if producto_seleccionado and not df_productos.empty:
        producto_info_selected = df_productos[df_productos["Etiqueta"] == producto_seleccionado]
        if not producto_info_selected.empty and "Cantidad" in producto_info_selected.columns:
            existencia_actual = int(producto_info_selected["Cantidad"].values[0])
        st.info(f"📦 Existencia actual: **{existencia_actual}** unidades.")

    # Extraer el nombre real del producto para el formulario
    producto = producto_info_selected["Nombre"].values[0] if not producto_info_selected.empty else ""
    # --- FIN CAMBIOS para mostrar la existencia ---

    cantidad = st.number_input("Cantidad", min_value=1, key="venta_cantidad")

    # Validar que la cantidad no exceda la existencia
    if cantidad > existencia_actual and existencia_actual >= 0:  # Solo si hay existencia definida
        st.warning(f"⚠️ La cantidad solicitada ({cantidad}) excede la existencia actual ({existencia_actual}).")
        # Opcional: Deshabilitar el botón de submit o ajustar la cantidad automáticamente
        # st.session_state.venta_cantidad = existencia_actual # Esto podría forzar la cantidad

    # Calcular precio y total EN TIEMPO REAL (para la UI antes del submit)
    precio = 0.0
    if not producto_info_selected.empty and "Precio Unitario" in producto_info_selected.columns:
        precio_from_df = producto_info_selected["Precio Unitario"].values[0]
        precio = float(precio_from_df) if pd.notna(precio_from_df) else 0.0
    total_ui_display_original = cantidad * precio  # Use a different variable name for clarity

    st.markdown(f"**Precio unitario:** ${precio:.2f}")
    st.markdown(f"**Total de la venta:** ${total_ui_display_original:.2f}")

    # --- Campo de descuento ---
    descuento = st.number_input(
        "Descuento ($)",
        min_value=0.0,
        max_value=float(total_ui_display_original),
        value=0.0,
        step=0.01,
        key="venta_descuento"
    )

    # Calcular importe neto antes de anticipo
    importe_neto = total_ui_display_original - descuento
    if importe_neto < 0:
        importe_neto = 0.0

    st.markdown(f"**Importe neto (después de descuento):** ${importe_neto:.2f}")

    # --- Lógica y UI para Anticipos Disponibles (VISIBLES) ---
    anticipos_cliente_total = st.session_state.transacciones_data[
        (st.session_state.transacciones_data["Categoría"] == "Anticipo Cliente") &
        (st.session_state.transacciones_data["Cliente"] == cliente) &
        (st.session_state.transacciones_data["Tipo"] == "Ingreso")
        ]["Monto"].sum()

    anticipos_aplicados_total = st.session_state.transacciones_data[
        (st.session_state.transacciones_data["Categoría"] == "Anticipo Aplicado") &
        (st.session_state.transacciones_data["Cliente"] == cliente) &
        (st.session_state.transacciones_data["Tipo"] == "Egreso")  # ✅
        ]["Monto"].sum()

    saldo_anticipos = float(anticipos_cliente_total) - float(anticipos_aplicados_total)

    # Initialize or retrieve application amount for this sale
    # This key ensures that the value persists across reruns but can be reset by the user.
    if "input_anticipo_visible" not in st.session_state:
        st.session_state["input_anticipo_visible"] = 0.0

    if saldo_anticipos > 0:
        st.subheader("Gestión de Anticipos")
        st.info(f"✨ **Anticipo disponible para {cliente}:** ${saldo_anticipos:.2f}")

        # Permitir al usuario decidir cuánto anticipo aplicar
        # The default value should be 0 unless it's a specific scenario.
        # We use a helper variable to manage the actual displayed value vs the stored session_state value.
        user_input_anticipo = st.number_input(
            f"¿Cuánto anticipo desea aplicar a esta venta?",
            min_value=0.0,
            max_value=min(saldo_anticipos, total_ui_display_original),
            # Max is the lower of available anticipo or sale total
            value=st.session_state["input_anticipo_visible"],  # Use the value from session state
            step=0.01,
            key="input_anticipo_visible_widget"
            # Use a different key for the widget to not conflict with the session_state key
        )
        # Update the session_state variable when the widget changes
        st.session_state["input_anticipo_visible"] = user_input_anticipo
    else:
        # If no anticipos available, ensure the input_anticipo_visible is reset to 0
        st.session_state["input_anticipo_visible"] = 0.0

    # The actual anticipo amount to be applied for calculations
    aplicar_anticipo = st.session_state["input_anticipo_visible"]

    # Calculate the adjusted total after applying the anticipo (for UI)
    total_ajustado_ui_display = importe_neto - aplicar_anticipo
    st.markdown(f"**Total de la venta (ajustado por anticipo):** ${total_ajustado_ui_display:.2f}")

    # --- INICIO DEL FORMULARIO PRINCIPAL DE VENTA ---
    with st.form("form_ventas"):
        cliente_info = st.session_state.clientes[st.session_state.clientes["Nombre"] == cliente].iloc[0]
        limite_credito_raw = cliente_info.get("Límite de crédito", 0.0)
        try:
            limite_credito = float(limite_credito_raw) if pd.notna(limite_credito_raw) else 0.0
        except Exception:
            st.warning("⚠️ El límite de crédito del cliente no es válido. Se asignará 0.")
            limite_credito = 0.0

        # Filtrar pagos de cobranza para el cliente (para crédito)
        pagos = st.session_state.transacciones_data[  # Usar session_state.transacciones_data
            (st.session_state.transacciones_data["Categoría"] == "Cobranza") & (
                    st.session_state.transacciones_data["Cliente"] == cliente)
            ]
        pagos_realizados = pagos["Monto"].sum() if not pagos.empty else 0.0
        pagos_realizados = float(pagos_realizados)

        ventas_cliente = st.session_state.ventas[st.session_state.ventas["Cliente"] == cliente]

        total_credito_otorgado = 0.0
        if "Tipo de venta" in ventas_cliente.columns and "Monto Crédito" in ventas_cliente.columns:
            credito_otorgado_series = ventas_cliente[
                ventas_cliente["Tipo de venta"].isin(["Crédito", "Mixta"])
            ]["Monto Crédito"]
            total_credito_otorgado = float(credito_otorgado_series.sum()) if not credito_otorgado_series.empty else 0.0

        credito_usado = float(total_credito_otorgado) - float(pagos_realizados)
        credito_disponible = float(limite_credito) - float(credito_usado)

        st.markdown(f"💳 **Crédito autorizado:** ${limite_credito:.2f}")
        st.markdown(f"🔸 **Crédito usado:** ${credito_usado:.2f}")
        st.markdown(f"🟢 **Disponible para crédito:** ${credito_disponible:.2f}")

        # Monto contado y método de pago
        # The max_value must be the total adjusted, not the original total
        monto_contado = st.number_input("💵 Monto pagado al contado", min_value=0.0,
                                        max_value=float(total_ajustado_ui_display),
                                        step=0.01, key="venta_monto_contado_final")
        metodo_pago = st.selectbox("Método de pago (contado)", ["Efectivo", "Transferencia", "Tarjeta"],
                                   key="venta_metodo_pago_final")

        monto_credito = total_ajustado_ui_display - monto_contado  # Calculate based on the adjusted total for UI
        st.markdown(f"**🧾 Crédito solicitado:** ${monto_credito:.2f}")

        submitted = st.form_submit_button("Registrar venta")

        if submitted:
            # --- RECARGAR DATOS FRESCOS JUSTO ANTES DE PROCESAR ---
            st.session_state.ventas = leer_ventas()
            for col in numeric_cols_ventas:
                if col in st.session_state.ventas.columns:
                    st.session_state.ventas[col] = pd.to_numeric(st.session_state.ventas[col], errors='coerce').fillna(
                        0.0)

            st.session_state.transacciones_data = leer_transacciones()
            if "Monto" in st.session_state.transacciones_data.columns:
                st.session_state.transacciones_data["Monto"] = pd.to_numeric(
                    st.session_state.transacciones_data["Monto"],
                    errors='coerce').fillna(0.0)
            st.session_state.productos = leer_productos()  # Recargar productos para existencia y precio

            # --- OBTENER VALORES ACTUALES DE LOS INPUTS DEL FORMULARIO ---
            submitted_fecha = fecha
            submitted_cliente = cliente
            submitted_producto = producto
            submitted_cantidad = cantidad
            submitted_monto_contado = monto_contado
            submitted_metodo_pago = metodo_pago

            # --- RECALCULAR PRECIO Y EXISTENCIA AL MOMENTO DEL SUBMIT CON DATOS FRESCOS ---
            current_producto_info = st.session_state.productos[
                st.session_state.productos["Nombre"] == submitted_producto]

            # Obtiene la 'Clave' del producto seleccionado
            clave_producto = current_producto_info["Clave"].values[0] if not current_producto_info.empty else "N/A"

            current_existencia = 0
            if not current_producto_info.empty and "Cantidad" in current_producto_info.columns:
                current_existencia = int(current_producto_info["Cantidad"].values[0])

            submitted_precio = 0.0
            if not current_producto_info.empty and "Precio Unitario" in current_producto_info.columns:
                submitted_precio = float(current_producto_info["Precio Unitario"].values[0])

            # --- RECALCULAR TOTALES Y COMPONENTES CON LOS VALORES DEL SUBMIT ---
            submitted_total_original = submitted_cantidad * submitted_precio
            submitted_descuento = st.session_state.get("venta_descuento", 0.0)
            submitted_importe_neto = submitted_total_original - submitted_descuento
            if submitted_importe_neto < 0:
                submitted_importe_neto = 0.0

            # This is the crucial part: Use the *explicitly entered* anticipo value
            anticipo_final_aplicado = st.session_state.get("input_anticipo_visible", 0.0)

            submitted_total_ajustado = submitted_importe_neto - anticipo_final_aplicado

            # The monto_credito_f MUST be the difference between the adjusted total and the submitted cash amount
            monto_credito_f = submitted_total_ajustado - submitted_monto_contado

            # Ensure amounts are not negative due to floating point inaccuracies
            monto_credito_f = max(0.0, monto_credito_f)
            submitted_monto_contado = max(0.0, submitted_monto_contado)
            anticipo_final_aplicado = max(0.0, anticipo_final_aplicado)

            # --- RECALCULAR CRÉDITO DISPONIBLE AL MOMENTO DEL SUBMIT CON DATOS FRESCOS ---
            current_cliente_info = \
                st.session_state.clientes[st.session_state.clientes["Nombre"] == submitted_cliente].iloc[0]
            current_limite_credito = float(current_cliente_info.get("Límite de crédito", 0.0))

            current_pagos = st.session_state.transacciones_data[
                (st.session_state.transacciones_data["Categoría"] == "Cobranza") & (
                        st.session_state.transacciones_data["Cliente"] == submitted_cliente)
                ]
            current_pagos_realizados = current_pagos["Monto"].sum() if not current_pagos.empty else 0.0

            current_ventas_cliente = st.session_state.ventas[st.session_state.ventas["Cliente"] == submitted_cliente]
            current_total_credito_otorgado = 0.0
            if "Tipo de venta" in current_ventas_cliente.columns and "Monto Crédito" in current_ventas_cliente.columns:
                current_credito_otorgado_series = current_ventas_cliente[
                    current_ventas_cliente["Tipo de venta"].isin(["Crédito", "Mixta"])
                ]["Monto Crédito"]
                current_total_credito_otorgado = float(
                    current_credito_otorgado_series.sum()) if not current_credito_otorgado_series.empty else 0.0

            current_credito_usado = float(current_total_credito_otorgado) - float(current_pagos_realizados)
            current_credito_disponible = float(current_limite_credito) - float(current_credito_usado)

            # --- DEBUG: Mostrar valores clave al momento del SUBMIT ---
            # st.subheader("DEBUG: Valores al momento del Submit")
            # st.write(f"submitted_fecha: {submitted_fecha}")
            # st.write(f"submitted_cliente: {submitted_cliente}")
            # st.write(f"submitted_producto: {submitted_producto}")
            # st.write(f"submitted_cantidad: {submitted_cantidad}")
            # st.write(f"submitted_precio (recalculado): {submitted_precio}")
            # st.write(f"submitted_total_original (recalculado): {submitted_total_original}")
            # st.write(f"anticipo_final_aplicado (del session_state): {anticipo_final_aplicado}")
            # st.write(f"submitted_total_ajustado (recalculado): {submitted_total_ajustado}")
            # st.write(f"submitted_monto_contado (del form): {submitted_monto_contado}")
            # st.write(f"monto_credito_f (recalculado): {monto_credito_f}")
            # st.write(f"current_existencia: {current_existencia}")
            # st.write(f"current_credito_disponible: {current_credito_disponible}")
            # --- FIN DEBUG ---

            suma_componentes = submitted_monto_contado + monto_credito_f + anticipo_final_aplicado

            # Tolerancia para comparación de punto flotante
            epsilon = 0.01

            # Validar contra el importe neto (total - descuento)
            diferencia_total = abs(round(suma_componentes, 2) - round(submitted_importe_neto, 2))

            # Validaciones finales
            if submitted_cantidad > current_existencia and current_existencia >= 0:
                st.error(
                    f"❌ No hay suficiente existencia de {submitted_producto}. "
                    f"Solo quedan {current_existencia} unidades."
                )
            elif diferencia_total > epsilon:
                st.error(
                    f"❌ La suma Contado + Crédito + Anticipo debe igualar el Importe Neto "
                    f"(${submitted_importe_neto:.2f}). Desfase: {diferencia_total:.4f}"
                )
            elif monto_credito_f > current_credito_disponible + epsilon:
                st.error(
                    f"❌ El crédito solicitado (${monto_credito_f:.2f}) excede el disponible (${current_credito_disponible:.2f})."
                )
            else:
                # Determinar tipo de venta
                if monto_credito_f > 0 and (submitted_monto_contado > 0 or anticipo_final_aplicado > 0):
                    tipo_venta = "Mixta"
                elif monto_credito_f > 0 and submitted_monto_contado == 0 and anticipo_final_aplicado == 0:
                    tipo_venta = "Crédito"
                elif monto_credito_f == 0 and (submitted_monto_contado > 0 or anticipo_final_aplicado > 0):
                    tipo_venta = "Contado"
                elif monto_credito_f == 0 and submitted_monto_contado == 0 and anticipo_final_aplicado == 0 and submitted_total_original == 0:
                    tipo_venta = "Gratuita"
                else:
                    tipo_venta = "Indefinido"


                venta_dict = {
                    "Fecha": submitted_fecha.isoformat(),
                    "Cliente": submitted_cliente,
                    "Producto": submitted_producto,
                    "Clave del Producto": clave_producto,  # <-- Agregamos la clave aquí
                    "Cantidad": float(submitted_cantidad),
                    "Precio Unitario": float(submitted_precio),
                    "Total": submitted_total_original,
                    "Descuento": float(submitted_descuento),
                    "Importe Neto": float(submitted_importe_neto),
                    "Monto Crédito": monto_credito_f,
                    "Monto Contado": submitted_monto_contado,
                    "Anticipo Aplicado": anticipo_final_aplicado,
                    "Método de pago": submitted_metodo_pago if submitted_monto_contado > 0 else (
                        "Crédito" if monto_credito_f > 0 else (
                            "Anticipo" if anticipo_final_aplicado > 0 else "N/A"
                        )
                    ),
                    "Tipo de venta": tipo_venta
                }
                guardar_venta(venta_dict)


                if submitted_monto_contado > 0:
                    guardar_transaccion({
                        "Fecha": submitted_fecha.isoformat(),
                        "Descripción": f"Pago de contado por venta a {submitted_cliente}",
                        "Categoría": "Ventas",
                        "Tipo": "Ingreso",
                        "Monto": submitted_monto_contado,
                        "Cliente": submitted_cliente,
                        "Método de pago": submitted_metodo_pago
                    })

                if anticipo_final_aplicado > 0:
                    guardar_transaccion({
                        "Fecha": submitted_fecha.isoformat(),
                        "Descripción": f"Anticipo aplicado a venta de {submitted_cliente}",
                        "Categoría": "Anticipo Aplicado",
                        "Tipo": "Egreso",  # ✅ Cambio aquí
                        "Monto": float(anticipo_final_aplicado),
                        "Cliente": submitted_cliente,
                        "Método de pago": "Anticipo"
                    })

                epsilon = 0.01

                # 📌 Venta a crédito pura (sin contado ni anticipo)
                if monto_credito_f > epsilon and submitted_monto_contado <= epsilon and anticipo_final_aplicado <= epsilon:
                    guardar_transaccion({
                        "Fecha": submitted_fecha.isoformat(),
                        "Descripción": f"Venta a crédito para {submitted_cliente}",
                        "Categoría": "Ventas a Crédito",
                        "Tipo": "Ingreso",
                        "Monto": monto_credito_f,
                        "Cliente": submitted_cliente,
                        "Método de pago": "Crédito"
                    })

                # --- DESCONTAR CANTIDAD DEL INVENTARIO ---
                producto_clave = st.session_state.productos.loc[
                    st.session_state.productos["Nombre"] == submitted_producto, "Clave"].iloc[0]
                nueva_cantidad_inventario = current_existencia - submitted_cantidad
                actualizar_producto_por_clave(producto_clave, {"Cantidad": nueva_cantidad_inventario})
                # --- FIN DESCUENTO INVENTARIO ---

                # Update session state after successful operation
                st.session_state.ventas = leer_ventas()
                st.session_state.transacciones_data = leer_transacciones()
                st.session_state.productos = leer_productos()

                # Crucial for the next sale: Reset the anticipo input to 0 after a successful sale
                st.session_state["input_anticipo_visible"] = 0.0

                st.success("✅ Venta registrada correctamente")
                st.rerun()

    st.divider()
    st.subheader("📋 Histórico de ventas")

    # --- Date Range Selection for Export ---
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Fecha de inicio", value=pd.to_datetime(
            st.session_state.ventas["Fecha"]).min() if not st.session_state.ventas.empty else None)
    with col2:
        end_date = st.date_input("Fecha de fin", value=pd.to_datetime(
            st.session_state.ventas["Fecha"]).max() if not st.session_state.ventas.empty else None)

    filtered_ventas_df = st.session_state.ventas.copy()

    if not filtered_ventas_df.empty:
        filtered_ventas_df["Fecha"] = pd.to_datetime(filtered_ventas_df["Fecha"])
        if start_date:
            filtered_ventas_df = filtered_ventas_df[filtered_ventas_df["Fecha"] >= pd.to_datetime(start_date)]
        if end_date:
            filtered_ventas_df = filtered_ventas_df[filtered_ventas_df["Fecha"] <= pd.to_datetime(end_date)]

    st.dataframe(filtered_ventas_df, use_container_width=True)

    if not filtered_ventas_df.empty:
        st.download_button(
            label="Descargar histórico de ventas a Excel",
            data=to_excel(filtered_ventas_df),
            file_name="historico_ventas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No hay datos de ventas para el rango de fechas seleccionado o en general.")

    if not st.session_state.ventas.empty:
        st.subheader("📊 Ingresos diarios")
        df_daily = st.session_state.ventas.copy()
        df_daily["Total"] = pd.to_numeric(df_daily["Total"], errors='coerce').fillna(0.0)
        df_daily = df_daily.groupby("Fecha")["Total"].sum().reset_index()
        fig = px.bar(df_daily, x="Fecha", y="Total", title="Ventas por día", template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)