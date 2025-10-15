from fastapi import APIRouter
from src.services.pathfinding_service import find_smart_route, find_standard_route
from fastapi import APIRouter, HTTPException, Query
router = APIRouter()
import requests

from pydantic import BaseModel
class AddressRequest(BaseModel):
    address: str

#trans from geo to loc
@router.post(
    "/loc-to-coords",
    summary="Chuyển đổi từ địa chỉ sang tọa độ"
)
def loc_to_coords(request: AddressRequest):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": request.address,
        "format": "json",
        "limit": 1
    }
    headers = {"User-Agent": "my_app"}
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Lỗi khi gọi Nominatim API")

    data = response.json()
    if not data:
        raise HTTPException(status_code=404, detail="Không tìm thấy tọa độ cho địa chỉ này")

    return {
        "address": request.address,
        "latitude": data[0]["lat"],
        "longitude": data[0]["lon"]
    }


#coords-to-loc
@router.post(
    "/coords-to-loc",
    summary="Chuyển từ tọa độ sang địa chỉ"
)
def coords_to_loc(
        latitude: float = Query(
            ...,
            description="Nhập kinh độ",
            example=105.67899
        ),
        longitude: float = Query(
            ...,
            description="Nhập vĩ độ",
            example=21.23456
        )
):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json"
    }
    headers = {"User-Agent": "my_app"}

    response = requests.get(url, params=params, headers=headers)
    data = response.json()

    if "error" in data:
        raise HTTPException(status_code=404, detail="Không tìm thấy địa chỉ")

    return {
        "latitude": latitude,
        "longitude": longitude,
        "address": data["display_name"]
    }
