import streamlit as st
import io
import pandas as pd
import datetime
from utils.db import (
    guardar_producto,
    leer_productos,
    actualizar_producto_por_clave,
    eliminar_producto_por_clave
)


def render():
    st.title("📦 Gestión de Productos")

    # Cargar productos desde Firestore
    if "productos" not in st.session_state:
        productos_data = leer_productos()
        st.session_state.productos = pd.DataFrame(productos_data)

    # Asegurar columnas necesarias
    columnas_necesarias = ["Clave", "Nombre", "Categoría", "Precio Unitario", "Costo Unitario", "Cantidad",
                           "Descripción"]
    for col in columnas_necesarias:
        if col not in st.session_state.productos.columns:
            st.session_state.productos[col] = pd.Series(dtype="object")

    # Campos temporales
    valores_iniciales = {
        "clave": "",
        "nombre": "",
        "categoria": "Producto",
        "precio": 0.0,
        "costo": 0.0,
        "cantidad": 0,
        "descripcion": ""
    }
    for campo, valor in valores_iniciales.items():
        if campo not in st.session_state:
            st.session_state[campo] = valor

    # Botón limpiar campos
    if st.button("🧹 Limpiar campos"):
        for campo, valor in valores_iniciales.items():
            st.session_state[campo] = valor
        st.rerun()

    # Formulario de producto
    with st.form("form_productos"):
        st.subheader("Agregar nuevo producto/servicio")
        clave = st.text_input("Clave del producto", value=st.session_state.clave, key="clave")
        nombre = st.text_input("Nombre", value=st.session_state.nombre, key="nombre")
        categoria = st.selectbox("Categoría", ["Producto", "Servicio", "Otro"], key="categoria")
        precio = st.number_input("Precio Unitario", min_value=0.0, format="%.2f", value=float(st.session_state.precio),
                                 key="precio")
        costo = st.number_input("Costo Unitario", min_value=0.0, format="%.2f", value=float(st.session_state.costo),
                                key="costo")
        cantidad = st.number_input("Cantidad en inventario", min_value=0, step=1, value=int(st.session_state.cantidad),
                                   key="cantidad")
        descripcion = st.text_area("Descripción", value=st.session_state.descripcion, key="descripcion")
        submitted = st.form_submit_button("Guardar producto")

        if submitted:
            if "Clave" not in st.session_state.productos.columns:
                st.session_state.productos["Clave"] = pd.Series(dtype="object")

            if clave in st.session_state.productos["Clave"].values:
                st.error(f"❌ Ya existe un producto con la clave '{clave}'. Usa una clave distinta.")
            elif precio <= 0 or costo < 0 or cantidad <= 0:
                st.warning("⚠️ El precio y la cantidad deben ser mayores a cero. El costo no puede ser negativo.")
            else:
                nuevo_producto = {
                    "Clave": clave,
                    "Nombre": nombre,
                    "Categoría": categoria,
                    "Precio Unitario": precio,
                    "Costo Unitario": costo,
                    "Cantidad": cantidad,
                    "Descripción": descripcion
                }
                guardar_producto(nuevo_producto)
                nuevo_df = pd.DataFrame([nuevo_producto])
                st.session_state.productos = pd.concat([st.session_state.productos, nuevo_df], ignore_index=True)
                st.success("✅ Producto guardado en Firestore y agregado al catálogo")

    st.divider()
    st.subheader("📋 Inventario / Catálogo")

    filtro = st.text_input("Buscar por clave o nombre")
    if filtro:
        df_filtrado = st.session_state.productos[
            st.session_state.productos["Clave"].str.contains(filtro, case=False, na=False) |
            st.session_state.productos["Nombre"].str.contains(filtro, case=False, na=False)
            ]
        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.dataframe(st.session_state.productos, use_container_width=True)

    st.divider()
    st.subheader("🛠️ Editar o eliminar producto")

    if not st.session_state.productos.empty:
        claves_disponibles = st.session_state.productos["Clave"].dropna().unique()
        seleccionado = st.selectbox("Selecciona un producto", claves_disponibles)
        filtro = st.session_state.productos["Clave"] == seleccionado

        if filtro.any():
            datos = st.session_state.productos[filtro].iloc[0]

            nuevo_precio = st.number_input("Nuevo precio", value=float(datos["Precio Unitario"]), format="%.2f")
            nuevo_costo = st.number_input("Nuevo costo", value=float(datos.get("Costo Unitario", 0.0)), format="%.2f")
            nueva_cantidad = st.number_input("Nuevo stock", value=int(datos["Cantidad"]), step=1)
            nueva_descripcion = st.text_area("Nueva descripción", value=datos["Descripción"])

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✏️ Actualizar producto"):
                    actualizar_producto_por_clave(seleccionado, {
                        "Precio Unitario": nuevo_precio,
                        "Costo Unitario": nuevo_costo,
                        "Cantidad": nueva_cantidad,
                        "Descripción": nueva_descripcion
                    })
                    idx = st.session_state.productos.index[st.session_state.productos["Clave"] == seleccionado][0]
                    st.session_state.productos.at[idx, "Precio Unitario"] = nuevo_precio
                    st.session_state.productos.at[idx, "Costo Unitario"] = nuevo_costo
                    st.session_state.productos.at[idx, "Cantidad"] = nueva_cantidad
                    st.session_state.productos.at[idx, "Descripción"] = nueva_descripcion
                    st.success("✅ Producto actualizado")

            with col2:
                if st.button("🗑️ Eliminar producto"):
                    eliminar_producto_por_clave(seleccionado)
                    st.session_state.productos = st.session_state.productos[
                        st.session_state.productos["Clave"] != seleccionado
                        ]
                    st.success("✅ Producto eliminado del inventario y Firestore")