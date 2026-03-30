from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from db import get_db

bp = Blueprint("home", __name__)

@bp.route("/")
@login_required
def index():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Cuentas
    cursor.execute(
        "SELECT id, nombre, saldo FROM cuentas WHERE usuario_id = %s",
        (current_user.id,)
    )
    cuentas = cursor.fetchall()

    saldo_general = round(sum(c[2] for c in cuentas), 2)

    # 2. Movimientos
    cursor.execute("""
        SELECT * FROM movimientos 
        WHERE usuario_id = %s 
        ORDER BY fecha DESC, id DESC
    """, (current_user.id,))
    movimientos = cursor.fetchall()

    # 3. Deudas
    cursor.execute("""
        SELECT * FROM deudas 
        WHERE usuario_id = %s AND estado = 'pendiente' 
        ORDER BY id DESC LIMIT 5
    """, (current_user.id,))
    deudas_list = cursor.fetchall()

    # --- 4. TOTALES ---
    cursor.execute("""
        SELECT SUM(monto) FROM movimientos 
        WHERE usuario_id = %s AND LOWER(tipo) = 'ingreso'
    """, (current_user.id,))
    ingresos_total = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT SUM(monto) FROM movimientos 
        WHERE usuario_id = %s AND LOWER(tipo) = 'egreso'
    """, (current_user.id,))
    egresos_total = cursor.fetchone()[0] or 0

    cursor.execute("""
        SELECT SUM(monto) FROM deudas 
        WHERE usuario_id = %s AND estado = 'pendiente'
    """, (current_user.id,))
    deudas_total = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT SUM(precio_total) FROM ventas WHERE usuario_id = %s",
        (current_user.id,)
    )
    ganancia_mes = cursor.fetchone()[0] or 0

    cursor.execute(
        "SELECT SUM(monto) FROM gastos WHERE usuario_id = %s",
        (current_user.id,)
    )
    gasto_mes = cursor.fetchone()[0] or 0

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
    
    # Verificar que el movimiento sea del usuario
    cursor.execute(
        "SELECT * FROM movimientos WHERE id=%s AND usuario_id=%s",
        (mid, current_user.id)
    )
    movimiento = cursor.fetchone()
    
    if movimiento:
        monto = movimiento[3]   # monto
        tipo = movimiento[2].lower()  # tipo
        cuenta = movimiento[4]  # cuenta_origen

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
                (monto, movimiento[5], current_user.id)  # cuenta_destino
            )

        cursor.execute(
            "DELETE FROM movimientos WHERE id=%s",
            (mid,)
        )

        conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("home.index"))
