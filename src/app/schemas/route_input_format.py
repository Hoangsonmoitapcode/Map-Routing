from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Point(BaseModel):
    """
    Định nghĩa một điểm tọa độ địa lý (lon, lat).
    """

    lon: float = Field(
        ..., description="Kinh độ (Longitude)", example=105.85
    )
    lat: float = Field(
        ..., description="Vĩ độ (Latitude)", example=21.02
    )

class RouteRequest(BaseModel):
    """
    Định nghĩa cấu trúc cho một yêu cầu tìm đường hoàn chỉnh.
    Đây là "tờ khai" mà frontend (Streamlit) phải điền vào khi gửi yêu cầu.
    """
    start_point: Point
    end_point: Point
    blocking_geometries: List[Dict[str, Any]] = Field(
        default=[],
        description="Danh sách các đối tượng GeoJSON (Polygon, LineString, Point) đại diện cho các vùng cấm/ngập."
    )

