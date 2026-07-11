import sqlite3
from flask import Flask, render_template, request, url_for, redirect, session, flash
import os
import urllib.request
import json

app = Flask(__name__)
# Llave secreta necesaria para mantener las sesiones de usuario seguras
app.secret_key = "mi_llave_secreta_super_segura_gastronomia"

def obtener_conexion():
    conexion = sqlite3.connect("gastronomia_db.sqlite")

    return conexion

def consultar_api(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as respuesta:
            return json.loads(respuesta.read().decode())
    except Exception as e:
        print(f"Error en la API: {e}")
        return None

@app.route('/')
def inicio():
    return render_template('inicio.html')

# ==========================================
# AUTENTICACIÓN: LOGIN, REGISTRO Y LOGOUT
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')

        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, correo, contrasena FROM usuarios WHERE correo = ?", (correo,))
        usuario = cursor.fetchone()
        cursor.close()
        conexion.close()

        if usuario and usuario[2] == contrasena:
            session['usuario_id'] = usuario[0]
            session['usuario_correo'] = usuario[1]
            flash("¡Inicio de sesión exitoso!", "exito")
            return redirect(url_for('inicio'))
        else:
            flash("El correo no existe o la contraseña es incorrecta.", "error")
    
    return render_template('login.html')

@app.route('/crear-cuenta', methods=['GET', 'POST'])
def crear_cuenta():
    if request.method == 'POST':
        correo = request.form.get('correo')
        contrasena = request.form.get('contrasena')

        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute("SELECT id FROM usuarios WHERE correo = ?", (correo,))
        if cursor.fetchone():
            flash("Ese correo ya está registrado. Intenta iniciar sesión.", "error")
            cursor.close()
            conexion.close()
            return redirect(url_for('crear_cuenta'))

        cursor.execute("INSERT INTO usuarios (correo, contrasena) VALUES (?, ?)", (correo, contrasena))
        conexion.commit()
        cursor.close()
        conexion.close()
        
        flash("Cuenta creada con éxito. ¡Ya puedes iniciar sesión!", "exito")
        return redirect(url_for('login'))

    return render_template('crear_cuenta.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('inicio'))

# ==========================================
# VER PANEL COMPLETO (TABLA)
# ==========================================
@app.route('/tabla')
def dashboard():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    sql = """
        SELECT r.id, u.correo, r.nombre_receta, r.descripcion, r.categoria, r.imagen, r.region 
        FROM recetas r 
        JOIN usuarios u ON r.usuario_id = u.id
    """
    cursor.execute(sql)
    productos_db = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template('tabla.html', inventario=productos_db)

# ==========================================
# MOSTRAR FORMULARIO DE RECOLECCIÓN
# ==========================================
@app.route('/formulario')
def f():
    if 'usuario_id' not in session:
        flash("Debes iniciar sesión para registrar una receta.", "error")
        return redirect(url_for('login'))
    return render_template('formulario.html')

# ==========================================
# PROCESAR E INSERTAR NUEVO REGISTRO
# ==========================================
@app.route('/registro', methods=['POST'])
def registro():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    nombre_receta = request.form.get('nombre_receta')
    categoria = request.form.get('categoria')
    region = request.form.get('region')
    descripcion = request.form.get('descripcion')
    imagen = request.files.get('imagen')

    nombre_archivo = ""
    if imagen:
        nombre_archivo = imagen.filename 
        CARPETA_IMAGENES = os.path.join('static', 'imagenes')
        if not os.path.exists(CARPETA_IMAGENES):
            os.makedirs(CARPETA_IMAGENES)
        imagen.save(os.path.join(CARPETA_IMAGENES, nombre_archivo))

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    comando_sql = """
        INSERT INTO recetas (usuario_id, nombre_receta, categoria, region, descripcion, imagen) 
        VALUES (?, ?, ?, ?, ?, ?)
    """
    valores = (usuario_id, nombre_receta, categoria, region, descripcion, nombre_archivo)
    cursor.execute(comando_sql, valores)
    conexion.commit()
    cursor.close()
    conexion.close()

    return redirect(url_for('dashboard'))

# ==========================================
# RUTA PARA MOSTRAR EL FORMULARIO DE EDICIÓN
# ==========================================
@app.route('/editar/<int:id_receta>')
def mostrar_editar(id_receta):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    # Consulta optimizada con el orden de índices exacto para editar.html
    cursor.execute("SELECT id, usuario_id, nombre_receta, categoria, region, descripcion, imagen FROM recetas WHERE id = ?", (id_receta,))
    receta = cursor.fetchone()
    cursor.close()
    conexion.close()
    
    if receta:
        return render_template('editar.html', receta=receta)
    return redirect(url_for('dashboard'))

# ==========================================
# PROCESAR LA ACTUALIZACIÓN (UPDATE)
# ==========================================
@app.route('/actualizar/<int:id_receta>', methods=['POST'])
def actualizar_receta(id_receta):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nombre_receta = request.form.get('nombre_receta')
    categoria = request.form.get('categoria')
    region = request.form.get('region')
    descripcion = request.form.get('descripcion')
    imagen = request.files.get('imagen')

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    if imagen and imagen.filename != "":
        nombre_archivo = imagen.filename
        CARPETA_IMAGENES = os.path.join('static', 'imagenes')
        imagen.save(os.path.join(CARPETA_IMAGENES, nombre_archivo))
        
        comando_sql = """
            UPDATE recetas 
            SET nombre_receta=?, categoria=?, region=?, descripcion=?, imagen=? 
            WHERE id=?
        """
        valores = (nombre_receta, categoria, region, descripcion, nombre_archivo, id_receta)
    else:
        comando_sql = """
            UPDATE recetas 
            SET nombre_receta=?, categoria=?, region=?, descripcion=? 
            WHERE id=?
        """
        valores = (nombre_receta, categoria, region, descripcion, id_receta)

    cursor.execute(comando_sql, valores)
    conexion.commit()
    cursor.close()
    conexion.close()

    return redirect(url_for('dashboard'))

# ==========================================
# RUTA PARA ELIMINAR UN REGISTRO (DELETE)
# ==========================================
@app.route('/eliminar/<int:id_receta>')
def eliminar_receta(id_receta):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    comando_sql = "DELETE FROM recetas WHERE id = ?"
    cursor.execute(comando_sql, (id_receta,))
    conexion.commit()
    cursor.close()
    conexion.close()
    return redirect(url_for('dashboard'))

# ==========================================
# VISTAS DE LAS APIS
# ==========================================
@app.route('/categorias')
def categorias():
    urls = {
        'masas': 'https://www.themealdb.com/api/json/v1/1/filter.php?c=Pasta',
        'carnes': 'https://www.themealdb.com/api/json/v1/1/filter.php?c=Beef',
        'reposteria': 'https://www.themealdb.com/api/json/v1/1/filter.php?c=Dessert'
    }
    platos_totales = []
    for cat_nombre, url in urls.items():
        respuesta = consultar_api(url)
        if respuesta and respuesta.get('meals'):
            for meal in respuesta['meals'][:2]:
                platos_totales.append({
                    'id': meal['idMeal'],
                    'titulo': meal['strMeal'],
                    'imagen': meal['strMealThumb'],
                    'categoria_tipo': cat_nombre,
                    'categoria_badge': cat_nombre.capitalize(),
                    'origen': 'API Pública'
                })
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT r.id, r.nombre_receta, r.imagen, r.categoria, u.correo FROM recetas r JOIN usuarios u ON r.usuario_id = u.id")
    for fila in cursor.fetchall():
        url_img = url_for('static', filename='imagenes/' + fila[2]) if fila[2] else ""
        platos_totales.append({
            'id': f"db-{fila[0]}",
            'titulo': fila[1],
            'imagen': url_img,
            'categoria_tipo': fila[3].lower(),
            'categoria_badge': fila[3].capitalize(),
            'origen': f"Por: {fila[4]}"
        })
    cursor.close()
    conexion.close()
    return render_template('categorias.html', platos=platos_totales)

@app.route('/paises')
def paises():
    urls = {
        'japon': 'https://www.themealdb.com/api/json/v1/1/filter.php?a=Japanese',
        'mexico': 'https://www.themealdb.com/api/json/v1/1/filter.php?a=Mexican',
        'china': 'https://www.themealdb.com/api/json/v1/1/filter.php?a=Chinese'
    }
    platos_totales = []
    for region_nombre, url in urls.items():
        respuesta = consultar_api(url)
        if respuesta and respuesta.get('meals'):
            for meal in respuesta['meals'][:2]:
                platos_totales.append({
                    'id': meal['idMeal'],
                    'titulo': meal['strMeal'],
                    'imagen': meal['strMealThumb'],
                    'region_tipo': region_nombre,
                    'region_badge': region_nombre.capitalize(),
                    'origen': 'Especialidad Internacional'
                })
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT r.id, r.nombre_receta, r.imagen, r.region, u.correo FROM recetas r JOIN usuarios u ON r.usuario_id = u.id")
    for fila in cursor.fetchall():
        url_img = url_for('static', filename='imagenes/' + fila[2]) if fila[2] else ""
        platos_totales.append({
            'id': f"db-{fila[0]}",
            'titulo': fila[1],
            'imagen': url_img,
            'region_tipo': fila[3].lower(),
            'region_badge': fila[3].capitalize(),
            'origen': f"Por: {fila[4]}"
        })
    cursor.close()
    conexion.close()
    return render_template('region.html', platos=platos_totales)

if __name__ == '__main__':
    app.run(debug=True, port=5500)