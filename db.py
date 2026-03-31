import os
import sys
import psycopg2
import psycopg2.extras

        conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)

        # Wrapper para simular conn.execute()
        class ConnWrapper:
            def __init__(self, conn):
                self.conn = conn

            def execute(self, query, params=()):
                cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # 🔥 Convertir ? → %s
                query = query.replace("?", "%s")

                cursor.execute(query, params)
                return cursor

            def commit(self):
                self.conn.commit()

            def rollback(self):
                self.conn.rollback()

            def close(self):
                self.conn.close()

            def cursor(self):
                return self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        return ConnWrapper(conn)

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


def init_db():
    conn = get_db()

    # ⚠️ Usamos conn.execute directamente (ya funciona en ambos)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nombre_completo TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            fecha_nacimiento TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id SERIAL PRIMARY KEY,
            nombre TEXT NOT NULL,
            saldo REAL NOT NULL DEFAULT 0,
            usuario_id INTEGER
        )
    """)

    conn.execute("""
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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS deudas (
            id SERIAL PRIMARY KEY,
            deudor TEXT,
            acreedor TEXT,
            monto REAL,
            estado TEXT,
            motivo TEXT,
            usuario_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS emprendimientos (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            usuario_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            emprendimiento_id INTEGER,
            nombre TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            precio REAL DEFAULT 0,
            usuario_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_emprendimiento (
            id SERIAL PRIMARY KEY,
            emprendimiento_id INTEGER,
            fecha TEXT,
            concepto TEXT,
            detalle TEXT,
            monto REAL,
            usuario_id INTEGER,
            producto_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER,
            fecha TEXT,
            cantidad INTEGER,
            precio_total REAL,
            usuario_id INTEGER
        )
    """)

    conn.execute("""
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
    conn.close()
