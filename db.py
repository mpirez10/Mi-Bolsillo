import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise Exception("DATABASE_URL no está configurada")

    conn = psycopg2.connect(database_url)
    return conn


def get_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)


def init_db():
    conn = get_db()
    cursor = get_cursor(conn)

    # --- USUARIOS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre_completo TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            fecha_nacimiento TEXT,
            password TEXT NOT NULL
        )
    """)

    # --- CUENTAS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            saldo NUMERIC DEFAULT 0,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        )
    """)

    # --- MOVIMIENTOS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY,
            fecha TEXT,
            tipo TEXT,
            monto NUMERIC,
            cuenta_origen TEXT,
            cuenta_destino TEXT,
            motivo TEXT,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        )
    """)

    # --- DEUDAS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deudas (
            id SERIAL PRIMARY KEY,
            deudor TEXT,
            acreedor TEXT,
            monto NUMERIC,
            estado TEXT,
            motivo TEXT,
            fecha TEXT,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        )
    """)

    # --- EMPRENDIMIENTOS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emprendimientos (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        )
    """)

    # --- PRODUCTOS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            emprendimiento_id INTEGER REFERENCES emprendimientos(id) ON DELETE CASCADE,
            nombre TEXT,
            stock INTEGER DEFAULT 0,
            precio NUMERIC DEFAULT 0,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        )
    """)

    # --- MOVIMIENTOS EMPRENDIMIENTO ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_emprendimiento (
            id SERIAL PRIMARY KEY,
            emprendimiento_id INTEGER REFERENCES emprendimientos(id) ON DELETE CASCADE,
            fecha TEXT,
            concepto TEXT,
            detalle TEXT,
            monto NUMERIC,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE,
            producto_id INTEGER
        )
    """)

    # --- VENTAS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER REFERENCES productos(id) ON DELETE CASCADE,
            fecha TEXT,
            cantidad INTEGER,
            precio_total NUMERIC,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        )
    """)

    # --- GASTOS ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY,
            emprendimiento_id INTEGER REFERENCES emprendimientos(id) ON DELETE CASCADE,
            fecha TEXT,
            concepto TEXT,
            monto NUMERIC,
            usuario_id INTEGER REFERENCES usuarios(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
