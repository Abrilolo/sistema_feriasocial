import uuid
import random
from datetime import datetime, timedelta
from app.db.session import SessionLocal
from app.models.student import Student
from app.models.project import Project
from app.models.checkin import Checkin
from app.models.temp_code import TempCode
from app.models.registration import Registration

def seed():
    db = SessionLocal()
    try:
        print("Obteniendo estudiantes con checkin...")
        checkins = db.query(Checkin).all()
        projects = db.query(Project).all()
        
        if not projects or not checkins:
            print("Faltan proyectos o checkins!")
            return

        print(f"Encontrados {len(checkins)} checkins. Generando registros...")

        # Ya tenemos a los students en checkin
        student_ids = [c.student_id for c in checkins]
        registrants = random.sample(student_ids, min(200, len(student_ids)))

        new_codes = []
        new_registrations = []

        now = datetime.utcnow()

        # Generar todo puramente en memoria
        for s_id in registrants:
            p = random.choice(projects)
            t_id = uuid.uuid4()
            t = TempCode(
                id=t_id,
                code=f"SIM-REG-{s_id}-{uuid.uuid4().hex[:6]}",
                project_id=p.id,
                created_by_user_id=p.owner_user_id,
                expires_at=now + timedelta(minutes=5),
                is_active=False,
                used_at=now
            )
            new_codes.append(t)
            
            r = Registration(
                id=uuid.uuid4(),
                student_id=s_id,
                project_id=p.id,
                temp_code_id=t_id,
                status="CONFIRMED",
                created_at=now
            )
            new_registrations.append(r)
        
        print(f"Haciendo bulk insert de {len(new_codes)} registros...")
        db.add_all(new_codes)
        db.flush()
        db.add_all(new_registrations)
        db.commit()
        print("Registros añadidos exitosamente!")

    except Exception as e:
        print(f"Error {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
