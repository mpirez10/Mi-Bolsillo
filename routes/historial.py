from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from datetime import datetime
from db import get_db

bp = Blueprint('historial', __name__)

@bp.route('/historial')
@login_required
def ver_historial():
    # Parámetros de la URL (Paginación y Filtros)
    page = request.args.get('page', 1, type=int)
    per_page = 15
    offset = (page - 1) * per_page
    
    q = request.args.get('q', '')
    tipo = request.args.get('tipo', 'TODOS')
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')
    
    conn = get_db()
    cursor = conn.cursor()

    # 1. Construcción dinámica de la consulta SQL
    # Empezamos con la base: filtrar por el usuario actual
    query_base = "FROM movimientos WHERE usuario_id = %s"
    params = [current_user.id]

    if q:
        # Buscamos en detalle, motivo o cuenta_origen (usamos ILIKE para ignorar mayúsculas)
        query_base += " AND (motivo ILIKE %s OR cuenta_origen ILIKE %s OR cuenta_destino ILIKE %s)"
        search_q = f"%{q}%"
        params.extend([search_q, search_q, search_q])

    if tipo != 'TODOS':
        query_base += " AND tipo = %s"
        params.append(tipo)

    if desde and hasta:
        query_base += " AND fecha BETWEEN %s AND %s"
        params.extend([desde, hasta])

    try:
        # 2. Obtener la suma neta filtrada (Ingresos - Egresos)
        sql_suma = f"""
            SELECT 
                SUM(CASE WHEN tipo = 'Ingreso' THEN monto ELSE 0 END) - 
                SUM(CASE WHEN tipo = 'Egreso' THEN monto ELSE 0 END) as neto
            {query_base}
        """
        cursor.execute(sql_suma, params)
        res_suma = cursor.fetchone()
        
        # El nombre del campo en el resultado será 'neto' (o el índice 0)
        if isinstance(res_suma, dict):
            suma_total_filtrada = res_suma["neto"] or 0
        else:
            suma_total_filtrada = res_suma[0] or 0

        # 3. Obtener los movimientos paginados
        # Agregamos orden, límite y offset
        query_movimientos = f"SELECT * {query_base} ORDER BY fecha DESC LIMIT %s OFFSET %s"
        params_paginados = params + [per_page, offset]
        
        cursor.execute(query_movimientos, params_paginados)
        movimientos = cursor.fetchall()

        # 4. Verificar si hay más páginas (para el botón 'Ver más')
        cursor.execute(f"SELECT COUNT(*) {query_base}", params)
        res_count = cursor.fetchone()
        total_movs = res_count["count"] if isinstance(res_count, dict) else res_count[0]
        hay_mas_viejos = (offset + per_page) < total_movs

        return render_template('historial.html', 
                               movimientos=movimientos,
                               hay_mas_viejos=hay_mas_viejos,
                               page=page,
                               suma_total_filtrada=suma_total_filtrada,
                               filtros={'q': q, 'tipo': tipo, 'desde': desde, 'hasta': hasta})

    except Exception as e:
        print(f"Error en historial: {e}")
        return f"Error al cargar el historial: {e}"
    finally:
        cursor.close()
        conn.close()
