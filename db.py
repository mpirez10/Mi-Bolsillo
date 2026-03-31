import os
import sys

def get_db():
    database_url = os.getenv("DATABASE_URL")

    # 🔥 PRODUCCIÓN (PostgreSQL - Render)
    if database_url:
        import psycopg2
        import psycopg2.extras

        conn = psycopg2.connect(database_url)
        return conn

    # 💻 LOCAL (SQLite)
    else:
        import sqlite3

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))

        db_path = os.path.join(base_dir, "finanzas.db")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")

        return conn


# 🔥 FUNCIÓN CLAVE: ejecuta queries compatible con ambos motores
def query_db(conn, query, params=(), fetchone=False, fetchall=False):
    cursor = conn.cursor()

    # 👉 Convertir ? → %s si es PostgreSQL
    if "psycopg2" in str(type(conn)):
        query = query.replace("?", "%s")

    cursor.execute(query, params)

    if fetchone:
        result = cursor.fetchone()
    elif fetchall:
        result = cursor.fetchall()
    else:
        result = None

    cursor.close()
    return result


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    is_postgres = "psycopg2" in str(type(conn))

    # 👉 Tipos distintos según motor
    ID_TYPE = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    TEXT_TYPE = "TEXT"
    REAL_TYPE = "REAL"
    DATE_TYPE = "DATE"

    # --- TABLAS ---
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS usuarios (
            id {ID_TYPE},
            nombre_completo {TEXT_TYPE} NOT NULL,
            correo {TEXT_TYPE} UNIQUE NOT NULL,
            fecha_nacimiento {DATE_TYPE} NOT NULL,
            password {TEXT_TYPE} NOT NULL
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS cuentas (
            id {ID_TYPE},
            nombre {TEXT_TYPE} NOT NULL,
            saldo {REAL_TYPE} NOT NULL DEFAULT 0,
            usuario_id INTEGER
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS movimientos (
            id {ID_TYPE},
            fecha {DATE_TYPE},
            tipo {TEXT_TYPE},
            monto {REAL_TYPE},
            cuenta_origen {TEXT_TYPE},
            cuenta_destino {TEXT_TYPE},
            motivo {TEXT_TYPE},
            usuario_id INTEGER
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS deudas (
            id {ID_TYPE},
            deudor {TEXT_TYPE},
            acreedor {TEXT_TYPE},
            monto {REAL_TYPE},
            estado {TEXT_TYPE},
            motivo {TEXT_TYPE},
            usuario_id INTEGER
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS emprendimientos (
            id {ID_TYPE},
            nombre {TEXT_TYPE},
            usuario_id INTEGER
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS productos (
            id {ID_TYPE},
            emprendimiento_id INTEGER,
            nombre {TEXT_TYPE} NOT NULL,
            stock INTEGER DEFAULT 0,
            precio REAL DEFAULT 0,
            usuario_id INTEGER
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS movimientos_emprendimiento (
            id {ID_TYPE},
            emprendimiento_id INTEGER,
            fecha {DATE_TYPE},
            concepto {TEXT_TYPE},
            detalle {TEXT_TYPE},
            monto {REAL_TYPE},
            usuario_id INTEGER,
            producto_id INTEGER
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS ventas (
            id {ID_TYPE},
            producto_id INTEGER,
            fecha {DATE_TYPE},
            cantidad INTEGER,
            precio_total {REAL_TYPE},
            usuario_id INTEGER
        )
    """)

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS gastos (
            id {ID_TYPE},
            emprendimiento_id INTEGER,
            fecha {DATE_TYPE},
            concepto {TEXT_TYPE},
            monto {REAL_TYPE},
            usuario_id INTEGER
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
