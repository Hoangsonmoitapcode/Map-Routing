import requests
from fastapi import HTTPException


def get_coords_from_address(address: str) -> dict:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 1, "countrycodes": "vn"}
    headers = {"User-Agent": "my_app"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            raise HTTPException(status_code=404, detail=f"không tìm thấy tọa độ cho địa chỉ: {address}")

        lat_str = data[0].get("lat")
        lon_str = data[0].get("lon")

        if not lat_str or not lon_str:
            raise HTTPException(status_code=400, detail=f"api không trả về tọa độ hợp lệ cho: {address}")

        return {
            "address": address,
            "latitude": float(lat_str),
            "longitude": float(lon_str)
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"lỗi khi gọi nominatim api: {e}")


def get_address_from_coords(latitude: float, longitude: float) -> dict:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": latitude, "lon": longitude, "format": "json"}
    headers = {"User-Agent": "my_app"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise HTTPException(status_code=404, detail="không tìm thấy địa chỉ cho tọa độ này")

        return {
            "latitude": latitude,
            "longitude": longitude,
            "address": data.get("display_name", "không có tên hiển thị")
        }
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"lỗi khi gọi nominatim api: {e}")


def get_coords_tuple(address: str) -> tuple:
    result = get_coords_from_address(address)
    return (float(result["latitude"]), float(result["longitude"]))
