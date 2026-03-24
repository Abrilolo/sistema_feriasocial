# Script to append endpoints to views.py and public.py

views_path = r'c:\Users\atave\Documents\GitHub\sistema_feriasocial\app\routers\views.py'
public_path = r'c:\Users\atave\Documents\GitHub\sistema_feriasocial\app\routers\public.py'

views_addition = """

@router.get("/estudiante", response_class=HTMLResponse)
def student_qr_page(request: Request):
    return templates.TemplateResponse("estudiante_qr.html", {"request": request})
"""

public_addition = """

@router.post("/generate-qr")
def generate_qr_token(
    payload: GenerateQRRequest,
    db: Session = Depends(get_db),
):
    from app.core.security import create_access_token
    from datetime import timedelta

    matricula = payload.matricula.strip().upper()
    email = payload.email.strip().lower()

    # 1) Buscar estudiante
    student = db.query(Student).filter(Student.matricula == matricula).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estudiante no encontrado.",
        )

    # 2) Validar correo
    if student.email.lower() != email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo no coincide con la matrícula registrada.",
        )

    # 3) Generar token de invitación (QR)
    token_data = {
        "sub": str(student.id),
        "type": "invite",
        "matricula": student.matricula,
        "name": student.full_name
    }
    token = create_access_token(token_data, expires_delta=timedelta(hours=2))

    return {
        "ok": True,
        "qr_token": token,
        "student": {
            "matricula": student.matricula,
            "full_name": student.full_name
        }
    }
"""

with open(views_path, 'a', encoding='utf-8') as f:
    f.write(views_addition)

with open(public_path, 'a', encoding='utf-8') as f:
    f.write(public_addition)

print("Successfully appended endpoints to views.py and public.py")
