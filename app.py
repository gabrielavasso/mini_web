from flask import Flask, render_template, request, redirect, url_for, session, flash
from dotenv import load_dotenv
import os
import re
import cloudinary
import cloudinary.uploader
import cloudinary.api

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecreto"

# === Configuración Cloudinary ===
cloudinary_url = os.getenv("CLOUDINARY_URL")
if cloudinary_url:
    cloudinary.config(cloudinary_url=cloudinary_url)
else:
    # Configuración manual si no hay variable en entorno
    cloudinary.config(
        cloud_name="djuurobvo",
        api_key="567997862976986",
        api_secret="TjUDD_bUkejGoAdxYs0JrEase_I"
    )

# === Filtro para extraer ID de YouTube ===
def youtube_id(link):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", link)
    return match.group(1) if match else ""

app.jinja_env.filters['youtube_id'] = youtube_id

# === Helpers para Cloudinary ===
def listar_albums():
    """Obtiene lista de carpetas dentro de mini_web en Cloudinary"""
    resultado = cloudinary.api.subfolders("mini_web")
    return [folder["name"] for folder in resultado["folders"]]

def listar_fotos_album(album):
    """Obtiene fotos de una carpeta específica"""
    resultado = cloudinary.api.resources(
        type="upload",
        prefix=f"mini_web/{album}/",
        max_results=100
    )
    fotos = []
    for foto in resultado.get("resources", []):
        fotos.append({
            "url": foto["secure_url"],
            "public_id": foto["public_id"]
        })
    return fotos

# === Rutas principales ===
@app.route("/")
def index():
    albums = listar_albums()
    return render_template("index.html", galeria=albums)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario = request.form["usuario"].strip()
        contrasena = request.form["contrasena"].strip()

        if usuario == os.getenv("USUARIO") and contrasena == os.getenv("CONTRASENA"):
            session["logueado"] = True
            return redirect(url_for("bienvenida"))
        else:
            error = "Usuario o contraseña incorrectos"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    session['logout_mensaje'] = True
    return redirect(url_for('mensaje_logout'))

@app.route("/mensaje_logout")
def mensaje_logout():
    if session.get('logout_mensaje'):
        session.pop('logout_mensaje')
        return render_template('mensaje_logout.html')
    return redirect(url_for('index'))

# === Crear álbum ===
@app.route("/crear_album", methods=["GET", "POST"])
def crear_album():
    if not session.get("logueado"):
        return redirect(url_for("login"))

    mensaje = None
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if nombre:
            # Verificamos si ya existe la carpeta en Cloudinary
            albums = listar_albums()
            if nombre not in albums:
                # Creamos carpeta virtual (subiendo archivo vacío opcionalmente)
                flash(f"Álbum '{nombre}' creado correctamente.")
                return redirect(url_for("ver_album", carpeta=nombre))
            else:
                mensaje = f"⚠️ El álbum '{nombre}' ya existe."
    return render_template("crear_album.html", mensaje=mensaje)

# === Subir fotos (desde página de álbum) ===
@app.route("/upload/<carpeta>", methods=["POST"])
def upload(carpeta):
    if not session.get("logueado"):
        return redirect(url_for("login"))

    archivos = request.files.getlist("fotos")

    for archivo in archivos:
        if archivo:
            cloudinary.uploader.upload(archivo, folder=f"mini_web/{carpeta}")

    flash("📸 Fotos subidas correctamente.")
    return redirect(url_for("ver_album", carpeta=carpeta))

# === Subir fotos (desde formulario general) ===
@app.route("/upload_form", methods=["GET", "POST"])
def upload_form():
    if request.method == "POST":
        if not session.get("logueado"):
            return redirect(url_for("login"))

        carpeta = request.form.get("carpeta")
        archivos = request.files.getlist("fotos")

        for archivo in archivos:
            if archivo:
                cloudinary.uploader.upload(archivo, folder=f"mini_web/{carpeta}")

        flash("📸 Fotos subidas correctamente.")
        return redirect(url_for("ver_album", carpeta=carpeta))

    albums = listar_albums()
    return render_template("upload.html", albums=albums)

# === Ver álbum ===
@app.route("/ver_album/<carpeta>")
def ver_album(carpeta):
    imagenes = listar_fotos_album(carpeta)
    return render_template("ver_album.html", carpeta=carpeta, imagenes=imagenes)

# === Eliminar foto o álbum ===
@app.route("/eliminar_fotos", methods=["POST"])
def eliminar_fotos():
    if not session.get("logueado"):
        return redirect(url_for("login"))

    carpeta = request.form.get("carpeta", "").strip()
    public_id = request.form.get("public_id", "").strip()

    if carpeta and public_id:
        # Eliminar foto específica
        cloudinary.uploader.destroy(public_id)
        flash(f"🗑️ Foto eliminada de '{carpeta}'.")
        return redirect(url_for("ver_album", carpeta=carpeta))

    elif carpeta and not public_id:
        # Eliminar todo el álbum (todas las fotos)
        fotos = listar_fotos_album(carpeta)
        for foto in fotos:
            cloudinary.uploader.destroy(foto["public_id"])
        flash(f"🗑️ Álbum '{carpeta}' eliminado completamente.")
        return redirect(url_for("galeria"))

    flash("❌ No se pudo eliminar la foto o álbum.")
    return redirect(url_for("galeria"))

# === Galería principal ===
@app.route("/galeria")
def galeria():
    albums = listar_albums()
    return render_template("galeria.html", albums=albums)

# === Canciones (queda igual que antes si usás JSON para eso) ===
@app.route("/canciones", methods=["GET", "POST"])
def canciones():
    return render_template("canciones.html")

# === Carta y Notas (no tocamos) ===
@app.route("/carta")
def carta():
    return render_template("carta.html")

@app.route("/notas")
def notas():
    return render_template("notas.html")

@app.route("/bienvenida")
def bienvenida():
    if not session.get("logueado"):
        return redirect(url_for("login"))
    return render_template("bienvenida.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
