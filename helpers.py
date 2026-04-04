import datetime

def normalizar_fecha(fecha_str):
    if not fecha_str:
        raise ValueError("La fecha no puede estar vacía.")

    # Limpiamos todo lo que no sea número
    solo_numeros = ''.join(ch for ch in str(fecha_str) if ch.isdigit())

    # CASO 1: Viene del calendario (AAAA-MM-DD -> 8 números: 20260404)
    if len(solo_numbers) == 8:
        anio = int(solo_numeros[0:4])
        mes = int(solo_numeros[4:6])
        dia = int(solo_numeros[6:8])
        # Guardamos solo los últimos 2 dígitos del año para tu formato DD/MM/YY
        anio_corto = str(anio)[2:]
    
    # CASO 2: Viene manual largo (DDMMYYYY -> 8 números: 04042026)
    # Nota: Si los primeros 4 dígitos no parecen un año (ej. 2026), 
    # asumimos que el año está al final.
    elif len(solo_numeros) == 8 and int(solo_numeros[0:4]) > 31: 
        # (Este elif es un refuerzo por si entra DDMMYYYY)
        dia = int(solo_numeros[0:2])
        mes = int(solo_numeros[2:4])
        anio = int(solo_numeros[4:8])
        anio_corto = str(anio)[2:]

    # CASO 3: Viene manual corto (DDMMYY -> 6 números: 040426)
    elif len(solo_numeros) == 6:
        dia = int(solo_numeros[0:2])
        mes = int(solo_numeros[2:4])
        anio_corto = solo_numeros[4:6]
        anio_int = int(anio_corto)
        anio = anio_int + (2000 if anio_int <= 50 else 1900)
    
    else:
        raise ValueError("Formato de fecha no reconocido. Usá DDMMYY o el calendario.")

    # VALIDACIÓN FINAL: Verificamos que la fecha sea real (ej. no 31/02)
    try:
        datetime.date(int(anio), mes, dia)
    except ValueError:
        raise ValueError("Fecha inexistente (día o mes incorrecto).")

    # Retornamos el string que vos querés para la DB
    return f"{dia:02d}/{mes:02d}/{anio_corto}"
