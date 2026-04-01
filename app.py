import os
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash
from db import get_db, init_db
from flask import render_template, request, redirect, url_for, jsonify
import psycopg2
import psycopg2.extras  # Esto es fundamental para el RealDictCursor

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

# Agenda
@app.route('/agenda/<int:id>')
def ver_agenda(id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Traemos las agendas que pertenecen solo a este emprendimiento (id=1 es Barbería)
    cur.execute("SELECT id, fecha FROM agendas WHERE emprendimiento_id = %s ORDER BY fecha DESC", (id,))
    agendas = cur.fetchall()
    
    for agenda in agendas:
        cur.execute("SELECT * FROM turnos WHERE agenda_id = %s ORDER BY hora ASC", (agenda['id'],))
        agenda['turnos'] = cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template('emprendimiento/agenda.html', agendas=agendas, emprendimiento_id=id)

@app.route('/agregar_dia', methods=['POST'])
def agregar_dia():
    fecha = request.form.get('fecha')
    # Capturamos el id que mandamos en el input hidden
    eid = request.form.get('emprendimiento_id') 

    if not fecha or not eid:
        return redirect(url_for('ver_agenda', id=eid))

    conn = get_db()
    cur = conn.cursor()
    # Usamos el eid real en el INSERT
    cur.execute("INSERT INTO agendas (fecha, emprendimiento_id) VALUES (%s, %s)", (fecha, eid))
    conn.commit()
    cur.close()
    conn.close()

    # CORRECCIÓN DEL ERROR: Ahora le pasamos el id al url_for
    return redirect(url_for('ver_agenda', id=eid))

@app.route('/guardar_turno', methods=['POST'])
def guardar_turno():
    # 1. Capturamos los datos del form
    eid = request.form.get('emprendimiento_id') # <--- Capturamos el ID real
    agenda_id = request.form.get('agenda_id')
    turno_id = request.form.get('turno_id')
    hora = request.form.get('hora')
    cliente = request.form.get('cliente')
    detalle = request.form.get('detalle')
    monto = request.form.get('monto') or 0

    conn = get_db()
    cur = conn.cursor()

    if turno_id:
        # Modo Edición
        cur.execute("""
            UPDATE turnos 
            SET hora = %s, cliente = %s, detalle = %s, monto = %s 
            WHERE id = %s
        """, (hora, cliente, detalle, monto, turno_id))
    else:
        # Modo Nuevo
        cur.execute("""
            INSERT INTO turnos (agenda_id, hora, cliente, detalle, monto, estado)
            VALUES (%s, %s, %s, %s, %s, 'Pendiente')
        """, (agenda_id, hora, cliente, detalle, monto))

    conn.commit()
    cur.close()
    conn.close()

    # 2. REDIRECCIÓN CORRECTA: Usamos 'eid' que es la variable que definimos arriba
    return redirect(url_for('ver_agenda', id=eid))

@app.route('/actualizar_estado/<int:id>', methods=['POST'])
def actualizar_estado(id):
    datos = request.get_json()
    nuevo_estado = datos.get('estado')

    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # 1. Traemos la info (Usando emprendimiento_id que ya vimos que existe en agendas)
        cur.execute("""
            SELECT a.fecha, a.emprendimiento_id, t.cliente, t.detalle, t.monto, t.estado as estado_anterior
            FROM turnos t
            JOIN agendas a ON t.agenda_id = a.id
            WHERE t.id = %s
        """, (id,))
        
        turno = cur.fetchone()

        if not turno:
            return jsonify({"status": "error", "message": "Turno no encontrado"}), 404

        # 2. Actualizamos el estado del turno (Para que el botón cambie sí o sí)
        cur.execute("UPDATE turnos SET estado = %s WHERE id = %s", (nuevo_estado, id))
        
        # 3. Si es PAGO, insertamos en movimientos
        if nuevo_estado == 'Pago' and turno['estado_anterior'] != 'Pago':
            detalle_mov = f"Turno: {turno['cliente']}"
            if turno['detalle']:
                detalle_mov += f" - {turno['detalle']}"
            
            # Cambié 'eid' por 'emprendimiento_id' también aquí
            cur.execute("""
                INSERT INTO movimientos (emprendimiento_id, fecha, tipo, detalle, monto)
                VALUES (%s, %s, 'INGRESO', %s, %s)
            """, (
                turno['emprendimiento_id'], 
                str(turno['fecha']), 
                detalle_mov, 
                turno['monto']
            ))

        conn.commit()
        return jsonify({"status": "success"})

    except Exception as e:
        conn.rollback()
        print(f"ERROR CRÍTICO: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/borrar_turno/<int:id>', methods=['POST'])
def borrar_turno(id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM turnos WHERE id = %s", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"success": True}) # Usamos JSON para que el AJAX lo borre sin recargar

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

# --- INICIALIZAR DB (crea tablas si no existen) ---
with app.app_context():
    init_db()

# --- RUN LOCAL ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
