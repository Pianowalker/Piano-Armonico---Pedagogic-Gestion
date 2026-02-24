# Piano Armónico - Gestión Pedagógica

Aplicación web local para la gestión pedagógica de la materia "Piano Armónico" en un conservatorio.

## Características

- ✅ Registro de alumnos con información completa
- ✅ Gestión de trabajos musicales (repertorio) por alumno
- ✅ Validación automática de requisitos de examen según año y tipo de alumno
- ✅ Filtros y búsqueda de alumnos
- ✅ Vista por año/curso
- ✅ Interfaz clara y funcional

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## Instalación

1. Instalar las dependencias:
```bash
pip install -r requirements.txt
```

## Uso

1. Iniciar la aplicación:
```bash
python app.py
```

2. Abrir en el navegador:
```
http://127.0.0.1:5000
```

## Estructura del Proyecto

```
.
├── app.py                 # Aplicación principal Flask
├── models.py              # Modelos de datos (SQLAlchemy)
├── validaciones.py        # Lógica de validación de requisitos
├── requirements.txt       # Dependencias Python
├── piano_armonico.db     # Base de datos SQLite (se crea automáticamente)
├── templates/            # Plantillas HTML
│   ├── base.html
│   ├── lista_alumnos.html
│   ├── perfil_alumno.html
│   ├── form_alumno.html
│   ├── form_trabajo.html
│   └── vista_año.html
└── static/               # Archivos estáticos
    ├── style.css
    └── script.js
```

## Funcionalidades Principales

### Gestión de Alumnos
- Crear, editar y visualizar alumnos
- Filtros por año, tipo, estado académico y estado de cursada
- Búsqueda por nombre o apellido

### Gestión de Trabajos Musicales
- Agregar trabajos (estudios, obras, arreglos)
- Editar y eliminar trabajos
- Seguimiento del estado de estudio

### Validación de Requisitos
La aplicación valida automáticamente los requisitos de examen según:
- Año/curso del alumno
- Tipo de alumno (pianista / no pianista)
- Trabajos resueltos

Los requisitos incluyen:
- Cantidad mínima de trabajos
- Estilos requeridos (jazz, tango, folclore)
- Formatos requeridos (piano solo, acompañamiento)
- Arreglos propios
- Requisitos específicos para no pianistas

## Notas

- La base de datos se crea automáticamente en la primera ejecución
- Los datos se almacenan localmente en SQLite
- La aplicación está diseñada para uso local
- El código está estructurado para facilitar migración futura a backend remoto

## Desarrollo

Para modificar las reglas de validación de requisitos, editar el archivo `validaciones.py`.

