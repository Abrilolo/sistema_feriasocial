#app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.security import verify_password, create_access_token, get_current_user
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Swagger manda username = email, password = password
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login-cookie")
@limiter.limit("5/minute")
def login_cookie(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login que configura cookie HttpOnly segura"""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    access_token = create_access_token({"sub": str(user.id), "role": user.role})

    from fastapi.responses import JSONResponse
    response = JSONResponse(
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "organization_name": getattr(user, "organization_name", None),
            }
        }
    )

    # Configurar cookie segura (HttpOnly, Secure, SameSite=Lax)
    # Nota: Secure=True requiere HTTPS. En desarrollo local puede causar problemas.
    import os
    is_production = os.getenv("ENVIRONMENT", "development") == "production"

    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,  # No accesible desde JavaScript (protección XSS)
        secure=is_production,  # Solo HTTPS en producción
        samesite="lax",  # Protección CSRF
        max_age=60 * 60 * 24 * 7,  # 7 días
        path="/",
    )

    return response


@router.post("/logout")
def logout():
    """Logout que limpia la cookie"""
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie(key="access_token", path="/")
    return response


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "organization_name": getattr(user, "organization_name", None),
        "is_active": user.is_active,
    }