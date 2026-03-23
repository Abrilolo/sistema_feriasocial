from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.security import decode_access_token

router = APIRouter(tags=["views"])
templates = Jinja2Templates(directory="app/templates")


def get_current_user_from_cookie(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None

    if token.startswith("Bearer "):
        token = token.replace("Bearer ", "", 1)

    try:
        payload = decode_access_token(token)
        return payload
    except Exception:
        return None


def require_roles(request: Request, allowed_roles: list[str]):
    user = get_current_user_from_cookie(request)

    if not user:
        return None

    user_role = user.get("role")
    if user_role not in allowed_roles:
        return None

    return user


@router.get("/inscripcion-proyecto", response_class=HTMLResponse)
def registro_page(request: Request):
    return templates.TemplateResponse("registro_publico.html", {"request": request})


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
def socio_page(request: Request):
    user = require_roles(request, ["SOCIO"])
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
def becario_page(request: Request):
    user = require_roles(request, ["BECARIO"])
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
def admin_page(request: Request):
    user = require_roles(request, ["ADMIN"])
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
def student_qr_page(request: Request):
    return templates.TemplateResponse("estudiante_qr.html", {"request": request})
