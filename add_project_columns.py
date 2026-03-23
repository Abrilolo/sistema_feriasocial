import sqlalchemy as sa
from app.db.session import engine

alter_statements = [
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS periodo VARCHAR(255);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS carreras_permitidas VARCHAR(255);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS objetivo VARCHAR(2000);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS actividades VARCHAR(2000);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS horario VARCHAR(255);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS competencias_requeridas VARCHAR(2000);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS modalidad VARCHAR(255);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS lugar_trabajo VARCHAR(255);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS duracion VARCHAR(255);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS poblacion_atendida VARCHAR(255);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS horas_acreditar VARCHAR(255);",
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS comentarios_adicionales VARCHAR(2000);",
]

with engine.connect() as conn:
    for stmt in alter_statements:
        try:
            conn.execute(sa.text(stmt))
            print(f"Executed: {stmt}")
        except Exception as e:
            print(f"Error executing {stmt}: {e}")
    conn.commit()
    print("Migración completada exitosamente.")
