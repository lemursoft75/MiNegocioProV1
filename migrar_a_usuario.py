# migrar_datos_a_usuario.py
import firebase_admin
from firebase_admin import credentials, firestore
import os

# UID del usuario al que quieres mover toda la data
UID = "qd6vLE2nN9WOsuvRA86vP64pm0B3"

# Usar el serviceAccountKey.json que ya tienes en tu proyecto
cred = credentials.Certificate(os.path.join("utils", "serviceAccountKey.json"))
firebase_admin.initialize_app(cred)

db = firestore.client()

# Lista de colecciones en la raíz que quieres mover
colecciones_a_migrar = ["clientes", "productos", "ventas", "transacciones"]

for coleccion in colecciones_a_migrar:
    print(f"Migrando colección: {coleccion} ...")

    docs = db.collection(coleccion).stream()
    for doc in docs:
        data = doc.to_dict()
        # Copiar documento a la nueva ubicación
        db.collection("usuarios").document(UID).collection(coleccion).document(doc.id).set(data)
        print(f"  ✅ {coleccion}/{doc.id} migrado a usuarios/{UID}/{coleccion}")

    print(f"Eliminando colección raíz: {coleccion} ...")
    # Si quieres borrar los originales después de migrar, descomenta esta parte:
    # for doc in db.collection(coleccion).stream():
    #     db.collection(coleccion).document(doc.id).delete()

print("🎯 Migración completa.")
