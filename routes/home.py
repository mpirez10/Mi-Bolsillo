from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from db import get_db

bp = Blueprint("home", __name__)

@bp.route("/")
@login_required
def index():
    # 1. CAPTURAR FILTROS Y PAGINACIÓN
    busqueda = request.args.get('q', '').strip()
    tipo_filtro = request.args.get('tipo', '')
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')
    
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    conn = get_db()
    cursor = conn.cursor()

    # --- CUENTAS (Igual que antes) ---
    cursor.execute("SELECT id, nombre, saldo FROM cuentas WHERE usuario_id = %s", (current_user.id,))
    cuentas = cursor.fetchall()
    saldo_general = round(sum(c['saldo'] for c in cuentas), 2)

    # --- 2. MOTOR DE MOVIMIENTOS CON PAGINACIÓN INTELIGENTE ---
    query_base = " FROM movimientos WHERE usuario_id = %s"
    params_movs = [current_user.id]

    # Construimos las condiciones de filtro
    filtros_sql = ""
    if busqueda:
        filtros_sql += " AND (motivo ILIKE %s OR detalle ILIKE %s OR cuenta_origen ILIKE %s OR cuenta_destino ILIKE %s)"
        params_movs.extend([f"%{busqueda}%"] * 4)
    if tipo_filtro:
        filtros_sql += " AND UPPER(tipo) = %s"
        params_movs.append(tipo_filtro.upper())
    if desde:
        filtros_sql += " AND fecha >= %s"
        params_movs.append(desde)
    if hasta:
        filtros_sql += " AND fecha <= %s"
        params_movs.append(hasta)

    # Lógica de Paginación
    limit = 10
    offset = (page - 1) * limit
    
    # IMPORTANTE: Ahora el límite de 30 aplica SIEMPRE para no saturar, 
    # pero sobre el resultado YA filtrado.
    if page > 3:
        page = 3
        offset = 20

    # Ejecutamos la consulta con filtros + orden + paginación
    query_final = f"SELECT * {query_base} {filtros_sql} ORDER BY fecha DESC, id DESC LIMIT {limit} OFFSET {offset}"
    cursor.execute(query_final, params_movs)
    movimientos = cursor.fetchall()

    # Lógica de botones (hay más si trajo 10 y no estamos en la página 3)
    es_busqueda_activa = any([busqueda, tipo_filtro, desde, hasta])
    hay_mas_viejos = len(movimientos) == limit and page < 3

    # --- 3 y 4. DEUDAS Y TOTALES (Igual que antes) ---
    # ... (mantené el resto de tu código igual)

    # --- 3. DEUDAS ---
    cursor.execute("SELECT * FROM deudas WHERE usuario_id = %s AND estado = 'pendiente' ORDER BY id DESC LIMIT 5", (current_user.id,))
    deudas_list = cursor.fetchall()

    # --- 4. TOTALES ---
    def fetch_sum(query):
        cursor.execute(query, (current_user.id,))
        res = cursor.fetchone()
        return res['total'] if res and res['total'] else 0

    ingresos_total = fetch_sum("SELECT SUM(monto) AS total FROM movimientos WHERE usuario_id = %s AND LOWER(tipo) = 'ingreso'")
    egresos_total = fetch_sum("SELECT SUM(monto) AS total FROM movimientos WHERE usuario_id = %s AND LOWER(tipo) = 'egreso'")
    deudas_total = fetch_sum("SELECT SUM(monto) AS total FROM deudas WHERE usuario_id = %s AND estado = 'pendiente'")
    ganancia_mes = fetch_sum("SELECT SUM(precio_total) AS total FROM ventas WHERE usuario_id = %s")
    gasto_mes = fetch_sum("SELECT SUM(monto) AS total FROM gastos WHERE usuario_id = %s")

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
        gasto_mes=gasto_mes,
        filtros={'q': busqueda, 'tipo': tipo_filtro, 'desde': desde, 'hasta': hasta},
        page=page,
        hay_mas_viejos=hay_mas_viejos,
        es_busqueda_activa=es_busqueda_activa
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
        # Acceso directo por clave. Si es 'transferencia' usamos .get() por las dudas
        monto = movimiento['monto']
        tipo = movimiento['tipo'].lower()
        cuenta = movimiento['cuenta_origen']
        cuenta_destino = movimiento.get('cuenta_destino')

        if tipo == 'ingreso':
            cursor.execute("UPDATE cuentas SET saldo = saldo - %s WHERE nombre = %s AND usuario_id = %s", (monto, cuenta, current_user.id))
        elif tipo == 'egreso':
            cursor.execute("UPDATE cuentas SET saldo = saldo + %s WHERE nombre = %s AND usuario_id = %s", (monto, cuenta, current_user.id))
        elif tipo == 'transferencia':
            cursor.execute("UPDATE cuentas SET saldo = saldo + %s WHERE nombre = %s AND usuario_id = %s", (monto, cuenta, current_user.id))
            cursor.execute("UPDATE cuentas SET saldo = saldo - %s WHERE nombre = %s AND usuario_id = %s", (monto, cuenta_destino, current_user.id))

        cursor.execute("DELETE FROM movimientos WHERE id=%s", (mid,))
        conn.commit()

    cursor.close()
    conn.close()
    return redirect(url_for("home.index"))
