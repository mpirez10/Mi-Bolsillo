import os
import psycopg2
import psycopg2.extras

def get_db():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise Exception("DATABASE_URL no configurada")

    # Normalizar prefijo si Render entrega postgres://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(
        database_url,
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre_completo TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            fecha_nacimiento TEXT,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            saldo REAL DEFAULT 0,
            usuario_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY,
            fecha TEXT,
            tipo TEXT,
            monto REAL,
            cuenta_origen TEXT,
            cuenta_destino TEXT,
            motivo TEXT,
            usuario_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deudas (
            id SERIAL PRIMARY KEY,
            deudor TEXT,
            acreedor TEXT,
            monto REAL,
            estado TEXT,
            motivo TEXT,
            fecha TEXT,
            usuario_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER,
            fecha TEXT,
            cantidad INTEGER,
            precio_total REAL,
            usuario_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY,
            emprendimiento_id INTEGER,
            fecha TEXT,
            concepto TEXT,
            monto REAL,
            usuario_id INTEGER
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
