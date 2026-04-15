from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from db import get_db

bp = Blueprint("home", __name__)

@bp.route("/")
@login_required
def index():
    # 1. CAPTURAR FILTROS DE LA URL
    busqueda = request.args.get('q', '').strip()
    tipo_filtro = request.args.get('tipo', '')
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')

    conn = get_db()
    cursor = conn.cursor()

    # --- CUENTAS (Igual que antes) ---
    cursor.execute("SELECT id, nombre, saldo FROM cuentas WHERE usuario_id = %s", (current_user.id,))
    cuentas = cursor.fetchall()
    saldo_general = round(sum(c['saldo'] for c in cuentas), 2)

    # --- 2. MOVIMIENTOS FILTRABLES (El motor de la Opción 1) ---
    query_movs = "SELECT * FROM movimientos WHERE usuario_id = %s"
    params_movs = [current_user.id]

    if busqueda:
        query_movs += " AND (motivo ILIKE %s OR detalle ILIKE %s OR cuenta_origen ILIKE %s OR cuenta_destino ILIKE %s)"
        params_movs.extend([f"%{busqueda}%"] * 4)

    if tipo_filtro:
        query_movs += " AND UPPER(tipo) = %s"
        params_movs.append(tipo_filtro.upper())

    if desde:
        query_movs += " AND fecha >= %s"
        params_movs.append(desde)

    if hasta:
        query_movs += " AND fecha <= %s"
        params_movs.append(hasta)

    # Si NO hay filtros, clavamos el LIMIT 10. Si hay filtros, mostramos TODO lo que coincida.
    if not (busqueda or tipo_filtro or desde or hasta):
        query_movs += " ORDER BY fecha DESC, id DESC LIMIT 10"
    else:
        query_movs += " ORDER BY fecha DESC, id DESC"

    cursor.execute(query_movs, params_movs)
    movimientos = cursor.fetchall()

    # --- 3. DEUDAS (Igual) ---
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

    # Retornamos también el diccionario 'filtros' para que el HTML sepa qué mostrar en los inputs
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
        filtros={'q': busqueda, 'tipo': tipo_filtro, 'desde': desde, 'hasta': hasta}
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
