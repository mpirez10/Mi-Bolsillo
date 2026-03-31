import os
import sys
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash
from db import get_db, init_db

# --- CONFIGURACIÓN DE APP ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "dev_key")


# --- VERIFICAR SI HAY USUARIOS ---
def hay_usuarios():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return total > 0


# --- REDIRECCIÓN AUTOMÁTICA ---
@app.before_request
def verificar_primer_uso():
    if request.endpoint is None:
        return

    if request.endpoint.startswith('static'):
        return

    if not hay_usuarios() and request.endpoint != 'setup':
        return redirect(url_for('setup'))


# --- SETUP ---
@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if hay_usuarios():
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        password = request.form.get('password')
        fecha_nac = request.form.get('fecha_nacimiento')

        if not nombre or not correo or not password:
            return "Faltan datos", 400

        hashed_pw = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO usuarios (nombre_completo, correo, fecha_nacimiento, password) 
            VALUES (%s, %s, %s, %s)
            """,
            (nombre, correo, fecha_nac, hashed_pw)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('auth.login'))

    return render_template('setup.html')


# --- LOGIN MANAGER ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "Tienes que iniciar sesión."


# --- MODELO USUARIO ---
class Usuario(UserMixin):
    def __init__(self, id, nombre_completo, correo, fecha_nacimiento=None):
        self.id = id
        self.nombre_completo = nombre_completo
        self.correo = correo
        self.fecha_nacimiento = fecha_nacimiento


# --- CARGAR USUARIO (SOLO POSTGRES) ---
@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, nombre_completo, correo, fecha_nacimiento 
        FROM usuarios 
        WHERE id = %s
        """,
        (user_id,)
    )

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return Usuario(
            user['id'],
            user['nombre_completo'],
            user['correo'],
            user['fecha_nacimiento']
        )

    return None


# --- RESPALDO (DESACTIVADO EN PRODUCCIÓN) ---
@app.route('/respaldo')
def descargar_respaldo():
    return "Respaldo desactivado en PostgreSQL", 404


# --- IMPORTACIÓN DE RUTAS ---
from routes import home, cuentas, movimientos, deudas, auth
from routes.finanzas import finanzas_bp
from routes.emprendimiento import emprendimiento_bp

app.register_blueprint(home.bp)
app.register_blueprint(cuentas.bp)
app.register_blueprint(movimientos.bp)
app.register_blueprint(deudas.bp)
app.register_blueprint(auth.auth_bp)
app.register_blueprint(finanzas_bp)
app.register_blueprint(emprendimiento_bp)


# --- INIT DB ---
init_db()


# --- RUN LOCAL ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
