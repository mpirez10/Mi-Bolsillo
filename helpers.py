import datetime

def normalizar_fecha(fecha_str):
    """
    Convierte un string de 6 dígitos (DDMMYY) en formato DD/MM/YY validando la fecha.
    Ejemplo: '290224' → '29/02/24'
    """

    if not fecha_str:
        raise ValueError("La fecha no puede estar vacía.")

    solo_numeros = ''.join(ch for ch in str(fecha_str) if ch.isdigit())

    if len(solo_numeros) != 6:
        raise ValueError("La fecha debe tener 6 dígitos (DDMMYY).")

    dia = int(solo_numeros[0:2])
    mes = int(solo_numeros[2:4])
    anio = int(solo_numeros[4:6])

    # Convertir YY a YYYY
    if anio <= 50:
        anio += 2000
    else:
        anio += 1900

    try:
        fecha = datetime.date(anio, mes, dia)
    except ValueError:
        raise ValueError("Fecha inválida (día o mes incorrecto).")

    return fecha.strftime("%d/%m/%y")