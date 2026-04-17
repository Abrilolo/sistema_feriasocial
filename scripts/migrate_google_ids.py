"""
Script de Anonimización Retroactiva de google_id.
Convierte IDs de Google en texto plano a hashes determinísticos (SHA-256).
"""
import sys
import hashlib
import hmac
import re

sys.path.insert(0, ".")

from sqlalchemy import text
from app.db.session import engine, SessionLocal
from app.core.config import settings
from app.services.auth_service import StudentAuthService

def migrate_ids():
    print("=== Iniciando anonimización de google_id en Supabase ===")
    
    db = SessionLocal()
    try:
        # 1. Obtener alumnos que tienen el google_id original (que no es un hash de 64 chars)
        # Los IDs de Google son numéricos largos, los hashes son hex de 64 chars.
        students = db.execute(text(
            "SELECT id, google_id FROM students WHERE google_id IS NOT NULL AND LENGTH(google_id) < 60"
        )).fetchall()
        
        if not students:
            print("No se encontraron registros que requieran anonimización.")
            return

        print(f"Encontrados {len(students)} registros para procesar.")
        
        count = 0
        for s_id, g_id in students:
            # Calcular el mismo hash que usa el backend ahora
            hashed = StudentAuthService.hash_google_id(g_id)
            
            # Actualizar en la BD
            db.execute(
                text("UPDATE students SET google_id = :hashed WHERE id = :id"),
                {"hashed": hashed, "id": s_id}
            )
            count += 1
            if count % 10 == 0:
                print(f"Procesados {count}...")

        db.commit()
        print(f"\n✅ Anonimización completada: {count} registros actualizados.")
        print("Ahora en Supabase verás hashes de 64 caracteres en lugar de los IDs reales.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante la migración: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_ids()
