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
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cuentas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nombre TEXT NOT NULL, 
            saldo REAL NOT NULL DEFAULT 0,
            usuario_id INTEGER
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
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
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
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
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nombre TEXT, 
            tabla_stock TEXT,
            usuario_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emprendimiento_id INTEGER,
            nombre TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            precio_costo REAL DEFAULT 0,
            precio_venta REAL DEFAULT 0,
            usuario_id INTEGER,
            FOREIGN KEY (emprendimiento_id) REFERENCES emprendimientos(id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS movimientos_emprendimiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            emprendimiento_id INTEGER, 
            fecha TEXT, 
            concepto TEXT, 
            detalle TEXT, 
            monto REAL,
            usuario_id INTEGER
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            producto_id INTEGER, 
            fecha TEXT, 
            cantidad INTEGER, 
            precio_total REAL,
            usuario_id INTEGER,
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            emprendimiento_id INTEGER, 
            fecha TEXT, 
            concepto TEXT, 
            monto REAL,
            usuario_id INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre_completo TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            fecha_nacimiento TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()