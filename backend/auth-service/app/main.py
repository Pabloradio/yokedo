from fastapi import FastAPI
from app.routers import auth   # <-- Import nuevo

app = FastAPI(title="Yokedo Auth Service")

# Registrar router de autenticación
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

@app.get("/")
def root():
    return {"message": "Auth service running 🚀"}
