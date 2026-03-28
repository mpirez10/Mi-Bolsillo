from flask import Blueprint, render_template_string, request, redirect, url_for
from flask_login import login_required, current_user # <--- Seguridad
from db import get_db # <--- Conexión centralizada

finanzas_bp = Blueprint('finanzas', __name__)

@finanzas_bp.route('/finanzas')
@login_required # <--- Solo vos entrás
def home():
    conn = get_db()
    
    # Solo TUS datos en todas las tablas
    cuentas = conn.execute("SELECT * FROM cuentas WHERE usuario_id = ?", (current_user.id,)).fetchall()
    movimientos = conn.execute("SELECT * FROM movimientos WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 10", (current_user.id,)).fetchall()
    deudas = conn.execute("SELECT * FROM deudas WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 10", (current_user.id,)).fetchall()
    
    # Nota: Si usás una tabla aparte para deudores, acá la filtramos también
    try:
        deudores = conn.execute("SELECT * FROM deudores WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 10", (current_user.id,)).fetchall()
    except:
        deudores = [] # Por si todavía no creaste la tabla deudores independiente

    conn.close()

    # Mantenemos tu diseño original en string, pero filtrado
    return render_template_string("""
        <h1>Finanzas Personales - Panel de Control</h1>
        <p>Usuario: <strong>{{ current_user.nombre_completo }}</strong></p>

        <h2>Cuentas</h2>
        <table border="1">
            <tr><th>Nombre</th><th>Saldo</th><th>Acciones</th></tr>
            {% for c in cuentas %}
            <tr>
                <td>{{c['nombre']}}</td>
                <td>${{c['saldo']}}</td>
                <td>
                    <a href="/finanzas/eliminar_cuenta/{{c['id']}}" onclick="return confirm('¿Eliminar esta cuenta?')">ELIMINAR</a>
                </td>
            </tr>
            {% endfor %}
        </table>

        <h2>Últimos Movimientos</h2>
        <table border="1">
            <tr><th>Fecha</th><th>Tipo</th><th>Monto</th><th>Motivo</th><th>Acciones</th></tr>
            {% for m in movimientos %}
            <tr>
                <td>{{m['fecha']}}</td>
                <td>{{m['tipo']}}</td>
                <td>${{m['monto']}}</td>
                <td>{{m['motivo']}}</td>
                <td>
                    <a href="/finanzas/eliminar_movimiento/{{m['id']}}" onclick="return confirm('¿Eliminar este movimiento?')">ELIMINAR</a>
                </td>
            </tr>
            {% endfor %}
        </table>

        <h2>Deudas</h2>
        <table border="1">
            <tr><th>Persona</th><th>Monto</th><th>Estado</th><th>Acciones</th></tr>
            {% for d in deudas %}
            <tr>
                <td>{{d['acreedor'] if d['deudor'] in ['YO', 'MAIKOL'] else d['deudor']}}</td>
                <td>${{d['monto']}}</td>
                <td>{{d['estado']}}</td>
                <td>
                    <a href="/finanzas/eliminar_deuda/{{d['id']}}" onclick="return confirm('¿Eliminar esta deuda?')">ELIMINAR</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    """, cuentas=cuentas, movimientos=movimientos, deudas=deudas, deudores=deudores)

# Rutas de eliminación PROTEGIDAS (Solo borrás lo tuyo)
@finanzas_bp.route('/finanzas/eliminar_cuenta/<int:cid>')
@login_required
def eliminar_cuenta(cid):
    conn = get_db()
    conn.execute("DELETE FROM cuentas WHERE id=? AND usuario_id=?", (cid, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('finanzas.home'))

@finanzas_bp.route('/finanzas/eliminar_movimiento/<int:mid>')
@login_required
def eliminar_movimiento(mid):
    conn = get_db()
    conn.execute("DELETE FROM movimientos WHERE id=? AND usuario_id=?", (mid, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('finanzas.home'))

@finanzas_bp.route('/finanzas/eliminar_deuda/<int:did>')
@login_required
def eliminar_deuda(did):
    conn = get_db()
    conn.execute("DELETE FROM deudas WHERE id=? AND usuario_id=?", (did, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('finanzas.home'))