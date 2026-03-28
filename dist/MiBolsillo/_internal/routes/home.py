from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from db import get_db

bp = Blueprint("home", __name__)

@bp.route("/")
@login_required
def index():
    conn = get_db()
    
    # 1. Traemos SOLO tus cuentas y calculamos el Saldo General
    cuentas = conn.execute("SELECT id, nombre, saldo FROM cuentas WHERE usuario_id = ?", (current_user.id,)).fetchall()
    saldo_general = round(sum(c['saldo'] for c in cuentas), 2)
    
    # 2. Movimientos y deudas filtrados por tu usuario
    movimientos = conn.execute("""
        SELECT * FROM movimientos 
        WHERE usuario_id = ? 
        ORDER BY fecha DESC, id DESC
    """, (current_user.id,)).fetchall()
    
    deudas_list = conn.execute("""
        SELECT * FROM deudas 
        WHERE usuario_id = ? AND estado = 'pendiente' 
        ORDER BY id DESC LIMIT 5
    """, (current_user.id,)).fetchall()

    # --- 3. DATOS PARA LOS GRÁFICOS (Sincronización con JS) ---
    
    # Totales para el gráfico de Balance (Torta)
    # Usamos LOWER(tipo) para evitar problemas si escribiste 'Ingreso' o 'ingreso'
    res_ingresos = conn.execute("""
        SELECT SUM(monto) FROM movimientos 
        WHERE usuario_id = ? AND LOWER(tipo) = 'ingreso'
    """, (current_user.id,)).fetchone()
    ingresos_total = res_ingresos[0] if res_ingresos[0] else 0

    res_egresos = conn.execute("""
        SELECT SUM(monto) FROM movimientos 
        WHERE usuario_id = ? AND LOWER(tipo) = 'egreso'
    """, (current_user.id,)).fetchone()
    egresos_total = res_egresos[0] if res_egresos[0] else 0

    res_deudas = conn.execute("""
        SELECT SUM(monto) FROM deudas 
        WHERE usuario_id = ? AND estado = 'pendiente'
    """, (current_user.id,)).fetchone()
    deudas_total = res_deudas[0] if res_deudas[0] else 0

    # Estadísticas para el gráfico de Emprendimiento (Dashboard rápido)
    res_ganancia = conn.execute("SELECT SUM(precio_total) FROM ventas WHERE usuario_id = ?", (current_user.id,)).fetchone()
    ganancia_mes = res_ganancia[0] if res_ganancia[0] else 0
    
    res_gasto = conn.execute("SELECT SUM(monto) FROM gastos WHERE usuario_id = ?", (current_user.id,)).fetchone()
    gasto_mes = res_gasto[0] if res_gasto[0] else 0
    
    conn.close()

    return render_template("index.html", 
                           cuentas=cuentas, 
                           saldo_general=saldo_general,
                           movimientos=movimientos, 
                           deudas=deudas_list,
                           ingresos_total=ingresos_total,
                           egresos_total=egresos_total,
                           deudas_total=deudas_total,
                           ganancia_mes=ganancia_mes, 
                           gasto_mes=gasto_mes)


@bp.route("/eliminar_movimiento/<int:mid>")
@login_required
def eliminar_movimiento(mid):
    conn = get_db()
    
    # Verificamos que el movimiento sea tuyo antes de hacer nada
    movimiento = conn.execute("SELECT * FROM movimientos WHERE id=? AND usuario_id=?", (mid, current_user.id)).fetchone()
    
    if movimiento:
        monto = movimiento['monto']
        tipo = movimiento['tipo'].lower()
        cuenta = movimiento['cuenta_origen']
        
        if tipo == 'ingreso':
            conn.execute("UPDATE cuentas SET saldo = saldo - ? WHERE nombre = ? AND usuario_id = ?", (monto, cuenta, current_user.id))
        elif tipo == 'egreso':
            conn.execute("UPDATE cuentas SET saldo = saldo + ? WHERE nombre = ? AND usuario_id = ?", (monto, cuenta, current_user.id))
        elif tipo == 'transferencia':
            conn.execute("UPDATE cuentas SET saldo = saldo + ? WHERE nombre = ? AND usuario_id = ?", (monto, cuenta, current_user.id))
            conn.execute("UPDATE cuentas SET saldo = saldo - ? WHERE nombre = ? AND usuario_id = ?", (monto, movimiento['cuenta_destino'], current_user.id))
            
        conn.execute("DELETE FROM movimientos WHERE id=?", (mid,))
        conn.commit()
        
    conn.close()
    return redirect(url_for("home.index"))