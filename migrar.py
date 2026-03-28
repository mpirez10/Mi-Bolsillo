import sqlite3

conn = sqlite3.connect("finanzas.db")
cursor = conn.cursor()

# 🔥 LIMPIAR SI YA EXISTEN (CLAVE)
cursor.execute("DROP TABLE IF EXISTS productos_new")
cursor.execute("DROP TABLE IF EXISTS movimientos_emprendimiento_new")

# Crear nuevas tablas
cursor.execute("""
CREATE TABLE productos_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emprendimiento_id INTEGER,
    nombre TEXT NOT NULL,
    detalle TEXT,
    talle TEXT,
    stock INTEGER DEFAULT 0,
    precio REAL DEFAULT 0,
    usuario_id INTEGER
)
""")

cursor.execute("""
CREATE TABLE movimientos_emprendimiento_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    emprendimiento_id INTEGER, 
    fecha TEXT, 
    concepto TEXT, 
    detalle TEXT, 
    monto REAL,
    usuario_id INTEGER,
    producto_id INTEGER
)
""")

# 🔥 IMPORTANTE: AJUSTAR SEGÚN TU DB REAL
cursor.execute("""
INSERT INTO productos_new (id, emprendimiento_id, nombre, stock, precio, usuario_id)
SELECT id, emprendimiento_id, nombre, stock, precio, usuario_id
FROM productos
""")

cursor.execute("""
INSERT INTO movimientos_emprendimiento_new 
(id, emprendimiento_id, fecha, concepto, detalle, monto, usuario_id)
SELECT id, emprendimiento_id, fecha, concepto, detalle, monto, usuario_id
FROM movimientos_emprendimiento
""")

# Borrar viejas
cursor.execute("DROP TABLE productos")
cursor.execute("DROP TABLE movimientos_emprendimiento")

# Renombrar
cursor.execute("ALTER TABLE productos_new RENAME TO productos")
cursor.execute("ALTER TABLE movimientos_emprendimiento_new RENAME TO movimientos_emprendimiento")

conn.commit()
conn.close()

print("✅ Migración completada con éxito")