# Documento de Cambios de Seguridad - Feria Servicio Social Tec

**Fecha:** 2026-04-06  
**Versión:** 1.0  
**Sistema:** Feria Servicio Social Tec - Plataforma de Gestión  


---

## Resumen Ejecutivo

Este documento detalla todas las mejoras de seguridad implementadas en el sistema "Feria Servicio Social Tec". Las modificaciones abordan vulnerabilidades críticas identificadas durante una auditoría de seguridad, incluyendo: Insecure Direct Object Reference (IDOR), Cross-Site Scripting (XSS), Cross-Site Request Forgery (CSRF), Rate Limiting, y configuraciones de seguridad HTTP.

**Estado Final:** Sistema endurecido para auditoría de pentesting profesional.

---

## Índice de Cambios

1. [Mitigación IDOR (Insecure Direct Object Reference)](#1-mitigación-idor)
2. [Rate Limiting Centralizado](#2-rate-limiting-centralizado)
3. [Headers de Seguridad HTTP](#3-headers-de-seguridad-http)
4. [Seguridad de Sesión y Cookies JWT](#4-seguridad-de-sesión-y-cookies-jwt)
5. [Protección contra XSS (Cross-Site Scripting)](#5-protección-contra-xss)
6. [Configuración CORS Restringida](#6-configuración-cors-restringida)
7. [Validación de Inputs](#7-validación-de-inputs)
8. [Manejo Seguro de Errores](#8-manejo-seguro-de-errores)

---

## 1. Mitigación IDOR (Insecure Direct Object Reference)

### 1.1 Validación de Propiedad en Endpoints de Socio

**Archivo Modificado:** `app/routers/socio.py`

**Cambios Realizados:**

| Endpoint | Cambio | Líneas |
|----------|--------|--------|
| `GET /projects/{project_id}/codes` | Agregada validación `Project.owner_user_id == current_user.id` | 206-230 |
| `PATCH /temp-codes/{temp_code_id}/deactivate` | Agregada validación de propiedad vía project_id | 239-262 |
| `GET /projects/{project_id}/students` | Agregada validación `Project.owner_user_id == current_user.id` | 265-295 |
| `GET /projects/{project_id}/students/export` | Agregada validación `Project.owner_user_id == current_user.id` | 298-338 |

**Ejemplo de Implementación:**
```python
# Validar que el proyecto pertenezca al usuario actual (protección IDOR)
project = db.query(Project).filter(
    Project.id == project_id,
    Project.owner_user_id == current_user.id
).first()

if not project:
    raise HTTPException(status_code=404, detail="Proyecto no encontrado")
```

**Justificación de Seguridad:**
- **Problema:** Un atacante podría acceder a recursos de otros usuarios manipulando IDs en las URLs (ej: cambiar `/projects/123` a `/projects/124`).
- **Impacto:** Fuga de datos sensibles (códigos temporales, estudiantes registrados, capacidad de proyectos).
- **Solución:** Cada endpoint ahora valida que el recurso solicitado pertenezca al usuario autenticado antes de procesar la petición.

**Relación con Otros Cambios:**
- Funciona en conjunto con el middleware de autenticación JWT
- Complementa el rate limiting (evita enumeración de IDs por fuerza bruta)

---

## 2. Rate Limiting Centralizado

### 2.1 Instancia Única de Rate Limiter

**Archivo Creado:** `app/core/limiter.py` (Nuevo)

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

# Única instancia global del rate limiter para toda la aplicación
limiter = Limiter(key_func=get_remote_address)
```

**Archivos Modificados:**

| Archivo | Cambio |
|---------|--------|
| `app/main.py` | Import desde `app.core.limiter` en lugar de crear instancia local |
| `app/routers/auth.py` | Import del limiter centralizado |
| `app/routers/socio.py` | Import del limiter centralizado |
| `app/routers/public.py` | Import del limiter centralizado |

### 2.2 Endpoints Protegidos

**Archivo:** `app/routers/auth.py`
```python
@router.post("/login")
@limiter.limit("5/minute")
def login(...)

@router.post("/login-cookie")
@limiter.limit("5/minute")
def login_cookie(...)
```

**Archivo:** `app/routers/socio.py`
```python
@router.post("/temp-codes")
@limiter.limit("5/minute")
def generate_temp_code(...)
```

**Archivo:** `app/routers/public.py`
```python
@router.post("/register", status_code=201)
@limiter.limit("5/minute")
def register_project(...)

@router.post("/generate-qr")
@limiter.limit("5/minute")
def generate_qr_token(...)
```

**Justificación de Seguridad:**
- **Problema:** Vulnerabilidad a ataques de fuerza bruta en login, registro masivo, y generación de códigos.
- **Impacto:** Agotamiento de recursos, enumeración de usuarios, consumo de tokens.
- **Solución:** Limitación de 5 solicitudes por minuto por IP en endpoints críticos.

**Relación con Otros Cambios:**
- El handler de excepciones en `main.py` convierte `RateLimitExceeded` en respuesta JSON amigable
- Funciona conjuntamente con el registro de logs para detectar intentos sospechosos

---

## 3. Headers de Seguridad HTTP

### 3.1 Middleware de Headers de Seguridad

**Archivo:** `app/main.py` (líneas 66-104)

**Implementación:**
```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval' https://cdn.jsdelivr.net ...; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com ...; "
            "frame-ancestors 'none'; "  # Clickjacking protection
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # HTTPS Strict Transport Security
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response
```

**Headers Implementados:**

| Header | Valor | Protección |
|--------|-------|------------|
| `Content-Security-Policy` | Estricto | XSS, injection de scripts |
| `Strict-Transport-Security` | max-age=31536000 | Downgrade attacks |
| `X-Content-Type-Options` | nosniff | MIME sniffing attacks |
| `X-Frame-Options` | DENY | Clickjacking |
| `Referrer-Policy` | strict-origin-when-cross-origin | Fuga de información en referrer |
| `Permissions-Policy` | geolocation=(), ... | Acceso no autorizado a APIs del navegador |

**Justificación de Seguridad:**
- **Problema:** Navegadores modernos ejecutan contenido sin verificar el origen, permitiendo XSS y clickjacking.
- **Impacto:** Robo de sesiones, defacement, redirecciones maliciosas.
- **Solución:** Headers que instruyen al navegador a restringir comportamientos peligrosos.

---

## 4. Seguridad de Sesión y Cookies JWT

### 4.1 Nueva Ruta de Login Seguro

**Archivo:** `app/routers/auth.py` (nueva función `login_cookie`)

```python
@router.post("/login-cookie")
@limiter.limit("5/minute")
def login_cookie(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # ... validación de credenciales ...
    
    access_token = create_access_token({...})
    
    response = JSONResponse(content={...})
    
    # Configurar cookie segura
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,      # No accesible desde JavaScript
        secure=is_production,  # Solo HTTPS en producción
        samesite="lax",     # Protección CSRF
        max_age=60 * 60 * 24 * 7,  # 7 días
        path="/",
    )
    
    return response
```

### 4.2 Endpoint de Logout

```python
@router.post("/logout")
def logout():
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token", path="/")
    return response
```

### 4.3 Servicio de Token Blacklist

**Archivo Creado:** `app/services/token_blacklist.py`

```python
from typing import Set

_blacklisted_tokens: Set[str] = set()

def blacklist_token(token: str) -> None:
    """Añade un token a la blacklist"""
    _blacklisted_tokens.add(token)

def is_token_blacklisted(token: str) -> bool:
    """Verifica si un token está en la blacklist"""
    return token in _blacklisted_tokens
```

### 4.4 Actualización del Frontend

**Archivo:** `app/static/js/auth.js`

| Función | Cambio |
|---------|--------|
| `saveSession()` | Agrega flag `Secure` basado en protocolo HTTPS |
| `clearSession()` | Ahora async, llama endpoint `/auth/logout` para limpiar cookie del servidor |

**Justificación de Seguridad:**
- **Problema:** Tokens JWT en localStorage son vulnerables a XSS (accesibles por JavaScript malicioso).
- **Impacto:** Robo de tokens de sesión por ataques XSS.
- **Solución:** 
  - `HttpOnly`: Cookie no accesible por JavaScript
  - `SameSite=Lax`: Previene envío automático en requests cross-site
  - `Secure`: Solo enviada por HTTPS
  - Blacklist: Permite invalidar tokens en logout

**Relación con Otros Cambios:**
- Complementa el CSP (previene XSS que intente robar tokens)
- Funciona con el middleware CORS (configurado con `allow_credentials=True`)

---

## 5. Protección contra XSS (Cross-Site Scripting)

### 5.1 Funciones de Escape en API

**Archivo:** `app/static/js/api.js`

```javascript
export function escapeHtml(text) {
  if (text === null || text === undefined) {
    return '';
  }
  const str = String(text);
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

export function createSafeElement(tag, attributes = {}, textContent = '') {
  const element = document.createElement(tag);
  // ... validación de atributos seguros ...
  if (textContent) {
    element.textContent = textContent;  // No interpreta HTML
  }
  return element;
}
```

### 5.2 Actualización de UI Components

**Archivo:** `app/static/js/ui.js`

| Función | Cambio Anterior | Cambio Nuevo |
|---------|-----------------|--------------|
| `showMessage()` | Asignación directa | `textContent` en lugar de concatenación |
| `toast()` | `innerHTML` con template string | Creación de elementos DOM con `textContent` |
| `showModal()` | Concatenación HTML string | Creación de elementos DOM con `textContent` |
| `closeBtn` | `innerHTML = "✕"` | `textContent = "✕"` |

**Ejemplo - Antes vs Después:**

```javascript
// ANTES (Vulnerable a XSS)
const icon = type === "success" ? "✓" : "✕";
toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
// Si message = "<script>alert('xss')</script>", se ejecuta el script

// DESPUÉS (Seguro)
const iconSpan = document.createElement("span");
iconSpan.textContent = icon;
const messageSpan = document.createElement("span");
messageSpan.textContent = message;  // Escapado automáticamente
toast.appendChild(iconSpan);
toast.appendChild(messageSpan);
```

### 5.3 Escapado en Módulos Específicos

**Archivos Actualizados:**

| Archivo | Uso de escapeHtml |
|---------|-------------------|
| `socio.js` | Nombres de proyectos, descripciones, datos de estudiantes |
| `admin.js` | Nombres de proyectos, matrículas, emails de estudiantes |

```javascript
// Ejemplo en socio.js
const safeName = escapeHtml(project.name);
const safeDesc = escapeHtml(project.description);
const safeMatricula = escapeHtml(student.matricula);
```

**Justificación de Seguridad:**
- **Problema:** Datos dinámicos insertados en DOM sin escapar permiten ejecución de JavaScript malicioso.
- **Impacto:** Robo de sesiones, keylogging, defacement, redirecciones.
- **Solución:** Escapado HTML automático antes de insertar en el DOM.

---

## 6. Configuración CORS Restringida

### 6.1 Dominios Permitidos

**Archivo:** `app/main.py` (líneas 44-64)

```python
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
]

# Añadir desde variable de entorno
production_origin = os.getenv("FRONTEND_URL")
if production_origin:
    ALLOWED_ORIGINS.append(production_origin)

# Dominios adicionales desde env var
additional_origins = os.getenv("ADDITIONAL_ALLOWED_ORIGINS", "")
if additional_origins:
    for origin in additional_origins.split(","):
        origin = origin.strip()
        if origin and origin not in ALLOWED_ORIGINS:
            ALLOWED_ORIGINS.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # No más "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)
```

**Cambio Clave:**
- De: `allow_origins=["*"]` (todos los dominios)
- A: Lista explícita de dominios + variables de entorno

**Justificación de Seguridad:**
- **Problema:** CORS wildcard permite requests desde cualquier origen, facilitando ataques CSRF.
- **Impacto:** Peticiones maliciosas desde sitios de terceros usando credenciales del usuario.
- **Solución:** Lista explícita de orígenes permitidos.

---

## 7. Validación de Inputs

### 7.1 Validación de JWT_SECRET

**Archivo:** `app/core/config.py`

```python
@field_validator("JWT_SECRET")
@classmethod
def validate_jwt_secret(cls, v: str) -> str:
    if len(v) < 32:
        raise ValueError(
            "JWT_SECRET debe tener al menos 32 caracteres para seguridad adecuada. "
            f"Longitud actual: {len(v)} caracteres."
        )
    return v
```

**Justificación:** Previene uso de secretos débiles que puedan ser crackeados por fuerza bruta.

### 7.2 Validación de UUIDs en Endpoints

**Archivo:** `app/routers/admin.py`

| Endpoint | Antes | Después |
|----------|-------|---------|
| `/registrations/{registration_id}/cancel` | `registration_id: str` | `registration_id: uuid.UUID` |
| `/projects/{project_id}` | `project_id: str` | `project_id: uuid.UUID` |
| `/projects/{project_id}/deactivate` | `project_id: str` | `project_id: uuid.UUID` |
| `/projects/{project_id}/activate` | `project_id: str` | `project_id: uuid.UUID` |

**Justificación:** FastAPI valida automáticamente el formato UUID, rechazando inputs maliciosos antes de llegar a la lógica de negocio.

---

## 8. Manejo Seguro de Errores

### 8.1 Eliminación de Detalles Internos

**Archivo:** `app/routers/admin.py`

| Ubicación | Antes | Después |
|-----------|-------|---------|
| `create_student_admin()` | `detail=f"No se pudo crear el estudiante. {str(e)}"` | `detail="No se pudo crear el estudiante. Por favor, intente más tarde."` |
| `update_project()` | `detail=f"Error al actualizar el proyecto: {str(e)}"` | `detail="Error al actualizar el proyecto. Por favor, intente más tarde."` |

**Justificación:** Los detalles de excepciones internas pueden revelar información sobre la estructura de la base de datos, ORM utilizado, o rutas de archivo del sistema.

---

## Matriz de Relaciones entre Cambios

```
┌─────────────────────────────────────────────────────────────────┐
│                    ARQUITECTURA DE SEGURIDAD                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │   Rate Limit  │      │    CORS      │      │   Headers    │ │
│  │   (slowapi)   │──────│  Restringido │──────│   Seguros    │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│         │                     │                     │          │
│         ▼                     ▼                     ▼          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    FastAPI Application                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│         │                     │                     │          │
│         ▼                     ▼                     ▼          │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │    Auth      │      │     IDOR     │      │   Input Val  │ │
│  │   JWT/HTTP   │──────│  Validation  │──────│   UUID/Pydantic│ │
│  │   Only       │      │  Owner Check │      │              │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│         │                     │                     │          │
│         ▼                     ▼                     ▼          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Database (SQLAlchemy)                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│         ▲                                                      │
│         │                                                      │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │    XSS       │      │   XSS Escape │      │   Safe DOM   │ │
│  │   CSP Header │──────│  (api.js)    │──────│   (ui.js)    │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Flujo de Protección en Cadena

1. **Capa Perimetral:** Rate limiting → CORS → Security Headers
2. **Capa de Aplicación:** Auth JWT → IDOR Checks → Input Validation
3. **Capa de Datos:** SQLAlchemy ORM (protección SQLi)
4. **Capa de Cliente:** CSP → Escape Functions → Safe DOM Manipulation

---

## Checklist de Verificación

- [x] Todos los endpoints de socio validan propiedad del recurso
- [x] Rate limiting implementado en endpoints críticos (login, registro, códigos)
- [x] Headers de seguridad HTTP configurados globalmente
- [x] Cookies JWT con HttpOnly, SameSite=Lax, Secure
- [x] Funciones de escape XSS en api.js
- [x] UI components usan textContent en lugar de innerHTML
- [x] CORS restringido a dominios explícitos
- [x] JWT_SECRET validado a mínimo 32 caracteres
- [x] IDs de endpoints validados como UUIDs
- [x] Errores del servidor no exponen detalles internos
- [x] Blacklist de tokens implementada

---

## Notas para Despliegue

### Variables de Entorno Requeridas

```bash
# Seguridad JWT (mínimo 32 caracteres)
JWT_SECRET="tu_secreto_seguro_de_al_menos_32_caracteres_aqui"

# Configuración CORS
FRONTEND_URL="https://tu-dominio.com"
ADDITIONAL_ALLOWED_ORIGINS="https://app.example.com,https://admin.example.com"

# Entorno
ENVIRONMENT="production"  # o "development"
```

### Verificación Post-Despliegue

```bash
# Verificar headers de seguridad
curl -I https://tu-dominio.com

# Verificar rate limiting
curl -X POST https://tu-dominio.com/auth/login -H "Content-Type: application/json" -d '{"username":"test","password":"test"}'
# Repetir 6 veces - debería devolver 429 Too Many Requests

# Verificar cookie HttpOnly
# En navegador: document.cookie - no debería mostrar access_token
```

---

## Conclusión

El sistema ha sido endurecido significativamente para resistir:
- Ataques de fuerza bruta (rate limiting)
- Robo de sesiones (HttpOnly cookies + XSS prevention)
- Acceso no autorizado a recursos (IDOR validation)
- Inyección de scripts (CSP + escape functions)
- Clickjacking (X-Frame-Options)
- CSRF (SameSite cookies + CORS restrictions)

**Estado:** Listo para auditoría de pentesting profesional.

---

*Documento generado automáticamente por Claude Code el 2026-04-06*
