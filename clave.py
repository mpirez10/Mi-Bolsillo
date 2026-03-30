import os
from cryptography.fernet import Fernet

clave = os.getenv("FERNET_KEY")

f = Fernet(clave.encode())