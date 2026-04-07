# Plan de Fortalecimiento de Seguridad (Security Hardening) - Feria Servicio Social Tec

Este plan detalla las acciones necesarias para proteger el sistema contra ataques comunes, inyecciones de query (SQLi), y asegurar que pase una auditoría de Pentesting profesional.

## 1. Defensa contra Inyección SQL y Parámetros
Asegurar que todas las consultas a la base de datos sean parametrizadas y que no haya fugas de información por errores de query.
- [ ] **Acción**: Auditar todos los routers para asegurar que NO se utilice `sqlalchemy.text()` con parámetros concatenados por string. Usar siempre el ORM (`db.query` o `select`).
- [ ] **Acción**: Forzar validación de UUIDs en rutas. No aceptar strings genéricos donde se espera un ID de base de datos.
- [ ] **Acción**: Implementar un middleware de manejo de errores global que no devuelva detalles internos de la base de datos en las respuestas JSON (evitar fugas de esquema).

## 2. Mitigación de IDOR (Insecure Direct Object Reference)
Se detectó que un SOCIO puede acceder a recursos de otros mediante la manipulación de IDs.
- [ ] **Acción**: En `app/routers/socio.py`, añadir validación de propiedad en cada endpoint: `filter(Project.owner_user_id == current_user.id)`. Especialmente en listar códigos, estudiantes y exportar CSV.
- [ ] **Acción**: Escapar y sanitizar todas las entradas de usuario en los modelos Pydantic (especialmente campos de texto).

## 3. Seguridad de Sesión y JWT
- [ ] **Acción**: Configurar cookies de JWT con parámetros de seguridad:
    - `HttpOnly=True` (Previene robo vía XSS).
    - `Secure=True` (Solo sobre HTTPS).
    - `SameSite='Lax'` (Protege contra CSRF básico).
- [ ] **Acción**: Implementar una "blacklist" de tokens para cierres de sesión efectivos.

## 4. Protección contra Fuerza Bruta y DoS
- [ ] **Acción**: Implementar Rate Limiting (Máximo 5 intentos/min por IP) en los endpoints críticos:
    - `/auth/login` (Login)
    - `/public/register` (Registro con código)
    - `/socio/temp-codes` (Generación de códigos)
- [ ] **Acción**: Implementar un bloqueo temporal de 5-15 minutos tras 5 intentos fallidos en el login.

## 6. Protección CSRF (Cross-Site Request Forgery)
Las peticiones que modifican estado (POST/PUT/PATCH/DELETE) son vulnerables.
- [ ] **Acción**: Implementar un middleware de Double Submit Cookie o utilizar un token CSRF manual en el header `X-CSRF-Token` para todas las peticiones asíncronas desde el frontend.

## 7. Headers de Seguridad (Security Headers)
Configurar headers globales en `main.py` para dificultar ataques al navegador.
- [ ] **Acción**: Añadir `Content-Security-Policy (CSP)` estricto (no inline scripts, solo dominios permitidos).
- [ ] **Acción**: Añadir `HSTS` (Strict-Transport-Security) para forzar HTTPS.
- [ ] **Acción**: Añadir `X-Content-Type-Options: nosniff`.
- [ ] **Acción**: Añadir `X-Frame-Options: DENY` (Protección Clickjacking).

## 8. Seguridad en el Frontend (XSS)
- [ ] **Acción**: Reemplazar todas las asignaciones `innerHTML` por `textContent` en `app/static/js/` donde no se requiera explícitamente HTML.
- [ ] **Acción**: En Jinja2, evitar el uso del filtro `| safe` con variables que vengan del usuario (ej: nombres de proyectos, descripciones).

---

## Roadmap de Ejecución para Claude Code:

1.  **Seguridad de Routers**: Primero aplicar filtros de propiedad en `socio.py` para cerrar los IDORs inmediatamente.
2.  **Infraestructura de Seguridad**: Configurar los headers globales y el Rate Limiting en `main.py`.
3.  **Seguridad de JWT**: Actualizar la lógica de creación de cookies en `auth.py`.
4.  **Auditoría de Frontend**: Corregir debilidades de XSS en los archivos JS estáticos.
