from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# BƯỚC 1: Import service chuyên gia
from src.services import geocoding_service

router = APIRouter()

# --- Schemas (Giữ nguyên để đảm bảo tương thích) ---
class AddressRequest(BaseModel):
    address: str

# --- Endpoints đã được refactor ---

@router.post(
    "/loc-to-coords",
    summary="Chuyển đổi từ địa chỉ sang tọa độ"
)
def loc_to_coords(request: AddressRequest):
    """
    Endpoint này nhận một địa chỉ, sau đó gọi geocoding_service để xử lý.
    """
    # BƯỚC 2: Giao toàn bộ công việc cho service
    # Toàn bộ logic gọi requests.get đã được chuyển vào service
    return geocoding_service.get_coords_from_address(request.address)


@router.post(
    "/coords-to-loc",
    summary="Chuyển từ tọa độ sang địa chỉ"
)
def coords_to_loc(
        latitude: float = Query(
            ...,
            description="Nhập vĩ độ",
            example=21.23456
        ),
        longitude: float = Query(
            ...,
            description="Nhập kinh độ",
            example=105.67899
        )
):
    """
    Endpoint này nhận tọa độ, sau đó gọi geocoding_service để xử lý.
    """
    #BƯỚC 3: Giao toàn bộ công việc cho service
    return geocoding_service.get_address_from_coords(latitude, longitude)