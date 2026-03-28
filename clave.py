from cryptography.fernet import Fernet

# Generamos la llave
clave = Fernet.generate_key()

# La mostramos en pantalla (esto te va a dar un chorizo de letras y números)
print("--------------------------------------------------")
print("Copiá esta clave y guardala bien:")
print(clave.decode())
print("--------------------------------------------------")