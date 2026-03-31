from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from db import get_db

emprendimiento_bp = Blueprint('emprendimiento', __name__)

# --- HOME ---
@emprendimiento_bp.route('/emprendimiento')
@login_required
def emprendimiento_home():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, nombre FROM emprendimientos WHERE usuario_id = %s",
        (current_user.id,)
    )
    emprendimientos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('emprendimiento/lista.html', emprendimientos=emprendimientos)


# --- CREAR ---
@emprendimiento_bp.route('/emprendimiento/crear', methods=['GET','POST'])
@login_required
def crear_emprendimiento():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()

        if not nombre:
            return "Nombre inválido"

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO emprendimientos (nombre, usuario_id) VALUES (%s, %s)",
            (nombre, current_user.id)
        )
        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for('emprendimiento.emprendimiento_home'))

    return render_template('emprendimiento/crear.html')


# --- RESUMEN ---
@emprendimiento_bp.route('/emprendimiento/resumen/<int:eid>', methods=['GET','POST'])
@login_required
def resumen(eid):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT nombre FROM emprendimientos WHERE id=%s AND usuario_id=%s",
        (eid, current_user.id)
    )
    res = cursor.fetchone()

    if not res:
        cursor.close()
        conn.close()
        return "No autorizado"

    nombre_emprendimiento = res[0]

    # --- POST MOVIMIENTO ---
    if request.method == 'POST' and 'concepto' in request.form:
        fecha = request.form.get('fecha')
        concepto = request.form.get('concepto')
        detalle = request.form.get('detalle', '')

        try:
            monto = float(request.form.get('monto', 0))
            if monto <= 0:
                return "Monto inválido"
        except:
            return "Monto inválido"

        producto_id = request.form.get('producto_id') or None

        try:
            cursor.execute("""
                INSERT INTO movimientos_emprendimiento
                (emprendimiento_id, fecha, concepto, detalle, monto, usuario_id, producto_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (eid, fecha, concepto, detalle, monto, current_user.id, producto_id))

            if concepto == "INGRESO":
                cursor.execute("""
                    INSERT INTO ventas (producto_id, fecha, cantidad, precio_total, usuario_id)
                    VALUES (%s,%s,%s,%s,%s)
                """, (producto_id, fecha, 1, monto, current_user.id))

                if producto_id:
                    cursor.execute(
                        "SELECT stock FROM productos WHERE id=%s AND usuario_id=%s",
                        (producto_id, current_user.id)
                    )
                    stock = cursor.fetchone()

                    if not stock or stock[0] <= 0:
                        conn.rollback()
                        cursor.close()
                        conn.close()
                        return "Sin stock"

                    cursor.execute("""
                        UPDATE productos
                        SET stock = stock - 1
                        WHERE id=%s AND usuario_id=%s
                    """, (producto_id, current_user.id))

            elif concepto == "EGRESO":
                cursor.execute("""
                    INSERT INTO gastos (emprendimiento_id, fecha, concepto, monto, usuario_id)
                    VALUES (%s,%s,%s,%s,%s)
                """, (eid, fecha, detalle, monto, current_user.id))

            conn.commit()

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return f"Error: {e}"

        cursor.close()
        conn.close()
        return redirect(url_for('emprendimiento.resumen', eid=eid))

    # --- DATOS ---
    cursor.execute("""
        SELECT id, nombre, detalle, talle, stock
        FROM productos
        WHERE emprendimiento_id=%s AND usuario_id=%s AND stock > 0
    """, (eid, current_user.id))
    productos_lista = cursor.fetchall()

    cursor.execute("""
        SELECT COALESCE(SUM(monto),0)
        FROM movimientos_emprendimiento
        WHERE emprendimiento_id=%s AND usuario_id=%s AND concepto='INGRESO'
    """, (eid, current_user.id))
    ingresos = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COALESCE(SUM(monto),0)
        FROM movimientos_emprendimiento
        WHERE emprendimiento_id=%s AND usuario_id=%s AND concepto='EGRESO'
    """, (eid, current_user.id))
    gastos = cursor.fetchone()[0]

    cursor.execute("""
        SELECT id, fecha, concepto, detalle, monto, producto_id
        FROM movimientos_emprendimiento
        WHERE emprendimiento_id=%s AND usuario_id=%s
        ORDER BY fecha DESC, id DESC LIMIT 15
    """, (eid, current_user.id))
    movimientos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'emprendimiento/resumen.html',
        nombre=nombre_emprendimiento,
        eid=eid,
        saldo=ingresos - gastos,
        ingresos=ingresos,
        gastos=gastos,
        movimientos=movimientos,
        productos_lista=productos_lista
    )


# --- STOCK ---
@emprendimiento_bp.route('/emprendimiento/stock/<int:eid>', methods=['GET','POST'])
@login_required
def stock(eid):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT nombre FROM emprendimientos WHERE id=%s AND usuario_id=%s",
        (eid, current_user.id)
    )
    res = cursor.fetchone()

    if not res:
        cursor.close()
        conn.close()
        return "Acceso denegado"

    if request.method == 'POST':
        nombre = request.form.get('nombre_prod', '').strip()

        if not nombre:
            cursor.close()
            conn.close()
            return "Nombre inválido"

        precio = float(request.form.get('precio_prod', 0))
        stock_val = int(request.form.get('stock_prod', 0))

        cursor.execute("""
            INSERT INTO productos
            (emprendimiento_id, nombre, detalle, talle, precio, stock, usuario_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
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

    cursor.execute("""
        SELECT * FROM productos
        WHERE emprendimiento_id=%s AND usuario_id=%s
    """, (eid, current_user.id))
    productos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('emprendimiento/stock.html', nombre=res[0], eid=eid, productos=productos)


# --- ELIMINAR PRODUCTO ---
@emprendimiento_bp.route('/emprendimiento/eliminar_producto/<int:pid>/<int:eid>')
@login_required
def eliminar_producto(pid, eid):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM ventas WHERE producto_id=%s AND usuario_id=%s", (pid, current_user.id))
        cursor.execute("DELETE FROM productos WHERE id=%s AND usuario_id=%s", (pid, current_user.id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return f"Error: {e}"

    cursor.close()
    conn.close()

    return redirect(url_for('emprendimiento.stock', eid=eid))


# --- ACTUALIZAR STOCK ---
@emprendimiento_bp.route('/emprendimiento/actualizar_stock/<int:pid>', methods=['POST'])
@login_required
def actualizar_stock(pid):
    data = request.get_json()
    nuevo_stock = data.get('nuevo_stock')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE productos SET stock=%s WHERE id=%s AND usuario_id=%s",
        (nuevo_stock, pid, current_user.id)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"ok": True})


# --- ACTUALIZAR PRECIO ---
@emprendimiento_bp.route('/emprendimiento/actualizar_precio/<int:pid>', methods=['POST'])
@login_required
def actualizar_precio(pid):
    data = request.get_json()
    nuevo_precio = data.get('nuevo_precio')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE productos SET precio=%s WHERE id
