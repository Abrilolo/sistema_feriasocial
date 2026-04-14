# Documentación Criptográfica y de Seguridad - Feria Servicio Social

> **Documento para nuevos desarrolladores**  
> Este documento explica en detalle todas las medidas criptográficas y de seguridad implementadas en el sistema, el concepto teórico detrás de cada una, y la ubicación exacta del código.

---

## Tabla de Contenidos

1. [Autenticación y Autorización](#1-autenticación-y-autorización)
2. [Hashing de Contraseñas](#2-hashing-de-contraseñas)
3. [Tokens JWT (JSON Web Tokens)](#3-tokens-jwt-json-web-tokens)
4. [Protección contra Fuerza Bruta](#4-protección-contra-fuerza-bruta)
5. [Seguridad de Cookies](#5-seguridad-de-cookies)
6. [Configuración CORS](#6-configuración-cors)
7. [Headers de Seguridad HTTP](#7-headers-de-seguridad-http)
8. [Google OAuth 2.0](#8-google-oauth-20)
9. [Validación de Datos](#9-validación-de-datos)
10. [Protección de Credenciales](#10-protección-de-credenciales)

---

## 1. Autenticación y Autorización

### 1.1 Concepto: ¿Qué es la Autenticación?

La **autenticación** es el proceso de verificar que un usuario es quien dice ser. En este sistema usamos dos métodos:

1. **Autenticación por credenciales** (email + contraseña) para usuarios internos (ADMIN, SOCIO, BECARIO)
2. **Autenticación OAuth 2.0** con Google para estudiantes

La **autorización** ocurre después: determina qué recursos puede acceder el usuario autenticado basándose en su rol.

### 1.2 Implementación: Dependencia `get_current_user`

**Archivo:** `app/core/security.py` (líneas 73-88)

```python
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    """
    Extrae y valida el JWT del header Authorization.
    Retorna el objeto User completo desde la base de datos.
    """
    payload = decode_access_token(token)  # Decodifica el JWT
    user_id = payload.get("sub")          # Obtiene el ID del usuario
    if not user_id:
        raise HTTPException(status_code=401, detail="Token sin subject (sub)")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if not getattr(user, "is_active", True):
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    return user
```

**¿Cómo funciona?**
1. El cliente envía un request con el header: `Authorization: Bearer <token_jwt>`
2. `oauth2_scheme` extrae el token del header
3. `decode_access_token` valida la firma y expiración del JWT
4. Se busca el usuario en la BD usando el ID del payload
5. Se verifica que el usuario esté activo (`is_active=True`)

### 1.3 Implementación: Control de Roles

**Archivo:** `app/core/security.py` (líneas 91-99)

```python
def require_role(required_role: str):
    """
    Factory que crea una dependencia para verificar roles específicos.
    Uso: Depends(require_role("ADMIN"))
    """
    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado: requiere rol {required_role}",
            )
        return user
    return _checker
```

**¿Por qué es seguro?**
- No confía en el rol enviado por el cliente
- Consulta el rol desde la base de datos usando el ID del JWT
- Un atacante no puede falsificar su rol porque el JWT está firmado

### 1.4 Autenticación desde Cookies (Vistas HTML)

**Archivo:** `app/routers/views.py` (líneas 14-45)

```python
def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    """
    Versión de get_current_user para vistas HTML que usan cookies
    en lugar del header Authorization.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    if token.startswith("Bearer "):
        token = token.replace("Bearer ", "", 1)

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None

        # CRÍTICO: Validar contra la base de datos, no solo confiar en el JWT
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None

        return {
            "sub": str(user.id),
            "role": user.role,
            "email": user.email,
            "organization_name": getattr(user, "organization_name", None),
        }
    except Exception:
        return None
```

**Concepto de seguridad:** Verificación Doble
- El JWT prueba que el usuario alguna vez fue autenticado
- La consulta a BD verifica que el usuario aún existe y está activo
- Esto previene que usuarios desactivados mantengan acceso con tokens antiguos

---

## 2. Hashing de Contraseñas

### 2.1 Concepto: ¿Por qué hashear contraseñas?

Las contraseñas **NUNCA** deben almacenarse en texto plano. Si la base de datos se filtra:
- Texto plano: El atacante tiene las contraseñas reales
- Hash: El atacante solo tiene valores irreversibles

Usamos **bcrypt**, un algoritmo diseñado específicamente para contraseñas que es:
- **Lento intencionalmente**: Dificulta ataques de fuerza bruta
- **Sal automático**: Cada hash tiene una sal única (protección contra rainbow tables)
- **Adaptativo**: Se puede aumentar el costo computacional con el tiempo

### 2.2 Implementación: Hashing con bcrypt

**Archivo:** `app/core/security.py` (líneas 22-39)

```python
def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando bcrypt con sal automática.
    
    bcrypt incluye la sal en el resultado, por lo que no necesitamos
    almacenarla por separado. El formato es: $2b$cost$sal+hash
    """
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        raise ValueError("Password demasiado largo para bcrypt (max 72 bytes).")
    salt = bcrypt.gensalt()  # Genera sal aleatoria de 16 bytes
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica una contraseña contra su hash bcrypt.
    El hash almacenado incluye la sal, por lo que bcrypt puede reconstruir.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False
```

**Ejemplo de uso:**
```python
# Al crear usuario:
user.hashed_password = hash_password("MiPasswordSeguro123!")
# Almacena: $2b$12$LQv3c1yqBWVHxkd8L... (60 caracteres)

# Al verificar login:
if verify_password(password_ingresada, user.hashed_password):
    # Contraseña correcta
```

### 2.3 Validación de Fortaleza de Contraseñas

**Archivo:** `app/routers/admin.py` (líneas 28-53)

```python
class AdminUserCreateIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # Mínimo 8 caracteres
    role: str

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Valida que la contraseña cumpla con requisitos de seguridad:
        - Mínimo 8 caracteres
        - Al menos una letra mayúscula
        - Al menos una letra minúscula
        - Al menos un número
        - Al menos un carácter especial
        """
        if not re.search(r'[A-Z]', v):
            raise ValueError("La contraseña debe contener al menos una letra mayúscula")
        if not re.search(r'[a-z]', v):
            raise ValueError("La contraseña debe contener al menos una letra minúscula")
        if not re.search(r'\d', v):
            raise ValueError("La contraseña debe contener al menos un número")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-=+\[\]\\\/]', v):
            raise ValueError("La contraseña debe contener al menos un carácter especial")
        return v
```

**¿Por qué es importante?**
- Previene contraseñas débiles como "123456" o "password"
- Aumenta el espacio de búsqueda para ataques de fuerza bruta
- `A1!` (3 tipos de caracteres) vs `aaa` (1 tipo) = mucho más seguro

---

## 3. Tokens JWT (JSON Web Tokens)

### 3.1 Concepto: ¿Qué es un JWT?

Un JWT es un estándar (RFC 7519) para transmitir información de forma compacta y segura entre partes. Se compone de tres partes separadas por puntos:

```
eyJhbGciOiJIUzI1NiIs...  # Header (codificado en Base64)
.eyJzdWIiOiIxMjM0NTY3...  # Payload (datos del usuario)
.SflKxwRJSMeKKF2QT4f...  # Signature (firma HMAC)
```

**Flujo típico:**
1. Usuario inicia sesión con credenciales válidas
2. Servidor genera JWT firmado con clave secreta
3. Cliente almacena JWT (localStorage o cookie)
4. Cliente envía JWT en cada request
5. Servidor verifica firma del JWT (sin consultar BD)

### 3.2 Implementación: Creación de JWT

**Archivo:** `app/core/security.py` (líneas 45-56)

```python
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Crea un JWT firmado con los datos proporcionados.
    
    Args:
        data: Diccionario con datos a incluir en el token (ej: {"sub": user_id})
        expires_delta: Tiempo de expiración (default: ACCESS_TOKEN_EXPIRE_MINUTES)
    
    Returns:
        String JWT codificado (header.payload.signature)
    """
    to_encode = data.copy()

    expire_minutes = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60)
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=expire_minutes))
    to_encode.update({"exp": expire})  # Agrega claim de expiración

    # Firma el token con HMAC-SHA256 (HS256)
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    return encoded_jwt
```

**Parámetros criptográficos:**
- **Algoritmo:** HS256 (HMAC con SHA-256)
- **Clave secreta:** `settings.JWT_SECRET` (debe ser ≥32 caracteres aleatorios)
- **Expiración:** 60 minutos por defecto (previene tokens robados indefinidos)

### 3.3 Implementación: Validación de JWT

**Archivo:** `app/core/security.py` (líneas 58-67)

```python
def decode_access_token(token: str) -> dict:
    """
    Decodifica y valida un JWT.
    
    Verifica:
    1. Firma válida (con JWT_SECRET)
    2. No ha expirado (claim 'exp')
    3. Formato correcto
    
    Raises:
        HTTPException 401 si el token es inválido o expiró
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return payload
    except JWTError:  # Token malformado, firma inválida, o expirado
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

**Claims importantes:**
- `sub` (subject): Identificador del usuario
- `exp` (expiration): Timestamp de expiración
- `role`: Rol del usuario (ADMIN/SOCIO/BECARIO/student)
- `type`: Tipo de token (invite para QR)

### 3.4 Implementación: Validación de JWT_SECRET

**Archivo:** `app/core/config.py` (líneas 22-30)

```python
@field_validator("JWT_SECRET")
@classmethod
def validate_jwt_secret(cls, v: str) -> str:
    """
    Valida que el JWT_SECRET cumpla con requisitos mínimos de seguridad.
    Un secret corto permite ataques de fuerza bruta contra el JWT.
    """
    if len(v) < 32:
        raise ValueError(
            "JWT_SECRET debe tener al menos 32 caracteres para seguridad adecuada. "
            f"Longitud actual: {len(v)} caracteres."
        )
    return v
```

**Concepto de seguridad:**
- La clave secreta debe tener alta entropía (aleatoriedad)
- 32 caracteres hexadecimales = 128 bits de entropía
- Fuerza bruta contra 128 bits es computacionalmente imposible hoy

---

## 4. Protección contra Fuerza Bruta

### 4.1 Concepto: Ataques de Fuerza Bruta

Un atacante intenta adivinar credenciales probando miles de combinaciones:
- Contraseñas comunes ("password123", "qwerty")
- Variaciones de palabras del diccionario
- Datos personales de la víctima

### 4.2 Implementación: Rate Limiting

**Archivo:** `app/core/limiter.py`

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

# Única instancia global del rate limiter para toda la aplicación
limiter = Limiter(key_func=get_remote_address)
```

**Archivo:** `app/routers/auth.py` (ejemplo de uso)

```python
@router.post("/login")
@limiter.limit("5/minute")  # Máximo 5 intentos por minuto por IP
def login(request: Request, ...):
    ...
```

**¿Cómo funciona?**
1. Cada request identifica al cliente por su IP (`get_remote_address`)
2. Se mantiene un contador de requests por IP en memoria
3. Si una IP excede el límite, se bloquea temporalmente
4. El cliente recibe HTTP 429 (Too Many Requests)

**Limitaciones actuales:**
- El contador está en memoria (no persiste entre reinicios)
- En múltiples workers/replicas, cada uno tiene su propio contador
- **Mejora recomendada:** Usar Redis para rate limiting distribuido

---

## 5. Seguridad de Cookies

### 5.1 Concepto: ¿Por qué proteger las cookies?

Las cookies pueden ser robadas y usadas para suplantar identidad:
- **XSS (Cross-Site Scripting):** JavaScript malicioso lee `document.cookie`
- **CSRF (Cross-Site Request Forgery):** Sitio malicioso envía requests automáticos
- **Sniffing:** Interceptación de cookies en redes no seguras

### 5.2 Implementación: Cookies HttpOnly y Secure

**Archivo:** `app/routers/auth.py` (líneas 87-95)

```python
response.set_cookie(
    key="access_token",
    value=f"Bearer {access_token}",
    httponly=True,   # JavaScript NO puede leer esta cookie (protección XSS)
    secure=is_production,  # Solo se envía por HTTPS (protección sniffing)
    samesite="lax",  # Cookie solo enviada a mismo sitio (protección CSRF)
    max_age=60 * 60 * 24 * 7,  # 7 días de duración
    path="/",      # Disponible en todo el sitio
)
```

**Atributos de seguridad:**

| Atributo | Propósito | Protege contra |
|----------|-----------|----------------|
| `httponly=True` | JavaScript no puede leer la cookie | XSS attacks |
| `secure=True` | Cookie solo viaja por HTTPS | Sniffing en redes WiFi |
| `samesite="lax"` | Cookie no enviada en requests cross-site | CSRF attacks |

**Token de estudiante:**
```python
response.set_cookie(
    key="student_token",
    value=access_token,
    httponly=True,
    secure=settings.ENVIRONMENT == "production",
    samesite="lax",
    max_age=60 * 60 * 2,  # 2 horas (menos tiempo para estudiantes)
    path="/",
)
```

### 5.3 Logout y Eliminación de Cookies

**Archivo:** `app/routers/auth.py` (líneas 100-106)

```python
@router.post("/logout")
def logout():
    """Logout que limpia la cookie del lado del servidor"""
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token", path="/")
    return response
```

**Concepto:** Aunque el cliente pueda "olvidar" la cookie, el logout debe invalidarla del lado del servidor para prevenir reutilización.

---

## 6. Configuración CORS

### 6.1 Concepto: ¿Qué es CORS?

**CORS (Cross-Origin Resource Sharing)** controla qué sitios web pueden hacer requests a nuestra API. Por defecto, los navegadores bloquean requests entre diferentes orígenes (dominios).

### 6.2 Implementación: CORS Seguro

**Archivo:** `app/main.py` (líneas 44-82)

```python
# Configuración de CORS - Dominios permitidos
# En producción, solo se permite el dominio configurado en FRONTEND_URL
is_production = os.getenv("ENVIRONMENT", "development").lower() == "production"

if is_production:
    # En producción: solo permitir el dominio configurado explícitamente
    ALLOWED_ORIGINS = []
    production_origin = os.getenv("FRONTEND_URL")
    if production_origin:
        ALLOWED_ORIGINS.append(production_origin)

    # Añadir dominios adicionales si están configurados
    additional_origins = os.getenv("ADDITIONAL_ALLOWED_ORIGINS", "")
    if additional_origins:
        for origin in additional_origins.split(","):
            origin = origin.strip()
            if origin and origin not in ALLOWED_ORIGINS:
                ALLOWED_ORIGINS.append(origin)

    if not ALLOWED_ORIGINS:
        logger.warning("PRODUCCIÓN: No se ha configurado FRONTEND_URL.")
else:
    # En desarrollo: permitir localhost
    ALLOWED_ORIGINS = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Solo estos orígenes pueden hacer requests
    allow_credentials=True,        # Permitir cookies en requests CORS
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],  # Métodos permitidos
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)
```

**¿Por qué es seguro?**
- En producción, `localhost` **NUNCA** está en la lista permitida
- Sin `FRONTEND_URL` configurado, el CORS bloquea todas las peticiones
- Previene que sitios maliciosos hagan requests a la API

---

## 7. Headers de Seguridad HTTP

### 7.1 Concepto: Headers de Seguridad

Los headers HTTP pueden instruir al navegador sobre comportamientos de seguridad adicionales. Son importantes porque protegen contra varios ataques del lado del cliente.

### 7.2 Implementación: Security Headers Middleware

**Archivo:** `app/main.py` (líneas 84-119)

```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que agrega headers de seguridad a todas las respuestas.
    Estos headers instruyen al navegador sobre comportamientos seguros.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Content Security Policy: Controla qué recursos puede cargar el navegador
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "  # Por defecto, solo recursos del mismo origen
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "  # Scripts permitidos
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "  # CSS permitido
            "font-src 'self' https://fonts.gstatic.com; "  # Fuentes permitidas
            "img-src 'self' data: blob:; "  # Imágenes permitidas
            "connect-src 'self'; "  # Requests AJAX/Fetch solo al mismo origen
            "frame-ancestors 'none'; "  # No permitir que el sitio sea embebido en iframes
            "base-uri 'self'; "  # Elemento <base> solo puede apuntar a mismo origen
            "form-action 'self';"  # Formularios solo pueden enviar a mismo origen
        )

        # HTTPS Strict Transport Security: Fuerza HTTPS por 1 año
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # X-Content-Type-Options: No adivinar el tipo MIME (previene MIME sniffing)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: No permitir embeber el sitio en iframes (clickjacking)
        response.headers["X-Frame-Options"] = "DENY"

        # Referrer-Policy: Limitar información enviada en header Referer
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: Deshabilitar APIs sensibles del navegador
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(self)"

        return response

app.add_middleware(SecurityHeadersMiddleware)
```

**Explicación de cada header:**

| Header | Propósito | Ataque que previene |
|--------|-----------|---------------------|
| `Content-Security-Policy` | Controla fuentes de recursos | XSS, data injection |
| `Strict-Transport-Security` | Fuerza HTTPS | SSL stripping, MITM |
| `X-Content-Type-Options` | No adivinar MIME types | MIME sniffing attacks |
| `X-Frame-Options` | No permitir iframes | Clickjacking |
| `Referrer-Policy` | Limitar datos en referer | Information leakage |
| `Permissions-Policy` | Deshabilitar APIs | Privilege escalation |

---

## 8. Google OAuth 2.0

### 8.1 Concepto: ¿Qué es OAuth 2.0?

**OAuth 2.0** es un protocolo de autorización que permite a los usuarios otorgar acceso limitado a sus recursos (ej: perfil de Google) sin compartir sus credenciales.

**Flujo (Authorization Code):**
1. Usuario hace clic en "Login con Google"
2. Redirección a Google para autenticación
3. Google redirige de vuelta con un "código de autorización"
4. Servidor intercambia el código por tokens de acceso
5. Servidor usa tokens para obtener información del usuario

**Ventajas de seguridad:**
- El servicio nunca ve la contraseña del usuario
- El usuario puede revocar el acceso en cualquier momento desde Google
- Google maneja la seguridad (2FA, detección de intrusiones, etc.)

### 8.2 Implementación: Configuración OAuth

**Archivo:** `app/routers/auth.py` (líneas 18-29)

```python
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,       # Client ID de Google Cloud
        client_secret=settings.GOOGLE_CLIENT_SECRET,  # Client Secret de Google Cloud
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'  # Qué información solicitamos
        }
    )
```

### 8.3 Implementación: Endpoint de Login

**Archivo:** `app/routers/auth.py` (líneas 124-137)

```python
@router.get("/google/login")
async def google_login(request: Request):
    """
    Inicia el flujo OAuth 2.0 con Google.
    
    1. Genera state token (CSRF protection)
    2. Redirige al usuario a accounts.google.com
    3. Google solicita credenciales y consentimiento
    4. Google redirige a /auth/google/callback con código de autorización
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth no está configurado. Contacta al administrador."
        )

    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, str(redirect_uri))
```

### 8.4 Implementación: Callback y Validación

**Archivo:** `app/routers/auth.py` (líneas 140-221)

```python
@router.get("/google/callback", name="google_callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Procesa la respuesta de Google OAuth.
    
    Flujo:
    1. Intercambia el código de autorización por tokens
    2. Obtiene información del usuario desde Google
    3. Valida que el email sea del dominio institucional (@tec.mx)
    4. Busca o crea el estudiante en la base de datos
    5. Genera JWT propio del sistema
    """
    try:
        # Paso 1: Intercambiar código por tokens
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error al autorizar con Google: {str(e)}"
        )

    # Paso 2: Obtener información del usuario
    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudo obtener información del usuario de Google"
        )

    email = user_info.get('email', '').lower()
    google_id = user_info.get('sub')  # ID único de Google
    full_name = user_info.get('name')
    picture_url = user_info.get('picture')

    # Paso 3: VALIDACIÓN CRÍTICA - Solo emails institucionales
    if not email.endswith(f"@{settings.STUDENT_EMAIL_DOMAIN}"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Solo se permiten correos @{settings.STUDENT_EMAIL_DOMAIN}"
        )

    # Paso 4: Extraer matrícula del email
    matricula = email.split('@')[0].upper()

    # Paso 5: Buscar o crear estudiante
    student = db.query(Student).filter(Student.email == email).first()

    if student:
        # Actualizar datos de Google si ya existe
        student.google_id = google_id
        student.full_name = full_name or student.full_name
        student.picture_url = picture_url or student.picture_url
        db.commit()
    else:
        # Crear nuevo estudiante
        student = Student(
            email=email,
            matricula=matricula,
            full_name=full_name,
            google_id=google_id,
            picture_url=picture_url,
        )
        db.add(student)
        db.commit()
        db.refresh(student)

    # Paso 6: Generar JWT propio del sistema
    access_token = create_access_token({
        "sub": str(student.id),
        "type": "student",
        "email": student.email,
        "matricula": student.matricula,
        "name": student.full_name
    })

    # Paso 7: Establecer cookie y redirigir
    response = RedirectResponse(url="/acceso-estudiante", status_code=302)
    response.set_cookie(
        key="student_token",
        value=access_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=60 * 60 * 2,  # 2 horas
        path="/",
    )

    return response
```

**Puntos de seguridad importantes:**
1. **Validación de dominio:** Solo `@tec.mx` puede registrarse
2. **Extracción de matrícula:** Se extrae automáticamente del email
3. **Sincronización:** Si el estudiante ya existe, se actualizan sus datos de Google
4. **JWT propio:** Aunque Google da tokens, creamos nuestro propio JWT para consistencia

---

## 9. Validación de Datos

### 9.1 Concepto: ¿Por qué validar?

La validación de datos previene:
- **Inyección SQL:** Datos maliciosos que alteran queries
- **XSS:** Scripts en campos de texto que ejecutan en otros usuarios
- **Datos corruptos:** Valores que rompen la lógica de negocio
- **DoS:** Datos extremadamente grandes que saturan memoria

### 9.2 Implementación: Pydantic Models

**Archivo:** `app/routers/admin.py` (ejemplos)

```python
from pydantic import BaseModel, EmailStr, Field

class AdminUserCreateIn(BaseModel):
    """
    Modelo Pydantic para creación de usuarios.
    Valida automáticamente tipos y restricciones.
    """
    email: EmailStr  # Valida formato de email (ej: usuario@dominio.com)
    password: str = Field(
        min_length=8,      # Longitud mínima
        max_length=72      # bcrypt trunca a 72 bytes
    )
    role: str

class AdminStudentCreateIn(BaseModel):
    """Modelo para creación de estudiantes."""
    matricula: str = Field(
        min_length=1,      # No vacío
        max_length=50,     # Límite razonable
        pattern=r'^[A-Za-z0-9]+$'  # Solo alfanumérico
    )
    email: EmailStr
    full_name: str | None = Field(max_length=255)  # Opcional, máximo 255 chars
```

### 9.3 Implementación: Sanitización Manual

**Archivo:** `app/routers/public.py` (líneas 44-46)

```python
@router.post("/register", status_code=201)
def register_project(request: Request, payload: RegisterProjectRequest, ...):
    # Sanitización de entradas de usuario
    matricula = payload.matricula.strip().upper()  # Normalizar formato
    email = payload.email.strip().lower()          # Normalizar email
    temp_code_value = (payload.temp_temp or "").strip().upper()
    # ...
```

**Buenas prácticas aplicadas:**
- `strip()`: Elimina espacios en blanco
- `upper()/lower()`: Normaliza mayúsculas/minúsculas
- `max_length` en campos de texto: Previene payloads enormes

---

## 10. Protección de Credenciales

### 10.1 Concepto: Gestión de Secretos

Las credenciales (contraseñas, claves API, tokens) nunca deben:
- Estar en el código fuente
- Estar en el repositorio git
- Mostrarse en logs o errores

### 10.2 Implementación: Variables de Entorno

**Archivo:** `app/core/config.py` (líneas 6-32)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Configuración cargada desde variables de entorno.
    Pydantic Settings busca automáticamente en el archivo .env
    """
    # Base de datos
    DATABASE_URL: str  # Requerida, falla si no existe
    
    # JWT
    JWT_SECRET: str     # Requerida
    JWT_ALG: str = "HS256"  # Valor por defecto
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # Valor por defecto
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None    # Opcional
    GOOGLE_CLIENT_SECRET: str | None = None # Opcional
    STUDENT_EMAIL_DOMAIN: str = "tec.mx"   # Valor por defecto
    
    model_config = SettingsConfigDict(
        env_file=".env",      # Archivo a cargar
        extra="ignore",      # Ignorar variables extra en .env
    )
```

**Archivo:** `.env.example`

```bash
# Este archivo se commitea como ejemplo, SIN valores reales
DATABASE_URL=postgresql://user:PASSWORD@host:port/database
JWT_SECRET=GENERA_UNO_SEGURO_DE_32_CARACTERES_MINIMO
GOOGLE_CLIENT_ID=TU_CLIENT_ID.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=TU_CLIENT_SECRET
```

### 10.3 Validación de Configuración

**Archivo:** `scripts/security_check.py`

Script que verifica antes del despliegue:
```python
def check_jwt_secret():
    """Verifica que JWT_SECRET sea seguro."""
    secret = settings.JWT_SECRET
    if len(secret) < 32:
        return False  # Rechazar despliegue
    if secret in ["supersecret", "password", "123456"]:
        return False  # Valor por defecto inseguro
    return True

def check_environment():
    """Verifica configuración de producción."""
    if ENVIRONMENT == "production":
        if not FRONTEND_URL:
            return False  # CORS bloquearía todo
    return True
```

---

## Resumen de Seguridad

| Capa | Tecnología | Protege contra |
|------|-----------|----------------|
| **Transporte** | HTTPS | MITM, sniffing |
| **Autenticación** | JWT + bcrypt | Suplantación de identidad |
| **Autorización** | RBAC (roles) | Acceso no autorizado |
| **Sesión** | HttpOnly Cookies | XSS, session hijacking |
| **Integridad** | JWT Firmado | Tampering de tokens |
| **API** | Rate Limiting | DoS, fuerza bruta |
| **Navegador** | Security Headers | XSS, clickjacking |
| **Datos** | Pydantic Validation | Inyección, corrupción |
| **Configuración** | Env Variables | Fuga de credenciales |

---

## Checklist para Nuevos Desarrolladores

Antes de hacer deploy, verifica:

- [ ] `.env` está en `.gitignore` y **NUNCA** commiteado
- [ ] `JWT_SECRET` tiene al menos 32 caracteres aleatorios
- [ ] Contraseñas requieren mayúscula, minúscula, número y especial
- [ ] Cookies usan `httponly=True` y `secure=True` en producción
- [ ] CORS solo permite dominios explícitos en producción
- [ ] Rate limiting está activo en endpoints de login
- [ ] Headers de seguridad están configurados
- [ ] Ejecutar `python scripts/security_check.py` pasa todas las pruebas

---

## Recursos Adicionales

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [JWT.io - Debugger](https://jwt.io/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Docs](https://fastapi.tiangolo.com/tutorial/security/)
