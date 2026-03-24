# Sistema Feria Social - Tec de Monterrey

Este es el sistema para la gestión de la Feria de Servicio Social del Tec de Monterrey.

## Estructura del Proyecto

- `app/`: Contiene el código principal de la aplicación FastAPI.
    - `models/`: Modelos de base de datos (SQLAlchemy).
    - `routers/`: Rutas y controladores de la API y vistas.
    - `schemas/`: Esquemas de validación (Pydantic).
    - `services/`: Lógica de negocio.
    - `static/`: Archivos estáticos (CSS, JS, imágenes).
    - `templates/`: Plantillas HTML (Jinja2).
- `scripts/`: Scripts de utilidad y carga de datos.
    - `fixes/`: Scripts de mantenimiento y correcciones puntuales (anteriormente en la raíz).
- `alembic/`: Migraciones de la base de datos.

## Documentación Adicional

- [Guía de Desarrollo Frontend (Stitch)](./STITCH_FRONTEND_GUIDE.md): Instrucciones detalladas para mejorar la interfaz y arquitectura del frontend.

## Ejecución Local

Para ejecutar el servidor de desarrollo:

```bash
uvicorn app.main:app --reload
```
