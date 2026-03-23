import sqlalchemy as sa
from app.db.session import engine

alter_statements = [
    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS clave_programa VARCHAR(255);",
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
