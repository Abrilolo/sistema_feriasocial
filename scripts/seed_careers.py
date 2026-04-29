"""
Seed script para cargar carreras en la base de datos desde CSV.
Uso: python scripts/seed_careers.py
"""
import sys
import csv
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_db
from app.models.career import Career
from sqlalchemy.orm import Session


def seed_careers(db: Session, csv_path: str | None = None):
    """Carga las carreras en la base de datos desde CSV."""
    if csv_path is None:
        csv_path = Path(__file__).parent.parent / "app" / "data" / "carreras.csv"

    csv_path = Path(csv_path)

    if not csv_path.exists():
        print(f"❌ Archivo CSV no encontrado: {csv_path}")
        return

    print(f"Cargando carreras desde: {csv_path}")

    # Leer CSV
    careers_data = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                careers_data.append({
                    "nombre_carrera": row.get("Nombre de la Carrera", "").strip(),
                    "siglas": row.get("Siglas", "").strip(),
                    "escuela": row.get("Escuela", "").strip(),
                })
    except Exception as e:
        print(f"❌ Error al leer CSV: {e}")
        return

    if not careers_data:
        print("❌ No se encontraron carreras en el CSV")
        return

    # Verificar si ya existen
    existing_count = db.query(Career).count()
    if existing_count > 0:
        print(f"Ya existen {existing_count} carreras en la base de datos.")
        response = input("¿Deseas reemplazarlas? (s/n): ").strip().lower()
        if response != "s":
            print("Cancelado.")
            return

        db.query(Career).delete()
        db.commit()
        print("Carreras anteriores eliminadas.")

    # Insertar nuevas carreras
    for data in careers_data:
        career = Career(**data)
        db.add(career)

    db.commit()
    print(f"✓ {len(careers_data)} carreras cargadas exitosamente.")


if __name__ == "__main__":
    db = next(get_db())
    try:
        seed_careers(db)
    finally:
        db.close()
