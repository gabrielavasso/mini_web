from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import json
import re
import cloudinary
import cloudinary.uploader

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecreto"

# === Configuración Cloudinary ===
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_URL").split("@")[1],
    api_key=os.getenv("CLOUDINARY_URL").split("//")[1].split(":")[0],
    api_secret=os.getenv("CLOUDINARY_URL").split(":")[2].split("@")[0]
)

# Archivos JSON para datos
NOTAS_FILE = os.path.join("data", "notas.json")
FOTOS_FILE = os.path.join("data", "fotos.json")
CANCIONES_FILE = os.path.join("data", "canciones.json")

# Crear archivos y carpetas necesarios
os.makedirs("data", exist_ok=True)
if not os.path.exists(NOTAS_FILE):
    with open(NOTAS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)
if not os.path.exists(FOTOS_FILE):
    with open(FOTOS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)  # Diccionario con {album: [fotos]}
if not os.path.exists(CANCIONES_FILE):
    with open(CANCIONES_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# Filtro para extraer ID de YouTube
def youtube_id(link):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", link)
    return match.group(1) if match else ""

app.jinja_env.filters['youtube_id'] = youtube_id

# === Rutas principales ===
@app.route("/")
def index():
    with open(FOTOS_FILE, "r", encoding="utf-8") as f:
        fotos = json.load(f)
    return render_template("index.html", galeria=fotos)

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
            with open(FOTOS_FILE, "r", encoding="utf-8") as f:
                fotos = json.load(f)
            if nombre not in fotos:
                fotos[nombre] = []
                with open(FOTOS_FILE, "w", encoding="utf-8") as f:
                    json.dump(fotos, f, indent=4, ensure_ascii=False)
                mensaje = f"✅ Álbum '{nombre}' creado exitosamente."
            else:
                mensaje = f"⚠️ El álbum '{nombre}' ya existe."
    return render_template("crear_album.html", mensaje=mensaje)

# === Subir fotos a Cloudinary ===
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not session.get("logueado"):
        return redirect(url_for("login"))

    if request.method == "POST":
        carpeta = request.form["carpeta"]
        archivos = request.files.getlist("fotos")

        with open(FOTOS_FILE, "r", encoding="utf-8") as f:
            fotos = json.load(f)

        if carpeta not in fotos:
            fotos[carpeta] = []

        for archivo in archivos:
            if archivo:
                resultado = cloudinary.uploader.upload(archivo, folder=f"mini_web/{carpeta}")
                fotos[carpeta].append({
                    "url": resultado['secure_url'],
                    "public_id": resultado['public_id']
                })

        with open(FOTOS_FILE, "w", encoding="utf-8") as f:
            json.dump(fotos, f, indent=4, ensure_ascii=False)

        flash("📸 Fotos subidas correctamente.")
        return redirect(url_for("ver_album", carpeta=carpeta))

    with open(FOTOS_FILE, "r", encoding="utf-8") as f:
        fotos = json.load(f)
    return render_template("upload.html", albums=list(fotos.keys()))

# === Ver álbum ===
@app.route("/ver_album/<carpeta>")
def ver_album(carpeta):
    with open(FOTOS_FILE, "r", encoding="utf-8") as f:
        fotos = json.load(f)
    imagenes = fotos.get(carpeta, [])
    return render_template("ver_album.html", carpeta=carpeta, imagenes=imagenes)

# === Eliminar foto o álbum ===
@app.route("/eliminar_fotos", methods=["POST"])
def eliminar_fotos():
    if not session.get("logueado"):
        return redirect(url_for("login"))

    carpeta = request.form.get("carpeta", "").strip()
    nombre = request.form.get("nombre", "").strip()

    with open(FOTOS_FILE, "r", encoding="utf-8") as f:
        fotos = json.load(f)

    if carpeta in fotos:
        if nombre:
            foto = next((f for f in fotos[carpeta] if f["url"] == nombre), None)
            if foto:
                cloudinary.uploader.destroy(foto["public_id"])
                fotos[carpeta].remove(foto)
                flash(f"🗑️ Foto eliminada de '{carpeta}'.")
            else:
                flash("❌ No se encontró la foto.")
        else:
            for foto in fotos[carpeta]:
                cloudinary.uploader.destroy(foto["public_id"])
            del fotos[carpeta]
            flash(f"🗑️ Álbum '{carpeta}' eliminado completamente.")

    with open(FOTOS_FILE, "w", encoding="utf-8") as f:
        json.dump(fotos, f, indent=4, ensure_ascii=False)

    return redirect(url_for("galeria"))

# === Galería principal ===
@app.route("/galeria")
def galeria():
    with open(FOTOS_FILE, "r", encoding="utf-8") as f:
        fotos = json.load(f)
    return render_template("galeria.html", galeria=fotos)

# === Canciones ===
@app.route("/canciones", methods=["GET", "POST"])
def canciones():
    # Cargar canciones
    with open(CANCIONES_FILE, "r", encoding="utf-8") as f:
        canciones = json.load(f)

    if request.method == "POST":
        if not session.get("logueado"):
            return redirect(url_for("login"))

        link = request.form.get("link", "").strip()
        if link:
            canciones.append(link)
            with open(CANCIONES_FILE, "w", encoding="utf-8") as f:
                json.dump(canciones, f, indent=4, ensure_ascii=False)
            flash("🎵 Canción agregada correctamente.")

    return render_template("canciones.html", canciones=canciones)

@app.route("/eliminar_cancion", methods=["POST"])
def eliminar_cancion():
    if not session.get("logueado"):
        return redirect(url_for("login"))

    link = request.form.get("link", "").strip()

    with open(CANCIONES_FILE, "r", encoding="utf-8") as f:
        canciones = json.load(f)

    if link in canciones:
        canciones.remove(link)
        with open(CANCIONES_FILE, "w", encoding="utf-8") as f:
            json.dump(canciones, f, indent=4, ensure_ascii=False)
        flash("🗑️ Canción eliminada.")

    return redirect(url_for("canciones"))

# === Rutas adicionales ===
@app.route("/carta")
def carta():
    return render_template("carta.html")

@app.route("/notas", methods=["GET", "POST"])
def notas():
    if os.path.exists(NOTAS_FILE):
        with open(NOTAS_FILE, "r", encoding="utf-8") as f:
            todas_las_notas = json.load(f)
    else:
        todas_las_notas = []

    if request.method == "POST":
        autor = request.form["autor"]
        mensaje = request.form["mensaje"]
        nueva_nota = {"autor": autor, "mensaje": mensaje}
        todas_las_notas.append(nueva_nota)

        with open(NOTAS_FILE, "w", encoding="utf-8") as f:
            json.dump(todas_las_notas, f, indent=4, ensure_ascii=False)

        return redirect(url_for("notas"))

    return render_template("notas.html", notas=todas_las_notas, total=len(todas_las_notas), enumerate=enumerate)

@app.route("/bienvenida")
def bienvenida():
    if not session.get("logueado"):
        return redirect(url_for("login"))
    return render_template("bienvenida.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
