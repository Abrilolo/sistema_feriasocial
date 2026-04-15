#!/bin/bash
# build.sh — Script de build para Render
# Render lo ejecuta ANTES de iniciar el servidor en cada deploy.
# Garantiza que las migraciones de BD siempre estén al día.

set -e  # Salir inmediatamente si cualquier comando falla

echo "=== [1/2] Instalando dependencias ==="
pip install -r requirements.txt

echo "=== [2/2] Aplicando migraciones de base de datos ==="
python -m alembic upgrade head

echo "=== Build completado exitosamente ==="
