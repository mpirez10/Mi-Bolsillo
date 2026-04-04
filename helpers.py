import datetime

def normalizar_fecha(fecha_str):
    if not fecha_str:
        raise ValueError("La fecha no puede estar vacía.")

    # Limpiamos todo lo que no sea número
    solo_numeros = ''.join(ch for ch in str(fecha_str) if ch.isdigit())

    # CASO 1: Viene del calendario (AAAA-MM-DD -> 8 números: 20260404)
    if len(solo_numeros) == 8 and int(solo_numeros[0:4]) > 1900: 
        anio = int(solo_numeros[0:4])
        mes = int(solo_numeros[4:6])
        dia = int(solo_numeros[6:8])
        anio_corto = str(anio)[2:]
    
    # CASO 2: Viene manual largo (DDMMYYYY -> 04042026)
    elif len(solo_numeros) == 8:
        dia = int(solo_numeros[0:2])
        mes = int(solo_numeros[2:4])
        anio = int(solo_numeros[4:8])
        anio_corto = str(anio)[2:]

    # CASO 3: Viene manual corto (DDMMYY -> 040426)
    elif len(solo_numeros) == 6:
        dia = int(solo_numeros[0:2])
        mes = int(solo_numeros[2:4])
        anio_corto = solo_numeros[4:6]
        anio_int = int(anio_corto)
        anio = anio_int + (2000 if anio_int <= 50 else 1900)
    
    else:
        raise ValueError("Formato de fecha no reconocido.")

    # VALIDACIÓN FINAL
    try:
        datetime.date(int(anio), mes, dia)
    except ValueError:
        raise ValueError("Fecha inexistente.")

    return f"{dia:02d}/{mes:02d}/{anio_corto}"
