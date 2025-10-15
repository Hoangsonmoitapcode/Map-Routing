from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.database.load_database import load_graph_from_db
from src.app.models.models_loader import load_flood_model


from src.app.api.path_finding import init_routes  # Hoặc src.api.routes.path_finding

# Global variables
G_base = None
flood_model = None
router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load data at startup"""
    global G_base, flood_model, router

    print("Starting up...")
    print("Loading map data from PostGIS...")
    G_base = load_graph_from_db()

    print("Loading flood prediction model...")
    flood_model = load_flood_model()

    if flood_model:
        print("Flood model loaded successfully.")
    else:
        print("Running without flood prediction model. Smart routing disabled.")

    # ✅ Initialize router với G_base và flood_model
    router = init_routes(G_base, flood_model)

    # ✅ THÊM: Đăng ký router với prefix
    app.include_router(
        router,
        prefix="/api/v1/routing",  # Thêm prefix để URL đẹp hơn
        tags=["routing"]
    )

    print("API Ready!")

    yield
    print("Shutting down...")


app = FastAPI(lifespan=lifespan)


# Health check cho Docker
@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)