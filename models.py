"""
Modelos de datos para la aplicación Piano Armónico
Usa SQLAlchemy para facilitar migración futura a otros SGBD
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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
    comentarios = db.Column(db.Text)
    
    # Relación con trabajos musicales
    trabajos = db.relationship('TrabajoMusical', backref='alumno', lazy=True, cascade='all, delete-orphan')
    
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

