import requests
from fastapi import HTTPException

#ham xu ly address & lat& lon

def get_coords_from_address(address: str) -> dict:
    """
    Gọi API Nominatim để chuyển đổi địa chỉ thành tọa độ.
    """
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1, "countrycodes": "vn"}
    headers = {"User-Agent": "my_app"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if not data:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy tọa độ cho địa chỉ: {address}")

        return {
            "address": address,
            "latitude": data[0]["lat"],
            "longitude": data[0]["lon"]
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi gọi Nominatim API: {e}")


def get_address_from_coords(latitude: float, longitude: float) -> dict:
    """
    Gọi API Nominatim để chuyển đổi tọa độ thành địa chỉ (Reverse Geocoding).
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": latitude, "lon": longitude, "format": "json"}
    headers = {"User-Agent": "my_app"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise HTTPException(status_code=404, detail="Không tìm thấy địa chỉ cho tọa độ này")

        return {
            "latitude": latitude,
            "longitude": longitude,
            "address": data.get("display_name", "Không có tên hiển thị")
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi gọi Nominatim API: {e}")

def get_coords_tuple(address: str) -> tuple:
    """
    Trả về (lat, lon) dạng tuple để dễ dùng trong pathfinding.
    """
    result = get_coords_from_address(address)
    return (float(result["latitude"]), float(result["longitude"]))