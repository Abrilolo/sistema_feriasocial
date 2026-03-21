#api/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.auth import router as auth_router
from app.routers.admin import router as admin_router
from app.routers.socio import router as socio_router
from app.routers.becario import router as becario_router
from app.routers.checkins import router as checkins_router
from app.routers.public import router as public_router
from app.routers import views

app = FastAPI(title="Feria Servicio Social Tec")


app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}

app.include_router(views.router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(socio_router)
app.include_router(becario_router)
app.include_router(checkins_router)
app.include_router(public_router)
