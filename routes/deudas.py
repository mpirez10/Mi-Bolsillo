from flask import Blueprint, request, render_template, redirect, url_for
from flask_login import login_required, current_user # <--- Seguridad
from db import get_db
from helpers import normalizar_fecha

bp = Blueprint("deudas", __name__)

@bp.route("/deudas")
@login_required # <--- Candado
def lista_deudas():
    conn = get_db()
    # Solo TUS deudas
    deudas = conn.execute("SELECT * FROM deudas WHERE usuario_id = ? ORDER BY id DESC", (current_user.id,)).fetchall()
    # Solo TUS cuentas para elegir con qué pagar
    cuentas = conn.execute("SELECT nombre FROM cuentas WHERE usuario_id = ?", (current_user.id,)).fetchall()
    conn.close()
    return render_template("deudas.html", deudas=deudas, cuentas=cuentas)

@bp.route("/deudas/nueva", methods=["GET", "POST"])
@login_required # <--- Candado
def nueva_deuda():
    if request.method == "POST":
        deudor = request.form["deudor"].upper()
        acreedor = request.form["acreedor"].upper()
        monto_raw = request.form.get("monto", "0")
        monto = round(float(monto_raw.replace(',', '.').strip()), 2)
        
        motivo = request.form["motivo"]
        fecha_cruda = request.form["fecha"]
        
        try:
            fecha = normalizar_fecha(fecha_cruda)
        except ValueError:
            return "Error: Fecha inválida."
        
        conn = get_db()
        # Guardamos la deuda vinculada a TU ID
        conn.execute("""
            INSERT INTO deudas (deudor, acreedor, monto, motivo, fecha, estado, usuario_id) 
            VALUES (?,?,?,?,?,?,?)
        """, (deudor, acreedor, monto, motivo, fecha, 'pendiente', current_user.id))
        conn.commit()
        conn.close()
        return redirect(url_for('deudas.lista_deudas'))
        
    return render_template("nueva_deuda.html")

@bp.route("/eliminar_deuda/<int:id>")
@login_required # <--- Candado
def eliminar_deuda(id):
    conn = get_db()
    # Solo podés borrar deudas que sean tuyas
    conn.execute("DELETE FROM deudas WHERE id = ? AND usuario_id = ?", (id, current_user.id))
    conn.commit()
    conn.close()
    return redirect(url_for('deudas.lista_deudas'))

@bp.route("/deudas/pagar/<int:id>", methods=["POST"])
@login_required # <--- Candado
def pagar_deuda(id):
    cuenta_nombre = request.form.get("cuenta_pago")
    if not cuenta_nombre:
        return "Error: Debes seleccionar una cuenta para pagar."

    conn = get_db()
    # 1. Buscamos la deuda asegurando que sea TUYA
    deuda = conn.execute("SELECT * FROM deudas WHERE id = ? AND usuario_id = ?", (id, current_user.id)).fetchone()

    if deuda:
        monto = deuda['monto']
        # Lógica para saber si sale o entra plata (ajustada a tus nombres habituales)
        soy_yo = (deuda['deudor'] in ['YO', 'MAIKOL', 'MAIKOL PIREZ'])
        tipo_mov = "Egreso" if soy_yo else "Ingreso"
        
        try:
            # A. Actualizamos el saldo de TU cuenta
            if soy_yo:
                conn.execute("UPDATE cuentas SET saldo = saldo - ? WHERE nombre = ? AND usuario_id = ?", 
                             (monto, cuenta_nombre, current_user.id))
            else:
                conn.execute("UPDATE cuentas SET saldo = saldo + ? WHERE nombre = ? AND usuario_id = ?", 
                             (monto, cuenta_nombre, current_user.id))
            
            # B. Registramos el movimiento en TU historial
            motivo_historial = f"PAGO DEUDA: {deuda['motivo']} ({deuda['acreedor'] if soy_yo else deuda['deudor']})"
            conn.execute("""
                INSERT INTO movimientos (tipo, monto, cuenta_origen, motivo, fecha, usuario_id) 
                VALUES (?, ?, ?, ?, date('now'), ?)
            """, (tipo_mov, monto, cuenta_nombre, motivo_historial, current_user.id))
            
            # C. Marcamos como pagada
            conn.execute("UPDATE deudas SET estado = 'pagado' WHERE id = ? AND usuario_id = ?", (id, current_user.id))
            
            conn.commit()
        except Exception as e:
            conn.rollback()
            return f"Error al procesar el pago: {e}"
        finally:
            conn.close()
            
    return redirect(url_for('deudas.lista_deudas'))