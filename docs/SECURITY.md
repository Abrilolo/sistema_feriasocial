# Guía de Seguridad

Este documento describe las medidas de seguridad implementadas en el sistema y cómo mantenerlas.

## 🔒 Credenciales

### Archivo .env
- **NUNCA** hagas commit del archivo `.env`
- El archivo ya está en `.gitignore` (línea 138)
- Si accidentalmente expusiste credenciales, sigue la sección "Rotación de Credenciales"

### Variables Requeridas

```bash
# Base de datos (formato para Supabase)
DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@db.PROJECT_REF.supabase.co:5432/postgres?sslmode=require

# JWT (generar con: openssl rand -hex 32)
JWT_SECRET=tu_secret_de_32_caracteres_o_mas
JWT_ALG=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Entorno
ENVIRONMENT=development  # o "production"
FRONTEND_URL=https://tu-dominio.com  # Requerido en producción
```

## 🔄 Rotación de Credenciales

Si las credenciales fueron expuestas:

1. **Inmediato**: Cambiar contraseña de base de datos en Supabase
2. **Generar nuevo JWT_SECRET**: `openssl rand -hex 32`
3. **Actualizar `.env`** con las nuevas credenciales
4. **Limpiar historial git**: Ver `scripts/rotate_credentials.sh` o `.bat`

## 🛡️ Medidas Implementadas

### 1. Validación de Autenticación (views.py)
- Los usuarios se validan contra la base de datos en cada request
- Usuarios desactivados (`is_active=False`) son rechazados inmediatamente

### 2. Contraseñas Fuertes (admin.py)
Requisitos para nuevas contraseñas:
- Mínimo 8 caracteres
- Al menos una mayúscula
- Al menos una minúscula
- Al menos un número
- Al menos un carácter especial

### 3. Configuración CORS (main.py)
- En producción: solo permite el dominio configurado en `FRONTEND_URL`
- En desarrollo: permite localhost
- Variables `localhost` se ignoran en producción

### 4. Headers de Seguridad
- Content-Security-Policy
- Strict-Transport-Security
- X-Content-Type-Options
- X-Frame-Options
- Referrer-Policy
- Permissions-Policy

### 5. Rate Limiting
- Límites por IP usando slowapi
- Endpoints sensibles: 5 intentos por minuto

## 🚨 Verificación de Seguridad

Para verificar que la configuración es segura:

```bash
# Verificar que .env no esté trackeado
git ls-files | grep -E "\.env($|\.[^/]+)$"
# No debe mostrar ningún archivo .env

# Verificar que JWT_SECRET tenga al menos 32 caracteres
python -c "from app.core.config import settings; print(f'JWT_SECRET length: {len(settings.JWT_SECRET)} chars')"

# Verificar entorno
python -c "import os; print(f'ENVIRONMENT: {os.getenv(\"ENVIRONMENT\", \"development\")}')"
```

## 📋 Lista de Verificación Pre-Despliegue

- [ ] `ENVIRONMENT=production` está configurado
- [ ] `FRONTEND_URL` apunta al dominio correcto
- [ ] `JWT_SECRET` tiene al menos 32 caracteres aleatorios
- [ ] Contraseña de base de datos es fuerte y única
- [ ] `.env` no está en el historial de git
- [ ] Rate limiting está configurado con Redis (para múltiples instancias)

## 🐛 Reportar Vulnerabilidades

Si descubres una vulnerabilidad de seguridad:
1. NO la reportes en issues públicos
2. Contacta al equipo de desarrollo directamente
3. Proporciona detalles y pasos para reproducir

## 📚 Recursos

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Supabase Security](https://supabase.com/docs/guides/platform/security)
