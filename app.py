"""
Aplicación web para gestión pedagógica de Piano Armónico
Backend principal con Flask
"""

from flask import Flask, render_template, request, redirect, url_for
from datetime import date, datetime, time as dt_time, timedelta
from typing import Optional
from models import db, Alumno, TrabajoMusical, SeguimientoClase
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

        # Migración: agregar columnas 'day' y 'time' (horario) si no existen
        # Nota: NO se validan como obligatorias; pueden ser NULL.
        if 'day' not in columns:
            db.session.execute(text('ALTER TABLE alumnos ADD COLUMN day VARCHAR(20)'))
            db.session.commit()
            print("✓ Columna 'day' agregada exitosamente a la tabla 'alumnos'")

        if 'time' not in columns:
            db.session.execute(text('ALTER TABLE alumnos ADD COLUMN time VARCHAR(5)'))
            db.session.commit()
            print("✓ Columna 'time' agregada exitosamente a la tabla 'alumnos'")
    except Exception as e:
        # Si la tabla no existe aún, create_all() la creará con todas las columnas
        # Si hay otro error, lo mostramos pero no detenemos la aplicación
        print(f"Nota sobre migración de base de datos: {e}")
        db.session.rollback()


DIAS_HORARIOS = ['lunes', 'martes', 'miércoles']

RANGOS_HORARIOS = {
    'lunes': ('18:00', '22:00'),
    'martes': ('08:00', '16:00'),
    'miércoles': ('18:00', '22:00'),
}

INTERVALO_MINUTOS = 15


def _parse_hhmm(value: str) -> dt_time:
    return datetime.strptime(value, '%H:%M').time()


def generar_slots(day: str) -> list[str]:
    """Genera slots (HH:mm) para el día. No persiste nada en DB."""
    if day not in RANGOS_HORARIOS:
        return []

    inicio_str, fin_str = RANGOS_HORARIOS[day]
    inicio = datetime.combine(date.today(), _parse_hhmm(inicio_str))
    fin = datetime.combine(date.today(), _parse_hhmm(fin_str))

    slots: list[str] = []
    actual = inicio
    while actual <= fin:
        slots.append(actual.strftime('%H:%M'))
        actual += timedelta(minutes=INTERVALO_MINUTOS)
    return slots


def normalizar_horario(form_value: Optional[str]) -> Optional[str]:
    """Normaliza inputs vacíos a None. No valida obligatoriedad."""
    if form_value is None:
        return None
    value = form_value.strip()
    return value or None

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
            day=normalizar_horario(request.form.get('day')),
            time=normalizar_horario(request.form.get('time')),
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
    
    return render_template(
        'perfil_alumno.html',
        alumno=alumno,
        trabajos=trabajos,
        requisitos=requisitos,
    )


@app.route('/alumnos/<int:id>/seguimiento', methods=['GET', 'POST'])
def seguimiento_alumno(id):
    """Página de seguimiento clase a clase de un alumno"""
    alumno = Alumno.query.get_or_404(id)
    error = None
    
    if request.method == 'POST':
        comentarios = (request.form.get('comentarios') or '').strip()
        fecha_str = (request.form.get('fecha') or '').strip()
        
        if not comentarios:
            error = 'Los comentarios no pueden estar vacíos.'
        else:
            if fecha_str:
                try:
                    fecha_valor = date.fromisoformat(fecha_str)
                except ValueError:
                    fecha_valor = date.today()
            else:
                fecha_valor = date.today()
            
            seguimiento = SeguimientoClase(
                fecha=fecha_valor,
                comentarios=comentarios,
                alumno_id=alumno.id,
            )
            db.session.add(seguimiento)
            db.session.commit()
            return redirect(url_for('seguimiento_alumno', id=alumno.id))
    
    seguimientos = (
        SeguimientoClase.query
        .filter_by(alumno_id=alumno.id)
        .order_by(SeguimientoClase.fecha.asc(), SeguimientoClase.id.asc())
        .all()
    )
    
    return render_template(
        'seguimiento_alumno.html',
        alumno=alumno,
        seguimientos=seguimientos,
        error=error,
        hoy=date.today().isoformat(),
    )

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
        alumno.day = normalizar_horario(request.form.get('day'))
        alumno.time = normalizar_horario(request.form.get('time'))
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

@app.route('/seguimientos/<int:id>/editar', methods=['GET', 'POST'])
def editar_seguimiento(id):
    """Editar seguimiento de clase"""
    seguimiento = SeguimientoClase.query.get_or_404(id)
    alumno = seguimiento.alumno
    error = None

    if request.method == 'POST':
        comentarios = (request.form.get('comentarios') or '').strip()
        fecha_str = (request.form.get('fecha') or '').strip()

        if not comentarios:
            error = 'Los comentarios no pueden estar vacíos.'
        else:
            if fecha_str:
                try:
                    seguimiento.fecha = date.fromisoformat(fecha_str)
                except ValueError:
                    pass
            seguimiento.comentarios = comentarios
            db.session.commit()
            return redirect(url_for('seguimiento_alumno', id=alumno.id))

    seguimientos = (
        SeguimientoClase.query
        .filter_by(alumno_id=alumno.id)
        .order_by(SeguimientoClase.fecha.asc(), SeguimientoClase.id.asc())
        .all()
    )

    return render_template(
        'seguimiento_alumno.html',
        alumno=alumno,
        seguimientos=seguimientos,
        error=error,
        hoy=date.today().isoformat(),
        editando=seguimiento,
    )


@app.route('/seguimientos/<int:id>/eliminar', methods=['POST'])
def eliminar_seguimiento(id):
    """Eliminar seguimiento de clase"""
    seguimiento = SeguimientoClase.query.get_or_404(id)
    alumno_id = seguimiento.alumno_id
    db.session.delete(seguimiento)
    db.session.commit()
    return redirect(url_for('seguimiento_alumno', id=alumno_id))


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


@app.route('/horarios')
def horarios():
    """Agenda visual por día: slots generados dinámicamente."""
    day = (request.args.get('day') or 'lunes').strip().lower()
    if day not in DIAS_HORARIOS:
        day = 'lunes'

    slots = generar_slots(day)

    alumnos = (
        Alumno.query
        .filter(Alumno.day == day)
        .filter(Alumno.time.isnot(None))
        .filter(Alumno.time != '')
        .filter(Alumno.estado_cursada == 'activo')
        .order_by(Alumno.time.asc(), Alumno.apellido.asc(), Alumno.nombre.asc())
        .all()
    )

    alumnos_por_hora: dict[str, list[Alumno]] = {}
    for a in alumnos:
        if not a.time:
            continue
        alumnos_por_hora.setdefault(a.time, []).append(a)

    return render_template(
        'horarios.html',
        day=day,
        dias=DIAS_HORARIOS,
        slots=slots,
        alumnos_por_hora=alumnos_por_hora,
    )

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

