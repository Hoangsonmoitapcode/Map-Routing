from fastapi import APIRouter
from ..services.pathfinding_service import find_smart_route

router = APIRouter()


def init_routes(G_base, flood_model):
    """Initialize routes with loaded data"""

    @router.get("/")
    def read_root():
        return {"message": "AI Pathfinding API is ready!"}

    @router.get("/find_smart_route")
    def get_smart_route(start_node_id: int, end_node_id: int):
        return find_smart_route(G_base, flood_model, start_node_id, end_node_id)

    return router