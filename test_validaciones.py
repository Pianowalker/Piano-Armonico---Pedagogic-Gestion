"""
Tests de la lógica de validación de requisitos de examen.

Usan objetos simulados (SimpleNamespace) en lugar de modelos de la base de
datos, porque validar_requisitos_examen() solo lee atributos. Así los tests
son rápidos y no necesitan Flask ni SQLite.

Ejecutar con:  python -m pytest
"""

from types import SimpleNamespace

from validaciones import validar_requisitos_examen


# ----- Helpers para construir datos de prueba -----

def alumno(año, tipo='pianista', estado_academico='condicional', carrera=None):
    """Crea un alumno de prueba. 'condicional' es el estado que NO altera
    la cantidad mínima, útil para testear las reglas puras de cada año."""
    return SimpleNamespace(
        año=año,
        tipo=tipo,
        estado_academico=estado_academico,
        carrera=carrera,
    )


def trabajo(tipo='obra', estilo='académico', formato='piano solo',
            autoría_arreglo='propio', estado_estudio='resuelto',
            titulo='Obra de prueba', comentarios=''):
    return SimpleNamespace(
        tipo=tipo,
        estilo=estilo,
        formato=formato,
        autoría_arreglo=autoría_arreglo,
        estado_estudio=estado_estudio,
        titulo=titulo,
        comentarios=comentarios,
    )


def tiene(lista, fragmento):
    """True si algún mensaje de la lista contiene el fragmento dado."""
    return any(fragmento in mensaje for mensaje in lista)


# ----- Curso Técnica (caso especial con retorno temprano) -----

def test_tecnica_sin_trabajos_falta_todo():
    r = validar_requisitos_examen(alumno('Técnica'), [])
    assert tiene(r['faltantes'], 'Beyer')
    assert tiene(r['faltantes'], 'Bartók')
    assert tiene(r['faltantes'], 'Czerny')
    assert tiene(r['faltantes'], 'Obras: 0/3')
    assert r['cumplidos'] == []


def test_tecnica_completo_sin_faltantes():
    trabajos = [
        trabajo(tipo='estudio', titulo='Beyer Op.101 N°5'),
        trabajo(tipo='estudio', titulo='Bartók Mikrokosmos'),
        trabajo(tipo='estudio', titulo='Czerny Op.599'),
        trabajo(tipo='obra', titulo='Obra 1'),
        trabajo(tipo='obra', titulo='Obra 2'),
        trabajo(tipo='obra', titulo='Obra 3'),
    ]
    r = validar_requisitos_examen(alumno('Técnica'), trabajos)
    assert r['faltantes'] == []
    assert tiene(r['cumplidos'], 'Obras: 3/3')


def test_tecnica_detecta_autor_en_comentarios():
    # El autor puede estar en el título o en los comentarios.
    trabajos = [trabajo(tipo='estudio', titulo='Estudio N°5', comentarios='de Beyer')]
    r = validar_requisitos_examen(alumno('Técnica'), trabajos)
    assert tiene(r['cumplidos'], 'Beyer')


def test_tecnica_ignora_estudios_no_resueltos():
    trabajos = [trabajo(tipo='estudio', titulo='Beyer', estado_estudio='en proceso')]
    r = validar_requisitos_examen(alumno('Técnica'), trabajos)
    assert tiene(r['faltantes'], 'Beyer')


# ----- Cantidad mínima según año vs. estado académico -----

def test_condicional_usa_cantidad_del_año():
    # 'condicional' no altera la regla: FOBA 3 pide 5.
    r = validar_requisitos_examen(alumno('FOBA 3', estado_academico='condicional'), [])
    assert tiene(r['faltantes'], 'Cantidad mínima: 0/5')


def test_regular_fija_minimo_en_4_pisando_el_año():
    # Regla confirmada: el estado 'regular' fija la cantidad en 4 SIEMPRE,
    # incluso en Profesorado 3 (que por año pediría 8).
    r = validar_requisitos_examen(alumno('Profesorado 3', estado_academico='regular'), [])
    assert tiene(r['faltantes'], 'Cantidad mínima: 0/4')
    assert not tiene(r['faltantes'], '0/8')


def test_libre_fija_minimo_en_6_pisando_el_año():
    r = validar_requisitos_examen(alumno('FOBA Educación', estado_academico='libre'), [])
    assert tiene(r['faltantes'], 'Cantidad mínima: 0/6')


def test_solo_cuentan_trabajos_resueltos():
    trabajos = [trabajo(estado_estudio='en proceso') for _ in range(5)]
    r = validar_requisitos_examen(alumno('FOBA 3', estado_academico='condicional'), trabajos)
    assert tiene(r['faltantes'], 'Cantidad mínima: 0/5')


# ----- Estilos y formatos requeridos -----

def test_foba3_requiere_todos_los_estilos_y_formatos():
    r = validar_requisitos_examen(alumno('FOBA 3', estado_academico='condicional'), [])
    assert tiene(r['faltantes'], 'Falta estilo jazz')
    assert tiene(r['faltantes'], 'Falta estilo tango')
    assert tiene(r['faltantes'], 'Falta estilo folclore')
    assert tiene(r['faltantes'], 'Falta al menos un arreglo propio')
    assert tiene(r['faltantes'], 'Falta formato piano solo')
    assert tiene(r['faltantes'], 'Falta formato acompañamiento')


def test_piano_y_voz_cuenta_como_acompañamiento():
    trabajos = [trabajo(formato='piano y voz', estilo='jazz')]
    r = validar_requisitos_examen(alumno('FOBA 2 (canto)', estado_academico='condicional'), trabajos)
    assert tiene(r['cumplidos'], 'Formato acompañamiento presente')


# ----- Reglas para no pianistas -----

def test_no_pianista_requiere_estudios_y_obra_academica():
    r = validar_requisitos_examen(
        alumno('FOBA Educación', tipo='no pianista', estado_academico='condicional'), [])
    assert tiene(r['faltantes'], 'Faltan estudios')
    assert tiene(r['faltantes'], 'Falta obra académica')


def test_no_pianista_cumple_con_estudio_y_obra_academica():
    trabajos = [
        trabajo(tipo='estudio', estilo='académico'),
        trabajo(tipo='obra', estilo='académico'),
    ]
    r = validar_requisitos_examen(
        alumno('FOBA Educación', tipo='no pianista', estado_academico='condicional'), trabajos)
    assert tiene(r['cumplidos'], 'Estudios presentes')
    assert tiene(r['cumplidos'], 'Obra académica presente')


# ----- Requisitos específicos por carrera (Profesorado) -----

def test_profesorado_direccion_coral_requiere_piano_y_voz():
    r = validar_requisitos_examen(
        alumno('Profesorado 2', estado_academico='condicional', carrera='Dirección coral'), [])
    assert tiene(r['faltantes'], 'Falta formato piano y voz')
    assert tiene(r['faltantes'], 'Falta obra coral')


def test_profesorado_composicion_requiere_obra_propia():
    sin_obra = validar_requisitos_examen(
        alumno('Profesorado 1', estado_academico='condicional', carrera='Composición'), [])
    assert tiene(sin_obra['faltantes'], 'Falta composición propia')

    con_obra = validar_requisitos_examen(
        alumno('Profesorado 1', estado_academico='condicional', carrera='Composición'),
        [trabajo(tipo='obra')])
    assert tiene(con_obra['cumplidos'], 'Composición propia presente')


# ----- Año no reconocido: reglas mínimas -----

def test_año_no_reconocido_usa_reglas_minimas():
    r = validar_requisitos_examen(alumno('Curso Inventado', estado_academico='condicional'), [])
    assert tiene(r['faltantes'], 'Cantidad mínima: 0/3')
    assert not tiene(r['faltantes'], 'jazz')  # no exige estilos


# ----- Camino completo sin faltantes -----

def test_foba_educacion_completo_sin_faltantes():
    trabajos = [
        trabajo(estilo='jazz', formato='piano solo'),
        trabajo(estilo='académico', formato='piano y voz'),
        trabajo(estilo='académico', formato='piano solo'),
    ]
    r = validar_requisitos_examen(alumno('FOBA Educación', estado_academico='condicional'), trabajos)
    assert r['faltantes'] == []
