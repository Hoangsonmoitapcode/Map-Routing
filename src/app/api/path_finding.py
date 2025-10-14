#Chứa các endpoint chính để tìm đường, như /get-route và /get-smart-route.

from fastapi import APIRouter
from src.services.pathfinding_service import find_smart_route, find_standard_route
from fastapi import APIRouter, HTTPException

router = APIRouter()


def init_routes(G_base, flood_model):
    """Initialize api with loaded data"""

    @router.get("/")
    def read_root():
        return {"message": "AI Pathfinding API is ready!"}

    @router.get("/find_smart_route")
    def get_smart_route(start_node_id: int, end_node_id: int):
        if flood_model is None:  # ← Added check
            raise HTTPException(
                status_code=503,
                detail="Smart routing unavailable: flood model not loaded. Use /find_route instead."
            )
        return find_smart_route(G_base, flood_model, start_node_id, end_node_id)

    @router.get("/find_route")
    def get_route(start_node_id: int, end_node_id: int):
        # Endpoint này không cần 'flood_model'
        # Nó gọi đến hàm service mới mà chúng ta vừa tạo
        return find_standard_route(G_base, start_node_id, end_node_id)
    return router

