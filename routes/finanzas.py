from flask import Blueprint, render_template_string, redirect, url_for
from flask_login import login_required, current_user
from db import get_db

finanzas_bp = Blueprint('finanzas', __name__)

# --- HOME ---
@finanzas_bp.route('/finanzas')
@login_required
def home():
    conn = get_db()
    cursor = conn.cursor()

    # Cuentas
    cursor.execute(
        "SELECT id, nombre, saldo FROM cuentas WHERE usuario_id = %s",
        (current_user.id,)
    )
    cuentas = cursor.fetchall()

    # Movimientos
    cursor.execute(
        "SELECT id, fecha, tipo, monto, motivo FROM movimientos WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 10",
        (current_user.id,)
    )
    movimientos = cursor.fetchall()

    # Deudas
    cursor.execute(
        "SELECT id, deudor, acreedor, monto, estado FROM deudas WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 10",
        (current_user.id,)
    )
    deudas = cursor.fetchall()

    # Deudores (opcional)
    try:
        cursor.execute(
            "SELECT * FROM deudores WHERE usuario_id = %s ORDER BY fecha DESC LIMIT 10",
            (current_user.id,)
        )
        deudores = cursor.fetchall()
    except:
        deudores = []

    cursor.close()
    conn.close()

    return render_template_string("""
        <h1>Finanzas Personales - Panel</h1>
        <p>Usuario: <strong>{{ current_user.nombre_completo }}</strong></p>

        <h2>Cuentas</h2>
        <table border="1">
            <tr><th>Nombre</th><th>Saldo</th><th>Acciones</th></tr>
            {% for c in cuentas %}
            <tr>
                <td>{{ c[1] }}</td>
                <td>${{ c[2] }}</td>
                <td>
                    <a href="/finanzas/eliminar_cuenta/{{ c[0] }}" onclick="return confirm('¿Eliminar?')">Eliminar</a>
                </td>
            </tr>
            {% endfor %}
        </table>

        <h2>Movimientos</h2>
        <table border="1">
            <tr><th>Fecha</th><th>Tipo</th><th>Monto</th><th>Motivo</th><th>Acciones</th></tr>
            {% for m in movimientos %}
            <tr>
                <td>{{ m[1] }}</td>
                <td>{{ m[2] }}</td>
                <td>${{ m[3] }}</td>
                <td>{{ m[4] }}</td>
                <td>
                    <a href="/finanzas/eliminar_movimiento/{{ m[0] }}" onclick="return confirm('¿Eliminar?')">Eliminar</a>
                </td>
            </tr>
            {% endfor %}
        </table>

        <h2>Deudas</h2>
        <table border="1">
            <tr><th>Persona</th><th>Monto</th><th>Estado</th><th>Acciones</th></tr>
            {% for d in deudas %}
            <tr>
                <td>
                    {{ d[2] if d[1] in ['YO', 'MAIKOL', 'MAIKOL PIREZ'] else d[1] }}
                </td>
                <td>${{ d[3] }}</td>
                <td>{{ d[4] }}</td>
                <td>
                    <a href="/finanzas/eliminar_deuda/{{ d[0] }}" onclick="return confirm('¿Eliminar?')">Eliminar</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    """, cuentas=cuentas, movimientos=movimientos, deudas=deudas, deudores=deudores)


# --- ELIMINAR CUENTA ---
@finanzas_bp.route('/finanzas/eliminar_cuenta/<int:cid>')
@login_required
def eliminar_cuenta(cid):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM cuentas WHERE id=%s AND usuario_id=%s",
        (cid, current_user.id)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('finanzas.home'))


# --- ELIMINAR MOVIMIENTO ---
@finanzas_bp.route('/finanzas/eliminar_movimiento/<int:mid>')
@login_required
def eliminar_movimiento(mid):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM movimientos WHERE id=%s AND usuario_id=%s",
        (mid, current_user.id)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('finanzas.home'))


# --- ELIMINAR DEUDA ---
@finanzas_bp.route('/finanzas/eliminar_deuda/<int:did>')
@login_required
def eliminar_deuda(did):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM deudas WHERE id=%s AND usuario_id=%s",
        (did, current_user.id)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('finanzas.home'))
