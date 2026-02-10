from fastapi import FastAPI
from app.routers.debug_availability import router as debug_availability_router
from app.routers.availabilities import router as availabilities_router
from app.routers.weekly_templates import router as weekly_templates_router
from app.routers.day_overrides import router as day_overrides_router
from app.core.settings import settings


app = FastAPI(title="Yokedo Availability Service")
app.include_router(availabilities_router)
app.include_router(weekly_templates_router)
app.include_router(day_overrides_router)
# Register availability debug router
# Register availability debug router only in local environment
if settings.environment == "local":
    app.include_router(debug_availability_router)


@app.get("/")
def root():
    return {"message": "Availability service running 🚀"}

