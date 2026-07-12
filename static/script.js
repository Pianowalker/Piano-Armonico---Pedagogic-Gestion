// JavaScript para interactividad adicional
// Funcionalidad básica - la mayoría se maneja con formularios HTML estándar

document.addEventListener('DOMContentLoaded', function() {
    // Confirmación antes de eliminar trabajos (solo para trabajos musicales, no para alumnos)
    // Los formularios de eliminación de alumnos ya tienen su propia confirmación inline en el HTML
    // Buscar todos los formularios de eliminación, pero excluir los de alumnos
    const deleteForms = document.querySelectorAll('form[action*="eliminar"]');
    deleteForms.forEach(form => {
        const action = form.getAttribute('action') || '';
        // Solo procesar formularios de TRABAJOS, excluir alumnos
        if (action.includes('/trabajos/') && action.includes('/eliminar') && !action.includes('/alumnos/')) {
            // Solo agregar confirmación si el formulario no tiene ya un onsubmit definido
            // Esto evita dobles confirmaciones
            if (!form.hasAttribute('onsubmit')) {
                form.addEventListener('submit', function(e) {
                    if (!confirm('¿Está seguro de eliminar este trabajo?')) {
                        e.preventDefault();
                    }
                });
            }
        }
    });
    
    // Mostrar/ocultar campo de autoría del arreglo según el tipo
    const tipoSelect = document.getElementById('tipo');
    const autoriaGroup = document.getElementById('autoría-group');
    const autoriaSelect = document.getElementById('autoría_arreglo');
    
    if (tipoSelect && autoriaGroup) {
        function toggleAutoria() {
            if (tipoSelect.value === 'arreglo') {
                autoriaGroup.style.display = 'block';
                autoriaSelect.required = true;
            } else {
                autoriaGroup.style.display = 'none';
                autoriaSelect.required = false;
            }
        }
        
        // Ejecutar al cargar la página
        toggleAutoria();
        
        // Ejecutar al cambiar el tipo
        tipoSelect.addEventListener('change', toggleAutoria);
    }
    
    // Mostrar/ocultar campo de carrera según el año
    const añoSelect = document.getElementById('año');
    const carreraGroup = document.getElementById('carrera-group');
    
    if (añoSelect && carreraGroup) {
        function toggleCarrera() {
            if (añoSelect.value && añoSelect.value.startsWith('Profesorado')) {
                carreraGroup.style.display = 'block';
            } else {
                carreraGroup.style.display = 'none';
            }
        }
        
        // Ejecutar al cargar la página
        toggleCarrera();
        
        // Ejecutar al cambiar el año
        añoSelect.addEventListener('change', toggleCarrera);
    }
    
    // En la agenda semanal, al llegar con un día resaltado (?day=...),
    // scrollear hasta esa columna. Útil en móvil, donde los días se apilan.
    // Se hace por JS (y no con ancla #) para evitar que la carga de fuentes
    // desplace el layout después del salto nativo del navegador.
    const diaDestacado = document.querySelector('.dia-destacado');
    if (diaDestacado) {
        window.addEventListener('load', function() {
            diaDestacado.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    }

    // En "Cerrar cursada", el campo "Pasa al año" solo aplica si el alumno aprobó.
    const resultadoSelect = document.getElementById('resultado');
    const añoNuevoGroup = document.getElementById('año-nuevo-group');
    const añoNuevoSelect = document.getElementById('año_nuevo');
    if (resultadoSelect && añoNuevoGroup) {
        function toggleAñoNuevo() {
            const aprobo = resultadoSelect.value === 'aprobó';
            añoNuevoGroup.style.display = aprobo ? 'block' : 'none';
            if (añoNuevoSelect) añoNuevoSelect.required = aprobo;
        }
        toggleAñoNuevo();
        resultadoSelect.addEventListener('change', toggleAñoNuevo);
    }

    // Auto-ocultar los mensajes flash de éxito después de unos segundos.
    // Los de error/otros se dejan hasta que el usuario los cierre a mano.
    document.querySelectorAll('.flash-success').forEach(function(flash) {
        setTimeout(function() {
            flash.classList.add('flash-saliente');
            flash.addEventListener('transitionend', function() {
                flash.remove();
            });
        }, 4000);
    });

    // Dictado por voz para el campo de comentarios del seguimiento.
    // Usa la Web Speech API nativa del navegador (requiere HTTPS en producción).
    // El botón solo se muestra si el navegador soporta reconocimiento de voz.
    const btnDictado = document.getElementById('btn-dictado');
    const textareaComentarios = document.getElementById('comentarios');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (btnDictado && textareaComentarios && SpeechRecognition) {
        const estado = document.getElementById('dictado-estado');
        const recognition = new SpeechRecognition();
        recognition.lang = 'es-AR';
        // continuous=false es más fiable en Android Chrome: cada sesión entrega
        // solo los resultados de esa utterance, sin acumular sesiones anteriores
        // (lo que causaba palabras repetidas). Reiniciamos manualmente en 'end'.
        recognition.continuous = false;
        recognition.interimResults = true;

        let escuchando = false;
        let baseText = '';

        btnDictado.hidden = false;

        function setEstado(mensaje) {
            if (estado) estado.textContent = mensaje;
        }

        function sep(texto) {
            if (!texto) return '';
            return /\s$/.test(texto) ? '' : ' ';
        }

        function iniciar() {
            baseText = textareaComentarios.value;
            try { recognition.start(); } catch(e) {}
        }

        btnDictado.addEventListener('click', function() {
            if (escuchando) {
                escuchando = false;
                recognition.stop();
            } else {
                escuchando = true;
                iniciar();
            }
        });

        recognition.addEventListener('start', function() {
            btnDictado.classList.add('grabando');
            btnDictado.setAttribute('aria-pressed', 'true');
            btnDictado.querySelector('.dictado-texto').textContent = 'Detener';
            setEstado('Escuchando… hablá con normalidad.');
        });

        recognition.addEventListener('result', function(event) {
            let finalTexto = '';
            let interimTexto = '';
            for (let i = 0; i < event.results.length; i++) {
                const t = event.results[i][0].transcript;
                if (event.results[i].isFinal) finalTexto += t;
                else interimTexto += t;
            }
            if (finalTexto) {
                textareaComentarios.value = baseText + sep(baseText) + finalTexto.trim();
            } else if (interimTexto) {
                textareaComentarios.value = baseText + sep(baseText) + interimTexto.trim();
            }
        });

        recognition.addEventListener('end', function() {
            if (escuchando) {
                // El usuario no detuvo — confirmar lo transcripto y reiniciar
                baseText = textareaComentarios.value;
                try { recognition.start(); } catch(e) {}
            } else {
                btnDictado.classList.remove('grabando');
                btnDictado.setAttribute('aria-pressed', 'false');
                btnDictado.querySelector('.dictado-texto').textContent = 'Dictar';
                if (estado && estado.textContent.startsWith('Escuchando')) setEstado('');
            }
        });

        recognition.addEventListener('error', function(event) {
            if (event.error === 'aborted' || event.error === 'no-speech') return;
            escuchando = false;
            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                setEstado('Permiso de micrófono denegado. Habilitalo en el navegador.');
            } else {
                setEstado('Error de dictado: ' + event.error);
            }
        });
    }

    // Mejora de UX: auto-submit en algunos filtros (opcional)
    // Puedes descomentar si quieres que los filtros se apliquen automáticamente
    /*
    const autoSubmitFilters = document.querySelectorAll('.filtros-form select');
    autoSubmitFilters.forEach(select => {
        select.addEventListener('change', function() {
            // Opcional: auto-submit después de un pequeño delay
            setTimeout(() => {
                this.form.submit();
            }, 300);
        });
    });
    */
});

