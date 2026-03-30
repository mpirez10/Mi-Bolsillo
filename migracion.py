import sqlite3
import psycopg2
import os

# Conexión a SQLite (tu archivo actual)
sqlite_conn = sqlite3.connect("finanzas.db")
sqlite_cursor = sqlite_conn.cursor()

# Conexión a PostgreSQL (Render)
DATABASE_URL = "postgresql://mi_bolsillo_db_user:I8m9xjK7EfVGuB1PJoVqlDomqlYjiTXM@dpg-d75bvjp5pdvs73b8mi30-a.oregon-postgres.render.com/mi_bolsillo_db"

pg_conn = psycopg2.connect(DATABASE_URL)
pg_cursor = pg_conn.cursor()

# Ejemplo: migrar tabla usuarios
sqlite_cursor.execute("SELECT * FROM usuarios")
rows = sqlite_cursor.fetchall()
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    nombre_completo TEXT,
    correo TEXT,
    fecha_nacimiento DATE,
    password TEXT
);
""")
pg_conn.commit()
for row in rows:

    pg_cursor.execute("""
        INSERT INTO usuarios (id, nombre_completo, correo, fecha_nacimiento, password)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
    """, row)

pg_conn.commit()

print("Migración completada 🚀")

sqlite_conn.close()
pg_conn.close()