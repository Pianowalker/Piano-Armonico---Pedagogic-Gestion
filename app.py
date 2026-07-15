"""
Aplicación web para gestión pedagógica de Piano Armónico
Backend principal con Flask
"""

import unicodedata

from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import date, datetime, time as dt_time, timedelta
from typing import Optional
from models import db, Alumno, TrabajoMusical, SeguimientoClase, CicloArchivado
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
            print("Columna 'carrera' agregada exitosamente a la tabla 'alumnos'")

        # Migración: agregar columnas 'day' y 'time' (horario) si no existen
        # Nota: NO se validan como obligatorias; pueden ser NULL.
        if 'day' not in columns:
            db.session.execute(text('ALTER TABLE alumnos ADD COLUMN day VARCHAR(20)'))
            db.session.commit()
            print("Columna 'day' agregada exitosamente a la tabla 'alumnos'")

        if 'time' not in columns:
            db.session.execute(text('ALTER TABLE alumnos ADD COLUMN time VARCHAR(5)'))
            db.session.commit()
            print("Columna 'time' agregada exitosamente a la tabla 'alumnos'")

        # Migración: agregar 'ciclo_id' a trabajos y seguimientos (historial de ciclos).
        # NULL = pertenece al año en curso; con valor = ciclo archivado.
        cols_trabajos = [col['name'] for col in inspector.get_columns('trabajos_musicales')]
        if 'ciclo_id' not in cols_trabajos:
            db.session.execute(text('ALTER TABLE trabajos_musicales ADD COLUMN ciclo_id INTEGER REFERENCES ciclos_archivados(id)'))
            db.session.commit()
            print("Columna 'ciclo_id' agregada a 'trabajos_musicales'")

        cols_seg = [col['name'] for col in inspector.get_columns('seguimientos_clase')]
        if 'ciclo_id' not in cols_seg:
            db.session.execute(text('ALTER TABLE seguimientos_clase ADD COLUMN ciclo_id INTEGER REFERENCES ciclos_archivados(id)'))
            db.session.commit()
            print("Columna 'ciclo_id' agregada a 'seguimientos_clase'")
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

# Años/cursos disponibles (para promover al cerrar una cursada).
AÑOS = [
    'FOBA Educación', 'FOBA 2 (canto)', 'FOBA 3',
    'Profesorado 1', 'Profesorado 2', 'Profesorado 3', 'Profesorado 4',
    'Técnica',
]

RESULTADOS_CIERRE = ['aprobó', 'abandonó', 'cambió de cátedra']


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


def normalizar_busqueda(value: str) -> str:
    """Quita acentos y pasa a minúsculas para comparar sin distinguir tildes."""
    sin_acentos = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    return sin_acentos.casefold()

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
    # Por defecto (sin el parámetro en la URL) mostramos solo alumnos activos.
    # El valor '' (opción "Todos") desactiva el filtro explícitamente.
    estado_cursada = request.args.get('estado_cursada')
    if estado_cursada is None:
        estado_cursada = 'activo'
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

    alumnos = query.order_by(Alumno.apellido, Alumno.nombre).all()

    if busqueda:
        busqueda_normalizada = normalizar_busqueda(busqueda)
        alumnos = [
            a for a in alumnos
            if busqueda_normalizada in normalizar_busqueda(a.nombre_completo)
        ]

    total_alumnos = len(alumnos)

    # Progreso de requisitos por alumno (para la barra en la lista).
    # Cargamos todos los trabajos en una sola query y los agrupamos, para
    # evitar una consulta por alumno.
    progreso = {}
    if alumnos:
        ids = [a.id for a in alumnos]
        trabajos_por_alumno = {}
        trabajos_activos = TrabajoMusical.query.filter(
            TrabajoMusical.alumno_id.in_(ids),
            TrabajoMusical.ciclo_id.is_(None),
        ).all()
        for t in trabajos_activos:
            trabajos_por_alumno.setdefault(t.alumno_id, []).append(t)

        for a in alumnos:
            req = validar_requisitos_examen(a, trabajos_por_alumno.get(a.id, []))
            cumplidos = len(req['cumplidos'])
            total = cumplidos + len(req['faltantes'])
            progreso[a.id] = {
                'cumplidos': cumplidos,
                'total': total,
                'porcentaje': round(cumplidos / total * 100) if total else None,
            }

    return render_template(
        'lista_alumnos.html',
        alumnos=alumnos,
        total_alumnos=total_alumnos,
        progreso=progreso,
        estado_cursada_sel=estado_cursada,
    )


@app.route('/repertorio')
def repertorio():
    """Búsqueda de repertorio: qué alumnos trabajaron tal obra/estilo/formato.
    Busca solo en el repertorio activo (el histórico queda dentro de cada
    ciclo archivado, consultable desde el perfil del alumno)."""
    estilo = request.args.get('estilo', '')
    tipo = request.args.get('tipo', '')
    formato = request.args.get('formato', '')
    estado_estudio = request.args.get('estado_estudio', '')
    busqueda = request.args.get('busqueda', '').strip()

    query = TrabajoMusical.query.filter(TrabajoMusical.ciclo_id.is_(None))

    if estilo:
        query = query.filter(TrabajoMusical.estilo == estilo)
    if tipo:
        query = query.filter(TrabajoMusical.tipo == tipo)
    if formato:
        query = query.filter(TrabajoMusical.formato == formato)
    if estado_estudio:
        query = query.filter(TrabajoMusical.estado_estudio == estado_estudio)

    trabajos = query.join(Alumno).order_by(Alumno.apellido, Alumno.nombre, TrabajoMusical.titulo).all()

    if busqueda:
        busqueda_normalizada = normalizar_busqueda(busqueda)
        trabajos = [t for t in trabajos if busqueda_normalizada in normalizar_busqueda(t.titulo)]

    hay_filtros = any([estilo, tipo, formato, estado_estudio, busqueda])

    return render_template(
        'repertorio.html',
        trabajos=trabajos,
        hay_filtros=hay_filtros,
        filtros={
            'estilo': estilo, 'tipo': tipo, 'formato': formato,
            'estado_estudio': estado_estudio, 'busqueda': busqueda,
        },
    )


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
        flash(f'Alumno {alumno.nombre_completo} creado correctamente.', 'success')
        return redirect(url_for('perfil_alumno', id=alumno.id))

    return render_template('form_alumno.html')

@app.route('/alumnos/<int:id>')
def perfil_alumno(id):
    """Perfil completo del alumno"""
    alumno = Alumno.query.get_or_404(id)
    # Solo el repertorio activo (del año en curso); lo archivado no cuenta.
    trabajos = (
        TrabajoMusical.query
        .filter_by(alumno_id=id, ciclo_id=None)
        .order_by(TrabajoMusical.id.desc())
        .all()
    )

    # Validar requisitos de examen
    requisitos = validar_requisitos_examen(alumno, trabajos)

    return render_template(
        'perfil_alumno.html',
        alumno=alumno,
        trabajos=trabajos,
        requisitos=requisitos,
    )


def trabajos_seleccionados(alumno):
    """Devuelve los trabajos marcados en el form que pertenecen al alumno.
    Filtrar por alumno evita que se enlace una obra ajena manipulando el form."""
    ids = request.form.getlist('trabajos')
    if not ids:
        return []
    ids_int = [int(i) for i in ids if i.isdigit()]
    if not ids_int:
        return []
    return TrabajoMusical.query.filter(
        TrabajoMusical.id.in_(ids_int),
        TrabajoMusical.alumno_id == alumno.id,
    ).all()


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
            seguimiento.trabajos = trabajos_seleccionados(alumno)
            db.session.add(seguimiento)
            db.session.commit()
            flash('Seguimiento guardado correctamente.', 'success')
            return redirect(url_for('seguimiento_alumno', id=alumno.id))

    seguimientos = (
        SeguimientoClase.query
        .filter_by(alumno_id=alumno.id, ciclo_id=None)
        .order_by(SeguimientoClase.fecha.desc(), SeguimientoClase.id.desc())
        .all()
    )

    trabajos = (
        TrabajoMusical.query
        .filter_by(alumno_id=alumno.id, ciclo_id=None)
        .order_by(TrabajoMusical.id.desc())
        .all()
    )

    return render_template(
        'seguimiento_alumno.html',
        alumno=alumno,
        seguimientos=seguimientos,
        trabajos=trabajos,
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
        flash('Cambios guardados correctamente.', 'success')
        return redirect(url_for('perfil_alumno', id=alumno.id))

    return render_template('form_alumno.html', alumno=alumno)

@app.route('/alumnos/<int:id>/eliminar', methods=['POST'])
def eliminar_alumno(id):
    """Eliminar alumno"""
    alumno = Alumno.query.get_or_404(id)
    nombre = alumno.nombre_completo
    db.session.delete(alumno)
    db.session.commit()
    flash(f'Alumno {nombre} eliminado.', 'success')
    return redirect(url_for('lista_alumnos'))

@app.route('/alumnos/<int:id>/cerrar-cursada', methods=['GET', 'POST'])
def cerrar_cursada(id):
    """Archiva el año en curso de un alumno (repertorio + seguimientos) y,
    según el resultado, lo promueve al año siguiente o lo marca como inactivo."""
    alumno = Alumno.query.get_or_404(id)
    error = None

    if request.method == 'POST':
        resultado = request.form.get('resultado', '')
        año_nuevo = (request.form.get('año_nuevo') or '').strip()
        año_calendario_str = (request.form.get('año_calendario') or '').strip()

        if resultado not in RESULTADOS_CIERRE:
            error = 'Elegí un resultado válido.'
        elif resultado == 'aprobó' and año_nuevo not in AÑOS:
            error = 'Si el alumno aprobó, elegí a qué año pasa.'
        else:
            try:
                año_calendario = int(año_calendario_str)
            except ValueError:
                año_calendario = date.today().year

            ciclo = CicloArchivado(
                alumno_id=alumno.id,
                año=alumno.año,
                año_calendario=año_calendario,
                resultado=resultado,
                año_nuevo=año_nuevo if resultado == 'aprobó' else None,
            )
            db.session.add(ciclo)
            db.session.flush()  # asigna ciclo.id antes de mover el repertorio

            # Mover el repertorio y los seguimientos activos al ciclo archivado.
            for t in TrabajoMusical.query.filter_by(alumno_id=alumno.id, ciclo_id=None):
                t.ciclo_id = ciclo.id
            for s in SeguimientoClase.query.filter_by(alumno_id=alumno.id, ciclo_id=None):
                s.ciclo_id = ciclo.id

            if resultado == 'aprobó':
                alumno.año = año_nuevo
                alumno.estado_cursada = 'activo'
                # Si el nuevo año no es de profesorado, la carrera deja de aplicar.
                if not año_nuevo.startswith('Profesorado'):
                    alumno.carrera = None
                mensaje = f'Cursada cerrada. {alumno.nombre_completo} pasa a {año_nuevo}.'
            else:
                alumno.estado_cursada = 'abandonó'
                mensaje = f'Cursada cerrada ({resultado}). {alumno.nombre_completo} queda como inactivo.'

            db.session.commit()
            flash(mensaje, 'success')
            return redirect(url_for('perfil_alumno', id=alumno.id))

    return render_template(
        'cerrar_cursada.html',
        alumno=alumno,
        años=AÑOS,
        resultados=RESULTADOS_CIERRE,
        año_actual=date.today().year,
        error=error,
    )


@app.route('/alumnos/<int:id>/ciclo/<int:ciclo_id>')
def ver_ciclo(id, ciclo_id):
    """Vista de solo lectura de un ciclo archivado."""
    alumno = Alumno.query.get_or_404(id)
    ciclo = CicloArchivado.query.filter_by(id=ciclo_id, alumno_id=alumno.id).first_or_404()

    trabajos = (
        TrabajoMusical.query
        .filter_by(ciclo_id=ciclo.id)
        .order_by(TrabajoMusical.id.desc())
        .all()
    )
    seguimientos = (
        SeguimientoClase.query
        .filter_by(ciclo_id=ciclo.id)
        .order_by(SeguimientoClase.fecha.desc(), SeguimientoClase.id.desc())
        .all()
    )

    return render_template(
        'ver_ciclo.html',
        alumno=alumno,
        ciclo=ciclo,
        trabajos=trabajos,
        seguimientos=seguimientos,
    )


@app.route('/alumnos/<int:id>/trabajo/nuevo', methods=['GET', 'POST'])
def nuevo_trabajo(id):
    """Agregar trabajo musical a un alumno.
    Si la petición es AJAX (desde el seguimiento) devuelve JSON en vez de
    redirigir, para poder agregar el trabajo sin salir de la página."""
    alumno = Alumno.query.get_or_404(id)
    es_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        titulo = (request.form.get('titulo') or '').strip()
        tipo = request.form.get('tipo', '')
        estilo = request.form.get('estilo', '')
        formato = request.form.get('formato', '')
        estado_estudio = request.form.get('estado_estudio', '')

        if es_ajax and not (titulo and tipo and estilo and formato and estado_estudio):
            return {'error': 'Faltan datos del trabajo.'}, 400

        trabajo = TrabajoMusical(
            titulo=titulo,
            tipo=tipo,
            estilo=estilo,
            formato=formato,
            autoría_arreglo=request.form.get('autoría_arreglo', 'propio'),
            estado_estudio=estado_estudio,
            comentarios=request.form.get('comentarios', ''),
            alumno_id=id
        )
        db.session.add(trabajo)
        db.session.commit()

        if es_ajax:
            return {
                'id': trabajo.id,
                'titulo': trabajo.titulo,
                'estado_estudio': trabajo.estado_estudio,
            }

        flash(f'Trabajo «{trabajo.titulo}» agregado.', 'success')
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
        flash('Trabajo actualizado correctamente.', 'success')
        return redirect(url_for('perfil_alumno', id=trabajo.alumno_id))

    return render_template('form_trabajo.html', trabajo=trabajo, alumno=trabajo.alumno)

@app.route('/trabajos/<int:id>/eliminar', methods=['POST'])
def eliminar_trabajo(id):
    """Eliminar trabajo musical"""
    trabajo = TrabajoMusical.query.get_or_404(id)
    alumno_id = trabajo.alumno_id
    titulo = trabajo.titulo
    db.session.delete(trabajo)
    db.session.commit()
    flash(f'Trabajo «{titulo}» eliminado.', 'success')
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
            seguimiento.trabajos = trabajos_seleccionados(alumno)
            db.session.commit()
            flash('Seguimiento actualizado correctamente.', 'success')
            return redirect(url_for('seguimiento_alumno', id=alumno.id))

    seguimientos = (
        SeguimientoClase.query
        .filter_by(alumno_id=alumno.id, ciclo_id=None)
        .order_by(SeguimientoClase.fecha.desc(), SeguimientoClase.id.desc())
        .all()
    )

    trabajos = (
        TrabajoMusical.query
        .filter_by(alumno_id=alumno.id, ciclo_id=None)
        .order_by(TrabajoMusical.id.desc())
        .all()
    )

    return render_template(
        'seguimiento_alumno.html',
        alumno=alumno,
        seguimientos=seguimientos,
        trabajos=trabajos,
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
    flash('Seguimiento eliminado.', 'success')
    return redirect(url_for('seguimiento_alumno', id=alumno_id))


@app.route('/ano/<ano>')
def vista_año(ano):
    """Vista de alumnos por año/curso"""
    # El parámetro 'ano' viene de la URL, pero internamente usamos 'año' para la lógica
    año = ano

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
    """Agenda visual semanal: los tres días se muestran juntos.

    El parámetro 'day' es opcional y solo se usa para saltar directo
    (ancla) a la columna de ese día desde los accesos rápidos del menú.
    """
    day_destacado = (request.args.get('day') or '').strip().lower()
    if day_destacado not in DIAS_HORARIOS:
        day_destacado = None

    alumnos_activos = (
        Alumno.query
        .filter(Alumno.day.in_(DIAS_HORARIOS))
        .filter(Alumno.time.isnot(None))
        .filter(Alumno.time != '')
        .filter(Alumno.estado_cursada == 'activo')
        .order_by(Alumno.time.asc(), Alumno.apellido.asc(), Alumno.nombre.asc())
        .all()
    )

    semana = []
    for d in DIAS_HORARIOS:
        alumnos_por_hora: dict[str, list[Alumno]] = {}
        for a in alumnos_activos:
            if a.day == d and a.time:
                alumnos_por_hora.setdefault(a.time, []).append(a)
        semana.append({
            'day': d,
            'slug': normalizar_busqueda(d),  # sin tilde, para usar como ancla #
            'slots': generar_slots(d),
            'alumnos_por_hora': alumnos_por_hora,
        })

    return render_template(
        'horarios.html',
        semana=semana,
        day_destacado=day_destacado,
    )

if __name__ == '__main__':
    import os
    app.run(debug=True, host='127.0.0.1', port=int(os.environ.get('PORT', 5000)))

