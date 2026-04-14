# Limpieza de Historial Git - Credenciales Expuestas

## ⚠️ URGENTE

El archivo `.env` con credenciales sensibles fue subido al repositorio.
**DEBES** seguir estos pasos para limpiar el historial de git.

## Acciones Inmediatas Requeridas

### Paso 1: Realizar Cambios de Seguridad (Ya Hechos)

Los siguientes archivos fueron modificados/creados:
- `app/routers/views.py` - Validación de usuario contra BD
- `app/routers/admin.py` - Validación de contraseñas fuertes
- `app/main.py` - Configuración CORS segura
- `.env.example` - Ejemplo de configuración segura
- `scripts/security_check.py` - Script de verificación
- `docs/SECURITY.md` - Documentación de seguridad

### Paso 2: Rotar Credenciales en Supabase

1. **Cambiar contraseña de PostgreSQL**:
   - Ve a tu panel de Supabase
   - Project Settings → Database
   - Cambia la contraseña del usuario `postgres`
   - Guarda la nueva contraseña

2. **Actualizar archivo `.env` local**:
   ```bash
   # Actualiza DATABASE_URL con la nueva contraseña
   DATABASE_URL=postgresql://postgres.addhrktsfuogdfnpwevx:NUEVA_PASSWORD@...
   ```

3. **Generar nuevo JWT_SECRET**:
   ```bash
   # Linux/Mac
   openssl rand -hex 32

   # Windows (PowerShell)
   [convert]::ToBase64String((1..32 | % {Get-Random -Maximum 256} | % {'{0:X2}' -f $_}))
   ```

### Paso 3: Limpiar Historial de Git

**Opción A: Usar git-filter-repo (Recomendado)**

```bash
# 1. Instalar git-filter-repo
pip install git-filter-repo

# 2. Crear archivo de reemplazo
# Crea un archivo llamado "expressions.txt" con:
literal:TU_PASSWORD_ANTIGUA==>NUEVA_PASSWORD_PLACEHOLDER
literal:TU_JWT_ANTIGUO==>NUEVO_JWT_PLACEHOLDER

# 3. Ejecutar limpieza
git filter-repo --replace-text expressions.txt

# 4. Forzar push al remoto (⚠️ CUIDADO)
git push origin main --force-with-lease
```

**Opción B: Usar BFG Repo-Cleaner**

```bash
# 1. Descargar BFG
curl -o bfg.jar https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar

# 2. Crear archivo passwords.txt con contenido:
# PASSWORD_ANTIGUA==>***REMOVED***

# 3. Ejecutar
java -jar bfg.jar --replace-text passwords.txt repo.git

# 4. Limpiar y forzar push
cd repo.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push origin main --force
```

**Opción C: Reescribir Historial Manualmente (Nuclear)**

```bash
# 1. Crear nueva rama orfana
git checkout --orphan new-main

# 2. Agregar todos los archivos (excepto .env)
git add -A

# 3. Commit inicial
git commit -m "Initial commit with clean history"

# 4. Renombrar ramas
git branch -m main old-main
git branch -m new-main main

# 5. Forzar push
git push origin main --force

# 6. Eliminar rama antigua local
git branch -D old-main
```

### Paso 4: Verificar Limpieza

```bash
# Buscar credenciales antiguas en el historial
git log --all --full-history -- .env
git log --all -p --grep="contraseña"

# Si no encuentras nada, la limpieza fue exitosa
```

### Paso 5: Informar al Equipo

**IMPORTANTE**: Después de reescribir el historial:
- Todos los colaboradores deben clonar el repositorio nuevamente
- Cualquier PR abierto quedará obsoleto
- Los forks del repositorio tendrán historial inconsistente

Comunica al equipo:
```
ATENCIÓN: El historial del repositorio fue reescrito por seguridad.

Acciones requeridas:
1. Guarda tus cambios locales no commiteados
2. Elimina tu carpeta del repositorio local
3. Clona nuevamente: git clone <url>
4. Crea nuevas ramas para tus cambios pendientes
```

## Verificación Post-Limpieza

Ejecuta el script de seguridad:
```bash
python scripts/security_check.py
```

Debe mostrar:
- `[OK]` para todas las verificaciones
- Sin mensajes `[CRITICAL]`

## Prevención Futura

1. **Instalar pre-commit hook** (opcional):
   ```bash
   pip install pre-commit
   # Crear .pre-commit-config.yaml
   ```

2. **Verificar antes de cada commit**:
   ```bash
   git ls-files | grep -E "\.env($|\.[^/]+)$"
   # No debe mostrar ningún archivo .env
   ```

3. **Usar secret scanning de GitHub**:
   - Settings → Security & analysis
   - Habilitar "Secret scanning"

## Recursos

- [GitHub: Removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [git-filter-repo docs](https://github.com/newren/git-filter-repo)
- [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)
