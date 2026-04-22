from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.models import Movimiento  # Ajustá esto a tu importación real
from sqlalchemy import or_, and_
from datetime import datetime

historial_bp = Blueprint('historial', __name__)

@historial_bp.route('/historial')
@login_required
def historial():
    # 1. Parámetros de búsqueda y filtros
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    tipo = request.args.get('tipo', 'TODOS')
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')
    
    per_page = 15  # Más items por página que en el index
    
    # 2. Consulta base (solo lo que pertenece al usuario)
    query = Movimiento.query.filter_by(user_id=current_user.id)

    # 3. Aplicar Filtros (Lógica de Ingeniería)
    filtros_activos = []
    
    if q:
        query = query.filter(or_(
            Movimiento.detalle.ilike(f'%{q}%'),
            Movimiento.cuenta_origen.ilike(f'%{q}%'),
            Movimiento.motivo.ilike(f'%{q}%')
        ))
    
    if tipo != 'TODOS':
        query = query.filter(Movimiento.tipo == tipo)
        
    if desde and hasta:
        f_desde = datetime.strptime(desde, '%Y-%m-%d')
        f_hasta = datetime.strptime(hasta, '%Y-%m-%d')
        query = query.filter(Movimiento.fecha.between(f_desde, f_hasta))

    # 4. Cálculo del total filtrado antes de paginar
    suma_total_filtrada = sum(m.monto for m in query.all())

    # 5. Paginación
    movimientos_paginados = query.order_by(Movimiento.fecha.desc()).paginate(page=page, per_page=per_page)

    return render_template('historial.html', 
                           movimientos=movimientos_paginados.items,
                           hay_mas_viejos=movimientos_paginados.has_next,
                           page=page,
                           suma_total_filtrada=suma_total_filtrada,
                           filtros={'q': q, 'tipo': tipo, 'desde': desde, 'hasta': hasta})
