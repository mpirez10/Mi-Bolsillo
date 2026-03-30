import os
import sys

def get_db():
    database_url = os.getenv("DATABASE_URL")

    # 🔥 PRODUCCIÓN (Render con Postgres)
    if database_url:
        import psycopg2
        conn = psycopg2.connect(database_url)
        return conn

    # 💻 LOCAL (tu PC con SQLite)
    else:
        import sqlite3

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        db_path = os.path.join(base_dir, "finanzas.db")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # 🔥 activar claves foráneas
        conn.execute("PRAGMA foreign_keys = ON")

        return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre_completo TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            fecha_nacimiento DATE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            saldo REAL NOT NULL DEFAULT 0,
            usuario_id INTEGER REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY,
            fecha DATE,
            tipo TEXT,
            monto REAL,
            cuenta_origen TEXT,
            cuenta_destino TEXT,
            motivo TEXT,
            usuario_id INTEGER REFERENCES usuarios(id)
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
            usuario_id INTEGER REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emprendimientos (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            tabla_stock TEXT,
            usuario_id INTEGER REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            emprendimiento_id INTEGER REFERENCES emprendimientos(id),
            nombre TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            precio_costo REAL DEFAULT 0,
            precio_venta REAL DEFAULT 0,
            usuario_id INTEGER REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_emprendimiento (
            id SERIAL PRIMARY KEY,
            emprendimiento_id INTEGER REFERENCES emprendimientos(id),
            fecha DATE,
            concepto TEXT,
            detalle TEXT,
            monto REAL,
            usuario_id INTEGER REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER REFERENCES productos(id),
            fecha DATE,
            cantidad INTEGER,
            precio_total REAL,
            usuario_id INTEGER REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY,
            emprendimiento_id INTEGER REFERENCES emprendimientos(id),
            fecha DATE,
            concepto TEXT,
            monto REAL,
            usuario_id INTEGER REFERENCES usuarios(id)
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
