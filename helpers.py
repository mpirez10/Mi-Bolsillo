import datetime

def normalizar_fecha(fecha_str):
    if not fecha_str:
        raise ValueError("La fecha no puede estar vacía.")

    # 1. Si viene del calendario (formato AAAA-MM-DD)
    if '-' in fecha_str:
        try:
            partes = fecha_str.split('-')
            # Retornamos DD/MM/YY (tomamos los últimos 2 del año)
            return f"{partes[2]}/{partes[1]}/{partes[0][2:]}"
        except:
            raise ValueError("Error en formato de calendario.")

    # 2. Si viene manual (6 dígitos DDMMYY)
    solo_numeros = ''.join(ch for ch in str(fecha_str) if ch.isdigit())
    if len(solo_numeros) == 6:
        dia = int(solo_numeros[0:2])
        mes = int(solo_numeros[2:4])
        anio_corto = int(solo_numeros[4:6])
        anio_full = anio_corto + (2000 if anio_corto <= 50 else 1900)
        
        try:
            datetime.date(anio_full, mes, dia)
            return f"{solo_numeros[0:2]}/{solo_numeros[2:4]}/{solo_numeros[4:6]}"
        except ValueError:
            raise ValueError("Fecha inválida.")
    
    raise ValueError("Formato de fecha no reconocido.")
