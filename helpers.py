import datetime

def normalizar_fecha(fecha_str):
    """
    Convierte un string de 6 dígitos (DDMMYY) en formato DD/MM/YY validando la fecha.
    Ejemplo: '290224' → '29/02/24'
    """
    if not fecha_str:
        raise ValueError("La fecha no puede estar vacía.")

    # Limpiamos el string por si viene con barras o espacios
    solo_numeros = ''.join(ch for ch in str(fecha_str) if ch.isdigit())

    if len(solo_numeros) != 6:
        raise ValueError("La fecha debe tener 6 dígitos (DDMMYY).")

    dia = int(solo_numeros[0:2])
    mes = int(solo_numeros[2:4])
    anio_corto = int(solo_numeros[4:6])

    # Convertir YY a YYYY solo para validar que la fecha existe (ej. bisiestos)
    if anio_corto <= 50:
        anio_full = anio_corto + 2000
    else:
        anio_full = anio_corto + 1900

    try:
        # Esto solo sirve para validar (si metés 31/02/24, acá salta el error)
        datetime.date(anio_full, mes, dia)
    except ValueError:
        raise ValueError("Fecha inválida (día o mes incorrecto).")

    # SI PASÓ LA VALIDACIÓN: Devolvemos el string con el formato que vos querés
    return f"{solo_numeros[0:2]}/{solo_numeros[2:4]}/{solo_numeros[4:6]}"
