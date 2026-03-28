import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user 
from db import get_db 

emprendimiento_bp = Blueprint('emprendimiento', __name__)

# --- PÁGINA INICIAL ---
@emprendimiento_bp.route('/emprendimiento')
@login_required
def emprendimiento_home():
    conn = get_db()
    emprendimientos = conn.execute(
        "SELECT id, nombre FROM emprendimientos WHERE usuario_id = ?", 
        (current_user.id,)
    ).fetchall()
    return render_template('emprendimiento/lista.html', emprendimientos=emprendimientos)


# --- CREAR EMPRENDIMIENTO ---
@emprendimiento_bp.route('/emprendimiento/crear', methods=['GET','POST'])
@login_required
def crear_emprendimiento():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()

        if not nombre:
            return "Nombre inválido"

        conn = get_db()
        conn.execute(
            "INSERT INTO emprendimientos (nombre, usuario_id) VALUES (?, ?)", 
            (nombre, current_user.id)
        )
        conn.commit()
        return redirect(url_for('emprendimiento.emprendimiento_home'))

    return render_template('emprendimiento/crear.html')


# --- RESUMEN ---
@emprendimiento_bp.route('/emprendimiento/resumen/<int:eid>', methods=['GET','POST'])
@login_required
def resumen(eid):
    conn = get_db()
    
    res = conn.execute(
        "SELECT nombre FROM emprendimientos WHERE id=? AND usuario_id=?", 
        (eid, current_user.id)
    ).fetchone()
    
    if not res:
        return "Emprendimiento no encontrado o no tiene permiso."

    # --- PROCESAR MOVIMIENTO ---
    if request.method == 'POST' and 'concepto' in request.form:
        fecha = request.form.get('fecha')
        concepto = request.form.get('concepto')
        detalle_mov = request.form.get('detalle', '')

        try:
            monto = float(request.form.get('monto', 0))
            if monto <= 0:
                return "Monto inválido"
        except:
            return "Monto inválido"

        producto_id = request.form.get('producto_id')
        if producto_id == "":
            producto_id = None

        try:
            conn.execute("""
                INSERT INTO movimientos_emprendimiento 
                (emprendimiento_id, fecha, concepto, detalle, monto, usuario_id, producto_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (eid, fecha, concepto, detalle_mov, monto, current_user.id, producto_id))

            if concepto == "INGRESO":
                conn.execute("""
                    INSERT INTO ventas (producto_id, fecha, cantidad, precio_total, usuario_id) 
                    VALUES (?, ?, 1, ?, ?)
                """, (producto_id, fecha, monto, current_user.id))
                
                if producto_id:
                    stock_actual = conn.execute(
                        "SELECT stock FROM productos WHERE id=? AND usuario_id=?",
                        (producto_id, current_user.id)
                    ).fetchone()

                    if not stock_actual or stock_actual['stock'] <= 0:
                        conn.rollback()
                        return "Sin stock disponible"

                    conn.execute("""
                        UPDATE productos 
                        SET stock = stock - 1 
                        WHERE id=? AND usuario_id=? AND stock > 0
                    """, (producto_id, current_user.id))

            elif concepto == "EGRESO":
                conn.execute("""
                    INSERT INTO gastos (emprendimiento_id, fecha, concepto, monto, usuario_id) 
                    VALUES (?, ?, ?, ?, ?)
                """, (eid, fecha, detalle_mov, monto, current_user.id))

            conn.commit()

        except Exception as e:
            conn.rollback()
            return f"Error: {e}"

        return redirect(url_for('emprendimiento.resumen', eid=eid))

    # --- DATOS ---
    productos_lista = conn.execute("""
        SELECT id, nombre, detalle, talle, stock 
        FROM productos
        WHERE emprendimiento_id=? AND usuario_id=? AND stock > 0 
    """, (eid, current_user.id)).fetchall()

    ingresos = conn.execute("""
        SELECT SUM(monto) FROM movimientos_emprendimiento 
        WHERE emprendimiento_id=? AND usuario_id=? AND concepto='INGRESO'
    """, (eid, current_user.id)).fetchone()[0] or 0

    gastos = conn.execute("""
        SELECT SUM(monto) FROM movimientos_emprendimiento 
        WHERE emprendimiento_id=? AND usuario_id=? AND concepto='EGRESO'
    """, (eid, current_user.id)).fetchone()[0] or 0
    
    movimientos = conn.execute("""
        SELECT 
            m.id, m.fecha, m.concepto, m.detalle, m.monto,
            p.nombre AS nombre_producto, p.talle AS talle_producto
        FROM movimientos_emprendimiento m
        LEFT JOIN productos p ON m.producto_id = p.id
        WHERE m.emprendimiento_id=? AND m.usuario_id=? 
        ORDER BY m.fecha DESC, m.id DESC LIMIT 15
    """, (eid, current_user.id)).fetchall()

    datos_grafica = conn.execute("""
        SELECT fecha, SUM(monto) as total 
        FROM movimientos_emprendimiento 
        WHERE emprendimiento_id=? AND usuario_id=? AND concepto='INGRESO'
        GROUP BY fecha ORDER BY fecha ASC
    """, (eid, current_user.id)).fetchall()

    labels_ingresos = [row['fecha'] for row in datos_grafica]
    valores_ingresos = [float(row['total']) for row in datos_grafica]
    
    return render_template(
        'emprendimiento/resumen.html', 
        nombre=res['nombre'], 
        eid=eid, 
        saldo=ingresos - gastos, 
        ingresos=ingresos, 
        gastos=gastos, 
        movimientos=movimientos,
        labels_ingresos=labels_ingresos, 
        valores_ingresos=valores_ingresos,
        productos_lista=productos_lista
    )


# --- STOCK ---
@emprendimiento_bp.route('/emprendimiento/stock/<int:eid>', methods=['GET','POST'])
@login_required
def stock(eid):
    conn = get_db()

    res = conn.execute(
        "SELECT nombre FROM emprendimientos WHERE id=? AND usuario_id=?", 
        (eid, current_user.id)
    ).fetchone()
    
    if not res:
        return "Acceso denegado."

    if request.method == 'POST' and 'nombre_prod' in request.form:
        nombre = request.form.get('nombre_prod', '').strip()

        if not nombre:
            return "Nombre inválido"

        try:
            precio = float(request.form.get('precio_prod', 0))
            stock_val = int(request.form.get('stock_prod', 0))
        except:
            return "Datos inválidos"

        conn.execute("""
            INSERT INTO productos 
            (emprendimiento_id, nombre, detalle, talle, precio, stock, usuario_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            eid, 
            nombre, 
            request.form.get('detalle_prod', ''), 
            request.form.get('talle_prod', ''), 
            precio, 
            stock_val, 
            current_user.id
        ))

        conn.commit()

    productos = conn.execute("""
        SELECT * FROM productos 
        WHERE emprendimiento_id=? AND usuario_id=? 
        ORDER BY stock DESC
    """, (eid, current_user.id)).fetchall()

    return render_template(
        'emprendimiento/stock.html', 
        nombre=res['nombre'], 
        eid=eid, 
        productos=productos
    )


# --- ELIM@emprendimiento_bp.route('/emprendimiento/eliminar_producto/<int:pid>/<int:eid>')
@emprendimiento_bp.route('/emprendimiento/eliminar_producto/<int:pid>/<int:eid>')
@login_required
def eliminar_producto(pid, eid):
    conn = get_db()

    try:
        # 1. Desvincular producto de movimientos
        conn.execute("""
            UPDATE movimientos_emprendimiento 
            SET producto_id = NULL 
            WHERE producto_id = ? AND usuario_id = ?
        """, (pid, current_user.id))

        # 2. Desvincular ventas
        conn.execute("""
            DELETE FROM ventas 
            WHERE producto_id = ? AND usuario_id = ?
        """, (pid, current_user.id))

        # 3. Ahora sí eliminar producto
        conn.execute("""
            DELETE FROM productos 
            WHERE id=? AND usuario_id=?
        """, (pid, current_user.id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return f"Error al eliminar: {e}"

    finally:
        conn.close()

    return redirect(url_for('emprendimiento.stock', eid=eid))

# --- ACTUALIZAR STOCK ---
@emprendimiento_bp.route('/emprendimiento/actualizar_stock/<int:pid>', methods=['POST'])
@login_required
def actualizar_stock(pid):
    data = request.get_json()
    nuevo_stock = data.get('nuevo_stock')
    
    if nuevo_stock is None or nuevo_stock < 0:
        return jsonify({"status": "error", "message": "Stock inválido"}), 400

    conn = get_db()
    conn.execute(
        "UPDATE productos SET stock = ? WHERE id=? AND usuario_id=?", 
        (nuevo_stock, pid, current_user.id)
    )
    conn.commit()
    
    return jsonify({"status": "success", "nuevo_stock": nuevo_stock})


# --- ACTUALIZAR PRECIO ---
@emprendimiento_bp.route('/emprendimiento/actualizar_precio/<int:pid>', methods=['POST'])
@login_required
def actualizar_precio(pid):
    data = request.get_json()
    nuevo_precio = data.get('nuevo_precio')
    
    if nuevo_precio is None or nuevo_precio < 0:
        return jsonify({"status": "error", "message": "Precio inválido"}), 400

    conn = get_db()
    conn.execute(
        "UPDATE productos SET precio = ? WHERE id=? AND usuario_id=?", 
        (nuevo_precio, pid, current_user.id)
    )
    conn.commit()
    
    return jsonify({"status": "success", "nuevo_precio": nuevo_precio})

@emprendimiento_bp.route('/emprendimiento/editar_producto/<int:pid>/<int:eid>', methods=['POST'])
@login_required
def editar_producto(pid, eid):
    conn = get_db()

    nombre = request.form.get('nombre')
    detalle = request.form.get('detalle')
    talle = request.form.get('talle')
    precio = float(request.form.get('precio', 0))
    stock = int(request.form.get('stock', 0))

    conn.execute("""
        UPDATE productos 
        SET nombre=?, detalle=?, talle=?, precio=?, stock=? 
        WHERE id=? AND usuario_id=?
    """, (nombre, detalle, talle, precio, stock, pid, current_user.id))

    conn.commit()
    conn.close()

    return redirect(url_for('emprendimiento.stock', eid=eid))

@emprendimiento_bp.route('/emprendimiento/eliminar_movimiento/<int:mid>/<int:eid>')
@login_required
def eliminar_movimiento(mid, eid):
    conn = get_db()

    try:
        # 1. Verificar que el movimiento existe y es del usuario
        mov = conn.execute("""
            SELECT * FROM movimientos_emprendimiento 
            WHERE id = ? AND usuario_id = ?
        """, (mid, current_user.id)).fetchone()

        if not mov:
            conn.close()
            return "Error: Movimiento no encontrado o no tenés permiso."

        # 2. Si es ingreso (venta), revertir stock
        if mov['concepto'] == 'INGRESO' and mov['producto_id']:
            conn.execute("""
                UPDATE productos 
                SET stock = stock + 1 
                WHERE id = ? AND usuario_id = ?
            """, (mov['producto_id'], current_user.id))

        # 3. Eliminar el movimiento
        conn.execute("""
            DELETE FROM movimientos_emprendimiento 
            WHERE id = ? AND usuario_id = ?
        """, (mid, current_user.id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        return f"Error al eliminar movimiento: {e}"

    finally:
        conn.close()

    return redirect(url_for('emprendimiento.resumen', eid=eid))