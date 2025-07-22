import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import datetime
import pandas as pd


# Cargar variables desde .env
load_dotenv()
cred_path = os.getenv("SERVICE_ACCOUNT")  # Ruta del archivo JSON del servicio

# Inicializar Firebase solo una vez
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

# Cliente Firestore
db = firestore.client()

# --- Funciones para guardar datos ---

def guardar_venta(venta_dict):
    """Guarda la venta y la registra como ingreso contable"""
    db.collection("ventas").add(venta_dict)
    # Considera si este ingreso automático debe ser 'Total' o 'Monto Contado'
    # Actualmente registra el Total de la venta como ingreso contable general.
    registrar_ingreso_automatico(venta_dict)

def guardar_cliente(cliente_dict):
    """Agrega un nuevo cliente a la colección 'clientes'"""
    db.collection("clientes").add(cliente_dict)


def guardar_transaccion(transaccion_dict):
    """Agrega una transacción contable a la colección 'transacciones'"""
    db.collection("transacciones").add(transaccion_dict)


def registrar_pago_cobranza(cliente, monto, metodo_pago, fecha, descripcion=""):
    pago_dict = {
        "Fecha": fecha,
        "Descripción": descripcion or f"Abono de crédito por parte de {cliente}",
        "Categoría": "Cobranza",
        "Tipo": "Ingreso",
        "Monto": monto,
        "Cliente": cliente,
        "Método de pago": metodo_pago
    }
    db.collection("transacciones").add(pago_dict)


def guardar_producto(producto_dict):
    """Agrega un nuevo producto a la colección 'productos'"""
    db.collection("productos").add(producto_dict)

# --- Funciones para leer datos ---
def leer_ventas():
    """
    Lee todas las ventas guardadas en Firestore, asegurando una estructura uniforme
    y la conversión de columnas numéricas a un tipo numérico (float).
    """
    docs = db.collection("ventas").stream()
    ventas = []
    # ¡AQUÍ ESTÁ LA MODIFICACIÓN CLAVE!
    # Se añaden 'Monto Contado' y 'Anticipo Aplicado' a las columnas esperadas.
    columnas = [
        "Fecha", "Cliente", "Producto", "Cantidad", "Precio Unitario", "Total",
        "Monto Crédito", "Monto Contado", "Anticipo Aplicado", # Nuevas columnas
        "Método de pago", "Tipo de venta"
    ]

    for doc in docs:
        data = doc.to_dict()
        venta_normalizada = {col: data.get(col, None) for col in columnas}
        ventas.append(venta_normalizada)

    if not ventas:
        df = pd.DataFrame(columns=columnas)
    else:
        df = pd.DataFrame(ventas)
        # Asegurar que todas las columnas existan, si no se obtuvieron de Firestore
        for col in columnas:
            if col not in df.columns:
                df[col] = None

        # Convertir explícitamente columnas numéricas a float,
        # convirtiendo errores a NaN y luego a 0.0.
        # ¡IMPORTANTE! Asegúrate de que estas nuevas columnas también sean numéricas.
        numeric_cols = ["Cantidad", "Precio Unitario", "Total", "Monto Crédito", "Monto Contado", "Anticipo Aplicado"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

        # Reordenar las columnas según lo definido
        df = df[columnas]

    return df


def leer_transacciones():
    docs = db.collection("transacciones").stream()
    transacciones = []
    columnas = ["Fecha", "Descripción", "Categoría", "Tipo", "Monto", "Cliente", "Método de pago"]

    for doc in docs:
        data = doc.to_dict()
        transaccion_normalizada = {col: data.get(col, None) for col in columnas} # Usar None
        transacciones.append(transaccion_normalizada)

    if not transacciones:
        df = pd.DataFrame(columns=columnas)
    else:
        df = pd.DataFrame(transacciones)
        for col in columnas:
            if col not in df.columns:
                df[col] = None

        # Convertir 'Monto' a numérico
        if "Monto" in df.columns:
            df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0.0)

        df = df[columnas]

    return df


def leer_cobranza():
    """Lee transacciones clasificadas como 'Cobranza'"""
    docs = db.collection("transacciones").where("Categoría", "==", "Cobranza").stream()
    cobranza = []
    columnas = ["Fecha", "Cliente", "Descripción", "Monto", "Método de pago"]

    for doc in docs:
        data = doc.to_dict()
        registro = {col: data.get(col, None) for col in columnas} # Usar None
        cobranza.append(registro)

    df = pd.DataFrame(cobranza)
    # Asegurarse de que 'Monto' sea numérico para la cobranza también
    if "Monto" in df.columns:
        df["Monto"] = pd.to_numeric(df["Monto"], errors='coerce').fillna(0.0)

    return df


def calcular_balance_contable():
    transacciones = leer_transacciones()
    # Asegúrate de que 'Monto' ya es numérico gracias a leer_transacciones
    ingresos = transacciones.query("Tipo == 'Ingreso'")["Monto"].sum()
    gastos = transacciones.query("Tipo == 'Gasto'")["Monto"].sum()
    balance = ingresos - gastos
    return ingresos, gastos, balance


def leer_clientes():
    docs = db.collection("clientes").stream()
    clientes = []
    columnas = ["Nombre", "Correo", "Teléfono", "Dirección", "RFC", "Límite de crédito"]

    for doc in docs:
        data = doc.to_dict()
        cliente_normalizado = {col: data.get(col, None) for col in columnas} # Usar None
        clientes.append(cliente_normalizado)

    df = pd.DataFrame(clientes)
    if not clientes: # Si no hay clientes, el DF estará vacío, asegurar columnas
        df = pd.DataFrame(columns=columnas)
    else:
        for col in columnas:
            if col not in df.columns:
                df[col] = None # Asegurar que las columnas existen

    # Convertir 'Límite de crédito' a numérico
    if "Límite de crédito" in df.columns:
        df["Límite de crédito"] = pd.to_numeric(df["Límite de crédito"], errors='coerce').fillna(0.0)

    return df


def leer_productos():
    """Lee todos los productos registrados en Firestore, asegurando estructura uniforme"""
    docs = db.collection("productos").stream()
    productos = []
    columnas = ["Clave", "Nombre", "Categoría", "Precio Unitario", "Cantidad", "Descripción"]

    for doc in docs:
        data = doc.to_dict()
        producto_normalizado = {col: data.get(col, None) for col in columnas} # Usar None
        productos.append(producto_normalizado)

    df = pd.DataFrame(productos)
    if not productos: # Si no hay productos, el DF estará vacío, asegurar columnas
        df = pd.DataFrame(columns=columnas)
    else:
        for col in columnas:
            if col not in df.columns:
                df[col] = None # Asegurar que las columnas existen

    # Convertir 'Precio Unitario' y 'Cantidad' a numérico
    numeric_cols = ["Precio Unitario", "Cantidad"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    return df


# ✅ Actualizar un campo específico de un producto
def actualizar_producto_por_clave(clave, campos_actualizados: dict):
    productos_ref = db.collection("productos")
    query = productos_ref.where("Clave", "==", clave).get()
    if query:
        doc_id = query[0].id
        productos_ref.document(doc_id).update(campos_actualizados)

# 🗑️ Eliminar un producto por clave
def eliminar_producto_por_clave(clave):
    productos_ref = db.collection("productos")
    query = productos_ref.where("Clave", "==", clave).get()
    if query:
        doc_id = query[0].id
        productos_ref.document(doc_id).delete()

def registrar_ingreso_automatico(venta_dict):
    """Convierte una venta en ingreso contable"""
    ingreso = {
        "Fecha": venta_dict.get("Fecha", datetime.date.today().isoformat()),
        "Descripción": f"Venta a {venta_dict.get('Cliente', 'Cliente desconocido')}",
        "Categoría": "Ventas",
        "Tipo": "Ingreso",
        # Aseguramos que el Total sea un float aquí también
        "Monto": float(venta_dict.get("Total", 0.0))
    }
    db.collection("transacciones").add(ingreso)

# 🔍 Obtener el ID de documento Firestore (opcional para operaciones avanzadas)
def obtener_id_producto(clave):
    query = db.collection("productos").where("Clave", "==", clave).get()
    return query[0].id if query else None