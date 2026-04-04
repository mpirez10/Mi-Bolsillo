from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from db import get_db

bp = Blueprint("home", __name__)

@bp.route("/")
@login_required
def index():
    conn = get_db()
    cursor = conn.cursor()

    # --- 1. CUENTAS ---
    cursor.execute(
        "SELECT id, nombre, saldo FROM cuentas WHERE usuario_id = %s",
        (current_user.id,)
    )
    cuentas = cursor.fetchall()

    # 🔥 Compatible dict o tuple
    saldo_general = round(sum(
        (c['saldo'] if isinstance(c, dict) else c[2]) for c in cuentas
    ), 2)

    # --- 2. MOVIMIENTOS ---
    # Usamos TO_DATE si es PostgreSQL (Render usa ese por defecto)
    # Si usas SQLite cambiamos a DATE()
    cursor.execute("""
        SELECT * FROM movimientos 
        WHERE usuario_id = %s 
        ORDER BY TO_DATE(fecha, 'YYYY-MM-DD') DESC, id DESC
    """, (current_user.id,))
    movimientos = cursor.fetchall()
    # --- 3. DEUDAS ---
    cursor.execute("""
        SELECT * FROM deudas 
        WHERE usuario_id = %s AND estado = 'pendiente' 
        ORDER BY id DESC LIMIT 5
    """, (current_user.id,))
    deudas_list = cursor.fetchall()

    # --- 4. TOTALES (🔥 FIX KEYERROR) ---
    def get_value(row):
        if not row:
            return 0
        return row[0] if not isinstance(row, dict) else list(row.values())[0]

    cursor.execute("""
        SELECT SUM(monto) FROM movimientos 
        WHERE usuario_id = %s AND LOWER(tipo) = 'ingreso'
    """, (current_user.id,))
    ingresos_total = get_value(cursor.fetchone()) or 0

    cursor.execute("""
        SELECT SUM(monto) FROM movimientos 
        WHERE usuario_id = %s AND LOWER(tipo) = 'egreso'
    """, (current_user.id,))
    egresos_total = get_value(cursor.fetchone()) or 0

    cursor.execute("""
        SELECT SUM(monto) FROM deudas 
        WHERE usuario_id = %s AND estado = 'pendiente'
    """, (current_user.id,))
    deudas_total = get_value(cursor.fetchone()) or 0

    cursor.execute(
        "SELECT SUM(precio_total) FROM ventas WHERE usuario_id = %s",
        (current_user.id,)
    )
    ganancia_mes = get_value(cursor.fetchone()) or 0

    cursor.execute(
        "SELECT SUM(monto) FROM gastos WHERE usuario_id = %s",
        (current_user.id,)
    )
    gasto_mes = get_value(cursor.fetchone()) or 0

    cursor.close()
    conn.close()

    return render_template(
        "index.html", 
        cuentas=cuentas, 
        saldo_general=saldo_general,
        movimientos=movimientos, 
        deudas=deudas_list,
        ingresos_total=ingresos_total,
        egresos_total=egresos_total,
        deudas_total=deudas_total,
        ganancia_mes=ganancia_mes, 
        gasto_mes=gasto_mes
    )


@bp.route("/eliminar_movimiento/<int:mid>")
@login_required
def eliminar_movimiento(mid):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM movimientos WHERE id=%s AND usuario_id=%s",
        (mid, current_user.id)
    )
    movimiento = cursor.fetchone()

    if movimiento:
        # 🔥 Compatibilidad dict/tuple
        if isinstance(movimiento, dict):
            monto = movimiento['monto']
            tipo = movimiento['tipo'].lower()
            cuenta = movimiento['cuenta_origen']
            cuenta_destino = movimiento.get('cuenta_destino')
        else:
            monto = movimiento[3]
            tipo = movimiento[2].lower()
            cuenta = movimiento[4]
            cuenta_destino = movimiento[5]

        if tipo == 'ingreso':
            cursor.execute(
                "UPDATE cuentas SET saldo = saldo - %s WHERE nombre = %s AND usuario_id = %s",
                (monto, cuenta, current_user.id)
            )
        elif tipo == 'egreso':
            cursor.execute(
                "UPDATE cuentas SET saldo = saldo + %s WHERE nombre = %s AND usuario_id = %s",
                (monto, cuenta, current_user.id)
            )
        elif tipo == 'transferencia':
            cursor.execute(
                "UPDATE cuentas SET saldo = saldo + %s WHERE nombre = %s AND usuario_id = %s",
                (monto, cuenta, current_user.id)
            )
            cursor.execute(
                "UPDATE cuentas SET saldo = saldo - %s WHERE nombre = %s AND usuario_id = %s",
                (monto, cuenta_destino, current_user.id)
            )

        cursor.execute(
            "DELETE FROM movimientos WHERE id=%s",
            (mid,)
        )

        conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("home.index"))
