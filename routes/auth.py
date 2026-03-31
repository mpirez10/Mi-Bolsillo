from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db

auth_bp = Blueprint("auth", __name__)

# --- REGISTRO ---
@auth_bp.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre_completo")
        correo = request.form.get("correo", "").lower().strip()
        fecha_nac = request.form.get("fecha_nacimiento")
        password = request.form.get("password")

        if not nombre or not correo or not password:
            flash("Todos los campos obligatorios deben completarse.")
            return redirect(url_for('auth.registro'))

        if len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.")
            return redirect(url_for('auth.registro'))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM usuarios WHERE correo = %s",
            (correo,)
        )
        existe = cursor.fetchone()

        if existe:
            cursor.close()
            conn.close()
            flash("Ese correo ya está registrado, bo.")
            return redirect(url_for('auth.registro'))

        password_hash = generate_password_hash(password)

        try:
            cursor.execute("""
                INSERT INTO usuarios (nombre_completo, correo, fecha_nacimiento, password) 
                VALUES (%s, %s, %s, %s)
            """, (nombre, correo, fecha_nac, password_hash))

            conn.commit()
            cursor.close()
            conn.close()

            flash("¡Cuenta creada! Ya podés entrar.", "success")
            return redirect(url_for('auth.login'))

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            flash(f"Error: {e}", "danger")

    return render_template("registro.html")


# --- LOGIN ---
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").lower().strip()
        password = request.form.get("password")

        if not correo or not password:
            flash("Completá todos los campos.")
            return redirect(url_for('auth.login'))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, nombre_completo, correo, fecha_nacimiento, password FROM usuarios WHERE correo = %s",
            (correo,)
        )
        user = cursor.fetchone()

        cursor.close()
        conn.close()

       if user:
        try:
            # PostgreSQL (dict)
            id_usuario = user["id"]
            nombre = user["nombre_completo"]
            correo_db = user["correo"]
            fecha_nac = user["fecha_nacimiento"]
            password_hash = user["password"]
        except:
            # fallback tuple
            id_usuario = user[0]
            nombre = user[1]
            correo_db = user[2]
            fecha_nac = user[3]
            password_hash = user[4]

        if check_password_hash(password_hash, password):
            from app import Usuario

            usuario_obj = Usuario(
                id_usuario,
                nombre,
                correo_db,
                fecha_nac
            )

            login_user(usuario_obj)
            return redirect(url_for('home.index'))

        flash("Correo o contraseña incorrectos.")


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
            cursor.execute("""
                UPDATE usuarios 
                SET nombre_completo = %s, fecha_nacimiento = %s 
                WHERE id = %s
            """, (nuevo_nombre, nueva_fecha, current_user.id))

            if nueva_pass and nueva_pass.strip():
                if len(nueva_pass) < 6:
                    flash("La contraseña debe tener al menos 6 caracteres.", "danger")
                    return redirect(url_for('auth.perfil'))

                hash_pw = generate_password_hash(nueva_pass)
                cursor.execute(
                    "UPDATE usuarios SET password = %s WHERE id = %s",
                    (hash_pw, current_user.id)
                )

            conn.commit()

            current_user.nombre_completo = nuevo_nombre
            current_user.fecha_nacimiento = nueva_fecha

            flash("¡Perfil actualizado con éxito, bo!", "success")

        except Exception as e:
            conn.rollback()
            flash(f"Error al actualizar: {e}", "danger")

        cursor.close()
        conn.close()

        return redirect(url_for('auth.perfil'))

    cursor.execute(
        "SELECT id, nombre_completo, correo, fecha_nacimiento FROM usuarios WHERE id = %s",
        (current_user.id,)
    )
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template("perfil.html", user=user)
