import os

from fastapi import FastAPI

from app.routers import auth


root_path = os.getenv("AUTH_ROOT_PATH", "").strip() or None

app = FastAPI(title="Yokedo Auth Service", root_path=root_path)

# Register auth router
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Auth service running 🚀"}
