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

    # --- LÓGICA DE REGISTRO DE MÚLTIPLES PRODUCTOS ---
    st.subheader("Registrar nueva venta")

    # Inicializar la lista de productos en la venta si no existe
    if "productos_venta" not in st.session_state:
        st.session_state.productos_venta = []

    # Campos de cabecera de la venta (fuera del formulario de productos)
    fecha = st.date_input("Fecha", key="venta_fecha")
    cliente = st.selectbox("Cliente", st.session_state.clientes["Nombre"].tolist(), key="venta_cliente")

    # Formulario para agregar productos a la lista
    with st.form("form_agregar_producto", clear_on_submit=True):
        st.markdown("### Agregar producto a la venta")

        df_productos = st.session_state.productos.copy()
        df_productos["Etiqueta"] = df_productos.apply(
            lambda row: f"{row['Nombre']} | {row['Clave']} | {row['Marca_Tipo']}", axis=1
        )

        producto_idx = st.selectbox(
            "Producto/Servicio",
            df_productos.index,
            format_func=lambda i: df_productos.loc[i, "Etiqueta"],
            key="venta_producto_sel"
        )

        producto_info_selected = df_productos.loc[[producto_idx]]

        col_existencia = "existencia" if "existencia" in producto_info_selected.columns else "Cantidad"
        existencia_actual = int(producto_info_selected[col_existencia].values[0])

        st.info(f"📦 Existencia actual: *{existencia_actual}* unidades.")

        cantidad = st.number_input("Cantidad", min_value=1, key="cantidad_producto_add")

        # Validar que la cantidad no exceda la existencia
        if cantidad > existencia_actual and existencia_actual >= 0:
            st.warning(f"⚠️ La cantidad solicitada ({cantidad}) excede la existencia actual ({existencia_actual}).")

        precio_from_df = float(producto_info_selected["Precio Unitario"].values[0])
        st.markdown(f"**Precio unitario:** ${precio_from_df:.2f}")

        submitted_add_product = st.form_submit_button("➕ Agregar producto")

        if submitted_add_product:
            # Validaciones antes de agregar a la lista
            if cantidad <= 0:
                st.error("❌ La cantidad debe ser mayor que cero.")
            elif cantidad > existencia_actual and existencia_actual >= 0:
                st.error("❌ No hay suficiente existencia para agregar este producto.")
            else:
                # Agregar el producto a la lista temporal
                producto_dict = {
                    "Clave del Producto": str(producto_info_selected["Clave"].values[0]),
                    "Producto": producto_info_selected["Nombre"].values[0],
                    "Cantidad": cantidad,
                    "Precio Unitario": precio_from_df,
                    "Subtotal": cantidad * precio_from_df
                }
                st.session_state.productos_venta.append(producto_dict)
                st.success(f"✅ Se agregó {cantidad} unidad(es) de '{producto_dict['Producto']}' a la venta.")

    st.divider()

    # Mostrar la lista de productos agregados
    if st.session_state.productos_venta:
        st.markdown("### Productos en la venta")
        df_productos_venta = pd.DataFrame(st.session_state.productos_venta)
        st.dataframe(df_productos_venta, use_container_width=True)

        total_original_venta = df_productos_venta["Subtotal"].sum()
        st.markdown(f"**Total de la venta (sin descuento):** ${total_original_venta:.2f}")
    else:
        st.info("No se han agregado productos a la venta.")
        total_original_venta = 0.0

    # Lógica de pago y registro final
    with st.form("form_finalizar_venta"):
        if not st.session_state.productos_venta:
            st.warning("Debes agregar al menos un producto para registrar la venta.")
            final_sale_submitted = st.form_submit_button("Registrar venta", disabled=True)
        else:
            # --- Campo de descuento ---
            descuento = st.number_input(
                "Descuento ($)",
                min_value=0.0,
                max_value=float(total_original_venta),
                value=0.0,
                step=0.01,
                key="venta_descuento"
            )

            importe_neto = total_original_venta - descuento
            if importe_neto < 0:
                importe_neto = 0.0
            st.markdown(f"**Importe neto (después de descuento):** ${importe_neto:.2f}")

            # --- Lógica de Anticipos Disponibles ---
            cliente_nombre = st.session_state.get("venta_cliente")
            anticipos_cliente_total = st.session_state.transacciones_data[
                (st.session_state.transacciones_data["Categoría"] == "Anticipo Cliente") &
                (st.session_state.transacciones_data["Cliente"] == cliente_nombre) &
                (st.session_state.transacciones_data["Tipo"] == "Ingreso")
                ]["Monto"].sum()

            anticipos_aplicados_total = st.session_state.transacciones_data[
                (st.session_state.transacciones_data["Categoría"] == "Anticipo Aplicado") &
                (st.session_state.transacciones_data["Cliente"] == cliente_nombre) &
                (st.session_state.transacciones_data["Tipo"] == "Egreso")
                ]["Monto"].sum()

            saldo_anticipos = float(anticipos_cliente_total) - float(anticipos_aplicados_total)

            if "input_anticipo_visible" not in st.session_state:
                st.session_state["input_anticipo_visible"] = 0.0

            if saldo_anticipos > 0:
                st.subheader("Gestión de Anticipos")
                st.info(f"✨ **Anticipo disponible para {cliente_nombre}:** ${saldo_anticipos:.2f}")
                user_input_anticipo = st.number_input(
                    f"¿Cuánto anticipo desea aplicar a esta venta?",
                    min_value=0.0,
                    max_value=min(saldo_anticipos, importe_neto),
                    value=st.session_state["input_anticipo_visible"],
                    step=0.01,
                    key="input_anticipo_visible_widget"
                )
                st.session_state["input_anticipo_visible"] = user_input_anticipo
            else:
                st.session_state["input_anticipo_visible"] = 0.0

            aplicar_anticipo = st.session_state["input_anticipo_visible"]
            total_ajustado_ui_display = importe_neto - aplicar_anticipo
            st.markdown(f"**Total de la venta (ajustado por anticipo):** ${total_ajustado_ui_display:.2f}")

            # --- Información de Crédito ---
            cliente_info = st.session_state.clientes[st.session_state.clientes["Nombre"] == cliente].iloc[0]
            limite_credito_raw = cliente_info.get("Límite de crédito", 0.0)
            try:
                limite_credito = float(limite_credito_raw) if pd.notna(limite_credito_raw) else 0.0
            except Exception:
                st.warning("⚠️ El límite de crédito del cliente no es válido. Se asignará 0.")
                limite_credito = 0.0

            pagos = st.session_state.transacciones_data[
                (st.session_state.transacciones_data["Categoría"] == "Cobranza") &
                (st.session_state.transacciones_data["Cliente"] == cliente)
                ]
            pagos_realizados = float(pagos["Monto"].sum()) if not pagos.empty else 0.0

            ventas_cliente = st.session_state.ventas[st.session_state.ventas["Cliente"] == cliente]
            total_credito_otorgado = 0.0
            if "Tipo de venta" in ventas_cliente.columns and "Monto Crédito" in ventas_cliente.columns:
                credito_otorgado_series = ventas_cliente[
                    ventas_cliente["Tipo de venta"].isin(["Crédito", "Mixta"])
                ]["Monto Crédito"]
                total_credito_otorgado = float(
                    credito_otorgado_series.sum()) if not credito_otorgado_series.empty else 0.0

            credito_usado = float(total_credito_otorgado) - float(pagos_realizados)
            credito_disponible = float(limite_credito) - float(credito_usado)

            st.markdown(f"💳 *Crédito autorizado:* ${limite_credito:.2f}")
            st.markdown(f"🔸 *Crédito usado:* ${credito_usado:.2f}")
            st.markdown(f"🟢 *Disponible para crédito:* ${credito_disponible:.2f}")

            monto_contado = st.number_input(
                "💵 Monto pagado al contado",
                min_value=0.0,
                max_value=float(total_ajustado_ui_display),
                step=0.01,
                key="venta_monto_contado_final"
            )
            metodo_pago = st.selectbox("Método de pago (contado)", ["Efectivo", "Transferencia", "Tarjeta"],
                                       key="venta_metodo_pago_final")

            monto_credito = total_ajustado_ui_display - monto_contado
            st.markdown(f"*🧾 Crédito solicitado:* ${monto_credito:.2f}")

            final_sale_submitted = st.form_submit_button("Finalizar y Registrar Venta")

            if final_sale_submitted:
                # --- Recargar datos frescos ---
                st.session_state.ventas = leer_ventas()
                for col in numeric_cols_ventas:
                    if col in st.session_state.ventas.columns:
                        st.session_state.ventas[col] = pd.to_numeric(
                            st.session_state.ventas[col], errors='coerce'
                        ).fillna(0.0)

                st.session_state.transacciones_data = leer_transacciones()
                if "Monto" in st.session_state.transacciones_data.columns:
                    st.session_state.transacciones_data["Monto"] = pd.to_numeric(
                        st.session_state.transacciones_data["Monto"], errors='coerce'
                    ).fillna(0.0)

                st.session_state.productos = leer_productos()

                # --- Inputs del form ---
                submitted_fecha = fecha
                submitted_cliente = cliente
                submitted_monto_contado = monto_contado
                submitted_metodo_pago = metodo_pago

                submitted_total_original = total_original_venta
                submitted_descuento = descuento
                submitted_importe_neto = max(0.0, submitted_total_original - submitted_descuento)
                anticipo_final_aplicado = max(0.0, aplicar_anticipo)
                submitted_total_ajustado = submitted_importe_neto - anticipo_final_aplicado

                monto_credito_f = max(0.0, submitted_total_ajustado - submitted_monto_contado)
                submitted_monto_contado = max(0.0, submitted_monto_contado)

                # --- Recalcular crédito ---
                current_cliente_info = st.session_state.clientes[
                    st.session_state.clientes["Nombre"] == submitted_cliente
                    ].iloc[0]
                current_limite_credito = float(current_cliente_info.get("Límite de crédito", 0.0))

                current_pagos = st.session_state.transacciones_data[
                    (st.session_state.transacciones_data["Categoría"] == "Cobranza") &
                    (st.session_state.transacciones_data["Cliente"] == submitted_cliente)
                    ]
                current_pagos_realizados = current_pagos["Monto"].sum() if not current_pagos.empty else 0.0

                current_ventas_cliente = st.session_state.ventas[
                    st.session_state.ventas["Cliente"] == submitted_cliente
                    ]
                current_total_credito_otorgado = 0.0
                if "Tipo de venta" in current_ventas_cliente.columns and "Monto Crédito" in current_ventas_cliente.columns:
                    series_credito = current_ventas_cliente[
                        current_ventas_cliente["Tipo de venta"].isin(["Crédito", "Mixta"])
                    ]["Monto Crédito"]
                    current_total_credito_otorgado = float(series_credito.sum()) if not series_credito.empty else 0.0

                current_credito_usado = current_total_credito_otorgado - current_pagos_realizados
                current_credito_disponible = current_limite_credito - current_credito_usado

                # --- Validaciones ---
                suma_componentes = submitted_monto_contado + monto_credito_f + anticipo_final_aplicado
                epsilon = 0.01
                diferencia_total = abs(round(suma_componentes, 2) - round(submitted_importe_neto, 2))

                if diferencia_total > epsilon:
                    st.error(f"❌ La suma Contado + Crédito + Anticipo debe igualar el Importe Neto "
                             f"(${submitted_importe_neto:.2f}). Desfase: {diferencia_total:.4f}")
                elif monto_credito_f > current_credito_disponible + epsilon:
                    st.error(f"❌ El crédito solicitado (${monto_credito_f:.2f}) excede el disponible "
                             f"(${current_credito_disponible:.2f}).")
                else:
                    # --- Tipo de venta ---
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

                    # ... (código previo sin cambios)

                    # --- Guardar cada producto de la lista como una venta individual ---
                    total_descuento_aplicado = st.session_state.get("venta_descuento", 0.0)
                    total_monto_contado_final = monto_contado
                    total_monto_credito_f = monto_credito_f
                    total_anticipo_final_aplicado = anticipo_final_aplicado
                    importe_neto_total = submitted_importe_neto

                    # Iterar sobre la lista de productos
                    for i, producto_venta in enumerate(st.session_state.productos_venta):
                        clave_producto = producto_venta["Clave del Producto"]
                        cantidad_vendida = producto_venta["Cantidad"]

                        # Obtener información fresca del producto para evitar errores
                        df_prod_temp = leer_productos()
                        df_prod_temp["Clave"] = df_prod_temp["Clave"].astype(str)
                        current_producto_info = df_prod_temp[df_prod_temp["Clave"] == clave_producto]

                        if current_producto_info.empty:
                            st.error(f"❌ El producto con clave '{clave_producto}' no existe. Venta no registrada.")
                            return

                        col_existencia = "existencia" if "existencia" in current_producto_info.columns else "Cantidad"
                        current_existencia = int(
                            pd.to_numeric(current_producto_info[col_existencia], errors="coerce").fillna(0).iloc[0]
                        )

                        if cantidad_vendida > current_existencia and current_existencia >= 0:
                            st.error(f"❌ No hay suficiente existencia de {producto_venta['Producto']}. "
                                     f"Solo quedan {current_existencia} unidades. Venta no registrada.")
                            return

                        # APLICAR LOS VALORES TOTALES SOLO EN LA PRIMERA FILA
                        if i == 0:
                            venta_dict = {
                                "Fecha": submitted_fecha.isoformat(),
                                "Cliente": submitted_cliente,
                                "Producto": producto_venta["Producto"],
                                "Clave del Producto": clave_producto,
                                "Cantidad": float(cantidad_vendida),
                                "Precio Unitario": float(producto_venta["Precio Unitario"]),
                                "Total": producto_venta["Subtotal"],
                                "Descuento": float(total_descuento_aplicado),  # Aplica descuento en la primera fila
                                "Importe Neto": float(importe_neto_total),  # Aplica el importe neto total
                                "Monto Crédito": total_monto_credito_f,  # Aplica el crédito total
                                "Monto Contado": total_monto_contado_final,  # Aplica el contado total
                                "Anticipo Aplicado": total_anticipo_final_aplicado,  # Aplica el anticipo total
                                "Método de pago": submitted_metodo_pago if total_monto_contado_final > 0 else (
                                    "Crédito" if total_monto_credito_f > 0 else (
                                        "Anticipo" if total_anticipo_final_aplicado > 0 else "N/A"
                                    )
                                ),
                                "Tipo de venta": tipo_venta
                            }
                        else:
                            # Para las filas siguientes, solo guarda la información del producto
                            venta_dict = {
                                "Fecha": submitted_fecha.isoformat(),
                                "Cliente": submitted_cliente,
                                "Producto": producto_venta["Producto"],
                                "Clave del Producto": clave_producto,
                                "Cantidad": float(cantidad_vendida),
                                "Precio Unitario": float(producto_venta["Precio Unitario"]),
                                "Total": producto_venta["Subtotal"],
                                "Descuento": 0.0,
                                "Importe Neto": 0.0,
                                "Monto Crédito": 0.0,
                                "Monto Contado": 0.0,
                                "Anticipo Aplicado": 0.0,
                                "Método de pago": "N/A",
                                "Tipo de venta": "Multi-producto"  # Nuevo tipo para identificar
                            }

                        guardar_venta(venta_dict)

                        # Descontar inventario
                        nueva_cantidad_inventario = current_existencia - cantidad_vendida
                        actualizar_producto_por_clave(clave_producto, {col_existencia: nueva_cantidad_inventario})

                    # --- Transacciones (sin cambios) ---
                    if total_monto_contado_final > 0:
                        guardar_transaccion({
                            "Fecha": submitted_fecha.isoformat(),
                            "Descripción": f"Pago de contado por venta a {submitted_cliente}",
                            "Categoría": "Ventas",
                            "Tipo": "Ingreso",
                            "Monto": total_monto_contado_final,
                            "Cliente": submitted_cliente,
                            "Método de pago": submitted_metodo_pago
                        })

                    if total_anticipo_final_aplicado > 0:
                        guardar_transaccion({
                            "Fecha": submitted_fecha.isoformat(),
                            "Descripción": f"Anticipo aplicado a venta de {submitted_cliente}",
                            "Categoría": "Anticipo Aplicado",
                            "Tipo": "Egreso",
                            "Monto": float(total_anticipo_final_aplicado),
                            "Cliente": submitted_cliente,
                            "Método de pago": "Anticipo"
                        })

                    if total_monto_credito_f > epsilon and total_monto_contado_final <= epsilon and total_anticipo_final_aplicado <= epsilon:
                        guardar_transaccion({
                            "Fecha": submitted_fecha.isoformat(),
                            "Descripción": f"Venta a crédito para {submitted_cliente}",
                            "Categoría": "Ventas a Crédito",
                            "Tipo": "Ingreso",
                            "Monto": total_monto_credito_f,
                            "Cliente": submitted_cliente,
                            "Método de pago": "Crédito"
                        })

                    # --- Refrescar estado y limpiar lista de productos ---
                    st.session_state.ventas = leer_ventas()
                    st.session_state.transacciones_data = leer_transacciones()
                    st.session_state.productos = leer_productos()
                    st.session_state["input_anticipo_visible"] = 0.0
                    st.session_state.productos_venta = []  # Limpiar la lista para la próxima venta

                    st.success("✅ Venta registrada correctamente")
                    st.rerun()

                    # ... (resto del código sin cambios)

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