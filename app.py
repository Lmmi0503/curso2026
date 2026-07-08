import mysql.connector
from flask import Flask, render_template, request, url_for, redirect
import os
import urllib.request
import json

app = Flask(__name__)

def obtener_conexion():
    return mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "",
        database= "gastronomia_db"
    )

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
# VER PANEL COMPLETO (TABLA)
# ==========================================
@app.route('/tabla')
def dashboard():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    # Traemos el id (fila[0]) y el resto de columnas necesarias
    sql = "SELECT id, nombre_usuario, nombre_receta, descripcion, categoria, imagen, region FROM recetas"
    cursor.execute(sql)
    productos_db = cursor.fetchall()
    cursor.close()
    conexion.close()
    return render_template('tabla.html', inventario=productos_db)

@app.route('/formulario')
def f():
    return render_template('formulario.html')

# ==========================================
# PROCESAR E INSERTAR NUEVO REGISTRO
# ==========================================
@app.route('/registro', methods=['POST'])
def registro():
    nombre_usuario = request.form.get('nombre_usuario')
    correo_usuario = request.form.get('correo_usuario')
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
        INSERT INTO recetas (nombre_usuario, correo_usuario, nombre_receta, categoria, region, descripcion, imagen) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    valores = (nombre_usuario, correo_usuario, nombre_receta, categoria, region, descripcion, nombre_archivo)
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
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre_usuario, correo_usuario, nombre_receta, categoria, region, descripcion, imagen FROM recetas WHERE id = %s", (id_receta,))
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
    nombre_usuario = request.form.get('nombre_usuario')
    correo_usuario = request.form.get('correo_usuario')
    nombre_receta = request.form.get('nombre_receta')
    categoria = request.form.get('categoria')
    region = request.form.get('region')
    descripcion = request.form.get('descripcion')
    imagen = request.files.get('imagen')

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    if imagen and imagen.filename != "":
        # Si el usuario subió una nueva foto, la guardamos y actualizamos la columna de imagen
        nombre_archivo = imagen.filename
        CARPETA_IMAGENES = os.path.join('static', 'imagenes')
        imagen.save(os.path.join(CARPETA_IMAGENES, nombre_archivo))
        
        comando_sql = """
            UPDATE recetas 
            SET nombre_usuario=%s, correo_usuario=%s, nombre_receta=%s, categoria=%s, region=%s, descripcion=%s, imagen=%s 
            WHERE id=%s
        """
        valores = (nombre_usuario, correo_usuario, nombre_receta, categoria, region, descripcion, nombre_archivo, id_receta)
    else:
        # Si no subió una foto nueva, conservamos la que ya estaba en la base de datos
        comando_sql = """
            UPDATE recetas 
            SET nombre_usuario=%s, correo_usuario=%s, nombre_receta=%s, categoria=%s, region=%s, descripcion=%s 
            WHERE id=%s
        """
        valores = (nombre_usuario, correo_usuario, nombre_receta, categoria, region, descripcion, id_receta)

    cursor.execute(comando_sql, valores)
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
    cursor.execute("SELECT id, nombre_receta, imagen, categoria, nombre_usuario FROM recetas")
    for fila in cursor.fetchall():
        url_img = url_for('static', filename='imagenes/' + fila[2]) if fila[2] else ""
        platos_totales.append({
            'id': f"db-{fila[0]}",
            'titulo': fila[1],
            'imagen': url_img,
            'categoria_tipo': fila[3].lower(),
            'categoria_badge': fila[3].capitalize(),
            'origen': f"Local por {fila[4]}"
        })
    cursor.close()
    conexion.close()
    return render_template('categorias.html', platos=platos_totales)

# ==========================================
# RUTA PARA ELIMINAR UN REGISTRO (DELETE)
# ==========================================
@app.route('/eliminar/<int:id_receta>')
def eliminar_receta(id_receta):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Ejecutamos la sentencia DELETE para borrar de HeidiSQL
    comando_sql = "DELETE FROM recetas WHERE id = %s"
    cursor.execute(comando_sql, (id_receta,))
    
    conexion.commit()
    cursor.close()
    conexion.close()
    
    # Redirigimos de vuelta al panel para ver la tabla actualizada
    return redirect(url_for('dashboard'))

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
    cursor.execute("SELECT id, nombre_receta, imagen, region, nombre_usuario FROM recetas")
    for fila in cursor.fetchall():
        url_img = url_for('static', filename='imagenes/' + fila[2]) if fila[2] else ""
        platos_totales.append({
            'id': f"db-{fila[0]}",
            'titulo': fila[1],
            'imagen': url_img,
            'region_tipo': fila[3].lower(),
            'region_badge': fila[3].capitalize(),
            'origen': f"Local por {fila[4]}"
        })
    cursor.close()
    conexion.close()
    return render_template('region.html', platos=platos_totales)

if __name__ == '__main__':
    app.run(debug=True, port=5500)