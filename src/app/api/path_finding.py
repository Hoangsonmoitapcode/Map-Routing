# src/app/api/path_finding.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import osmnx as ox
import networkx as nx

from src.services.geocoding_service import get_coords_tuple
from src.services.weight_service import apply_dynamic_weights
from src.services.pathfinding_service import find_smart_route, find_standard_route

_G_base: Optional[nx.MultiDiGraph] = None
_flood_model = None


def init_routes(G_base: nx.MultiDiGraph, flood_model):  # ✅ Thêm type hint
    """
    Khởi tạo router với graph và model đã load từ main.py
    """
    global _G_base, _flood_model
    _G_base = G_base
    _flood_model = flood_model

    return router


router = APIRouter()


class RouteRequest(BaseModel):
    start_address: str
    end_address: str
    blocking_geometries: List[Dict[str, Any]] = []

"""
    Workflow:
    1. Geocode địa chỉ
    2. Gọi weight_service → nhận G_modified
    3. Gọi pathfinding_service → tìm đường
    4. Convert path → GeoJSON
"""

@router.post("/find-route", summary="Tìm đường thông minh với blocking conditions")
def find_route_endpoint(request: RouteRequest):

    try:
        # 1. Geocode
        start_lat, start_lon = get_coords_tuple(request.start_address)
        end_lat, end_lon = get_coords_tuple(request.end_address)

        # 2. Sử dụng G_base đã được load từ main.py
        if _G_base is None:
            raise HTTPException(status_code=500, detail="Graph chưa được load")

        # 3. Gọi weight_service
        G_modified, metadata = apply_dynamic_weights(
            _G_base,
            blocking_geometries=request.blocking_geometries,
            flood_model=_flood_model
        )

        # 4. Tìm nearest nodes
        # ✅ SỬA: Dùng ox.nearest_nodes thay vì ox.distance.nearest_nodes
        start_node = ox.nearest_nodes(G_modified, start_lon, start_lat)
        end_node = ox.nearest_nodes(G_modified, end_lon, end_lat)

        # 5. Gọi pathfinding_service
        result = find_smart_route(G_modified, start_node, end_node)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        # 6. Convert path → GeoJSON
        path = result["path"]
        route_geojson = _path_to_geojson(G_modified, path)
        distance = _calculate_distance(G_modified, path)
        duration = _calculate_duration(distance)

        return {
            "route": route_geojson,
            "distance": distance,
            "duration": duration,
            "nodes": path,
            "metadata": metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/find-standard-route", summary="Tìm đường tiêu chuẩn (không blocking)")
def find_standard_route_endpoint(request: RouteRequest):
    """Tìm đường tiêu chuẩn không có điều kiện gì"""
    try:
        # Geocode
        start_lat, start_lon = get_coords_tuple(request.start_address)
        end_lat, end_lon = get_coords_tuple(request.end_address)

        # Sử dụng G_base đã load
        if _G_base is None:
            raise HTTPException(status_code=500, detail="Graph chưa được load")

        # Tìm nearest nodes
        start_node = ox.nearest_nodes(_G_base, start_lon, start_lat)
        end_node = ox.nearest_nodes(_G_base, end_lon, end_lat)

        # Gọi pathfinding_service
        result = find_standard_route(_G_base, start_node, end_node)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        # Convert
        path = result["path"]
        route_geojson = _path_to_geojson(_G_base, path)
        distance = _calculate_distance(_G_base, path)
        duration = _calculate_duration(distance)

        return {
            "route": route_geojson,
            "distance": distance,
            "duration": duration,
            "nodes": path
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== HELPER FUNCTIONS =====

def _path_to_geojson(G, path):
    """Convert path → GeoJSON"""
    coords = []
    for node_id in path:
        node_data = G.nodes[node_id]
        if 'lon' in node_data and 'lat' in node_data:
            coords.append([node_data['lon'], node_data['lat']])
        elif 'x' in node_data and 'y' in node_data:
            coords.append([node_data['x'], node_data['y']])

    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords
        },
        "properties": {"node_count": len(path)}
    }


def _calculate_distance(G, path):
    """Tính khoảng cách (meters)"""
    total = 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if G.has_edge(u, v):
            edge_data = list(G[u][v].values())[0]
            total += edge_data.get('length', 0)
    return total


def _calculate_duration(distance_m):
    """Tính thời gian (phút)"""
    distance_km = distance_m / 1000
    return (distance_km / 25) * 60  # 25 km/h