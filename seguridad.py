from cryptography.fernet import Fernet

# --- ESTA ES LA LLAVE MAESTRA ---
# Guardala bien, si la perdés no recuperamos los datos ni a palos.
_CLAVE_MAESTRA = b'uAwuCVGI-004mEUMzNAaaU884jxl3d9NC3Pn0CzPaYc=' 
_cipher_suite = Fernet(_CLAVE_MAESTRA)

def encriptar(dato):
    """Convierte un número o texto en un chorizo de letras ilegible."""
    if dato is None or dato == "": 
        return None
    # Pasamos a string -> bytes -> encriptamos -> volvemos a string para la DB
    mensaje_bytes = str(dato).encode('utf-8')
    mensaje_encriptado = _cipher_suite.encrypt(mensaje_bytes)
    return mensaje_encriptado.decode('utf-8')

def desencriptar(dato_encriptado):
    """Convierte el chorizo de letras de la DB al valor real (1500, 'Juan', etc)."""
    if not dato_encriptado: 
        return None
    try:
        # Proceso inverso: string -> bytes -> desencriptamos -> string
        mensaje_bytes = dato_encriptado.encode('utf-8')
        mensaje_desencriptado = _cipher_suite.decrypt(mensaje_bytes)
        return mensaje_desencriptado.decode('utf-8')
    except Exception as e:
        # Si el dato no estaba encriptado o la clave falló, devolvemos el original
        # Esto sirve para no romper la app con datos viejos de la v1.1
        return dato_encriptado