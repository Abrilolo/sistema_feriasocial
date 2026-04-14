@echo off
REM ============================================
REM Script de rotación de credenciales expuestas
REM ============================================
echo ============================================
echo ROTACION DE CREDENCIALES DE SEGURIDAD
echo ============================================
echo.
echo Este script ayuda a rotar credenciales expuestas.
echo Sigue estos pasos:
echo.
echo 1. Genera un nuevo JWT_SECRET seguro:
echo    powershell -Command "[convert]::ToBase64String((1..32 | %% {Get-Random -Maximum 256} | %% {'{0:X2}' -f $_})) -replace '=', ''"
echo.
echo 2. Actualiza el archivo .env con:
echo    - Nuevo JWT_SECRET
echo    - Nueva contrasena de base de datos (si fue expuesta)
echo.
echo 3. Acciones a realizar en Supabase:
echo    a) Ve a Project Settings -^> Database
echo    b) Cambia la contrasena de postgres
echo    c) Actualiza DATABASE_URL en .env
echo.
echo 4. Despues de actualizar .env:
echo    a) NO hagas commit de .env
echo    b) Verifica que .env esta en .gitignore
echo.
echo ============================================
echo LIMPIAR HISTORIAL GIT DE CREDENCIALES
echo ============================================
echo.
echo Opcion A - Usar git-filter-repo (recomendado):
echo   1. Instala git-filter-repo: pip install git-filter-repo
echo   2. Ejecuta: git filter-repo --replace-text expresions.txt
echo   3. Crea expressions.txt con:
echo      literal:CONTRASENA_ANTIGUA==^>CONTRASENA_NUEVA
echo.
echo Opcion B - Usar BFG Repo-Cleaner:
echo   1. Descarga BFG: https://rtyley.github.io/bfg-repo-cleaner/
echo   2. java -jar bfg.jar --replace-text contrasenas.txt repo.git
echo.
echo Opcion C - Reescribir historial manualmente:
echo   1. git checkout --orphan new-main
echo   2. git add -A
echo   3. git commit -m "Initial commit with clean history"
echo   4. git branch -m main old-main
echo   5. git branch -m new-main main
echo   6. git push origin main --force
echo.
echo ADVERTENCIA: Opciones A, B y C reescriben el historial de git.
echo Todos los colaboradores deben clonar el repositorio nuevamente.
echo.
pause
