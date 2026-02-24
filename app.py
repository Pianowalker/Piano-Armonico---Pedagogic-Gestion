"""
Aplicación web para gestión pedagógica de Piano Armónico
Backend principal con Flask
"""

from flask import Flask, render_template, request, redirect, url_for
from models import db, Alumno, TrabajoMusical
from validaciones import validar_requisitos_examen
from sqlalchemy import inspect, text

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///piano_armonico.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'clave-secreta-local'  # Solo para uso local

db.init_app(app)

# Inicializar base de datos y migrar si es necesario
with app.app_context():
    db.create_all()
    
    # Migración: agregar columna 'carrera' si no existe
    try:
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('alumnos')]
        
        if 'carrera' not in columns:
            db.session.execute(text('ALTER TABLE alumnos ADD COLUMN carrera VARCHAR(50)'))
            db.session.commit()
            print("✓ Columna 'carrera' agregada exitosamente a la tabla 'alumnos'")
    except Exception as e:
        # Si la tabla no existe aún, create_all() la creará con todas las columnas
        # Si hay otro error, lo mostramos pero no detenemos la aplicación
        print(f"Nota sobre migración de base de datos: {e}")
        db.session.rollback()

@app.route('/')
def index():
    """Página principal - redirige a lista de alumnos"""
    return redirect(url_for('lista_alumnos'))

@app.route('/alumnos')
def lista_alumnos():
    """Lista de alumnos con filtros y búsqueda"""
    # Obtener parámetros de filtro
    año = request.args.get('año', '')
    tipo = request.args.get('tipo', '')
    estado_academico = request.args.get('estado_academico', '')
    estado_cursada = request.args.get('estado_cursada', '')
    busqueda = request.args.get('busqueda', '')
    
    # Construir query
    query = Alumno.query
    
    if año:
        query = query.filter(Alumno.año == año)
    if tipo:
        query = query.filter(Alumno.tipo == tipo)
    if estado_academico:
        query = query.filter(Alumno.estado_academico == estado_academico)
    if estado_cursada:
        query = query.filter(Alumno.estado_cursada == estado_cursada)
    if busqueda:
        query = query.filter(
            (Alumno.nombre.contains(busqueda)) |
            (Alumno.apellido.contains(busqueda))
        )
    
    alumnos = query.order_by(Alumno.apellido, Alumno.nombre).all()
    total_alumnos = len(alumnos)
    
    return render_template('lista_alumnos.html', alumnos=alumnos, total_alumnos=total_alumnos)

@app.route('/alumnos/nuevo', methods=['GET', 'POST'])
def nuevo_alumno():
    """Crear nuevo alumno"""
    if request.method == 'POST':
        alumno = Alumno(
            nombre=request.form['nombre'],
            apellido=request.form['apellido'],
            instrumento_principal=request.form.get('instrumento_principal', ''),
            tipo=request.form['tipo'],
            año=request.form['año'],
            estado_academico=request.form['estado_academico'],
            estado_cursada=request.form['estado_cursada'],
            carrera=request.form.get('carrera', '') if request.form.get('año', '').startswith('Profesorado') else None,
            comentarios=request.form.get('comentarios', '')
        )
        db.session.add(alumno)
        db.session.commit()
        return redirect(url_for('perfil_alumno', id=alumno.id))
    
    return render_template('form_alumno.html')

@app.route('/alumnos/<int:id>')
def perfil_alumno(id):
    """Perfil completo del alumno"""
    alumno = Alumno.query.get_or_404(id)
    trabajos = TrabajoMusical.query.filter_by(alumno_id=id).order_by(TrabajoMusical.id.desc()).all()
    
    # Validar requisitos de examen
    requisitos = validar_requisitos_examen(alumno, trabajos)
    
    return render_template('perfil_alumno.html', 
                         alumno=alumno, 
                         trabajos=trabajos,
                         requisitos=requisitos)

@app.route('/alumnos/<int:id>/editar', methods=['GET', 'POST'])
def editar_alumno(id):
    """Editar alumno existente"""
    alumno = Alumno.query.get_or_404(id)
    
    if request.method == 'POST':
        alumno.nombre = request.form['nombre']
        alumno.apellido = request.form['apellido']
        alumno.instrumento_principal = request.form.get('instrumento_principal', '')
        alumno.tipo = request.form['tipo']
        alumno.año = request.form['año']
        alumno.estado_academico = request.form['estado_academico']
        alumno.estado_cursada = request.form['estado_cursada']
        alumno.carrera = request.form.get('carrera', '') if request.form.get('año', '').startswith('Profesorado') else None
        alumno.comentarios = request.form.get('comentarios', '')
        
        db.session.commit()
        return redirect(url_for('perfil_alumno', id=alumno.id))
    
    return render_template('form_alumno.html', alumno=alumno)

@app.route('/alumnos/<int:id>/eliminar', methods=['POST'])
def eliminar_alumno(id):
    """Eliminar alumno"""
    alumno = Alumno.query.get_or_404(id)
    db.session.delete(alumno)
    db.session.commit()
    return redirect(url_for('lista_alumnos'))

@app.route('/alumnos/<int:id>/trabajo/nuevo', methods=['GET', 'POST'])
def nuevo_trabajo(id):
    """Agregar trabajo musical a un alumno"""
    alumno = Alumno.query.get_or_404(id)
    
    if request.method == 'POST':
        trabajo = TrabajoMusical(
            titulo=request.form['titulo'],
            tipo=request.form['tipo'],
            estilo=request.form['estilo'],
            formato=request.form['formato'],
            autoría_arreglo=request.form.get('autoría_arreglo', 'propio'),
            estado_estudio=request.form['estado_estudio'],
            comentarios=request.form.get('comentarios', ''),
            alumno_id=id
        )
        db.session.add(trabajo)
        db.session.commit()
        return redirect(url_for('perfil_alumno', id=id))
    
    return render_template('form_trabajo.html', alumno=alumno)

@app.route('/trabajos/<int:id>/editar', methods=['GET', 'POST'])
def editar_trabajo(id):
    """Editar trabajo musical"""
    trabajo = TrabajoMusical.query.get_or_404(id)
    
    if request.method == 'POST':
        trabajo.titulo = request.form['titulo']
        trabajo.tipo = request.form['tipo']
        trabajo.estilo = request.form['estilo']
        trabajo.formato = request.form['formato']
        trabajo.autoría_arreglo = request.form.get('autoría_arreglo', 'propio')
        trabajo.estado_estudio = request.form['estado_estudio']
        trabajo.comentarios = request.form.get('comentarios', '')
        
        db.session.commit()
        return redirect(url_for('perfil_alumno', id=trabajo.alumno_id))
    
    return render_template('form_trabajo.html', trabajo=trabajo, alumno=trabajo.alumno)

@app.route('/trabajos/<int:id>/eliminar', methods=['POST'])
def eliminar_trabajo(id):
    """Eliminar trabajo musical"""
    trabajo = TrabajoMusical.query.get_or_404(id)
    alumno_id = trabajo.alumno_id
    db.session.delete(trabajo)
    db.session.commit()
    return redirect(url_for('perfil_alumno', id=alumno_id))

@app.route('/ano/<ano>')
def vista_año(ano):
    """Vista de alumnos por año/curso"""
    # El parámetro 'ano' viene de la URL, pero internamente usamos 'año' para la lógica
    año = ano
    alumnos = Alumno.query.filter_by(año=año).order_by(Alumno.apellido, Alumno.nombre).all()
    
    # Obtener parámetros de filtro adicionales
    tipo = request.args.get('tipo', '')
    estado_academico = request.args.get('estado_academico', '')
    estado_cursada = request.args.get('estado_cursada', '')
    
    query = Alumno.query.filter_by(año=año)
    
    if tipo:
        query = query.filter(Alumno.tipo == tipo)
    if estado_academico:
        query = query.filter(Alumno.estado_academico == estado_academico)
    if estado_cursada:
        query = query.filter(Alumno.estado_cursada == estado_cursada)
    
    alumnos = query.order_by(Alumno.apellido, Alumno.nombre).all()
    
    return render_template('vista_año.html', año=año, alumnos=alumnos)

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

