import streamlit as st
import io
import pandas as pd
import datetime
from utils.db import (
    guardar_producto,
    leer_productos,
    actualizar_producto_por_clave,
    eliminar_producto_por_clave,
    guardar_transaccion
)

# --- Cachear productos para reducir llamadas a Firestore ---
@st.cache_data(ttl=60)
def get_productos():
    return leer_productos()


# Helper para Excel
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Productos')
    return output.getvalue()

def render():
    st.title("📦 Gestión de Productos")

    # Cargar productos (cacheado)
    if "productos" not in st.session_state:
        st.session_state.productos = get_productos()
    elif st.session_state.get("reload_productos", False):
        st.session_state.productos = get_productos()
        st.session_state.reload_productos = False

    # --- Agregar nuevo producto ---
    with st.form("form_productos_agregar"):
        st.subheader("Agregar nuevo producto/servicio")
        clave = st.text_input("Clave del producto")
        nombre = st.text_input("Nombre")
        marca_tipo = st.text_input("Marca_Tipo")
        modelo = st.text_input("Modelo")
        color = st.text_input("Color")
        talla = st.text_input("Talla")
        categoria = st.selectbox("Categoría", ["Producto", "Servicio", "Insumos", "Otro"])
        precio = st.number_input("Precio Unitario", min_value=0.0, format="%.2f")
        costo = st.number_input("Costo Unitario", min_value=0.0, format="%.2f")
        cantidad = st.number_input("Cantidad en inventario", min_value=0, step=1)
        descripcion = st.text_area("Descripción")
        submitted_add = st.form_submit_button("Guardar nuevo producto")

        if submitted_add:
            if clave in st.session_state.productos["Clave"].values:
                st.error(f"❌ Ya existe un producto con la clave '{clave}'.")
            elif precio <= 0 or costo < 0 or cantidad <= 0:
                st.warning("⚠️ El precio y la cantidad deben ser mayores a cero. El costo no puede ser negativo.")
            else:
                guardar_producto({
                    "Clave": clave, "Nombre": nombre, "Marca_Tipo": marca_tipo,
                    "Modelo": modelo, "Color": color, "Talla": talla,
                    "Categoría": categoria, "Precio Unitario": precio,
                    "Costo Unitario": costo, "Cantidad": cantidad,
                    "Descripción": descripcion
                })
                if costo * cantidad > 0:
                    guardar_transaccion({
                        "Fecha": datetime.date.today().isoformat(),
                        "Descripción": f"Compra inicial de inventario: {nombre} ({cantidad} unidades)",
                        "Categoría": "Compras", "Tipo": "Egreso",
                        "Monto": float(costo * cantidad), "Cliente": "N/A", "Método de pago": "N/A"
                    })
                st.session_state.reload_productos = True
                st.success("✅ Producto guardado.")
                st.rerun()

    st.divider()

    # --- Inventario / Catálogo ---
    st.subheader("📋 Inventario / Catálogo")
    filtro = st.text_input("Buscar por clave o nombre")
    df_to_display = st.session_state.productos.copy()

    if filtro:
        df_to_display = df_to_display[
            df_to_display["Clave"].str.contains(filtro, case=False, na=False) |
            df_to_display["Nombre"].str.contains(filtro, case=False, na=False)
        ]

    st.dataframe(df_to_display, use_container_width=True)

    if not df_to_display.empty:
        st.download_button(
            label="Descargar catálogo a Excel",
            data=to_excel(df_to_display),
            file_name="catalogo_productos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.divider()

    # --- Reabastecer producto ---
    st.subheader("➕ Dar entrada a productos existentes")
    if not st.session_state.productos.empty:
        claves_existentes = st.session_state.productos["Clave"].dropna().unique().tolist()
        with st.form("form_entrada_existente"):
            producto_sel = st.selectbox("Producto a reabastecer", claves_existentes)
            datos_producto = st.session_state.productos[st.session_state.productos["Clave"] == producto_sel].iloc[0]
            st.write(f"Stock actual: {int(datos_producto['Cantidad'])} unidades")
            cantidad_entrada = st.number_input("Cantidad a añadir", min_value=1, step=1)
            costo_unitario = st.number_input(
                "Costo Unitario", min_value=0.0, format="%.2f",
                value=float(datos_producto.get("Costo Unitario", 0.0))
            )
            submitted_entrada = st.form_submit_button("Registrar entrada")

            if submitted_entrada:
                nueva_cantidad = int(datos_producto["Cantidad"]) + cantidad_entrada
                actualizar_producto_por_clave(producto_sel, {
                    "Cantidad": nueva_cantidad,
                    "Costo Unitario": costo_unitario
                })
                if costo_unitario * cantidad_entrada > 0:
                    guardar_transaccion({
                        "Fecha": datetime.date.today().isoformat(),
                        "Descripción": f"Reabastecimiento de {datos_producto['Nombre']} ({cantidad_entrada} unidades)",
                        "Categoría": "Compras", "Tipo": "Egreso",
                        "Monto": float(costo_unitario * cantidad_entrada),
                        "Cliente": "N/A", "Método de pago": "N/A"
                    })
                st.session_state.reload_productos = True
                st.success("✅ Reabastecimiento registrado.")
                st.rerun()

    st.divider()

    # --- Editar o eliminar producto ---
    st.subheader("🛠️ Editar producto")
    if not st.session_state.productos.empty:
        claves_editar = st.session_state.productos["Clave"].dropna().unique().tolist()
        seleccionado = st.selectbox("Selecciona un producto", claves_editar)
        datos_editar = st.session_state.productos[st.session_state.productos["Clave"] == seleccionado].iloc[0]

        nuevo_nombre = st.text_input("Nuevo nombre", value=datos_editar.get("Nombre", ""))
        nuevo_marca = st.text_input("Marca_Tipo", value=datos_editar.get("Marca_Tipo", ""))
        nuevo_modelo = st.text_input("Modelo", value=datos_editar.get("Modelo", ""))
        nuevo_color = st.text_input("Color", value=datos_editar.get("Color", ""))
        nuevo_talla = st.text_input("Talla", value=datos_editar.get("Talla", ""))
        nuevo_precio = st.number_input("Nuevo precio", value=float(datos_editar.get("Precio Unitario", 0.0)), format="%.2f")
        nuevo_costo = st.number_input("Nuevo costo unitario", value=float(datos_editar.get("Costo Unitario", 0.0)), format="%.2f")
        nueva_descripcion = st.text_area("Nueva descripción", value=datos_editar.get("Descripción", ""))

        if st.button("✏️ Actualizar producto"):
            actualizar_producto_por_clave(seleccionado, {
                "Nombre": nuevo_nombre, "Marca_Tipo": nuevo_marca, "Modelo": nuevo_modelo,
                "Color": nuevo_color, "Talla": nuevo_talla,
                "Precio Unitario": nuevo_precio, "Costo Unitario": nuevo_costo,
                "Descripción": nueva_descripcion
            })
            st.session_state.reload_productos = True
            st.success("✅ Producto actualizado.")
            st.rerun()

        if st.button("🗑️ Eliminar producto"):
            eliminar_producto_por_clave(seleccionado)
            st.session_state.reload_productos = True
            st.success("✅ Producto eliminado.")
            st.rerun()
