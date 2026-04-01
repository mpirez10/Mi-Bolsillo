from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from db import get_db

emprendimiento_bp = Blueprint('emprendimiento', __name__)

def _get_value(row, key, index=0):
    if row is None:
        return None
    try:
        return row[key]
    except Exception:
        try:
            return row[index]
        except Exception:
            return None

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

    nombre_emprendimiento = _get_value(res, "nombre", 0)

    # --- POST MOVIMIENTO ---
    if request.method == 'POST' and 'concepto' in request.form:
        fecha = request.form.get('fecha')
        concepto = request.form.get('concepto')
        detalle = request.form.get('detalle', '')

        try:
            monto = float(request.form.get('monto', 0))
            if monto <= 0:
                cursor.close()
                conn.close()
                return "Monto inválido"
        except:
            cursor.close()
            conn.close()
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
                    stock_row = cursor.fetchone()
                    stock_val = _get_value(stock_row, "stock", 0)

                    if stock_val is None or int(stock_val) <= 0:
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
        SELECT COALESCE(SUM(monto),0) AS total
        FROM movimientos_emprendimiento
        WHERE emprendimiento_id=%s AND usuario_id=%s AND concepto='INGRESO'
    """, (eid, current_user.id))
    ingresos_row = cursor.fetchone()
    ingresos = _get_value(ingresos_row, "total", 0) or 0

    cursor.execute("""
        SELECT COALESCE(SUM(monto),0) AS total
        FROM movimientos_emprendimiento
        WHERE emprendimiento_id=%s AND usuario_id=%s AND concepto='EGRESO'
    """, (eid, current_user.id))
    gastos_row = cursor.fetchone()
    gastos = _get_value(gastos_row, "total", 0) or 0

    cursor.execute("""
        SELECT id, fecha, concepto, detalle, monto, producto_id
        FROM movimientos_emprendimiento
        WHERE emprendimiento_id=%s AND usuario_id=%s
        ORDER BY fecha DESC, id DESC LIMIT 15
    """, (eid, current_user.id))
    movimientos = cursor.fetchall()

    # --- Preparar datos para gráficos (seguro: listas vacías si no hay datos) ---
    labels_ingresos = []
    data_ingresos = []
    labels_gastos = []
    data_gastos = []

    for m in movimientos:
        concepto_m = _get_value(m, "concepto", 2)
        fecha_m = _get_value(m, "fecha", 1) or ""
        monto_m = _get_value(m, "monto", 4) or 0

        try:
            monto_val = float(monto_m)
        except:
            monto_val = 0.0

        if concepto_m == "INGRESO":
            labels_ingresos.append(fecha_m)
            data_ingresos.append(monto_val)
        elif concepto_m == "EGRESO":
            labels_gastos.append(fecha_m)
            data_gastos.append(monto_val)

    cursor.close()
    conn.close()

    return render_template(
        'emprendimiento/resumen.html',
        nombre=nombre_emprendimiento,
        eid=eid,
        saldo=(float(ingresos) - float(gastos)),
        ingresos=ingresos,
        gastos=gastos,
        movimientos=movimientos,
        productos_lista=productos_lista,
        valores_ingresos=data_ingresos,
        etiquetas_ingresos=labels_ingresos,
        valores_gastos=data_gastos,
        etiquetas_gastos=labels_gastos,
        labels_ingresos=labels_ingresos,
        data_ingresos=data_ingresos,
        labels_gastos=labels_gastos,
        data_gastos=data_gastos
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

    nombre_empr = _get_value(res, "nombre", 0)

    if request.method == 'POST':
        nombre = request.form.get('nombre_prod', '').strip()

        if not nombre:
            cursor.close()
            conn.close()
            return "Nombre inválido"

        try:
            precio = float(request.form.get('precio_prod', 0))
        except:
            precio = 0.0

        try:
            stock_val = int(request.form.get('stock_prod', 0))
        except:
            stock_val = 0

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

    return render_template('emprendimiento/stock.html', nombre=nombre_empr, eid=eid, productos=productos)

@emprendimiento_bp.route('/emprendimiento/editar_producto/<int:pid>/<int:eid>', methods=['POST'])
@login_required
def editar_producto(pid, eid):
    conn = get_db()
    cursor = conn.cursor()

    nombre = request.form.get('nombre', '').strip()
    detalle = request.form.get('detalle', '')
    talle = request.form.get('talle', '')
    try:
        precio = float(request.form.get('precio', 0))
    except:
        precio = 0.0
    try:
        stock_val = int(request.form.get('stock', 0))
    except:
        stock_val = 0

    try:
        cursor.execute("""
            UPDATE productos
            SET nombre=%s, detalle=%s, talle=%s, precio=%s, stock=%s
            WHERE id=%s AND usuario_id=%s
        """, (nombre, detalle, talle, precio, stock_val, pid, current_user.id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return f"Error: {e}"

    cursor.close()
    conn.close()
    return redirect(url_for('emprendimiento.stock', eid=eid))


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
        "UPDATE productos SET precio=%s WHERE id=%s AND usuario_id=%s",
        (nuevo_precio, pid, current_user.id)
    )
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"ok": True})
