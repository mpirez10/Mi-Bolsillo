from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from .models import Movimiento, Cuenta, Deuda  # Ajustá según tus modelos
from . import db
from sqlalchemy import or_
from datetime import datetime

historial = Blueprint('historial', __name__)

@historial.route('/historial')
@login_required
def ver_historial():
    # Parámetros de la URL
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '')
    tipo = request.args.get('tipo', 'TODOS')
    desde = request.args.get('desde', '')
    hasta = request.args.get('hasta', '')
    
    # Consulta base
    query = Movimiento.query.filter_by(user_id=current_user.id)

    # Lógica de Filtros
    if q:
        query = query.filter(or_(
            Movimiento.detalle.ilike(f'%{q}%'),
            Movimiento.cuenta_origen.ilike(f'%{q}%'),
            Movimiento.motivo.ilike(f'%{q}%')
        ))
    
    if tipo != 'TODOS':
        query = query.filter(Movimiento.tipo == tipo)
        
    if desde and hasta:
        try:
            f_desde = datetime.strptime(desde, '%Y-%m-%d')
            f_hasta = datetime.strptime(hasta, '%Y-%m-%d')
            query = query.filter(Movimiento.fecha.between(f_desde, f_hasta))
        except ValueError:
            pass # Por si las fechas vienen en formato raro

    # Total filtrado para el badge del historial
    suma_total_filtrada = sum(m.monto for m in query.all())

    # Paginación (15 por página está bien para historial)
    movimientos_paginados = query.order_by(Movimiento.fecha.desc()).paginate(page=page, per_page=15)

    return render_template('historial.html', 
                           movimientos=movimientos_paginados.items,
                           hay_mas_viejos=movimientos_paginados.has_next,
                           page=page,
                           suma_total_filtrada=suma_total_filtrada,
                           filtros={'q': q, 'tipo': tipo, 'desde': desde, 'hasta': hasta})
