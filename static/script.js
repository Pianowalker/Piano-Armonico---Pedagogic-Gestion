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

