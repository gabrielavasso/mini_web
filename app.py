from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import os
import json
import re
import shutil

load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecreto"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MUSIC_FOLDER'] = 'static/music'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['NOTAS_FILE'] = os.path.join("data", "notas.json")

# === Filtro personalizado para extraer ID de YouTube ===
def youtube_id(link):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", link)
    return match.group(1) if match else ""

app.jinja_env.filters['youtube_id'] = youtube_id

# === Crear carpetas necesarias ===
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs("data", exist_ok=True)
if not os.path.exists(app.config['NOTAS_FILE']):
    with open(app.config['NOTAS_FILE'], "w", encoding="utf-8") as f:
        json.dump([], f)

# === Función para validar archivos ===
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# === Rutas ===
@app.route("/")
def index():
    carpetas = os.listdir(app.config['UPLOAD_FOLDER'])
    galeria = {}
    for carpeta in carpetas:
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], carpeta)
        if os.path.isdir(ruta):
            imagenes = [f for f in os.listdir(ruta) if allowed_file(f)]
            galeria[carpeta] = imagenes
    return render_template("index.html", galeria=galeria)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        usuario = request.form["usuario"].strip()
        contrasena = request.form["contrasena"].strip()

        if usuario == os.getenv("USUARIO") and contrasena == os.getenv("CONTRASENA"):
            session["logueado"] = True
            return redirect(url_for("bienvenida"))  # Redirige a mensaje de bienvenida
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

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not session.get("logueado"):
        return redirect(url_for("login"))

    if request.method == "POST":
        carpeta = request.form["carpeta"]
        archivos = request.files.getlist("fotos")
        ruta_carpeta = os.path.join(app.config['UPLOAD_FOLDER'], carpeta)
        os.makedirs(ruta_carpeta, exist_ok=True)

        for archivo in archivos:
            if archivo and allowed_file(archivo.filename):
                nombre_seguro = secure_filename(archivo.filename)
                archivo.save(os.path.join(ruta_carpeta, nombre_seguro))

        flash("📸 Fotos subidas correctamente.")
        return redirect(url_for("ver_album", carpeta=carpeta))

    return render_template("upload.html")

@app.route("/uploads/<carpeta>/<nombre>")
def ver_imagen(carpeta, nombre):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], carpeta), nombre)

@app.route("/carta")
def carta():
    return render_template("carta.html")

@app.route("/notas", methods=["GET", "POST"])
def notas():
    archivo_notas = app.config['NOTAS_FILE']
    if os.path.exists(archivo_notas):
        with open(archivo_notas, "r", encoding="utf-8") as f:
            todas_las_notas = json.load(f)
    else:
        todas_las_notas = []

    if request.method == "POST":
        autor = request.form["autor"]
        mensaje = request.form["mensaje"]
        nueva_nota = {"autor": autor, "mensaje": mensaje}
        todas_las_notas.append(nueva_nota)

        with open(archivo_notas, "w", encoding="utf-8") as f:
            json.dump(todas_las_notas, f, indent=4, ensure_ascii=False)

        return redirect(url_for("notas"))

    return render_template("notas.html", notas=todas_las_notas, total=len(todas_las_notas), enumerate=enumerate)

@app.route("/eliminar_nota/<int:indice>", methods=["POST"])
def eliminar_nota(indice):
    archivo_notas = app.config['NOTAS_FILE']
    if os.path.exists(archivo_notas):
        with open(archivo_notas, "r", encoding="utf-8") as f:
            todas_las_notas = json.load(f)

        if 0 <= indice < len(todas_las_notas):
            todas_las_notas.pop(indice)
            with open(archivo_notas, "w", encoding="utf-8") as f:
                json.dump(todas_las_notas, f, indent=4, ensure_ascii=False)

    return redirect(url_for("notas"))

@app.route("/canciones", methods=["GET", "POST"])
def canciones():
    archivo_canciones = os.path.join("data", "canciones.json")
    if not os.path.exists(archivo_canciones):
        with open(archivo_canciones, "w", encoding="utf-8") as f:
            json.dump([], f)

    with open(archivo_canciones, "r", encoding="utf-8") as f:
        canciones = json.load(f)

    if request.method == "POST":
        if not session.get("logueado"):
            return redirect(url_for("login"))

        link = request.form["link"]
        canciones.append(link)
        with open(archivo_canciones, "w", encoding="utf-8") as f:
            json.dump(canciones, f, indent=4, ensure_ascii=False)
        flash("🎵 Canción agregada con éxito")
        return redirect(url_for("canciones"))

    return render_template("canciones.html", canciones=canciones)

@app.route("/galeria")
def galeria():
    carpetas = os.listdir(app.config['UPLOAD_FOLDER'])
    galeria = {}
    for carpeta in carpetas:
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], carpeta)
        if os.path.isdir(ruta):
            imagenes = [f for f in os.listdir(ruta) if allowed_file(f)]
            galeria[carpeta] = imagenes
    return render_template("galeria.html", galeria=galeria)

@app.route("/crear_album", methods=["GET", "POST"])
def crear_album():
    if not session.get("logueado"):
        return redirect(url_for("login"))

    mensaje = None
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if nombre:
            carpeta_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(nombre))
            if not os.path.exists(carpeta_path):
                os.makedirs(carpeta_path)
                mensaje = f"✅ Álbum '{nombre}' creado exitosamente."
            else:
                mensaje = f"⚠️ El álbum '{nombre}' ya existe."

    return render_template("crear_album.html", mensaje=mensaje)

@app.route("/eliminar_fotos", methods=["POST"])
def eliminar_fotos():
    if not session.get("logueado"):
        return redirect(url_for("login"))

    carpeta = request.form.get("carpeta", "").strip()
    nombre = request.form.get("nombre", "").strip()
    carpeta_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(carpeta))

    if nombre:
        # Eliminar foto específica
        ruta_foto = os.path.join(carpeta_path, secure_filename(nombre))
        if os.path.exists(ruta_foto):
            os.remove(ruta_foto)
            flash(f"🗑️ Foto '{nombre}' eliminada con éxito.")
        else:
            flash(f"❌ No se encontró la foto '{nombre}'.")
        return redirect(url_for('ver_album', carpeta=carpeta))
    else:
        # Eliminar carpeta completa
        if os.path.exists(carpeta_path):
            shutil.rmtree(carpeta_path)
            flash(f"🗑️ Álbum '{carpeta}' eliminado completamente.")
        else:
            flash(f"❌ No se encontró la carpeta '{carpeta}'.")
        return redirect(url_for('galeria'))

@app.route("/ver_album/<carpeta>")
def ver_album(carpeta):
    ruta_carpeta = os.path.join(app.config['UPLOAD_FOLDER'], carpeta)
    imagenes = []
    if os.path.exists(ruta_carpeta):
        imagenes = [f for f in os.listdir(ruta_carpeta) if allowed_file(f)]
    return render_template("ver_album.html", carpeta=carpeta, imagenes=imagenes)

@app.route("/panel")
def panel():
    if not session.get("logueado"):
        return redirect(url_for("login"))

    carpetas = os.listdir(app.config['UPLOAD_FOLDER'])
    total_carpetas = len(carpetas)
    total_fotos = 0
    for carpeta in carpetas:
        ruta = os.path.join(app.config['UPLOAD_FOLDER'], carpeta)
        if os.path.isdir(ruta):
            total_fotos += len([f for f in os.listdir(ruta) if allowed_file(f)])

    archivo_notas = app.config['NOTAS_FILE']
    total_notas = 0
    ultima_nota = None

    if os.path.exists(archivo_notas):
        with open(archivo_notas, "r", encoding="utf-8") as f:
            todas_las_notas = json.load(f)
            total_notas = len(todas_las_notas)
            if total_notas > 0:
                ultima_nota = todas_las_notas[-1]

    return render_template("panel.html", total_carpetas=total_carpetas, total_fotos=total_fotos, total_notas=total_notas, ultima_nota=ultima_nota)

# Crear carpetas iniciales si no existen
def crear_carpetas_iniciales():
    rutas = [
        os.path.join("static", "galeria", "Viaje a Brasil"),
        os.path.join("static", "galeria", "Eventos")
    ]
    for ruta in rutas:
        os.makedirs(ruta, exist_ok=True)

crear_carpetas_iniciales()

@app.route("/eliminar_cancion", methods=["POST"])
def eliminar_cancion():
    if not session.get("logueado"):
        return redirect(url_for("login"))
    
    link = request.form.get("link")
    if link and link in canciones:  # Asegurate de tener una lista 'canciones'
        canciones.remove(link)
        flash("🎵 Canción eliminada correctamente.")
    else:
        flash("⚠️ No se pudo eliminar la canción.")
    
    return redirect(url_for("canciones"))

@app.route("/bienvenida")
def bienvenida():
    if not session.get("logueado"):
        return redirect(url_for("login"))
    return render_template("bienvenida.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
