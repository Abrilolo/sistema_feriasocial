# Plan de Ejecución: Upgrade Visual "Premium"

Este plan detalla los pasos para transformar la interfaz de **Feria Servicio Social Tec** de un estado funcional a uno de clase mundial (Premium), respetando estrictamente toda la lógica y funciones actuales.

## ⚠️ Aviso de Cambios No-Visuales
Este plan **NO** requiere cambios en la base de datos, modelos o rutas del servidor. 
> [!IMPORTANT]
> Si durante la ejecución se detecta que una mejora visual requiere un cambio en el backend (ej. nuevos campos en la API), se notificará al usuario antes de proceder.

---

## Propuesta de Cambios Visuales

### 1. Sistema de Diseño (CSS Foundation)
- **Archivo**: [app/static/css/styles.css](file:///c:/AI/projects/github/sistema_feriasocial/app/static/css/styles.css)
- **Cambios**:
    - Implementar variables CSS para una paleta de colores coherente (Tec Blue, Slate, Emerald).
    - Estandarizar tipografía usando fuentes modernas (Inter o Roboto).
    - Definir un sistema de espaciado y bordes (radius de 16px-24px para un look moderno).
    - Crear clases de utilidad para "Glassmorphism" y sombras suaves.

### 2. Estructura Global (Base Layout)
- **Archivo**: [app/templates/base.html](file:///c:/AI/projects/github/sistema_feriasocial/app/templates/base.html)
- **Cambios**:
    - Rediseñar el `header.topbar` para que sea más limpio y sofisticado.
    - Mejorar la transición de "Sticky header" al hacer scroll.
    - Estandarizar el pie de página (si existe) o el contenedor principal.

### 3. Panel de Socio (Socio Dashboard)
- **Archivo**: [app/templates/socio_dashboard.html](file:///c:/AI/projects/github/sistema_feriasocial/app/templates/socio_dashboard.html) y [app/static/js/socio.js](file:///c:/AI/projects/github/sistema_feriasocial/app/static/js/socio.js)
- **Cambios**:
    - Migrar todos los estilos inline (`style="..."`) a clases CSS en [styles.css](file:///c:/AI/projects/github/sistema_feriasocial/app/static/css/styles.css).
    - **Visualizaciones**: Refinar los gráficos de Chart.js para que parezcan sacados de un dashboard de alto nivel (colores vibrantes, tooltips limpios).
    - **Acciones**: Rediseñar la sección de "Generar Código" para que se sienta como una herramienta interactiva premium.
    - **Tablas**: Aplicar el estilo `elegant-table` de forma consistente.

### 4. Panel de Administrador (Admin Dashboard)
- **Archivo**: [app/templates/admin_dashboard.html](file:///c:/AI/projects/github/sistema_feriasocial/app/templates/admin_dashboard.html)
- **Cambios**:
    - Sustituir los KPI simples por "Stat Cards" con iconos sutiles y micro-gráficos (Sparklines).
    - Mejorar el buscador de estudiantes con una interfaz más intuitiva.
    - Estandarizar los botones de acción para que tengan estados de hover y active definidos.

### 5. Catálogo de Proyectos (Proyectos Public)
- **Archivo**: [app/templates/catalogo_proyectos.html](file:///c:/AI/projects/github/sistema_feriasocial/app/templates/catalogo_proyectos.html)
- **Cambios**:
    - Implementar un diseño de "Cards" moderno con imágenes de fondo refinadas y overlays de texto legibles.
    - Añadir filtros visuales (Pills/Tags) en lugar de dropdowns aburridos.
    - Transiciones suaves al filtrar o buscar proyectos.

---

## Plan de Verificación

### Visual y UX
- **Responsive Design**: Verificar que todos los paneles se vean perfectos en móviles y tablets.
- **Micro-interacciones**: Asegurar que los botones y enlaces tengan feedback visual inmediato.
- **Accessibilidad**: Mantener un buen contraste de colores y legibilidad de texto.

### Integridad de Funciones
- **Prueba de Flujo**: Verificar que tras los cambios visuales, se pueda seguir:
    1. Haciendo login correctamente.
    2. Generando códigos temporales.
    3. Registrando estudiantes en el catálogo público.
    4. Exportando CSV sin errores.
