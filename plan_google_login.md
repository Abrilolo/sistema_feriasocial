# Plan de Implementación: Google Login para Estudiantes

Para profesionalizar el acceso de los estudiantes y evitar que tengan que teclear sus datos manualmente cada vez, implementaremos **Google Login (OAuth2)**. Esto permitirá que solo estudiantes con una cuenta institucional `@tec.mx` (o el dominio que configures) puedan generar su código QR de entrada.

---

## 1. Requisitos Previos (Google Cloud)
Se requiere una configuración fuera del código en la [consola de Google Cloud](https://console.cloud.google.com/):
1.  Crear un nuevo **Proyecto**.
2.  Configurar la **OAuth Consent Screen**.
3.  Crear **OAuth 2.0 Client IDs** (Tipo: Web Application).
4.  Configurar las **Authorized redirect URIs**:
    *   `http://localhost:8000/auth/google/callback` (Local)
    *   `https://tusitio.com/auth/google/callback` (Producción)

---

## 2. Backend (FastAPI + Authlib)
Usaremos `authlib` para manejar el flujo de OAuth de forma sencilla y segura.

### A. Actualización de Modelos (`app/models/student.py`)
Añadir campos para vincular la cuenta de Google.
```python
class Student(Base):
    # ... otros campos ...
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    picture_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
```

### B. Configuración de Variables (`.env`)
```bash
GOOGLE_CLIENT_ID=XXXXX.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=XXXXX
SECRET_KEY=UnaClaveMuySeguraParaLaSesion
```

### C. Nuevos Endpoints de Autenticación (`app/routers/auth.py` o un nuevo router)
1.  **`/auth/google/login`**: Redirige al usuario a la página de Google.
2.  **`/auth/google/callback`**:
    *   Recibe el código de Google.
    *   Valida el token y obtiene el perfil (nombre, email).
    *   **Validación Crítica:** Verificar que el email termine en `@tec.mx`.
    *   Busca al estudiante en la BD por email. Si existe, actualiza su `google_id`. Si no existe, lo crea.
    *   Genera un token JWT del sistema y lo guarda en una cookie segura.

---

## 3. Frontend (UI)
### A. Nueva Vista de Acceso (`app/templates/estudiante_qr.html`)
Sustituir el formulario manual por un botón de "Iniciar Sesión con Google".
```html
<div class="card" style="text-align: center;">
    <h2>¡Hola de nuevo!</h2>
    <p>Inicia sesión con tu cuenta institucional para generar tu código QR.</p>
    <a href="/auth/google/login" class="btn-google">
        <img src="/static/img/google-icon.png" alt="Google Logo">
        Continuar con Google
    </a>
</div>
```

---

## 4. Flujo de Experiencia del Usuario (UX)
1.  **Paso 1:** El estudiante entra a `/acceso-estudiante`.
2.  **Paso 2:** Hace clic en "Continuar con Google".
3.  **Paso 3:** Selecciona su cuenta de `@tec.mx`.
4.  **Paso 4:** Automáticamente se le redirige a la vista del QR con sus datos ya cargados (`A0123...`, Nombre Completo).
5.  **Paso 5:** El QR se genera instantáneamente sin teclear nada.

---

## 5. Beneficios de Seguridad
1.  **Identidad Verificada:** Eliminamos el riesgo de que un estudiante use la matrícula de otro, ya que validamos la sesión de Google.
2.  **Menos Errores:** No habrá errores de dedo al escribir el email o la matrícula.
3.  **Auditabilidad:** Sabremos exactamente quién inició sesión y cuándo.

---

## Próximos Pasos Sugeridos
1.  **Instalar dependencias:** `pip install authlib itsdangerous`
2.  **¿Deseas que proceda con la creación de las credenciales de prueba y los routers de Google Login ahora?**
