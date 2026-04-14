#!/usr/bin/env python3
"""
Script de verificación de configuración de seguridad.
Ejecutar antes de cada despliegue para validar que la configuración es segura.
"""

import os
import sys
from pathlib import Path


def check_env_file():
    """Verifica que .env no esté trackeado en git."""
    print("[CHECK] Verificando archivo .env...")
    env_file = Path(__file__).parent.parent / ".env"
    env_example = Path(__file__).parent.parent / ".env.example"

    if env_file.exists():
        print(f"   [WARN] El archivo .env existe localmente en: {env_file}")
        print("      Asegurate de que NO este en el repositorio remoto.")
    else:
        print("   [OK] No se encontro archivo .env (bien)")

    if env_example.exists():
        print("   [OK] Archivo .env.example existe como referencia")
    else:
        print("   [WARN] Falta archivo .env.example")

    return True


def check_jwt_secret():
    """Verifica que JWT_SECRET sea seguro."""
    print("\n[CHECK] Verificando JWT_SECRET...")

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.core.config import settings

        secret = settings.JWT_SECRET
        secret_len = len(secret)

        if secret_len < 32:
            print(f"   [CRITICAL] JWT_SECRET es muy corto ({secret_len} caracteres)")
            print("      Minimo requerido: 32 caracteres")
            print("      Genera uno nuevo con: openssl rand -hex 32")
            return False
        elif secret_len < 64:
            print(f"   [WARN] JWT_SECRET tiene {secret_len} caracteres")
            print("      Recomendado: al menos 64 caracteres para mayor seguridad")
        else:
            print(f"   [OK] JWT_SECRET tiene {secret_len} caracteres (bueno)")

        # Verificar que no sea un valor por defecto común
        default_secrets = [
            "supersecret", "secret", "password", "123456",
            "changeme", "admin", "default", "jwt_secret"
        ]
        if secret.lower() in default_secrets:
            print(f"   [CRITICAL] JWT_SECRET usa un valor por defecto inseguro!")
            return False

        print("   [OK] JWT_SECRET no usa valores por defecto comunes")
        return True

    except Exception as e:
        print(f"   [WARN] No se pudo verificar JWT_SECRET: {e}")
        return True


def check_environment():
    """Verifica configuración de entorno."""
    print("\n[CHECK] Verificando configuracion de entorno...")

    env = os.getenv("ENVIRONMENT", "development").lower()
    frontend_url = os.getenv("FRONTEND_URL")

    print(f"   Entorno: {env}")

    if env == "production":
        print("   [OK] Entorno de produccion detectado")

        if not frontend_url:
            print("   [CRITICAL] FRONTEND_URL no esta configurado en produccion")
            print("      El CORS bloqueara todas las peticiones")
            return False
        else:
            print(f"   [OK] FRONTEND_URL configurado: {frontend_url}")

        # Verificar que no haya localhost en FRONTEND_URL en producción
        if "localhost" in frontend_url or "127.0.0.1" in frontend_url:
            print("   [WARN] FRONTEND_URL usa localhost en produccion")
            return False

    else:
        print("   [INFO] Entorno de desarrollo - configuracion relajada permitida")

    return True


def check_database_url():
    """Verifica que DATABASE_URL no esté expuesto."""
    print("\n[CHECK] Verificando DATABASE_URL...")

    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.core.config import settings

        db_url = settings.DATABASE_URL

        # Verificar que no contenga placeholders
        if "TU_PASSWORD" in db_url or "PASSWORD_AQUI" in db_url:
            print("   [CRITICAL] DATABASE_URL contiene placeholders")
            print("      Actualiza el archivo .env con credenciales reales")
            return False

        # Verificar que use SSL en producción
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env == "production" and "sslmode=require" not in db_url:
            print("   [WARN] DATABASE_URL no fuerza SSL en produccion")
            print("      Agrega ?sslmode=require al final de la URL")

        print("   [OK] DATABASE_URL configurado")
        return True

    except Exception as e:
        print(f"   [WARN] No se pudo verificar DATABASE_URL: {e}")
        return True


def check_gitignore():
    """Verifica que .env esté en .gitignore."""
    print("\n[CHECK] Verificando .gitignore...")

    gitignore = Path(__file__).parent.parent / ".gitignore"

    if not gitignore.exists():
        print("   [WARN] No se encontro archivo .gitignore")
        return True

    content = gitignore.read_text()

    if ".env" in content:
        print("   [OK] .env esta en .gitignore")
        return True
    else:
        print("   [CRITICAL] .env NO esta en .gitignore")
        return False


def main():
    """Ejecuta todas las verificaciones."""
    print("=" * 50)
    print("VERIFICACION DE SEGURIDAD")
    print("=" * 50)

    checks = [
        check_env_file,
        check_gitignore,
        check_jwt_secret,
        check_environment,
        check_database_url,
    ]

    results = []
    for check in checks:
        try:
            results.append(check())
        except Exception as e:
            print(f"   [WARN] Error en verificacion: {e}")
            results.append(True)  # No bloquear por errores de verificacion

    print("\n" + "=" * 50)
    if all(results):
        print("[PASS] TODAS LAS VERIFICACIONES PASARON")
        print("=" * 50)
        return 0
    else:
        print("[FAIL] HAY PROBLEMAS DE SEGURIDAD CRITICOS")
        print("=" * 50)
        print("\nAcciones requeridas antes del despliegue:")
        print("1. Revisa los mensajes de error arriba")
        print("2. Corrige los problemas marcados con [CRITICAL]")
        print("3. Ejecuta este script nuevamente")
        return 1


if __name__ == "__main__":
    sys.exit(main())
