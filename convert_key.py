import json
import os

def convert_json_to_streamlit_toml(json_file_path, secret_name="GOOGLE_APPLICATION_CREDENTIALS_JSON"):
    """
    Convierte el contenido de un archivo JSON de clave de servicio de Google
    al formato TOML con comillas triples para Streamlit Secrets.

    Args:
        json_file_path (str): La ruta al archivo serviceAccountKey.json.
        secret_name (str): El nombre de la variable secreta en Streamlit.
                           Por defecto es "GOOGLE_APPLICATION_CREDENTIALS_JSON".

    Returns:
        str: El contenido formateado en TOML listo para copiar y pegar en Streamlit Secrets.
             Retorna None si el archivo no se encuentra o hay un error.
    """
    if not os.path.exists(json_file_path):
        print(f"Error: El archivo '{json_file_path}' no se encontró.")
        return None

    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_content = json.load(f)
            # Re-serializar el JSON para asegurar que esté en una sola línea con caracteres de escape
            # para el TOML multilinea. (Esta línea no es estrictamente necesaria para el output con indent=2,
            # pero la mantengo si la intención original era una única línea para algún otro propósito).
            json_string = json.dumps(json_content, indent=None, separators=(',', ':'))

        # Formatear como TOML con comillas triples
        toml_output = f"""
# {secret_name}
# Este contenido es para pegar directamente en la sección 'Secrets' de tu app en Streamlit Community Cloud.
# NO guardes este archivo en tu repositorio de Git.
{secret_name} = \"\"\"
{json.dumps(json_content, indent=2)}
\"\"\"
"""
        return toml_output
    except json.JSONDecodeError:
        print(f"Error: El archivo '{json_file_path}' no es un JSON válido.")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        return None

# --- Uso del script ---
if __name__ == "__main__":
    # Define la ruta a tu archivo serviceAccountKey.json
    # ¡Asegúrate de que esta ruta sea correcta en tu sistema!
    # A J U S T E   R E A L I Z A D O   A Q U Í
    service_key_file = r"C:\Cursos\Python\ERP Pymes\utils\serviceAccountKey.json"

    toml_output = convert_json_to_streamlit_toml(service_key_file)

    if toml_output:
        print("\n--- COPIA TODO EL CONTENIDO DE ABAJO Y PÉGALO EN STREAMLIT CLOUD SECRETS ---")
        print(toml_output)
        print("----------------------------------------------------------------------")
        print("\n¡Recuerda NUNCA subir tu archivo serviceAccountKey.json o el archivo .toml a Git!")
    else:
        print("\nNo se pudo generar el contenido TOML. Revisa los mensajes de error anteriores.")