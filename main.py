from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.database.load_database import load_graph_from_db
from src.app.models.models_loader import load_flood_model

from src.app.api.geocoding import router as geocoding_router
from src.app.api.path_finding import init_routes as init_pathfinding_routes

# global variables
G_base = None
flood_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """load data at startup"""
    global G_base, flood_model

    print("starting up...")
    print("loading map data from postgis...")
    G_base = load_graph_from_db()

    print("loading flood prediction model...")
    flood_model = load_flood_model()

    if flood_model:
        print("flood model loaded successfully.")
    else:
        print("running without flood prediction model. smart routing disabled.")

    # ✅ initialize pathfinding router
    pathfinding_router = init_pathfinding_routes(G_base, flood_model)

    # ✅ đăng ký pathfinding router
    app.include_router(
        pathfinding_router,
        prefix="/api/v1/routing",
        tags=["routing"]
    )

    # ✅ đăng ký geocoding router
    app.include_router(
        geocoding_router,
        prefix="/api/v1/geocoding",
        tags=["geocoding"]
    )

    print("api ready!")

    yield
    print("shutting down...")


app = FastAPI(
    lifespan=lifespan,
    title="smart routing api",
    description="api for smart routing and geocoding services",
    version="1.0.0"
)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
