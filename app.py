import os
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash
from db import get_db, init_db

# --- CONFIGURACIÓN DE APP ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

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

# --- CARGAR USUARIO ---
@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, nombre_completo, correo, fecha_nacimiento FROM usuarios WHERE id = %s",
        (user_id,)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        try:
            return Usuario(user["id"], user["nombre_completo"], user["correo"], user["fecha_nacimiento"])
        except Exception:
            return Usuario(user[0], user[1], user[2], user[3])
    return None

# --- VERIFICAR SI HAY USUARIOS ---
def hay_usuarios():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS count FROM usuarios")
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    try:
        return result["count"] > 0
    except Exception:
        return result[0] > 0

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

# --- RESPALDO (DESACTIVADO) ---
@app.route('/respaldo')
def descargar_respaldo():
    return "Respaldo desactivado en PostgreSQL", 404

# --- IMPORTACIÓN Y REGISTRO DE RUTAS ---
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

# --- RUTA TEMPORAL: REPARAR TODAS LAS SECUENCIAS ---
@app.route("/fix-all-seqs")
def fix_all_sequences():
    conn = get_db()
    cursor = conn.cursor()
    try:
        tablas = [
            ("usuarios", "id"),
            ("cuentas", "id"),
            ("movimientos", "id"),
            ("deudas", "id"),
            ("ventas", "id"),
            ("gastos", "id"),
            ("productos", "id"),
            ("movimientos_emprendimiento", "id"),
            ("emprendimientos", "id")
        ]

        for tabla, columna in tablas:
            seq_name = f"{tabla}_{columna}_seq"

            # 1) Crear secuencia si no existe
            cursor.execute(f"SELECT 1 FROM pg_class WHERE relkind = 'S' AND relname = %s", (seq_name,))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(f"CREATE SEQUENCE {seq_name}")

            # 2) Asegurar DEFAULT nextval para la columna
            cursor.execute(
                f"ALTER TABLE {tabla} ALTER COLUMN {columna} SET DEFAULT nextval(%s)",
                (seq_name,)
            )

            # 3) Resincronizar la secuencia con el MAX(id) existente
            cursor.execute(
                f"SELECT setval(%s, COALESCE(MAX({columna}), 1), false) FROM {tabla}",
                (seq_name,)
            )

        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return f"Error al reparar secuencias: {e}", 500

    cursor.close()
    conn.close()
    return "Secuencias reparadas correctamente"

# --- INICIALIZAR DB (crea tablas si no existen) ---
with app.app_context():
    init_db()

# --- RUN LOCAL ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
