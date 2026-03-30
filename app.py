import os
import sys
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash
from db import get_db, init_db
import webbrowser
from threading import Timer
from flask import Flask
from db import init_db

app = Flask(__name__)
def hay_usuarios():
    db = get_db()
    usuario = db.execute('SELECT COUNT(*) as total FROM usuarios').fetchone()
    return usuario['total'] > 0

# --- CONFIGURACIÓN DE RUTAS PARA EL EXE ---
if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__, template_folder='templates', static_folder='static')

app.secret_key = os.getenv("SECRET_KEY", "dev_key")

# --- REDIRECCIÓN AUTOMÁTICA ---
@app.before_request
def verificar_primer_uso():
    if request.endpoint is None:
        return

    if request.endpoint.startswith('static'):
        return

    if not hay_usuarios() and request.endpoint != 'setup':
        return redirect(url_for('setup'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if hay_usuarios():
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        correo = request.form.get('correo')
        pass_raw = request.form.get('password')
        fecha_nac = request.form.get('fecha_nacimiento')

        if not nombre or not correo or not pass_raw:
            return "Faltan datos obligatorios", 400

        hashed_pw = generate_password_hash(pass_raw)

        db = get_db()
        db.execute(
            'INSERT INTO usuarios (nombre_completo, correo, fecha_nacimiento, password) VALUES (?, ?, ?, ?)',
            (nombre, correo, fecha_nac, hashed_pw)
        )
        db.commit()
        return redirect(url_for('auth.login'))

    return render_template('setup.html')

# --- CONFIGURACIÓN DE LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "Tienes que iniciar sesión."

class Usuario(UserMixin):
    def __init__(self, id, nombre_completo, correo, fecha_nacimiento=None):
        self.id = id
        self.nombre_completo = nombre_completo
        self.correo = correo
        self.fecha_nacimiento = fecha_nacimiento

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    
    if user:
        return Usuario(
            user['id'], 
            user['nombre_completo'], 
            user['correo'], 
            user['fecha_nacimiento']
        )
    return None

@app.route('/respaldo')
def descargar_respaldo():
    try:
        db_path = os.path.join(os.getcwd(), "finanzas.db")
        fecha_today = datetime.now().strftime("%d-%m-%Y")
        nombre_descarga = f"Respaldo_MiBolsillo_{fecha_today}.db"
        
        if os.path.exists(db_path):
            return send_file(
                db_path,
                as_attachment=True,
                download_name=nombre_descarga
            )
        else:
            return "Error: No se encontró la base de datos, bo.", 404
    except Exception as e:
        return f"Error al generar el respaldo: {str(e)}", 500

# --- IMPORTACIÓN Y REGISTRO DE BLUEPRINTS ---
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

init_db()
if __name__ == "__main__":
    init_db()

    def abrir_ventana_profesional():
        url = "http://127.0.0.1:5000"
        try:
            os.system(f'start chrome --app={url} --window-size=1200,800')
        except:
            webbrowser.open_new(url)

    Timer(1.5, abrir_ventana_profesional).start()

    print("-----------------------------------------")
    print("🚀 MIBOLSILLO v1.2 - MODO SEGURO")
    print("🖥️  PC: Abriendo ventana de App...")
    print("📱 Celular: http://192.168.1.2:5000")
    print("-----------------------------------------")

    app.run(host='0.0.0.0', port=5000, debug=False)
