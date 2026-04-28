import random
import uuid
import sys
from datetime import datetime, timedelta

from app.db.session import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.student import Student
from app.models.project import Project
from app.models.checkin import Checkin
from app.models.temp_code import TempCode
from app.models.registration import Registration

def seed():
    db = SessionLocal()
    try:
        print("Iniciando simulación de datos...")

        # 1. Crear o asegurar usuarios básicos
        print("Asegurando administradores, socios y becarios...")
        roles = ["ADMIN", "SOCIO", "BECARIO"]
        users = {}
        for r in roles:
            email = f"{r.lower()}@test.com"
            u = db.query(User).filter(User.email == email).first()
            if not u:
                u = User(
                    email=email,
                    hashed_password=hash_password("password123"),
                    role=r,
                    organization_name=f"Organización {r}" if r == "SOCIO" else None,
                    is_active=True
                )
                db.add(u)
                db.commit()
                db.refresh(u)
            users[r] = u
        
        # 2. Add extra socios y becarios (para la gráfica de Personal)
        for i in range(1, 10):
            email = f"socio{i}@ong.com"
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, hashed_password=hash_password("pwd"), role="SOCIO", organization_name=f"Asociación Civil {i}"))
        for i in range(1, 15):
            email = f"staff{i}@tec.mx"
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, hashed_password=hash_password("pwd"), role="BECARIO"))
        db.commit()

        all_socios = db.query(User).filter(User.role == "SOCIO").all()
        admin_user = users["ADMIN"]
        becario_user = users["BECARIO"]

        # 3. Crear Proyectos
        print("Generando 15 Proyectos de la Feria...")
        project_names = [
            "Construcción de Viviendas", "Asesoría Legal Comunitaria", "Reforestación Urbana", 
            "Clases de Matemáticas", "Brigada Médica", "Apoyo a Emprendedores", 
            "Campaña de Reciclaje", "Desarrollo de App Social", "Consultoría Financiera Mipymes",
            "Mantenimiento de Escuelas", "Cuidado de Animales Rescatados", "Lectura en Hospitales",
            "Banco de Alimentos", "Taller de Arte para Niños", "Huertos Comunitarios"
        ]
        
        projects = []
        for name in project_names:
            p = db.query(Project).filter(Project.name == name).first()
            if not p:
                socio = random.choice(all_socios)
                capacity = random.choice([10, 15, 20, 30, 50, 100])
                p = Project(
                    name=name,
                    description=f"Descripción simulada para {name}",
                    capacity=capacity,
                    owner_user_id=socio.id,
                    is_active=True,
                    carreras_permitidas="ITC, LAF, IBT",
                    periodo="Febrero - Junio"
                )
                db.add(p)
                db.commit()
                db.refresh(p)
            projects.append(p)

        # 4. Crear Estudiantes (Simulando 200 Alumnos)
        print("Generando 200 Estudiantes...")
        students = db.query(Student).all()
        existing_mats = set(s.matricula for s in students)
        
        new_students = []
        for i in range(1, 401): # Vamos a hacer 400
            matricula = f"A0{random.randint(1000000, 9999999)}"
            if matricula not in existing_mats:
                email = f"{matricula}@tec.mx"
                s = Student(
                    matricula=matricula,
                    email=email,
                    full_name=f"Estudiante Simulado {i}",
                    career=random.choice(["ITC", "LAF", "IBT", "IMT", "LIN", "LDI"])
                )
                new_students.append(s)
                existing_mats.add(matricula)
        
        if new_students:
            db.add_all(new_students)
            db.commit()
            print(f"Insertados {len(new_students)} nuevos estudiantes.")
        
        students = db.query(Student).all()

        # 5. Simular Check-Ins (Aprox 300 Entraron a la Feria)
        print("Simulando Check-Ins en puerta...")
        checked_in_students = random.sample(students, min(300, len(students)))
        new_checkins = []
        for s in checked_in_students:
            c = db.query(Checkin).filter(Checkin.student_id == s.id).first()
            if not c:
                c = Checkin(
                    student_id=s.id,
                    becario_user_id=becario_user.id,
                    method="QR",
                    checked_in_at=datetime.utcnow() - timedelta(minutes=random.randint(10, 120))
                )
                new_checkins.append(c)
        if new_checkins:
            db.add_all(new_checkins)
            db.commit()

        # 6. Simular Códigos Temporales (Pases QR generados por Socios) y Registros
        print("Generando Pases QR y Registros en Proyectos...")
        # Asumamos que de los 140 que entraron, 100 se registraron (QR Usado), 15 tienen el QR en mano (Activo) y 5 expiraron.
        # Además algunos estudiantes sin check-in intentaron generar códigos pero expiraron.
        
        # Mezclamos
        registrants = random.sample(checked_in_students, min(200, len(checked_in_students)))
        active_pass_students = random.sample([x for x in checked_in_students if x not in registrants], 30)
        expired_pass_students = random.sample([x for x in checked_in_students if x not in registrants and x not in active_pass_students], 10)

        new_codes = []
        new_registrations = []

        for s in registrants:
            # Revisa si ya tiene un código
            t = db.query(TempCode).filter(TempCode.code.like(f"SIM-{s.matricula}-%")).first()
            if not t:
                p = random.choice(projects)
                t = TempCode(
                    code=f"SIM-{s.matricula}-{uuid.uuid4().hex[:6]}",
                    project_id=p.id,
                    created_by_user_id=p.owner_user_id,
                    expires_at=datetime.utcnow() + timedelta(minutes=5),
                    is_active=True,
                    used_at=datetime.utcnow()
                )
                db.add(t)
                db.flush() # Importante para obtener ID antes de registrar

                # Crear Registration
                reg = db.query(Registration).filter(Registration.student_id == s.id).first()
                if not reg:
                    reg = Registration(
                        student_id=s.id,
                        project_id=p.id,
                        temp_code_id=t.id,
                        status="CONFIRMED"
                    )
                    new_registrations.append(reg)
        
        # Pases Activos (Generados pero no canjeados)
        for s in active_pass_students:
            p = random.choice(projects)
            t = TempCode(
                code=f"SIM-ACT-{s.matricula}-{uuid.uuid4().hex[:6]}",
                project_id=p.id,
                created_by_user_id=p.owner_user_id,
                expires_at=datetime.utcnow() + timedelta(minutes=10),
                is_active=True,
                used_at=None
            )
            db.add(t)
            
        # Pases Expirados
        for s in expired_pass_students:
            p = random.choice(projects)
            t = TempCode(
                code=f"SIM-EXP-{s.matricula}-{uuid.uuid4().hex[:6]}",
                project_id=p.id,
                created_by_user_id=p.owner_user_id,
                expires_at=datetime.utcnow() - timedelta(minutes=10),
                is_active=True,
                used_at=None
            )
            db.add(t)

        db.add_all(new_registrations)
        db.commit()

        print("¡Simulación completada con éxito! Ya puedes ver hermosos datos en tu Dashboard.")

    except Exception as e:
        print(f"Error generando datos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
