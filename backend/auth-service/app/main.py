from fastapi import FastAPI
from app.routers import users

app = FastAPI(title="Yokedo Auth Service")

# Incluimos los endpoints del módulo users
app.include_router(users.router, prefix="/api/users", tags=["users"])

@app.get("/")
def read_root():
    return {"message": "Auth service running 🚀"}
