# Sistema de Gestión de Inventario y Contabilidad Sencilla

Este proyecto es un sistema de gestión de inventario y contabilidad básica desarrollado con Streamlit y Firestore. Permite a pequeñas empresas o individuos administrar sus productos, ventas, clientes y transacciones financieras de manera sencilla e intuitiva.

## 🌟 Características Principales

  * **Gestión de Productos:**
      * Registro y visualización de productos/servicios con clave, nombre, categoría, precio unitario, costo unitario y cantidad en inventario.
      * Funcionalidad para **dar entrada a productos existentes (reabastecimiento)**, registrando la cantidad añadida y su costo como un egreso contable.
      * Edición de precio, costo y descripción de productos existentes.
      * Eliminación de productos del inventario.
      * Búsqueda rápida por clave o nombre del producto.
  * **Gestión de Clientes:**
      * Registro de información de clientes (nombre, correo, teléfono, dirección, RFC, límite de crédito).
      * Visualización y edición de datos de clientes.
  * **Gestión de Ventas:**
      * Registro de ventas con detalles de productos, cantidades, tipo de venta (contado, crédito, mixta) y método de pago.
      * Cálculo automático del total de la venta y desglose de montos a crédito, contado y anticipos aplicados.
      * Registro automático de la porción al contado de la venta como un ingreso contable.
  * **Módulo de Cobranza:**
      * Visualización de saldos pendientes por cliente.
      * Registro de pagos de cobranza y gestión de excedentes (convertirlos en anticipos).
      * Manejo de pagos como anticipos si el cliente no tiene saldo pendiente.
      * Historial detallado de todas las transacciones de cobranza y anticipos.
  * **Contabilidad Básica:**
      * Registro manual de ingresos y **egresos** con descripción, categoría, tipo y monto.
      * **Registro automático de egresos por compras de inventario y reabastecimiento.**
      * **Balance general en tiempo real (Ingresos vs. Egresos).**
      * Visualización del historial completo de transacciones.
      * Gráficos de distribución de ingresos y egresos.
      * Exportación del historial contable a Excel.

## 🚀 Tecnologías Utilizadas

  * **Python:** Lenguaje de programación principal.
  * **Streamlit:** Para la construcción de la interfaz de usuario interactiva y el despliegue rápido.
  * **Pandas:** Para el manejo y análisis de datos en memoria.
  * **Plotly Express:** Para la visualización de datos (gráficos).
  * **Google Firestore:** Base de datos NoSQL en la nube para el almacenamiento persistente de todos los datos del sistema.
  * **python-dotenv:** Para la gestión segura de variables de entorno (como las credenciales de Firebase).
  * **firebase-admin:** SDK de Firebase para Python, para interactuar con Firestore.

## ⚙️ Configuración del Entorno

Para ejecutar este proyecto localmente, sigue estos pasos:

1.  **Clona el repositorio:**

    ```bash
    git clone <URL_DE_TU_REPOSITORIO>
    cd <nombre_del_directorio_del_proyecto>
    ```

2.  **Crea un entorno virtual (recomendado):**

    ```bash
    python -m venv venv
    # En Windows:
    venv\Scripts\activate
    # En macOS/Linux:
    source venv/bin/activate
    ```

3.  **Instala las dependencias:**

    ```bash
    pip install -r requirements.txt
    ```

    (Asegúrate de tener un archivo `requirements.txt` con todas las dependencias como `streamlit`, `pandas`, `firebase-admin`, `python-dotenv`, `plotly`). Si no lo tienes, puedes generarlo con `pip freeze > requirements.txt` después de instalar todo manualmente o usar la siguiente lista:

    ```
    streamlit
    pandas
    firebase-admin
    python-dotenv
    plotly
    xlsxwriter
    ```

4.  **Configura Firebase Firestore:**

      * Ve a la Consola de Firebase ([https://console.firebase.google.com/](https://console.firebase.google.com/)).
      * Crea un nuevo proyecto o selecciona uno existente.
      * Ve a `Build` \> `Firestore Database`. Inicializa la base de datos en modo de producción o prueba.
      * Ve a `Project settings` (el icono de engranaje) \> `Service accounts`.
      * Haz clic en `Generate new private key` para descargar un archivo JSON con tus credenciales de servicio.
      * **Guarda este archivo JSON** en un lugar seguro dentro de tu proyecto (por ejemplo, en una carpeta `secrets/`). **¡No lo subas a un repositorio público\!**

5.  **Configura las variables de entorno:**

      * Crea un archivo llamado `.env` en la raíz de tu proyecto.
      * Dentro de `.env`, añade la siguiente línea, reemplazando `<ruta/a/tu/archivo_json_de_servicio.json>` con la ruta real a tu archivo JSON de credenciales de Firebase:
        ```
        SERVICE_ACCOUNT=secrets/tu-archivo-de-servicio-firebase.json
        ```

## ▶️ Cómo Ejecutar

Una vez configurado, puedes iniciar la aplicación Streamlit desde tu terminal:

```bash
.streamlit run main.py
```

Esto abrirá la aplicación en tu navegador web predeterminado.

## 📂 Estructura del Proyecto

```
.
├── main.py                 # Punto de entrada principal de la aplicación Streamlit
├── modules/
│   ├── __init__.py         # Archivo vacío para que Python reconozca el directorio como un paquete
│   ├── productos.py        # Módulo para la gestión de productos/inventario
│   ├── clientes.py         # Módulo para la gestión de clientes
│   ├── ventas.py           # Módulo para el registro de ventas
│   ├── cobranza.py         # Módulo para la gestión de cobranza y saldos
│   └── contabilidad.py     # Módulo para la contabilidad básica y reportes
├── utils/
│   ├── __init__.py
│   └── db.py               # Funciones de utilidad para interactuar con Firestore
├── .env                    # Variables de entorno (no subir a Git)
├── requirements.txt        # Dependencias del proyecto
└── README.md               # Este archivo
```

## 🤝 Contribuciones

Si deseas contribuir a este proyecto, por favor:

1.  Haz un "fork" del repositorio.
2.  Crea una nueva rama (`git checkout -b feature/nombre-de-tu-caracteristica`).
3.  Realiza tus cambios y commitea (`git commit -am 'Agrega nueva característica'`).
4.  Sube tus cambios (`git push origin feature/nombre-de-tu-caracteristica`).
5.  Abre un Pull Request.

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles. (Si no tienes un archivo LICENSE, puedes crear uno o remover esta sección).

-----