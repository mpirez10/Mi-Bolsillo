from flask import Blueprint, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from db import get_db
from helpers import normalizar_fecha

bp = Blueprint("deudas", __name__)

# --- LISTA DE DEUDAS ---
@bp.route("/deudas")
@login_required
def lista_deudas():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, deudor, acreedor, monto, estado, motivo, fecha 
        FROM deudas 
        WHERE usuario_id = %s 
        ORDER BY id DESC
    """, (current_user.id,))
    
    deudas = cursor.fetchall()

    cursor.execute(
        "SELECT nombre FROM cuentas WHERE usuario_id = %s",
        (current_user.id,)
    )
    cuentas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("deudas.html", deudas=deudas, cuentas=cuentas)


# --- NUEVA DEUDA ---
@bp.route("/deudas/nueva", methods=["GET", "POST"])
@login_required
def nueva_deuda():
    if request.method == "POST":
        deudor = request.form.get("deudor", "").upper()
        acreedor = request.form.get("acreedor", "").upper()
        monto_raw = request.form.get("monto", "0")
        motivo = request.form.get("motivo", "")
        fecha_cruda = request.form.get("fecha")

        if not deudor or not acreedor or not motivo or not fecha_cruda:
            return "Error: Faltan datos."

        try:
            monto = round(float(monto_raw.replace(',', '.').strip()), 2)
            if monto <= 0:
                return "Error: Monto inválido."
        except:
            return "Error: Monto inválido."

        try:
            fecha = normalizar_fecha(fecha_cruda)
        except ValueError:
            return "Error: Fecha inválida."

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO deudas (deudor, acreedor, monto, motivo, fecha, estado, usuario_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (deudor, acreedor, monto, motivo, fecha, 'pendiente', current_user.id))

            conn.commit()

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return f"Error al crear la deuda: {e}"

        cursor.close()
        conn.close()

        return redirect(url_for('deudas.lista_deudas'))

    return render_template("nueva_deuda.html")


# --- ELIMINAR DEUDA ---
@bp.route("/eliminar_deuda/<int:id>")
@login_required
def eliminar_deuda(id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM deudas WHERE id = %s AND usuario_id = %s",
            (id, current_user.id)
        )
        conn.commit()

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return f"Error al eliminar la deuda: {e}"

    cursor.close()
    conn.close()

    return redirect(url_for('deudas.lista_deudas'))


# --- PAGAR DEUDA ---
@bp.route("/deudas/pagar/<int:id>", methods=["POST"])
@login_required
def pagar_deuda(id):
    cuenta_nombre = request.form.get("cuenta_pago")

    if not cuenta_nombre:
        return "Error: Debes seleccionar una cuenta para pagar."

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, deudor, acreedor, monto, motivo 
        FROM deudas 
        WHERE id = %s AND usuario_id = %s
    """, (id, current_user.id))

    deuda = cursor.fetchone()

    if not deuda:
        cursor.close()
        conn.close()
        return redirect(url_for('deudas.lista_deudas'))

    monto = deuda[3]
    deudor = deuda[1]
    acreedor = deuda[2]
    motivo = deuda[4]

    soy_yo = deudor in ['YO', 'MAIKOL', 'MAIKOL PIREZ']
    tipo_mov = "Egreso" if soy_yo else "Ingreso"

    try:
        if soy_yo:
            cursor.execute(
                "UPDATE cuentas SET saldo = saldo - %s WHERE nombre = %s AND usuario_id = %s",
                (monto, cuenta_nombre, current_user.id)
            )
        else:
            cursor.execute(
                "UPDATE cuentas SET saldo = saldo + %s WHERE nombre = %s AND usuario_id = %s",
                (monto, cuenta_nombre, current_user.id)
            )

        motivo_historial = f"PAGO DEUDA: {motivo} ({acreedor if soy_yo else deudor})"

        cursor.execute("""
            INSERT INTO movimientos (tipo, monto, cuenta_origen, motivo, fecha, usuario_id) 
            VALUES (%s, %s, %s, %s, CURRENT_DATE, %s)
        """, (tipo_mov, monto, cuenta_nombre, motivo_historial, current_user.id))

        cursor.execute(
            "UPDATE deudas SET estado = %s WHERE id = %s AND usuario_id = %s",
            ('pagado', id, current_user.id)
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return f"Error al procesar el pago: {e}"

    cursor.close()
    conn.close()

    return redirect(url_for('deudas.lista_deudas'))
