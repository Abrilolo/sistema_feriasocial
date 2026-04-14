from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.student import Student

router = APIRouter(tags=["views"])
templates = Jinja2Templates(directory="app/templates")


def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    """
    Obtiene el usuario actual desde la cookie, validando contra la base de datos.
    Esto previene que usuarios desactivados o eliminados sigan teniendo acceso.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None

    if token.startswith("Bearer "):
        token = token.replace("Bearer ", "", 1)

    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None

        # Validar que el usuario existe y está activo en la base de datos
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            return None

        # Retornar información actualizada del usuario desde la BD
        return {
            "sub": str(user.id),
            "role": user.role,
            "email": user.email,
            "organization_name": getattr(user, "organization_name", None),
        }
    except Exception:
        return None


def require_roles(request: Request, allowed_roles: list[str], db: Session = Depends(get_db)):
    """
    Verifica que el usuario tenga uno de los roles permitidos.
    Requiere conexión a base de datos para validar el estado actual del usuario.
    """
    user = get_current_user_from_cookie(request, db)

    if not user:
        return None

    user_role = user.get("role")
    if user_role not in allowed_roles:
        return None

    return user


def get_current_student_from_cookie(request: Request, db: Session = Depends(get_db)):
    """
    Obtiene el estudiante actual desde la cookie de estudiante (student_token).
    Valida el token JWT y verifica que el estudiante exista en la BD.
    """
    token = request.cookies.get("student_token")
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        student_id = payload.get("sub")
        if not student_id:
            return None

        # Validar que el estudiante existe en la base de datos
        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            return None

        return {
            "id": str(student.id),
            "email": student.email,
            "matricula": student.matricula,
            "full_name": student.full_name,
            "career": student.career,
        }
    except Exception:
        return None


@router.get("/inscripcion-proyecto", response_class=HTMLResponse)
def registro_page(request: Request, db: Session = Depends(get_db)):
    student = get_current_student_from_cookie(request, db)
    if not student:
        return RedirectResponse(url="/acceso-estudiante", status_code=302)
    return templates.TemplateResponse("registro_publico.html", {"request": request, "student": student})


@router.get("/catalogo-proyectos", response_class=HTMLResponse)
def catalog_page(request: Request):
    return templates.TemplateResponse("catalogo_proyectos.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/socio", response_class=HTMLResponse)
def socio_page(request: Request, db: Session = Depends(get_db)):
    user = require_roles(request, ["SOCIO"], db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "socio_dashboard.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.get("/becario", response_class=HTMLResponse)
def becario_page(request: Request, db: Session = Depends(get_db)):
    user = require_roles(request, ["BECARIO"], db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "becario_checkin.html",
        {
            "request": request,
            "user": user,
        },
    )


@router.get("/admin-panel", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(get_db)):
    user = require_roles(request, ["ADMIN"], db)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "user": user,
        },
    )

@router.get("/acceso-estudiante", response_class=HTMLResponse)
def student_qr_page(request: Request, db: Session = Depends(get_db)):
    """
    Página de acceso para estudiantes. Si está autenticado con Google,
    muestra sus datos y opción para generar QR.
    """
    from fastapi.responses import Response

    student = get_current_student_from_cookie(request, db)

    response = templates.TemplateResponse(
        "estudiante_qr.html",
        {
            "request": request,
            "student": student,
            "is_authenticated": student is not None,
        }
    )

    # Headers anti-cache para dispositivos compartidos
    # Evitan que el navegador muestre datos de sesión anterior
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response
