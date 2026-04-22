from flask_login import UserMixin
from db import get_db

class Usuario(UserMixin):
    """
    Clase de Usuario compatible con Flask-Login.
    Mantiene la sesión activa y expone los datos del usuario.
    """
    def __init__(self, id, nombre_completo, correo, fecha_nacimiento):
        self.id = id
        self.nombre_completo = nombre_completo
        self.correo = correo
        self.fecha_nacimiento = fecha_nacimiento

    @staticmethod
    def get_by_id(user_id):
        """
        Busca un usuario en la base de datos por su ID.
        Útil para el load_user de Flask-Login.
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, nombre_completo, correo, fecha_nacimiento FROM usuarios WHERE id = %s",
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                return None

            # Manejo dinámico por si el cursor devuelve diccionario o tupla
            if isinstance(user, dict):
                return Usuario(
                    user["id"], 
                    user["nombre_completo"], 
                    user["correo"], 
                    user["fecha_nacimiento"]
                )
            else:
                return Usuario(user[0], user[1], user[2], user[3])
                
        except Exception as e:
            print(f"Error al cargar usuario: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_email(correo):
        """
        Busca un usuario por correo para el proceso de Login.
        """
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT id, nombre_completo, correo, fecha_nacimiento, password FROM usuarios WHERE correo = %s",
                (correo.lower().strip(),)
            )
            user = cursor.fetchone()
            return user # Retornamos la data cruda para validar el hash en Auth.py
        finally:
            cursor.close()
            conn.close()
