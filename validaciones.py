"""
Lógica de validación de requisitos de examen
Las reglas están hardcodeadas según año y tipo de alumno
"""

def validar_requisitos_examen(alumno, trabajos):
    """
    Valida los requisitos de examen para un alumno según su año y tipo.
    Retorna un diccionario con el estado de cada requisito.
    """
    requisitos = {
        'cumplidos': [],
        'faltantes': [],
        'resumen': {}
    }
    
    # Filtrar solo trabajos resueltos para requisitos
    trabajos_resueltos = [t for t in trabajos if t.estado_estudio == 'resuelto']
    
    # Reglas según año y tipo
    año = alumno.año
    tipo = alumno.tipo
    
    # ===== CASO ESPECIAL: CURSO TÉCNICA =====
    if año == 'Técnica':
        # Requisitos exclusivos para Técnica
        # Estudios obligatorios: Beyer, Bartók, Czerny
        estudios_beyer = [t for t in trabajos_resueltos 
                         if t.tipo == 'estudio' and ('beyer' in t.titulo.lower() or 'beyer' in (t.comentarios or '').lower())]
        estudios_bartok = [t for t in trabajos_resueltos 
                          if t.tipo == 'estudio' and ('bartók' in t.titulo.lower() or 'bartok' in t.titulo.lower() or 
                                                       'bartók' in (t.comentarios or '').lower() or 'bartok' in (t.comentarios or '').lower())]
        estudios_czerny = [t for t in trabajos_resueltos 
                          if t.tipo == 'estudio' and ('czerny' in t.titulo.lower() or 'czerny' in (t.comentarios or '').lower())]
        
        # Obras (mínimo 3)
        obras = [t for t in trabajos_resueltos if t.tipo == 'obra']
        cantidad_obras = len(obras)
        
        # Validar estudios
        if len(estudios_beyer) >= 1:
            requisitos['cumplidos'].append("Estudios de Beyer presente")
        else:
            requisitos['faltantes'].append("Faltan estudios de Beyer")
        
        if len(estudios_bartok) >= 1:
            requisitos['cumplidos'].append("Estudios de Bartók presente")
        else:
            requisitos['faltantes'].append("Faltan estudios de Bartók")
        
        if len(estudios_czerny) >= 1:
            requisitos['cumplidos'].append("Estudios de Czerny presente")
        else:
            requisitos['faltantes'].append("Faltan estudios de Czerny")
        
        # Validar obras
        if cantidad_obras >= 3:
            requisitos['cumplidos'].append(f"Obras: {cantidad_obras}/3 mínimo cumplido")
        else:
            requisitos['faltantes'].append(f"Obras: {cantidad_obras}/3 mínimo (faltan {3 - cantidad_obras})")
        
        return requisitos
    
    # ===== REGLAS GENERALES POR AÑO =====
    
    if año == 'FOBA Educación':
        requisitos['resumen'] = {
            'cantidad_minima': 3,
            'requiere_jazz': True,
            'requiere_tango': False,
            'requiere_folclore': False,
            'requiere_arreglos_propios': False,
            'requiere_piano_solo': True,
            'requiere_acompañamiento': False
        }
    
    elif año == 'FOBA 2 (canto)':
        requisitos['resumen'] = {
            'cantidad_minima': 4,
            'requiere_jazz': True,
            'requiere_tango': True,
            'requiere_folclore': False,
            'requiere_arreglos_propios': False,
            'requiere_piano_solo': True,
            'requiere_acompañamiento': True
        }
    
    elif año == 'FOBA 3':
        requisitos['resumen'] = {
            'cantidad_minima': 5,
            'requiere_jazz': True,
            'requiere_tango': True,
            'requiere_folclore': True,
            'requiere_arreglos_propios': True,
            'requiere_piano_solo': True,
            'requiere_acompañamiento': True
        }
    
    elif año.startswith('Profesorado'):
        # Profesorado 1, 2, 3, 4
        num_profesorado = int(año.split()[-1]) if año.split()[-1].isdigit() else 1
        requisitos['resumen'] = {
            'cantidad_minima': 5 + num_profesorado,  # 6, 7, 8, 9 según el año
            'requiere_jazz': True,
            'requiere_tango': True,
            'requiere_folclore': True,
            'requiere_arreglos_propios': True,
            'requiere_piano_solo': True,
            'requiere_acompañamiento': True
        }
    
    else:
        # Año no reconocido - reglas mínimas
        requisitos['resumen'] = {
            'cantidad_minima': 3,
            'requiere_jazz': False,
            'requiere_tango': False,
            'requiere_folclore': False,
            'requiere_arreglos_propios': False,
            'requiere_piano_solo': True,
            'requiere_acompañamiento': False
        }
    
    # ===== VALIDACIONES ESPECÍFICAS PARA NO PIANISTAS =====
    if tipo == 'no pianista':
        requisitos['resumen']['requiere_estudios'] = True
        requisitos['resumen']['requiere_obra_clasica'] = True
    
    # ===== AJUSTAR CANTIDAD MÍNIMA SEGÚN ESTADO ACADÉMICO =====
    # Regular: mínimo 4 trabajos, Libre: mínimo 6 trabajos
    estado_academico = alumno.estado_academico
    if estado_academico == 'regular':
        requisitos['resumen']['cantidad_minima'] = 4
    elif estado_academico == 'libre':
        requisitos['resumen']['cantidad_minima'] = 6
    # Para otros estados (condicional, oyente), mantener el valor calculado anteriormente
    
    # ===== VALIDAR REQUISITOS =====
    reglas = requisitos['resumen']
    
    # 1. Cantidad mínima
    cantidad_actual = len(trabajos_resueltos)
    if cantidad_actual >= reglas['cantidad_minima']:
        requisitos['cumplidos'].append(f"Cantidad mínima: {cantidad_actual}/{reglas['cantidad_minima']} trabajos resueltos")
    else:
        requisitos['faltantes'].append(f"Cantidad mínima: {cantidad_actual}/{reglas['cantidad_minima']} trabajos resueltos")
    
    # 2. Estilos requeridos
    estilos_presentes = set(t.estilo for t in trabajos_resueltos)
    
    if reglas.get('requiere_jazz'):
        if 'jazz' in estilos_presentes:
            requisitos['cumplidos'].append("Estilo jazz presente")
        else:
            requisitos['faltantes'].append("Falta estilo jazz")
    
    if reglas.get('requiere_tango'):
        if 'tango' in estilos_presentes:
            requisitos['cumplidos'].append("Estilo tango presente")
        else:
            requisitos['faltantes'].append("Falta estilo tango")
    
    if reglas.get('requiere_folclore'):
        if 'folclore' in estilos_presentes:
            requisitos['cumplidos'].append("Estilo folclore presente")
        else:
            requisitos['faltantes'].append("Falta estilo folclore")
    
    # 3. Formatos requeridos
    formatos_presentes = set(t.formato for t in trabajos_resueltos)
    # Piano y voz cuenta como acompañamiento
    tiene_acompañamiento = 'acompañamiento' in formatos_presentes or 'piano y voz' in formatos_presentes
    
    if reglas.get('requiere_piano_solo'):
        if 'piano solo' in formatos_presentes:
            requisitos['cumplidos'].append("Formato piano solo presente")
        else:
            requisitos['faltantes'].append("Falta formato piano solo")
    
    if reglas.get('requiere_acompañamiento'):
        if tiene_acompañamiento:
            requisitos['cumplidos'].append("Formato acompañamiento presente")
        else:
            requisitos['faltantes'].append("Falta formato acompañamiento")
    
    # Requisito específico: Piano y voz para canto, FOBA Educación y Dirección coral
    requiere_piano_y_voz = False
    if año == 'FOBA Educación' or año == 'FOBA 2 (canto)':
        requiere_piano_y_voz = True
    elif año.startswith('Profesorado') and hasattr(alumno, 'carrera') and alumno.carrera == 'Dirección coral':
        requiere_piano_y_voz = True
    
    if requiere_piano_y_voz:
        if 'piano y voz' in formatos_presentes:
            requisitos['cumplidos'].append("Formato piano y voz presente")
        else:
            requisitos['faltantes'].append("Falta formato piano y voz (requisito obligatorio)")
    
    # 4. Arreglos propios
    if reglas.get('requiere_arreglos_propios'):
        arreglos_propios = [t for t in trabajos_resueltos 
                           if t.tipo == 'arreglo' and t.autoría_arreglo == 'propio']
        if len(arreglos_propios) >= 1:
            requisitos['cumplidos'].append(f"Arreglos propios: {len(arreglos_propios)} presente(s)")
        else:
            requisitos['faltantes'].append("Falta al menos un arreglo propio")
    
    # 5. Requisitos específicos para no pianistas
    if tipo == 'no pianista':
        tiene_estudios = any(t.tipo == 'estudio' for t in trabajos_resueltos)
        tiene_obra_clasica = any(t.estilo == 'académico' for t in trabajos_resueltos)
        
        if tiene_estudios:
            requisitos['cumplidos'].append("Estudios presentes")
        else:
            requisitos['faltantes'].append("Faltan estudios")
        
        if tiene_obra_clasica:
            requisitos['cumplidos'].append("Obra académica presente")
        else:
            requisitos['faltantes'].append("Falta obra académica")
    
    # 6. Requisitos adicionales según carrera (solo para profesorado)
    if año.startswith('Profesorado') and hasattr(alumno, 'carrera') and alumno.carrera:
        carrera = alumno.carrera
        
        if carrera == 'Educación musical':
            # Debe incluir al menos una canción (formato piano y voz o acompañamiento, no académico)
            tiene_cancion = any(
                t.formato in ['piano y voz', 'acompañamiento'] and t.estilo != 'académico'
                for t in trabajos_resueltos
            )
            if tiene_cancion:
                requisitos['cumplidos'].append("Canción presente (requisito de Educación musical)")
            else:
                requisitos['faltantes'].append("Falta canción (requisito de Educación musical)")
        
        elif carrera == 'Instrumento':
            # Debe incluir un arreglo adicional a piano solo (arreglo con formato acompañamiento o piano y voz)
            tiene_arreglo_adicional = any(
                t.tipo == 'arreglo' and t.formato != 'piano solo'
                for t in trabajos_resueltos
            )
            if tiene_arreglo_adicional:
                requisitos['cumplidos'].append("Arreglo adicional a piano solo presente (requisito de Instrumento)")
            else:
                requisitos['faltantes'].append("Falta arreglo adicional a piano solo (requisito de Instrumento)")
        
        elif carrera == 'Composición':
            # Debe incluir una composición propia (tipo obra)
            tiene_composicion = any(t.tipo == 'obra' for t in trabajos_resueltos)
            if tiene_composicion:
                requisitos['cumplidos'].append("Composición propia presente (requisito de Composición)")
            else:
                requisitos['faltantes'].append("Falta composición propia (requisito de Composición)")
        
        elif carrera == 'Dirección coral':
            # Debe incluir una obra coral (formato piano y voz o acompañamiento)
            tiene_obra_coral = any(
                t.formato in ['piano y voz', 'acompañamiento']
                for t in trabajos_resueltos
            )
            if tiene_obra_coral:
                requisitos['cumplidos'].append("Obra coral presente (requisito de Dirección coral)")
            else:
                requisitos['faltantes'].append("Falta obra coral (requisito de Dirección coral)")
    
    return requisitos

