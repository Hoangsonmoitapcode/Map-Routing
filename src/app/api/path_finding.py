# src/app/api/path_finding.py
from fastapi import APIRouter, HTTPException
from typing import Optional
import networkx as nx

from src.services import geocoding_service, pathfinding_service
from src.app.schemas.route_input_format import RouteRequest, Point

_G_base: Optional[nx.MultiDiGraph] = None
_flood_model = None


def init_routes(G_base: nx.MultiDiGraph, flood_model):
    """
    Khởi tạo router với graph và model đã load từ main.py
    """
    global _G_base, _flood_model
    _G_base = G_base
    _flood_model = flood_model
    return router


router = APIRouter()


@router.post("/find-route", summary="Tìm đường thông minh với model dự đoán ngập")
def find_route_endpoint(request: RouteRequest):
    """
    ⚠️ CHƯA IMPLEMENT - Dành cho tương lai
    """
    raise HTTPException(
        status_code=501,
        detail="Smart route với flood model chưa được implement. Vui lòng dùng /find-standard-route"
    )


@router.post("/find-standard-route", summary="Tìm đường tiêu chuẩn")
def find_standard_route_endpoint(
        start_address: str,
        end_address: str,
        blocking_geometries: list = None
):
    """
    Tìm đường tiêu chuẩn từ địa chỉ A đến địa chỉ B.

    Args:
        start_address: Địa chỉ bắt đầu
        end_address: Địa chỉ kết thúc
        blocking_geometries: Danh sách vùng cấm (GeoJSON format)
    """
    try:
        # 1. Kiểm tra graph đã load chưa
        if _G_base is None:
            raise HTTPException(status_code=500, detail="Graph chưa được load")

        # 2. Geocode địa chỉ → tọa độ
        start_coords = geocoding_service.get_coords_from_address(start_address)
        end_coords = geocoding_service.get_coords_from_address(end_address)

        # 3. Tạo RouteRequest object
        route_request = RouteRequest(
            start_point=Point(
                lat=start_coords["latitude"],
                lon=start_coords["longitude"]
            ),
            end_point=Point(
                lat=end_coords["latitude"],
                lon=end_coords["longitude"]
            ),
            blocking_geometries=blocking_geometries or []
        )

        # 4. Gọi pathfinding service
        result = pathfinding_service.find_standard_route(route_request, _G_base)

        # 5. Xử lý lỗi
        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi không mong muốn: {str(e)}")