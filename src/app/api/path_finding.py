# src/app/api/path_finding.py
from fastapi import APIRouter, HTTPException, Body
from typing import Optional, List, Dict, Any
import networkx as nx
import time
from src.services import geocoding_service, pathfinding_service
from src.app.schemas.route_input_format import RouteRequest, Point

_G_base: Optional[nx.MultiDiGraph] = None
_flood_model = None


router = APIRouter()


def init_routes(G_base: nx.MultiDiGraph, flood_model):
    """Khởi tạo router với graph và model đã load từ main.py"""
    global _G_base, _flood_model
    _G_base = G_base
    _flood_model = flood_model
    return router


@router.post("/find-route", summary="Tìm đường thông minh với model dự đoán ngập")
def find_route_endpoint(request: RouteRequest):
    raise HTTPException(
        status_code=501,
        detail="Smart route với flood model chưa được implement. Vui lòng dùng /find-standard-route"
    )


@router.post("/find-standard-route", summary="Tìm đường tiêu chuẩn")
def find_standard_route_endpoint(
    start_address: Optional[str] = Body(...),
    end_address: Optional[str] = Body(...),
    blocking_geometries: List[Dict[str, Any]] = Body(default=[]),
    flood_areas: List[Dict[str, Any]] = Body(default=[]),
    ban_areas: List[Dict[str, Any]] = Body(default=[])
):
    """Tìm đường tiêu chuẩn từ địa chỉ A đến địa chỉ B."""
    try:
        if _G_base is None:
            raise HTTPException(status_code=500, detail="Graph chưa được load")

        if not start_address or not end_address:
            raise HTTPException(status_code=400, detail="Thiếu địa chỉ đầu vào")

        start_coords = geocoding_service.get_coords_from_address(start_address)
        time.sleep(1.5)
        end_coords = geocoding_service.get_coords_from_address(end_address)

        if not start_coords:
            raise HTTPException(
                status_code=400,
                detail="Điểm bắt đầu có thể nằm trong vùng cấm hoặc ngoài bản đồ"
            )
        
        if not end_coords:
            raise HTTPException(
                status_code=400,
                detail="Điểm đến có thể nằm trong vùng cấm hoặc ngoài bản đồ"
            )

        # Log blocking geometries để debug
        print(f"Received {len(blocking_geometries or [])} blocking geometries")
        if blocking_geometries:
            for i, geom in enumerate(blocking_geometries):
                print(f"Blocking geometry {i}: {type(geom)} - {list(geom.keys()) if isinstance(geom, dict) else 'Not a dict'}")

        route_request = RouteRequest(
            start_point=Point(
                lat=start_coords["latitude"],
                lon=start_coords["longitude"]
            ),
            end_point=Point(
                lat=end_coords["latitude"],
                lon=end_coords["longitude"]
            ),
            blocking_geometries=blocking_geometries or [],
            flood_areas=flood_areas or [],
            ban_areas=ban_areas or []
        )

        result = pathfinding_service.find_standard_route(route_request, _G_base)

        if "error" in result:
            return {"error": result["error"], "message": "Không tìm thấy đường đi"}

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi không mong muốn: {str(e)}")
