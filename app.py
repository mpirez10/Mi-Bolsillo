import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_login import LoginManager, current_user, login_required
from werkzeug.security import generate_password_hash
from db import get_db, init_db
from routes.models import Usuario


# --- CONFIGURACIÓN DE APP ---
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "dev_key")

# --- LOGIN MANAGER ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = "Tenés que iniciar sesión, bo."
login_manager.login_message_category = "info"

# --- CARGAR USUARIO ---
@login_manager.user_loader
def load_user(user_id):
    return Usuario.get_by_id(user_id) # Usamos el método pro que creamos en models.py

# --- VERIFICAR SI HAY USUARIOS ---
def hay_usuarios():
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        result = cursor.fetchone()
        # Manejo por si es tupla o dict
        count = result[0] if isinstance(result, tuple) else result['count']
        return count > 0
    except:
        return False
    finally:
        cursor.close()
        conn.close()
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
@login_required
def descargar_respaldo():
    return "Respaldo desactivado en PostgreSQL", 404

# Agenda
@app.route('/agenda/<int:id>')
@login_required
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
@login_required
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
@login_required
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

@app.route('/api/ultimos_movimientos')
@login_required
def api_movimientos():
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Hacemos la consulta SQL pura para traer los últimos 30
        # Usamos COALESCE para que si cuenta_destino es NULL (en egresos) no rompa nada
        cursor.execute("""
            SELECT fecha, tipo, monto, cuenta_origen, motivo 
            FROM movimientos 
            WHERE usuario_id = %s 
            ORDER BY fecha DESC 
            LIMIT 30
        """, (current_user.id,))
        
        movs = cursor.fetchall()
        
        # Formateamos los datos para que el JavaScript los entienda
        resultado = []
        for m in movs:
            resultado.append({
                'fecha': m['fecha'].strftime('%d/%m/%Y') if hasattr(m['fecha'], 'strftime') else str(m['fecha']),
                'tipo': m['tipo'],
                'monto': f"$ {float(m['monto']):,.2f}",
                'cuenta': m['cuenta_origen'],
                'detalle': m['motivo']
            })
            
        return jsonify(resultado)

    except Exception as e:
        print(f"Error en API: {e}")
        return jsonify({"error": "No se pudieron cargar los movimientos"}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/actualizar_estado/<int:id>', methods=['POST'])
@login_required
def actualizar_estado(id):
    datos = request.get_json()
    nuevo_estado = datos.get('estado')
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cur.execute("""
            SELECT a.fecha, a.emprendimiento_id, t.cliente, t.detalle, t.monto, t.estado as estado_anterior
            FROM turnos t
            JOIN agendas a ON t.agenda_id = a.id
            WHERE t.id = %s
        """, (id,))
        turno = cur.fetchone()

        if not turno:
            return jsonify({"status": "error", "message": "Turno no encontrado"}), 404

        # Armamos el detalle como vos querés: CLIENTE + DETALLE
        texto_movimiento = f"{turno['cliente']}"
        if turno['detalle']:
            texto_movimiento += f" - {turno['detalle']}"

        # A. Si pasa a PAGO: Insertamos
        if nuevo_estado == 'Pago' and turno['estado_anterior'] != 'Pago':
            cur.execute("""
                INSERT INTO movimientos_emprendimiento 
                (emprendimiento_id, fecha, concepto, detalle, monto, usuario_id)
                VALUES (%s, %s, 'INGRESO', %s, %s, %s)
            """, (turno['emprendimiento_id'], turno['fecha'], texto_movimiento, turno['monto'], current_user.id))

        # B. Si deja de ser PAGO: Borramos usando nombre, monto y fecha para no errarle
        elif nuevo_estado != 'Pago' and turno['estado_anterior'] == 'Pago':
            cur.execute("""
                DELETE FROM movimientos_emprendimiento 
                WHERE emprendimiento_id = %s AND detalle = %s AND monto = %s AND fecha = %s AND usuario_id = %s
            """, (turno['emprendimiento_id'], texto_movimiento, turno['monto'], turno['fecha'], current_user.id))

        # Actualizamos el estado del turno
        cur.execute("UPDATE turnos SET estado = %s WHERE id = %s", (nuevo_estado, id))
        
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/borrar_turno/<int:id>', methods=['POST'])
@login_required
def borrar_turno(id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # 1. Obtenemos los datos necesarios del turno y la agenda antes de borrar
        cur.execute("""
            SELECT t.cliente, t.estado, t.monto, t.detalle, a.fecha, a.emprendimiento_id 
            FROM turnos t
            JOIN agendas a ON t.agenda_id = a.id
            WHERE t.id = %s
        """, (id,))
        turno = cur.fetchone()

        if turno:
            # 2. Si estaba Pago, borramos el movimiento de la caja
            if turno['estado'] == 'Pago':
                texto_movimiento = f"{turno['cliente']}"
                if turno['detalle']:
                    texto_movimiento += f" - {turno['detalle']}"
                
                cur.execute("""
                    DELETE FROM movimientos_emprendimiento 
                    WHERE emprendimiento_id = %s AND detalle = %s AND monto = %s AND fecha = %s AND usuario_id = %s
                """, (turno['emprendimiento_id'], texto_movimiento, turno['monto'], turno['fecha'], current_user.id))

            # 3. Borramos el turno definitivamente
            cur.execute("DELETE FROM turnos WHERE id = %s", (id,))
            
        conn.commit()
        return jsonify({"success": True})

    except Exception as e:
        conn.rollback()
        print(f"Error al borrar turno: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/borrar_dia/<int:id>', methods=['POST'])
@login_required
def borrar_dia(id):
    conn = get_db() # <--- Llamamos a la función para obtener la conexión
    try:
        # Usamos cursor_factory si necesitás diccionarios, 
        # pero para un DELETE simple con el cursor común alcanza
        with conn.cursor() as cursor:
            # 1. Borramos primero los turnos de ese día
            cursor.execute("DELETE FROM turnos WHERE agenda_id = %s", (id,))
            
            # 2. Ahora sí borramos la agenda
            cursor.execute("DELETE FROM agendas WHERE id = %s", (id,))
            
            # 3. Guardamos los cambios
            conn.commit()
            
        return '', 204
    except Exception as e:
        print(f"Error al borrar: {e}")
        conn.rollback() 
        return 'Error', 500
    finally:
        # 4. ¡Importantísimo cerrar la conexión! 
        # Si no la cerrás, Render se queda sin "slots" para la base de datos
        conn.close()


# --- IMPORTACIÓN Y REGISTRO DE RUTAS ---
from routes import home, cuentas, movimientos, deudas, auth, historial
from routes.finanzas import finanzas_bp
from routes.emprendimiento import emprendimiento_bp

app.register_blueprint(home.bp)
app.register_blueprint(cuentas.bp)
app.register_blueprint(movimientos.bp)
app.register_blueprint(deudas.bp)
app.register_blueprint(auth.auth_bp)
app.register_blueprint(finanzas_bp)
app.register_blueprint(emprendimiento_bp)
app.register_blueprint(historial.bp)

# --- INICIALIZAR DB (crea tablas si no existen) ---
with app.app_context():
    init_db()

# --- RUN LOCAL ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
