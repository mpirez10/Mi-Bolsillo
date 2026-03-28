from flask import Blueprint, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from db import get_db
from helpers import normalizar_fecha

bp = Blueprint("movimientos", __name__)

@bp.route("/movimiento", methods=["GET","POST"])
@login_required
def movimiento():
    conn = get_db()

    if request.method == "POST":
        tipo = request.form.get("tipo")
        monto_raw = request.form.get("monto", "0")
        cuenta_origen = request.form.get("cuenta_origen")
        cuenta_destino = request.form.get("cuenta_destino")
        motivo = request.form.get("motivo")
        fecha_cruda = request.form.get("fecha")

        # --- VALIDACIONES BÁSICAS ---
        if not tipo or not cuenta_origen or not motivo or not fecha_cruda:
            return "Error: Faltan datos obligatorios."

        try:
            monto = round(float(monto_raw.replace(',', '.').strip()), 2)
            if monto <= 0:
                return "Error: El monto debe ser mayor a 0."
        except ValueError:
            return "Error: Monto inválido."

        try:
            fecha = normalizar_fecha(fecha_cruda)
        except ValueError:
            return "Error: Fecha inválida. Use DDMMYY (6 números)."

        try:
            # --- VERIFICAR CUENTA ORIGEN ---
            cuenta = conn.execute(
                "SELECT saldo FROM cuentas WHERE nombre = ? AND usuario_id = ?",
                (cuenta_origen, current_user.id)
            ).fetchone()

            if not cuenta:
                return "Error: Cuenta origen no válida."

            # --- LÓGICA ---
            if tipo == "Ingreso":
                conn.execute(
                    "UPDATE cuentas SET saldo = saldo + ? WHERE nombre = ? AND usuario_id = ?", 
                    (monto, cuenta_origen, current_user.id)
                )

            elif tipo == "Egreso":
                if cuenta["saldo"] < monto:
                    return "Error: Saldo insuficiente."

                conn.execute(
                    "UPDATE cuentas SET saldo = saldo - ? WHERE nombre = ? AND usuario_id = ?", 
                    (monto, cuenta_origen, current_user.id)
                )

            elif tipo == "Transferencia":
                if not cuenta_destino:
                    return "Error: Falta cuenta destino."

                if cuenta_origen == cuenta_destino:
                    return "Error: La cuenta origen y destino no pueden ser iguales."

                cuenta_dest = conn.execute(
                    "SELECT * FROM cuentas WHERE nombre = ? AND usuario_id = ?",
                    (cuenta_destino, current_user.id)
                ).fetchone()

                if not cuenta_dest:
                    return "Error: Cuenta destino no válida."

                if cuenta["saldo"] < monto:
                    return "Error: Saldo insuficiente."

                conn.execute(
                    "UPDATE cuentas SET saldo = saldo - ? WHERE nombre = ? AND usuario_id = ?", 
                    (monto, cuenta_origen, current_user.id)
                )
                conn.execute(
                    "UPDATE cuentas SET saldo = saldo + ? WHERE nombre = ? AND usuario_id = ?", 
                    (monto, cuenta_destino, current_user.id)
                )

            # --- REGISTRO ---
            conn.execute("""
                INSERT INTO movimientos (tipo, monto, cuenta_origen, cuenta_destino, motivo, fecha, usuario_id) 
                VALUES (?,?,?,?,?,?,?)
            """, (tipo, monto, cuenta_origen, cuenta_destino, motivo, fecha, current_user.id))

            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"Error crítico al procesar el movimiento: {e}"

        return redirect(url_for('home.index'))

    cuentas = conn.execute(
        "SELECT nombre FROM cuentas WHERE usuario_id = ?", 
        (current_user.id,)
    ).fetchall()

    return render_template("movimiento.html", cuentas=cuentas)


@bp.route("/editar_fecha/<int:id>", methods=["GET", "POST"])
@login_required
def editar_fecha(id):
    conn = get_db()

    mov = conn.execute(
        "SELECT * FROM movimientos WHERE id = ? AND usuario_id = ?", 
        (id, current_user.id)
    ).fetchone()

    if not mov:
        return "Error: Movimiento no encontrado o no tenés permiso."

    if request.method == "POST":
        nueva_fecha_cruda = request.form.get("fecha")

        if not nueva_fecha_cruda:
            return "Error: Falta la fecha."

        try:
            nueva_fecha = normalizar_fecha(nueva_fecha_cruda)

            conn.execute(
                "UPDATE movimientos SET fecha = ? WHERE id = ? AND usuario_id = ?", 
                (nueva_fecha, id, current_user.id)
            )
            conn.commit()

            return redirect(url_for('home.index'))

        except ValueError:
            return "Error: Formato de fecha incorrecto. Usá DDMMYY."

    return render_template("editar_movimiento.html", mov=mov)