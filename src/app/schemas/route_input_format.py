from pydantic import BaseModel, Field
from typing import List, Dict, Any


class Point(BaseModel):
    """
    định nghĩa một điểm tọa độ địa lý (lat, lon)
    """
    lat: float = Field(
        ...,
        description="vĩ độ (latitude)",
        example=21.02,
        ge=-90,
        le=90
    )
    lon: float = Field(
        ...,
        description="kinh độ (longitude)",
        example=105.85,
        ge=-180,
        le=180
    )


class RouteRequest(BaseModel):
    """
    định nghĩa cấu trúc dữ liệu cho một yêu cầu tìm đường hoàn chỉnh
    """
    start_point: Point
    end_point: Point
    blocking_geometries: List[Dict[str, Any]] = Field(
        default=[],
        description="danh sách các đối tượng geojson (polygon, linestring, point) đại diện cho vùng cấm hoặc khu ngập"
    )


    