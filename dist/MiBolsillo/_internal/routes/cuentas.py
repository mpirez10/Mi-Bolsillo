from flask import Blueprint, request, render_template, redirect, url_for
from flask_login import login_required, current_user
from db import get_db

bp = Blueprint("cuentas", __name__)

@bp.route("/agregar_cuenta", methods=["GET","POST"])
@login_required
def agregar_cuenta():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip().upper()

        if not nombre:
            return "Error: El nombre de la cuenta no puede estar vacío."

        conn = get_db()

        # Verificamos si ya existe
        existe = conn.execute(
            "SELECT id FROM cuentas WHERE nombre = ? AND usuario_id = ?",
            (nombre, current_user.id)
        ).fetchone()

        if existe:
            return "Error: Ya tenés una cuenta con ese nombre."

        try:
            conn.execute("""
                INSERT INTO cuentas (nombre, saldo, usuario_id) 
                VALUES (?, ?, ?)
            """, (nombre, 0, current_user.id))

            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"Error al crear la cuenta: {e}"

        return redirect(url_for('home.index'))
    
    return render_template("agregar_cuenta.html")


@bp.route('/eliminar_cuenta/<int:id>')
@login_required
def eliminar_cuenta(id):
    conn = get_db()
    
    cuenta = conn.execute(
        "SELECT nombre FROM cuentas WHERE id=? AND usuario_id=?", 
        (id, current_user.id)
    ).fetchone()
    
    if cuenta:
        nombre_cuenta = cuenta['nombre']
        
        try:
            conn.execute("""
                UPDATE movimientos 
                SET cuenta_origen = 'ELIMINADA (' || ? || ')',
                    cuenta_destino = CASE 
                        WHEN cuenta_destino = ? THEN 'ELIMINADA' 
                        ELSE cuenta_destino 
                    END
                WHERE (cuenta_origen = ? OR cuenta_destino = ?) 
                AND usuario_id = ?
            """, (nombre_cuenta, nombre_cuenta, nombre_cuenta, nombre_cuenta, current_user.id))
            
            conn.execute(
                "DELETE FROM cuentas WHERE id=? AND usuario_id=?", 
                (id, current_user.id)
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"Error al eliminar la cuenta: {e}"

    return redirect(url_for('home.index'))