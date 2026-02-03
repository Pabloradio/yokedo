from fastapi import FastAPI
from app.routers.debug_availability import router as debug_availability_router



app = FastAPI(title="Yokedo Availability Service")

# Register availability debug router
app.include_router(debug_availability_router)

@app.get("/")
def root():
    return {"message": "Availability service running 🚀"}

