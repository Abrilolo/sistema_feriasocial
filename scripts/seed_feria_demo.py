# scripts/seed_feria_demo.py
"""
Seed completo para simular la feria en vivo.

Crea:
  - 6 socios formadores con sus proyectos (2 por socio)
  - 1 becario de entrada
  - 5  estudiantes solo con pre-registro (aún no llegaron)
  - 8  estudiantes que llegaron pero NO hicieron check-in todavía
      (tienen cuenta en students, sin checkin)
  - 7  estudiantes con check-in hecho pero sin proyecto
  - 15 estudiantes con check-in + registro confirmado en proyectos

Uso:
    python -m scripts.seed_feria_demo
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import hmac as hmac_lib
import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.career import Career
from app.models.checkin import Checkin
from app.models.pre_registration import PreRegistration
from app.models.project import Project
from app.models.registration import Registration
from app.models.student import Student
from app.models.temp_code import TempCode
from app.models.user import User

PASSWORD = "SoS1234!"

# ---------------------------------------------------------------------------
# Datos de socios y proyectos
# ---------------------------------------------------------------------------

SOCIOS_DATA = [
    {
        "email": "cruz.roja@feria.mx",
        "org": "Cruz Roja Mexicana",
        "projects": [
            {
                "name": "Primeros Auxilios Comunitarios",
                "desc": "Capacitar a comunidades vulnerables en técnicas básicas de primeros auxilios y RCP.",
                "capacity": 25,
                "modalidad": "Presencial",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "Medicina, Enfermería, ICS",
                "clave": "CRM-001",
            },
            {
                "name": "Brigadas de Salud Preventiva",
                "desc": "Jornadas de detección temprana de enfermedades crónicas en colonias marginadas.",
                "capacity": 20,
                "modalidad": "Presencial",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "Medicina, Nutrición, Psicología",
                "clave": "CRM-002",
            },
        ],
    },
    {
        "email": "bancoalimentos@feria.mx",
        "org": "Banco de Alimentos de Monterrey",
        "projects": [
            {
                "name": "Logística de Distribución Alimentaria",
                "desc": "Optimizar la cadena de distribución de alimentos a familias en situación de pobreza.",
                "capacity": 30,
                "modalidad": "Presencial",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "IEM, IIS, LAD",
                "clave": "BAM-001",
            },
            {
                "name": "Gestión de Voluntariado y Donaciones",
                "desc": "Administrar campañas de captación de donadores y coordinación de voluntarios.",
                "capacity": 20,
                "modalidad": "Híbrido",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "LAE, MKT, Comunicación",
                "clave": "BAM-002",
            },
        ],
    },
    {
        "email": "fundacion.telmex@feria.mx",
        "org": "Fundación Telmex Telcel",
        "projects": [
            {
                "name": "Digitalización de PYMEs Sociales",
                "desc": "Acompañar a microempresas sociales en su transformación digital.",
                "capacity": 18,
                "modalidad": "Híbrido",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "ITC, IIS, LAE, MKT",
                "clave": "FTT-001",
            },
            {
                "name": "Alfabetización Digital para Adultos Mayores",
                "desc": "Talleres de uso de smartphones y redes sociales en centros DIF.",
                "capacity": 22,
                "modalidad": "Presencial",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "Todas las carreras",
                "clave": "FTT-002",
            },
        ],
    },
    {
        "email": "dif.nl@feria.mx",
        "org": "DIF Nuevo León",
        "projects": [
            {
                "name": "Atención Psicosocial a Familias Vulnerables",
                "desc": "Intervención psicosocial con familias en riesgo en zonas metropolitanas.",
                "capacity": 15,
                "modalidad": "Presencial",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "Psicología, Trabajo Social, ICS",
                "clave": "DIF-001",
            },
            {
                "name": "Programa Nutricional Infantil",
                "desc": "Diagnóstico y seguimiento nutricional en estancias infantiles del DIF.",
                "capacity": 18,
                "modalidad": "Presencial",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "Nutrición, Medicina, Enfermería",
                "clave": "DIF-002",
            },
        ],
    },
    {
        "email": "aldeas.sos@feria.mx",
        "org": "Aldeas Infantiles SOS",
        "projects": [
            {
                "name": "Refuerzo Educativo para Niños en Acogimiento",
                "desc": "Apoyo académico y talleres de habilidades socioemocionales para menores.",
                "capacity": 20,
                "modalidad": "Presencial",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "Psicología, Educación, Trabajo Social",
                "clave": "AIS-001",
            },
            {
                "name": "Comunicación y Recaudación de Fondos",
                "desc": "Crear contenido digital y estrategias de comunicación para campañas de donación.",
                "capacity": 15,
                "modalidad": "Remoto",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "Comunicación, MKT, Diseño",
                "clave": "AIS-002",
            },
        ],
    },
    {
        "email": "cij.monterrey@feria.mx",
        "org": "Centro de Integración Juvenil",
        "projects": [
            {
                "name": "Prevención de Adicciones en Preparatorias",
                "desc": "Talleres y dinámicas de prevención dirigidos a jóvenes de preparatoria.",
                "capacity": 25,
                "modalidad": "Presencial",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "Psicología, Medicina, Comunicación",
                "clave": "CIJ-001",
            },
            {
                "name": "Rehabilitación y Reinserción Social",
                "desc": "Apoyo en talleres ocupacionales para personas en proceso de rehabilitación.",
                "capacity": 12,
                "modalidad": "Presencial",
                "horas": "480",
                "periodo": "Feb – Jun 2026",
                "carreras": "Psicología, Trabajo Social, Nutrición",
                "clave": "CIJ-002",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Estudiantes
# ---------------------------------------------------------------------------

# Grupo A: solo pre-registro (no llegaron / no han hecho login)
PREREGISTRO_ONLY = [
    ("A01810001", "ana.garcia2026@tec.mx", "Ana García Rodríguez",     "5512340001", "ITC"),
    ("A01810002", "carlos.mendez2026@tec.mx", "Carlos Méndez Torres",  "5512340002", "IEM"),
    ("A01810003", "sofia.luna2026@tec.mx",   "Sofía Luna Pérez",       "5512340003", "Psicología"),
    ("A01810004", "diego.reyes2026@tec.mx",  "Diego Reyes Castillo",   "5512340004", "LAE"),
    ("A01810005", "valeria.cruz2026@tec.mx", "Valeria Cruz Jiménez",   "5512340005", "Medicina"),
]

# Grupo B: ya hicieron login (están en students) pero NO hicieron check-in
LOGGED_NO_CHECKIN = [
    ("A01820001", "luis.herrera2026@tec.mx",   "Luis Herrera Morales",    "ITC"),
    ("A01820002", "mariana.vega2026@tec.mx",   "Mariana Vega Sánchez",    "Nutrición"),
    ("A01820003", "jose.flores2026@tec.mx",    "José Flores Gutiérrez",   "IEM"),
    ("A01820004", "paula.romero2026@tec.mx",   "Paula Romero Díaz",       "Comunicación"),
    ("A01820005", "andres.nava2026@tec.mx",    "Andrés Nava Espinoza",    "Medicina"),
    ("A01820006", "camila.ortiz2026@tec.mx",   "Camila Ortiz López",      "Diseño"),
    ("A01820007", "roberto.silva2026@tec.mx",  "Roberto Silva Ramírez",   "LAE"),
    ("A01820008", "natalia.rios2026@tec.mx",   "Natalia Ríos Mendoza",    "Psicología"),
]

# Grupo C: check-in hecho, sin proyecto todavía
CHECKIN_NO_PROJECT = [
    ("A01830001", "fernanda.ibarra2026@tec.mx",  "Fernanda Ibarra Salas",   "ITC"),
    ("A01830002", "miguel.leon2026@tec.mx",      "Miguel León Vargas",      "IIS"),
    ("A01830003", "daniela.nunez2026@tec.mx",    "Daniela Núñez Ramos",     "Trabajo Social"),
    ("A01830004", "emilio.paredes2026@tec.mx",   "Emilio Paredes Fuentes",  "MKT"),
    ("A01830005", "isabella.mora2026@tec.mx",    "Isabella Mora Delgado",   "Psicología"),
    ("A01830006", "santiago.bravo2026@tec.mx",   "Santiago Bravo Acosta",   "IEM"),
    ("A01830007", "valentina.gu2026@tec.mx",     "Valentina Guerrero Paz",  "Nutrición"),
]

# Grupo D: check-in + registro confirmado a proyecto
# (matricula, email, nombre, carrera, índice_proyecto 0-11)
FULL_REGISTERED = [
    ("A01840001", "alejandro.mp2026@tec.mx",  "Alejandro Montes Peña",       "ITC",           0),
    ("A01840002", "gabriela.ts2026@tec.mx",   "Gabriela Torres Salinas",     "Medicina",      0),
    ("A01840003", "hector.ao2026@tec.mx",     "Héctor Arce Olmedo",          "IEM",           1),
    ("A01840004", "lorena.vr2026@tec.mx",     "Lorena Vidal Ruiz",           "Nutrición",     1),
    ("A01840005", "pablo.ch2026@tec.mx",      "Pablo Chávez Hinojosa",       "LAE",           2),
    ("A01840006", "andrea.mg2026@tec.mx",     "Andrea Martínez García",      "MKT",           2),
    ("A01840007", "ivan.bm2026@tec.mx",       "Iván Blanco Meza",            "ITC",           3),
    ("A01840008", "diana.co2026@tec.mx",      "Diana Campos Orozco",         "Psicología",    4),
    ("A01840009", "oscar.fn2026@tec.mx",      "Óscar Fuentes Navarro",       "Trabajo Social",4),
    ("A01840010", "patricia.rl2026@tec.mx",   "Patricia Ríos Leal",          "Medicina",      5),
    ("A01840011", "jorge.at2026@tec.mx",      "Jorge Arellano Tapia",        "IEM",           5),
    ("A01840012", "claudia.bv2026@tec.mx",    "Claudia Becerra Villanueva",  "Educación",     6),
    ("A01840013", "raul.de2026@tec.mx",       "Raúl Domínguez Estrada",      "ITC",           7),
    ("A01840014", "monica.jf2026@tec.mx",     "Mónica Juárez Figueroa",      "Comunicación",  8),
    ("A01840015", "arturo.vm2026@tec.mx",     "Arturo Vega Medina",          "Psicología",    9),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fake_google_id(email: str) -> str:
    """Genera un google_id hasheado consistente para datos de prueba."""
    return hmac_lib.new(
        settings.JWT_SECRET.encode(),
        f"g_id.fake_{email}".encode(),
        hashlib.sha256,
    ).hexdigest()


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def checkin_time(minutes_ago: int) -> datetime:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).replace(tzinfo=None)


def make_used_code(project_id: uuid.UUID, user_id: uuid.UUID) -> TempCode:
    code = TempCode(
        id=uuid.uuid4(),
        code=uuid.uuid4().hex[:8].upper(),
        project_id=project_id,
        created_by_user_id=user_id,
        expires_at=utc_now() + timedelta(hours=2),
        is_active=False,
        used_at=utc_now(),
        created_at=utc_now(),
    )
    return code


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    db = SessionLocal()
    print("=" * 60)
    print("SEED FERIA DEMO")
    print("=" * 60)

    # ── 1. BECARIO ──────────────────────────────────────────────
    becario_email = "becario.entrada@feria.mx"
    becario = db.query(User).filter(User.email == becario_email).first()
    if not becario:
        becario = User(
            id=uuid.uuid4(),
            email=becario_email,
            hashed_password=hash_password(PASSWORD),
            role="BECARIO",
            organization_name="Staff Entrada",
            is_active=True,
            created_at=utc_now(),
        )
        db.add(becario)
        db.commit()
        db.refresh(becario)
        print(f"[+] Becario: {becario_email}")
    else:
        print(f"[=] Becario ya existe: {becario_email}")

    # ── 2. SOCIOS + PROYECTOS ────────────────────────────────────
    projects_list: list[Project] = []

    for s_data in SOCIOS_DATA:
        socio = db.query(User).filter(User.email == s_data["email"]).first()
        if not socio:
            socio = User(
                id=uuid.uuid4(),
                email=s_data["email"],
                hashed_password=hash_password(PASSWORD),
                role="SOCIO",
                organization_name=s_data["org"],
                is_active=True,
                created_at=utc_now(),
            )
            db.add(socio)
            db.commit()
            db.refresh(socio)
            print(f"[+] Socio: {s_data['email']} — {s_data['org']}")
        else:
            print(f"[=] Socio ya existe: {s_data['email']}")

        for p_data in s_data["projects"]:
            proj = db.query(Project).filter(
                Project.name == p_data["name"],
                Project.owner_user_id == socio.id,
            ).first()
            if not proj:
                proj = Project(
                    id=uuid.uuid4(),
                    name=p_data["name"],
                    description=p_data["desc"],
                    capacity=p_data["capacity"],
                    owner_user_id=socio.id,
                    is_active=True,
                    periodo=p_data["periodo"],
                    carreras_permitidas=p_data["carreras"],
                    modalidad=p_data["modalidad"],
                    horas_acreditar=p_data["horas"],
                    clave_programa=p_data["clave"],
                    created_at=utc_now(),
                )
                db.add(proj)
                db.commit()
                db.refresh(proj)
                print(f"    [+] Proyecto: {p_data['name']} (cupo {p_data['capacity']})")
            else:
                print(f"    [=] Proyecto ya existe: {p_data['name']}")
            projects_list.append(proj)

    # ── 3. GRUPO A — Solo pre-registro ──────────────────────────
    print("\n--- Grupo A: Solo pre-registro ---")
    careers_map = {c.siglas: c for c in db.query(Career).all()}

    for matricula, email, nombre, telefono, siglas in PREREGISTRO_ONLY:
        if db.query(PreRegistration).filter(PreRegistration.matricula == matricula).first():
            print(f"[=] PreReg ya existe: {matricula}")
            continue
        career = careers_map.get(siglas)
        pre = PreRegistration(
            id=uuid.uuid4(),
            matricula=matricula,
            email=email,
            full_name=nombre,
            phone=telefono,
            career_id=career.id if career else None,
            created_at=utc_now(),
        )
        db.add(pre)
        print(f"[+] Pre-reg: {matricula} — {nombre} ({siglas})")

    db.commit()

    # ── 4. GRUPO B — Login hecho, sin check-in ──────────────────
    print("\n--- Grupo B: Login sin check-in ---")
    for matricula, email, nombre, siglas in LOGGED_NO_CHECKIN:
        if db.query(Student).filter(Student.matricula == matricula).first():
            print(f"[=] Student ya existe: {matricula}")
            continue
        st = Student(
            id=uuid.uuid4(),
            matricula=matricula,
            email=email,
            full_name=nombre,
            career=siglas,
            google_id=fake_google_id(email),
            created_at=utc_now(),
        )
        db.add(st)
        print(f"[+] Student (sin checkin): {matricula} — {nombre}")

    db.commit()

    # ── 5. GRUPO C — Check-in, sin proyecto ─────────────────────
    print("\n--- Grupo C: Check-in sin proyecto ---")
    for i, (matricula, email, nombre, siglas) in enumerate(CHECKIN_NO_PROJECT):
        st = db.query(Student).filter(Student.matricula == matricula).first()
        if not st:
            st = Student(
                id=uuid.uuid4(),
                matricula=matricula,
                email=email,
                full_name=nombre,
                career=siglas,
                google_id=fake_google_id(email),
                created_at=utc_now(),
            )
            db.add(st)
            db.flush()

        if not db.query(Checkin).filter(Checkin.student_id == st.id).first():
            ci = Checkin(
                id=uuid.uuid4(),
                student_id=st.id,
                becario_user_id=becario.id,
                method="QR",
                checked_in_at=checkin_time(60 - i * 5),
            )
            db.add(ci)
            print(f"[+] Checkin: {matricula} — {nombre}")
        else:
            print(f"[=] Checkin ya existe: {matricula}")

    db.commit()

    # ── 6. GRUPO D — Check-in + registro ────────────────────────
    print("\n--- Grupo D: Check-in + registro en proyecto ---")
    for i, (matricula, email, nombre, siglas, proj_idx) in enumerate(FULL_REGISTERED):
        project = projects_list[proj_idx]

        st = db.query(Student).filter(Student.matricula == matricula).first()
        if not st:
            st = Student(
                id=uuid.uuid4(),
                matricula=matricula,
                email=email,
                full_name=nombre,
                career=siglas,
                google_id=fake_google_id(email),
                created_at=utc_now(),
            )
            db.add(st)
            db.flush()

        # Checkin
        if not db.query(Checkin).filter(Checkin.student_id == st.id).first():
            ci = Checkin(
                id=uuid.uuid4(),
                student_id=st.id,
                becario_user_id=becario.id,
                method="QR",
                checked_in_at=checkin_time(90 - i * 3),
            )
            db.add(ci)
            db.flush()

        # Registro
        if not db.query(Registration).filter(Registration.student_id == st.id).first():
            # Obtener el socio dueño del proyecto para el código
            owner = db.query(User).filter(User.id == project.owner_user_id).first()
            code = make_used_code(project.id, owner.id)
            db.add(code)
            db.flush()

            reg = Registration(
                id=uuid.uuid4(),
                student_id=st.id,
                project_id=project.id,
                temp_code_id=code.id,
                status="CONFIRMED",
                created_at=checkin_time(85 - i * 3),
            )
            db.add(reg)
            print(f"[+] Registrado: {matricula} - {nombre} -> {project.name[:40]}")
        else:
            print(f"[=] Registro ya existe: {matricula}")

    db.commit()

    # ── Resumen ─────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"  Socios:          {db.query(User).filter(User.role == 'SOCIO').count()}")
    print(f"  Becarios:        {db.query(User).filter(User.role == 'BECARIO').count()}")
    print(f"  Proyectos:       {db.query(Project).count()}")
    print(f"  Pre-registros:   {db.query(PreRegistration).count()}")
    print(f"  Students en BD:  {db.query(Student).count()}")
    print(f"  Check-ins:       {db.query(Checkin).count()}")
    print(f"  Registraciones:  {db.query(Registration).count()}")
    print("=" * 60)
    print("\nCredenciales de socios formadores:")
    for s in SOCIOS_DATA:
        print(f"  {s['email']:<35} | {s['org']}")
    print(f"\n  Contraseña (todos): {PASSWORD}")
    print(f"\n  Becario: becario.entrada@feria.mx | {PASSWORD}")
    db.close()


if __name__ == "__main__":
    main()
