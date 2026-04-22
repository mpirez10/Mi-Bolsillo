from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db
from .models import Usuario  # Importación limpia desde el modelo

auth_bp = Blueprint("auth", __name__)

# --- REGISTRO ---
@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre_completo")
        correo = request.form.get("correo", "").lower().strip()
        fecha_nac = request.form.get("fecha_nacimiento")
        password = request.form.get("password")

        # Validaciones básicas
        if not nombre or not correo or not password:
            flash("Todos los campos obligatorios deben completarse.", "warning")
            return redirect(url_for('auth.registro'))

        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "warning")
            return redirect(url_for('auth.registro'))

        conn = get_db()
        cursor = conn.cursor()

        try:
            # Verificar si ya existe
            cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
            if cursor.fetchone():
                flash("Ese correo ya está registrado, bo.", "info")
                return redirect(url_for('auth.registro'))

            # Hashear y guardar
            password_hash = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO usuarios (nombre_completo, correo, fecha_nacimiento, password) 
                VALUES (%s, %s, %s, %s)
            """, (nombre, correo, fecha_nac, password_hash))

            conn.commit()
            flash("¡Cuenta creada! Ya podés entrar.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            conn.rollback()
            # Loguear el error real en consola, pero no mostrárselo crudo al usuario
            print(f"Error en registro: {e}") 
            flash("Hubo un problema al crear la cuenta. Intentá de nuevo.", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template("registro.html")


# --- LOGIN ---
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").lower().strip()
        password = request.form.get("password")

        if not correo or not password:
            flash("Completá todos los campos.", "warning")
            return redirect(url_for('auth.login'))

        # Usamos el método estático del modelo para buscar la data
        user_data = Usuario.get_by_email(correo)

        if user_data:
            # Manejo seguro de dict o tupla según tu config de DB
            try:
                pw_hash = user_data["password"]
                uid = user_data["id"]
                nom = user_data["nombre_completo"]
                f_nac = user_data["fecha_nacimiento"]
            except (KeyError, TypeError):
                uid, nom, _, f_nac, pw_hash = user_data

            if check_password_hash(pw_hash, password):
                usuario_obj = Usuario(uid, nom, correo, f_nac)
                login_user(usuario_obj)
                return redirect(url_for('home.index'))

        flash("Correo o contraseña incorrectos.", "danger")

    return render_template("login.html")


# --- LOGOUT ---
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


# --- PERFIL ---
@auth_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        nuevo_nombre = request.form.get("nombre_completo")
        nueva_fecha = request.form.get("fecha_nacimiento")
        nueva_pass = request.form.get("password")

        if not nuevo_nombre:
            flash("El nombre no puede estar vacío.", "danger")
            return redirect(url_for('auth.perfil'))

        try:
            # Actualizar datos básicos
            cursor.execute("""
                UPDATE usuarios 
                SET nombre_completo = %s, fecha_nacimiento = %s 
                WHERE id = %s
            """, (nuevo_nombre, nueva_fecha, current_user.id))

            # Si quiere cambiar la pass
            if nueva_pass and nueva_pass.strip():
                if len(nueva_pass) < 6:
                    flash("La contraseña nueva es muy corta (mínimo 6).", "warning")
                else:
                    hash_pw = generate_password_hash(nueva_pass)
                    cursor.execute("UPDATE usuarios SET password = %s WHERE id = %s", 
                                 (hash_pw, current_user.id))

            conn.commit()
            
            # Actualizamos el objeto en sesión para que los cambios se vean al toque
            current_user.nombre_completo = nuevo_nombre
            current_user.fecha_nacimiento = nueva_fecha

            flash("¡Perfil actualizado con éxito, bo!", "success")

        except Exception as e:
            conn.rollback()
            print(f"Error en update perfil: {e}")
            flash("Error al actualizar los datos.", "danger")
        finally:
            cursor.close()
            conn.close()
        
        return redirect(url_for('auth.perfil'))

    # Para el GET, usamos el current_user que ya tiene la data cargada
    return render_template("perfil.html", user=current_user)
