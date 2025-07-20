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

# 🚀 Funciones para guardar datos

def guardar_venta(venta_dict):
    """Guarda la venta y la registra como ingreso contable"""
    db.collection("ventas").add(venta_dict)
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

# 📥 Funciones para leer datos

def leer_ventas():
    """Lee todas las ventas guardadas en Firestore con estructura uniforme"""
    docs = db.collection("ventas").stream()
    ventas = []
    columnas = ["Fecha", "Cliente", "Producto", "Cantidad", "Precio Unitario", "Total", "Método de pago",
                "Tipo de venta"]

    for doc in docs:
        data = doc.to_dict()
        venta_normalizada = {col: data.get(col, "") for col in columnas}
        ventas.append(venta_normalizada)

    return ventas


def leer_transacciones():
    """Lee todas las transacciones contables guardadas en Firestore"""
    docs = db.collection("transacciones").stream()
    transacciones = []
    columnas = ["Fecha", "Descripción", "Categoría", "Tipo", "Monto", "Cliente", "Método de pago"]

    for doc in docs:
        data = doc.to_dict()
        transaccion_normalizada = {col: data.get(col, "") for col in columnas}
        transacciones.append(transaccion_normalizada)

    return transacciones



def leer_cobranza():
    """Lee transacciones clasificadas como 'Cobranza'"""
    docs = db.collection("transacciones").where("Categoría", "==", "Cobranza").stream()
    cobranza = []
    columnas = ["Fecha", "Cliente", "Descripción", "Monto", "Método de pago"]

    for doc in docs:
        data = doc.to_dict()
        registro = {col: data.get(col, "") for col in columnas}
        cobranza.append(registro)

    return cobranza


def calcular_balance_contable():
    transacciones = leer_transacciones()
    df = pd.DataFrame(transacciones)
    ingresos = df.query("Tipo == 'Ingreso'")["Monto"].sum()
    gastos = df.query("Tipo == 'Gasto'")["Monto"].sum()
    balance = ingresos - gastos
    return ingresos, gastos, balance


def leer_clientes():
    """Lee todos los clientes registrados en Firestore con estructura uniforme"""
    docs = db.collection("clientes").stream()
    clientes = []
    columnas = ["Nombre", "Correo", "Teléfono", "Dirección", "RFC"]

    for doc in docs:
        data = doc.to_dict()
        cliente_normalizado = {col: data.get(col, "") for col in columnas}
        clientes.append(cliente_normalizado)

    return clientes


def leer_productos():
    """Lee todos los productos registrados en Firestore, asegurando estructura uniforme"""
    docs = db.collection("productos").stream()
    productos = []
    columnas = ["Clave", "Nombre", "Categoría", "Precio Unitario", "Cantidad", "Descripción"]

    for doc in docs:
        data = doc.to_dict()
        producto_normalizado = {col: data.get(col, "") for col in columnas}
        productos.append(producto_normalizado)

    return productos



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
        "Monto": venta_dict.get("Total", 0.0)
    }
    db.collection("transacciones").add(ingreso)

# 🔍 Obtener el ID de documento Firestore (opcional para operaciones avanzadas)
def obtener_id_producto(clave):
    query = db.collection("productos").where("Clave", "==", clave).get()
    return query[0].id if query else None
