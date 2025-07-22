# modules/cobranza.py

import streamlit as st
import pandas as pd
from utils.db import leer_ventas, guardar_transaccion, leer_transacciones, leer_clientes  # Importar leer_clientes


def render():
    st.title("💰 Módulo de cobranza")

    # Asegurarse de que los DataFrames estén en st.session_state y sean numéricos
    # Refresh transacciones_data and ventas_data on every rerun to ensure latest balances
    st.session_state.ventas_data = leer_ventas()
    st.session_state.transacciones_data = leer_transacciones()
    st.session_state.clientes = leer_clientes()  # Asegurar que clientes también se cargue

    ventas = st.session_state.ventas_data
    transacciones = st.session_state.transacciones_data
    clientes = st.session_state.clientes  # Obtener la referencia a clientes

    # Validar columnas necesarias, incluyendo el nuevo "Monto Crédito"
    columnas_necesarias_ventas = ["Cliente", "Tipo de venta", "Monto Crédito"]
    # Asegurarse de que las columnas existan y sean numéricas, si no, inicializarlas
    for col in ["Monto Crédito", "Monto Contado", "Anticipo Aplicado"]:  # Asegurar que estas también sean numéricas
        if col not in ventas.columns:
            ventas[col] = 0.0
        ventas[col] = pd.to_numeric(ventas[col], errors='coerce').fillna(0.0)

    if all(col in ventas.columns for col in columnas_necesarias_ventas):
        st.write("📦 Resumen de ventas (Crédito y Mixtas):", ventas[ventas["Tipo de venta"].isin(["Crédito", "Mixta"])][
            ["Cliente", "Tipo de venta", "Monto Crédito"]].head())
    else:
        st.warning(
            "⚠️ Las ventas no contienen las columnas necesarias para calcular saldos de crédito. Verifica tu función `leer_ventas`.")

    # ⚙️ Filtrar ventas a crédito o mixtas (solo la porción a crédito)
    ventas["Tipo de venta"] = ventas["Tipo de venta"].astype(str)
    creditos_reales = ventas[
        ventas["Tipo de venta"].isin(["Crédito", "Mixta"])].copy()

    if creditos_reales.empty:
        st.info("No hay ventas a crédito o mixtas registradas.")
        deuda_total = pd.DataFrame(columns=["Cliente", "Monto Crédito"])
    else:
        deuda_total = creditos_reales.groupby("Cliente")["Monto Crédito"].sum().reset_index()

    pagos_cobranza = transacciones[
        transacciones["Categoría"].astype(str) == "Cobranza"
        ] if not transacciones.empty else pd.DataFrame(columns=["Cliente", "Monto", "Categoría"])

    # También necesitamos considerar los anticipos aplicados como "pago" a la deuda para el cálculo del saldo
    anticipos_aplicados_a_cobranza = transacciones[
        transacciones["Categoría"].astype(str) == "Anticipo Aplicado"
        ] if not transacciones.empty else pd.DataFrame(columns=["Cliente", "Monto", "Categoría"])

    if not pagos_cobranza.empty and "Cliente" in pagos_cobranza.columns:
        pagos_cobranza["Monto"] = pd.to_numeric(pagos_cobranza["Monto"], errors='coerce').fillna(0.0)
        pagos_cobranza_sum = pagos_cobranza.groupby("Cliente")["Monto"].sum().reset_index()
    else:
        pagos_cobranza_sum = pd.DataFrame(columns=["Cliente", "Monto"])

    if not anticipos_aplicados_a_cobranza.empty and "Cliente" in anticipos_aplicados_a_cobranza.columns:
        anticipos_aplicados_a_cobranza["Monto"] = pd.to_numeric(anticipos_aplicados_a_cobranza["Monto"],
                                                                errors='coerce').fillna(0.0)
        # Los anticipos aplicados son 'Gasto' en la tabla de transacciones pero 'suman' a los pagos recibidos aquí.
        pagos_anticipos_sum = anticipos_aplicados_a_cobranza.groupby("Cliente")["Monto"].sum().reset_index()
    else:
        pagos_anticipos_sum = pd.DataFrame(columns=["Cliente", "Monto"])

    # Unir pagos de cobranza y anticipos aplicados para el total de "pagos realizados"
    # Usamos outer merge para no perder clientes que solo tienen un tipo de pago
    total_pagos_realizados = pagos_cobranza_sum.merge(pagos_anticipos_sum, on="Cliente", how="outer",
                                                      suffixes=('_cobranza', '_anticipo')).fillna(0)
    total_pagos_realizados['Total Pagos Realizados'] = total_pagos_realizados['Monto_cobranza'] + \
                                                       total_pagos_realizados['Monto_anticipo']
    pagos_total = total_pagos_realizados[['Cliente', 'Total Pagos Realizados']].rename(
        columns={'Total Pagos Realizados': 'Monto'})

    saldos = deuda_total.merge(pagos_total, on="Cliente", how="left").fillna(0)
    saldos["Monto Crédito"] = pd.to_numeric(saldos["Monto Crédito"], errors='coerce').fillna(0.0)
    saldos["Monto"] = pd.to_numeric(saldos["Monto"], errors='coerce').fillna(0.0)
    saldos["Saldo pendiente"] = saldos["Monto Crédito"] - saldos["Monto"]

    st.subheader("📋 Saldos pendientes por cliente")
    st.dataframe(
        saldos[["Cliente", "Monto Crédito", "Monto", "Saldo pendiente"]].rename(columns={
            "Monto Crédito": "Crédito otorgado",
            "Monto": "Pagos realizados"
        }),
        use_container_width=True
    )

    st.divider()
    st.subheader("🧾 Registrar nuevo pago")
    # Usar clientes de st.session_state
    cliente_opciones = clientes["Nombre"].tolist() if not clientes.empty else []

    if not cliente_opciones:
        st.info("No hay clientes registrados.")
        st.stop()  # Detener la ejecución si no hay clientes para seleccionar

    cliente_seleccionado = st.selectbox("Cliente", cliente_opciones, key="cobranza_cliente_select")

    # Si el cliente seleccionado tiene saldo pendiente, sugerir ese monto
    monto_sugerido = 0.0
    if cliente_seleccionado and not saldos.empty and cliente_seleccionado in saldos["Cliente"].tolist():
        saldo_info = saldos[saldos["Cliente"] == cliente_seleccionado]
        if not saldo_info.empty:
            monto_sugerido = saldo_info["Saldo pendiente"].values[0]
            if monto_sugerido < 0:  # Si el saldo es negativo (ya hay excedente/anticipo), no sugerir ese monto para pago de deuda
                monto_sugerido = 0.0

    monto = st.number_input("Monto a abonar", min_value=0.0, value=float(monto_sugerido), format="%.2f",
                            key="cobranza_monto_input")
    metodo_pago = st.selectbox("Método de pago", ["Efectivo", "Transferencia", "Tarjeta"], key="cobranza_metodo_pago")
    fecha = st.date_input("Fecha de pago", key="cobranza_fecha")
    descripcion = st.text_input("Referencia del pago (opcional)", key="cobranza_descripcion")

    if st.button("Procesar Pago",
                 key="cobranza_procesar_pago_btn_main"):  # Añadir key aquí para evitar duplicidad si el botón está fuera de un form
        # Asegurarse de tener el saldo más reciente
        st.session_state.transacciones_data = leer_transacciones()
        transacciones = st.session_state.transacciones_data

        # Recalcular saldos para el cliente específico justo antes de procesar
        # Esto es importante si se hicieron cambios desde la última renderización completa
        saldo_cliente = 0.0
        if cliente_seleccionado:
            # Recalcular anticipos para este cliente
            anticipos_cliente_total_actual = transacciones[
                (transacciones["Categoría"] == "Anticipo Cliente") &
                (transacciones["Cliente"] == cliente_seleccionado) &
                (transacciones["Tipo"] == "Ingreso")
                ]["Monto"].sum()
            anticipos_aplicados_total_actual = transacciones[
                (transacciones["Categoría"] == "Anticipo Aplicado") &
                (transacciones["Cliente"] == cliente_seleccionado) &
                (transacciones["Tipo"] == "Gasto")
                ]["Monto"].sum()
            saldo_anticipos_actual = float(anticipos_cliente_total_actual) - float(anticipos_aplicados_total_actual)

            # Recalcular deuda para este cliente (copia de la lógica de arriba)
            creditos_otorgados_actual = ventas[
                (ventas["Tipo de venta"].isin(["Crédito", "Mixta"])) &
                (ventas["Cliente"] == cliente_seleccionado)
                ]["Monto Crédito"].sum()

            pagos_cobranza_actual = transacciones[
                (transacciones["Categoría"].astype(str) == "Cobranza") &
                (transacciones["Cliente"] == cliente_seleccionado)
                ]["Monto"].sum()

            anticipos_aplicados_a_cobranza_actual = transacciones[
                (transacciones["Categoría"].astype(str) == "Anticipo Aplicado") &
                (transacciones["Cliente"] == cliente_seleccionado)
                ]["Monto"].sum()

            total_pagos_actual = float(pagos_cobranza_actual) + float(anticipos_aplicados_a_cobranza_actual)

            saldo_cliente = float(creditos_otorgados_actual) - total_pagos_actual

        monto_f = float(monto)

        if monto_f <= 0:
            st.error("❌ El monto a abonar debe ser mayor que cero.")
        elif monto_f > saldo_cliente and saldo_cliente > 0:
            # Caso 1: Abono excede el saldo pendiente (y hay saldo pendiente)
            st.warning(
                f"⚠️ El abono de ${monto_f:.2f} excede el saldo pendiente de ${saldo_cliente:.2f} para {cliente_seleccionado}.")
            excedente = monto_f - saldo_cliente

            st.session_state["pago_excedente_info"] = {
                "cliente": cliente_seleccionado,
                "monto_original": monto_f,
                "saldo_cliente": saldo_cliente,
                "excedente": excedente,
                "metodo_pago": metodo_pago,
                "fecha": fecha,
                "descripcion": descripcion
            }
            st.session_state["mostrar_opciones_excedente"] = True
            st.rerun()

        elif monto_f > 0 and saldo_cliente <= 0:
            # Caso 2: Cliente no tiene saldo pendiente, pero se está abonando un monto
            # Aquí, el monto completo es un anticipo o un excedente sobre un anticipo ya existente.
            st.warning(
                f"⚠️ El cliente {cliente_seleccionado} no tiene saldo pendiente. ¿Desea registrarlo como anticipo?")

            st.session_state["pago_anticipo_info"] = {
                "cliente": cliente_seleccionado,
                "monto": monto_f,  # El monto completo es el anticipo
                "metodo_pago": metodo_pago,
                "fecha": fecha,
                "descripcion": descripcion
            }
            st.session_state["mostrar_opciones_anticipo"] = True
            st.rerun()

        else:  # Si el monto es <= saldo_cliente (y > 0) - Pago normal de cobranza
            pago_dict = {
                "Fecha": fecha.isoformat(),
                "Descripción": descripcion or f"Abono de crédito por parte de {cliente_seleccionado}",
                "Categoría": "Cobranza",
                "Tipo": "Ingreso",
                "Monto": float(monto_f),
                "Cliente": cliente_seleccionado,
                "Método de pago": metodo_pago
            }
            guardar_transaccion(pago_dict)
            st.success(f"✅ Pago de ${monto_f:.2f} registrado para {cliente_seleccionado}")
            st.session_state.transacciones_data = leer_transacciones()
            st.session_state.ventas_data = leer_ventas()
            st.rerun()

    # --- Bloque para mostrar opciones de excedente (solo si se necesita) ---
    if st.session_state.get("mostrar_opciones_excedente", False):
        info = st.session_state["pago_excedente_info"]
        with st.form("form_opciones_excedente"):
            st.write(
                f"Para el cliente {info['cliente']}, abono ${info['monto_original']:.2f}, saldo ${info['saldo_cliente']:.2f}, excedente ${info['excedente']:.2f}.")
            opcion_excedente = st.radio(
                "¿Qué deseas hacer con el excedente?",
                ["Generar anticipo con el excedente", "Abonar solo el saldo pendiente", "Cancelar operación"],
                key="radio_excedente_form"  # Added key
            )
            col1, col2 = st.columns(2)
            with col1:
                confirmar_excedente = st.form_submit_button("Confirmar Opción")  # REMOVED KEY
            with col2:
                cancelar_opcion_excedente = st.form_submit_button("Cancelar")  # REMOVED KEY

        if confirmar_excedente:
            if opcion_excedente == "Generar anticipo con el excedente":
                # Guardar el pago de cobranza (saldo_cliente)
                pago_cobranza_dict = {
                    "Fecha": info["fecha"].isoformat(),
                    "Descripción": f"Abono de crédito para {info['cliente']}",
                    "Categoría": "Cobranza",
                    "Tipo": "Ingreso",
                    "Monto": float(info["saldo_cliente"]),
                    "Cliente": info["cliente"],
                    "Método de pago": info["metodo_pago"]
                }
                guardar_transaccion(pago_cobranza_dict)

                # Guardar el excedente como Anticipo Cliente
                anticipo_excedente_dict = {
                    "Fecha": info["fecha"].isoformat(),
                    "Descripción": info[
                                       "descripcion"] or f"Anticipo generado por excedente de pago para {info['cliente']}",
                    "Categoría": "Anticipo Cliente",
                    "Tipo": "Ingreso",
                    "Monto": float(info["excedente"]),
                    "Cliente": info["cliente"],
                    "Método de pago": info["metodo_pago"]
                }
                guardar_transaccion(anticipo_excedente_dict)

                st.success(
                    f"✅ Pago de ${info['saldo_cliente']:.2f} y anticipo de ${info['excedente']:.2f} registrados para {info['cliente']}")

            elif opcion_excedente == "Abonar solo el saldo pendiente":
                pago_dict = {
                    "Fecha": info["fecha"].isoformat(),
                    "Descripción": f"Abono exacto al saldo pendiente para {info['cliente']}.",
                    "Categoría": "Cobranza",
                    "Tipo": "Ingreso",
                    "Monto": float(info["saldo_cliente"]),
                    "Cliente": info["cliente"],
                    "Método de pago": info["metodo_pago"]
                }
                guardar_transaccion(pago_dict)
                st.success(
                    f"✅ Solo se registró el saldo pendiente de ${info['saldo_cliente']:.2f} para {info['cliente']}")
            elif opcion_excedente == "Cancelar operación":
                st.info("Operación de pago cancelada por el usuario.")

            del st.session_state["mostrar_opciones_excedente"]
            del st.session_state["pago_excedente_info"]
            st.session_state.transacciones_data = leer_transacciones()
            st.session_state.ventas_data = leer_ventas()
            st.rerun()
        elif cancelar_opcion_excedente:
            st.info("Operación de pago cancelada por el usuario.")
            del st.session_state["mostrar_opciones_excedente"]
            del st.session_state["pago_excedente_info"]
            st.rerun()

    # --- Bloque para mostrar opciones de anticipo (solo si se necesita) ---
    if st.session_state.get("mostrar_opciones_anticipo", False):
        info = st.session_state["pago_anticipo_info"]
        with st.form("form_opciones_anticipo"):
            st.write(f"El cliente {info['cliente']} no tiene saldo pendiente. Monto a registrar: ${info['monto']:.2f}.")
            opcion_anticipo = st.radio(
                "¿Desea registrar este monto como anticipo?",
                ["Sí, registrar como anticipo", "No, cancelar"],
                key="radio_anticipo_form"  # Added key
            )
            col1, col2 = st.columns(2)
            with col1:
                confirmar_anticipo = st.form_submit_button("Confirmar Opción")  # REMOVED KEY
            with col2:
                cancelar_opcion_anticipo = st.form_submit_button("Cancelar")  # REMOVED KEY

        if confirmar_anticipo:
            if opcion_anticipo == "Sí, registrar como anticipo":
                pago_dict = {
                    "Fecha": info["fecha"].isoformat(),
                    "Descripción": info["descripcion"] or f"Anticipo registrado para {info['cliente']}",
                    "Categoría": "Anticipo Cliente",
                    "Tipo": "Ingreso",
                    "Monto": float(info["monto"]),
                    "Cliente": info["cliente"],
                    "Método de pago": info["metodo_pago"]
                }
                guardar_transaccion(pago_dict)
                st.success(f"✅ Anticipo de ${info['monto']:.2f} registrado para {info['cliente']}")
            else:  # "No, cancelar"
                st.info("Operación de pago cancelada por el usuario.")

            del st.session_state["mostrar_opciones_anticipo"]
            del st.session_state["pago_anticipo_info"]
            st.session_state.transacciones_data = leer_transacciones()
            st.session_state.ventas_data = leer_ventas()
            st.rerun()
        elif cancelar_opcion_anticipo:
            st.info("Operación de pago cancelada por el usuario.")
            del st.session_state["mostrar_opciones_anticipo"]
            del st.session_state["pago_anticipo_info"]
            st.rerun()

    st.divider()
    st.subheader("📑 Historial de pagos")
    # Mostrar todas las transacciones de Cobranza y Anticipo Cliente/Aplicado
    historial_transacciones = st.session_state.transacciones_data[
        st.session_state.transacciones_data["Categoría"].astype(str).isin(
            ["Cobranza", "Anticipo Cliente", "Anticipo Aplicado"])
    ] if not st.session_state.transacciones_data.empty else pd.DataFrame()

    if not historial_transacciones.empty and all(col in historial_transacciones.columns for col in
                                                 ["Fecha", "Cliente", "Descripción", "Monto", "Método de pago",
                                                  "Categoría", "Tipo"]):
        historial_transacciones = historial_transacciones[
            ["Fecha", "Cliente", "Descripción", "Monto", "Método de pago", "Categoría", "Tipo"]]
        st.dataframe(historial_transacciones.sort_values("Fecha", ascending=False), use_container_width=True)
    else:
        st.info("Aún no se han registrado pagos o anticipos.")