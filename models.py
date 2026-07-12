"""
Modelos de datos para la aplicación Piano Armónico
Usa SQLAlchemy para facilitar migración futura a otros SGBD
"""

from datetime import date

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# Tabla de asociación muchos-a-muchos entre seguimientos y trabajos:
# una clase puede trabajar varias obras y una obra aparece en varias clases.
seguimiento_trabajo = db.Table(
    'seguimiento_trabajo',
    db.Column('seguimiento_id', db.Integer,
              db.ForeignKey('seguimientos_clase.id'), primary_key=True),
    db.Column('trabajo_id', db.Integer,
              db.ForeignKey('trabajos_musicales.id'), primary_key=True),
)


class Alumno(db.Model):
    """Modelo de Alumno"""
    __tablename__ = 'alumnos'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    instrumento_principal = db.Column(db.String(100))
    tipo = db.Column(db.String(20), nullable=False)  # 'pianista' o 'no pianista'
    año = db.Column(db.String(50), nullable=False)
    estado_academico = db.Column(db.String(20), nullable=False)  # 'regular', 'condicional', 'oyente', 'libre'
    estado_cursada = db.Column(db.String(20), nullable=False)  # 'activo', 'abandonó'
    carrera = db.Column(db.String(50))  # 'Educación musical', 'Instrumento', 'Dirección coral', 'Composición' (solo para profesorado)
    # Horario (opcional)
    day = db.Column(db.String(20), nullable=True)   # lunes, martes, miércoles
    time = db.Column(db.String(5), nullable=True)   # HH:mm (ej: 18:00)
    comentarios = db.Column(db.Text)
    
    # Relación con trabajos musicales
    trabajos = db.relationship('TrabajoMusical', backref='alumno', lazy=True, cascade='all, delete-orphan')
    # Relación con seguimientos de clase
    seguimientos = db.relationship(
        'SeguimientoClase',
        backref='alumno',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='SeguimientoClase.fecha'
    )
    
    def __repr__(self):
        return f'<Alumno {self.apellido}, {self.nombre}>'
    
    @property
    def nombre_completo(self):
        return f"{self.apellido}, {self.nombre}"

class TrabajoMusical(db.Model):
    """Modelo de Trabajo Musical (repertorio)"""
    __tablename__ = 'trabajos_musicales'
    
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'estudio', 'obra', 'arreglo'
    estilo = db.Column(db.String(20), nullable=False)  # 'jazz', 'tango', 'folclore', 'académico', 'otro'
    formato = db.Column(db.String(30), nullable=False)  # 'piano solo', 'acompañamiento', 'piano y voz'
    autoría_arreglo = db.Column(db.String(20), nullable=False, default='propio')  # 'propio', 'ajeno'
    estado_estudio = db.Column(db.String(20), nullable=False)  # 'iniciado', 'en proceso', 'resuelto'
    comentarios = db.Column(db.Text)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)
    
    def __repr__(self):
        return f'<TrabajoMusical {self.titulo}>'


class SeguimientoClase(db.Model):
    """Modelo de seguimiento clase a clase de un alumno"""
    __tablename__ = 'seguimientos_clase'
    
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    comentarios = db.Column(db.Text, nullable=False)
    alumno_id = db.Column(db.Integer, db.ForeignKey('alumnos.id'), nullable=False)

    # Trabajos musicales abordados en esta clase (muchos-a-muchos).
    trabajos = db.relationship(
        'TrabajoMusical',
        secondary=seguimiento_trabajo,
        backref=db.backref('seguimientos', lazy='select'),
        lazy='joined',
    )

    def __repr__(self):
        return f'<SeguimientoClase {self.fecha} - Alumno {self.alumno_id}>'

