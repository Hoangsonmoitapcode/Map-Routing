from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.services.database import load_graph_from_db
from src.services.models_loader import load_flood_model
from src.routes.path_finding import init_routes

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

    # Initialize routes with loaded data
    router = init_routes(G_base, flood_model)
    app.include_router(router)

    print("API Ready!")

    yield
    # Cleanup nếu cần
    print("Shutting down...")


app = FastAPI(lifespan=lifespan)


# Health check cho Docker
@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)