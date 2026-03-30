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
        cursor = conn.cursor()

        # Verificamos si ya existe
        cursor.execute(
            "SELECT id FROM cuentas WHERE nombre = %s AND usuario_id = %s",
            (nombre, current_user.id)
        )
        existe = cursor.fetchone()

        if existe:
            return "Error: Ya tenés una cuenta con ese nombre."

        try:
            cursor.execute("""
                INSERT INTO cuentas (nombre, saldo, usuario_id) 
                VALUES (%s, %s, %s)
            """, (nombre, 0, current_user.id))

            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"Error al crear la cuenta: {e}"

        cursor.close()
        conn.close()

        return redirect(url_for('home.index'))
    
    return render_template("agregar_cuenta.html")


@bp.route('/eliminar_cuenta/<int:id>')
@login_required
def eliminar_cuenta(id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT nombre FROM cuentas WHERE id=%s AND usuario_id=%s", 
        (id, current_user.id)
    )
    cuenta = cursor.fetchone()
    
    if cuenta:
        nombre_cuenta = cuenta[0]  # PostgreSQL devuelve tupla
        
        try:
            cursor.execute("""
                UPDATE movimientos 
                SET cuenta_origen = 'ELIMINADA (' || %s || ')',
                    cuenta_destino = CASE 
                        WHEN cuenta_destino = %s THEN 'ELIMINADA' 
                        ELSE cuenta_destino 
                    END
                WHERE (cuenta_origen = %s OR cuenta_destino = %s) 
                AND usuario_id = %s
            """, (nombre_cuenta, nombre_cuenta, nombre_cuenta, nombre_cuenta, current_user.id))
            
            cursor.execute(
                "DELETE FROM cuentas WHERE id=%s AND usuario_id=%s", 
                (id, current_user.id)
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"Error al eliminar la cuenta: {e}"

    cursor.close()
    conn.close()

    return redirect(url_for('home.index'))
