# Plan de Seguridad Corporativa — Feria Social

## Auditoría: Vulnerabilidades Actuales

| # | Vulnerabilidad | Severidad | OWASP | Estado |
|---|---|---|---|---|
| 1 | QR contiene matrícula en texto plano | 🔴 Alta | A02 Cryptographic Failures | Sin proteger |
| 2 | Swagger UI activo en producción | 🔴 Alta | A05 Misconfiguration | Sin proteger |
| 3 | `/db/ping` expuesto sin auth | 🟠 Media | A01 Broken Access Control | Público |
| 4 | `/public/projects` expone capacidades y cupo | 🟠 Media | A01 Broken Access Control | Público |
| 5 | FastAPI doc endpoints (`/docs`, `/redoc`) | 🟠 Media | A05 Misconfiguration | Sin proteger |
| 6 | `DEBUG: print()` con datos personales en logs | 🟡 Baja | A09 Logging Failures | En producción |
| 7 | `picture_url` de Google sin validación SSRF | 🟡 Baja | A10 SSRF | Sin filtrar |
| 8 | `/health` expone estado de BD sin auth | 🟡 Baja | A05 Misconfiguration | Público |

---

## Vulnerabilidad 1 — QR con matrícula en texto plano 🔴

### ¿Por qué es un riesgo?
Cualquier persona con un teléfono puede escanear el QR del estudiante y ver su matrícula. Con ese dato, en teoría podrían:
- Identificar al alumno en otros sistemas institucionales.
- Construir un QR falso con la matrícula de otro estudiante para hacer check-in doble (suplantación).

### Solución: UUID opaco de un solo uso
En lugar de la matrícula en texto, el QR contiene un **UUID temporal generado al momento de la petición**, que el servidor guarda y vincula al `student_id`. Es válido por 2 horas y de un solo escaneo.

```
QR muestra:  "f3a9d2b1-7e4c-4f2a-9c1d-3b8e2f1a0c5d"  (UUID opaco)
Becario escanea → POST /checkins/scan { "token": "f3a9d2b1-..." }
Servidor busca en tabla qr_tokens → encuentra student_id → hace check-in → invalida el token
```

**Nuevas tablas/campos necesarios:**
```sql
-- Nueva tabla qr_tokens
CREATE TABLE qr_tokens (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token       VARCHAR(36) UNIQUE NOT NULL,  -- UUID v4
    student_id  UUID NOT NULL REFERENCES students(id),
    expires_at  TIMESTAMP NOT NULL,
    used_at     TIMESTAMP,  -- NULL = no usado; fecha = ya escaneado
    created_at  TIMESTAMP DEFAULT now()
);
```

**Cambios en el código:**
- `POST /public/generate-qr` → crea un `qr_token` en BD, devuelve el UUID
- `POST /checkins/scan` → recibe UUID, busca en `qr_tokens`, hace check-in, marca como usado
- El QR ya no puede ser falsificado ni reutilizado
- La matrícula NUNCA aparece en el código QR

---

## Vulnerabilidad 2 — Swagger UI activo en producción 🔴

### ¿Por qué es un riesgo?
`/docs` y `/redoc` documentan **todos los endpoints, parámetros y schemas de tu API**. Es una guía perfecta para un atacante. Además, permite ejecutar peticiones directamente desde el browser contra producción.

### Solución
```python
# app/main.py
app = FastAPI(
    title="Feria Servicio Social Tec",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
)
```

**Resultado:** En producción, `/docs`, `/redoc` y `/openapi.json` devuelven 404.

---

## Vulnerabilidad 3 — `/db/ping` sin autenticación 🟠

### ¿Por qué es un riesgo?
Cualquier persona puede saber si tu base de datos está activa o no. Esta información es útil para planificar ataques de timing o DDoS selectivos.

### Solución
Eliminar el router o restringirlo a ADMIN:
```python
@router.get("/db/ping")
def ping_db(_=Depends(require_role("ADMIN"))):
    ok = db_ping()
    return {"db_ok": ok}
```

---

## Vulnerabilidad 4 — `/public/projects` expone datos sensibles 🟠

### ¿Por qué es un riesgo?
El endpoint expone `capacity` y `available` (cupos) de todos los proyectos sin autenticación. Un actor malicioso puede:
- Monitorear cupos en tiempo real para saber cuáles proyectos atacar primero.
- Hacer scraping de información confidencial de las organizaciones.

### Solución
Restringir a estudiantes autenticados (con `student_token`):
```python
@router.get("/projects")
def get_projects(
    db: Session = Depends(get_db),
    student: Student = Depends(get_current_student)  # ← AGREGAR
):
    ...
```

O en su defecto, **eliminar los campos `capacity` y `available`** de la respuesta pública y dejar solo nombre, descripción y carrera.

---

## Vulnerabilidad 5 — FastAPI expone `/openapi.json` 🟠

Ver Vulnerabilidad 2 — se resuelve con el mismo cambio en la inicialización de FastAPI.

---

## Vulnerabilidad 6 — `print()` con datos personales en logs 🟡

### ¿Qué está pasando?
En `auth.py` hay varios `print()` que exponen correos y datos de estudiantes en los logs del servidor. En Render, estos logs son visibles para cualquiera con acceso al dashboard.

```python
# PROBLEMÁTICO — expone PII en logs
print(f"DEBUG: NUEVO LOGIN DETECTADO -> {email}")
print(f"DEBUG: Enlazando estudiante existente ({email}) con google_id")
```

### Solución
Reemplazar todos los `print()` con `logging` a nivel `DEBUG`, que en producción no se imprime:
```python
import logging
logger = logging.getLogger(__name__)

# Solo visible en development
logger.debug("Nuevo login OAuth: %s", email)  # No incluir datos completos en INFO
```

Y en `app/main.py` producción:
```python
logging.basicConfig(level=logging.WARNING)  # Suprime DEBUG e INFO en producción
```

---

## Vulnerabilidad 7 — `picture_url` sin validación SSRF 🟡

### ¿Por qué es un riesgo?
Si el backend en algún momento hace fetch de esa URL (para caché, redimensión, etc.), podría ser usado para hacer peticiones internas a servidores privados (SSRF).

### Solución inmediata
Validar que la URL sea de dominios confiables de Google:
```python
import re
ALLOWED_PICTURE_DOMAINS = re.compile(r'^https://(lh\d\.googleusercontent\.com|googleusercontent\.com)/')

if picture_url and not ALLOWED_PICTURE_DOMAINS.match(picture_url):
    picture_url = None  # Descartar URLs de dominios no confiables
```

---

## Vulnerabilidad 8 — `/health` expone estado de BD 🟡

### Solución
Devolver solo `{"status": "ok"}` sin revelar el estado interno de la BD:
```python
@app.get("/health")
def health():
    return {"status": "ok"}  # No revelar estado de BD al público
```

---

## Plan de Implementación

### Fase 1 — Crítica (implementar hoy)
1. **Desactivar Swagger en producción** → 1 línea en `main.py`
2. **Proteger `/db/ping`** → 1 línea en `db.py`
3. **Remover `print()` con PII** → reemplazar por `logger.debug()` en `auth.py`

### Fase 2 — QR opaco (diseño más seguro)
4. **Crear tabla `qr_tokens`** en Supabase
5. **Modificar `generate-qr`** para crear token opaco
6. **Modificar `checkins/scan`** para validar token opaco y marcarlo como usado
7. **Actualizar `becario.js`** para enviar el token escaneado

### Fase 3 — Restricciones de acceso
8. **Proteger `/public/projects`** para requerir `student_token`
9. **Validar `picture_url`** para prevenir SSRF
10. **Limpiar `/health`**

---

## Comparativa: QR Actual vs QR Seguro

| Aspecto | QR Actual | QR Seguro (UUID) |
|---|---|---|
| Contenido | `A01659113` (matrícula visible) | `f3a9d2b1-7e4c-...` (UUID opaco) |
| ¿Puede falsificarse? | Sí, conociendo la matrícula | No, UUID generado server-side |
| ¿Puede reutilizarse? | Sí (no hay estado de "usado") | No, se invalida tras el primer escaneo |
| ¿Expone datos personales? | Sí | No |
| ¿Tamaño del QR? | Pequeño | Pequeño (UUID también es corto) |
| Validación server-side | Consulta por matrícula | Consulta por UUID + verifica `used_at` |

> [!IMPORTANT]
> El cambio más impactante es el **QR con UUID opaco**. Resuelve privacidad, suplantación y reutilización de un solo golpe.

> [!NOTE]
> El modelo de OAuth actual (JWT firmado en cookie HttpOnly) ya sigue buenas prácticas de la industria. El riesgo está en los datos que viajan en el QR y en los endpoints públicos, no en el sistema de autenticación principal.
