from fastapi import FastAPI
from src.database import load_graph_from_db
from src.models import load_flood_model
from src.routes.path_finding import router, init_routes

app = FastAPI()

# Load data at startup
print("Starting up...")
G_base = load_graph_from_db()
flood_model = load_flood_model()

# Initialize routes with loaded data
init_routes(G_base, flood_model)
app.include_router(router)

print("API Ready!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)