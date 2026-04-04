# helpers.py
import datetime

def normalizar_fecha(fecha_str):
    if not fecha_str:
        raise ValueError("La fecha no puede estar vacía.")

    # Limpiamos todo lo que no sea número
    solo_numeros = ''.join(ch for ch in str(fecha_str) if ch.isdigit())

    # Caso Calendario (AAAAMMDD -> 8 números)
    if len(solo_numeros) == 8 and int(solo_numeros[0:4]) > 1900:
        anio = solo_numeros[0:4]
        mes = solo_numeros[4:6]
        dia = solo_numeros[6:8]
        return f"{anio}-{mes}-{dia}" # Guardamos formato ISO para que SQL no se maree

    # Caso Manual (DDMMYY -> 6 números)
    elif len(solo_numeros) == 6:
        dia = solo_numeros[0:2]
        mes = solo_numeros[2:4]
        anio_corto = int(solo_numeros[4:6])
        anio = 2000 + anio_corto if anio_corto <= 50 else 1900 + anio_corto
        return f"{anio}-{mes}-{dia}"
    
    raise ValueError("Formato no reconocido.")
