import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import requests

# --- Cấu hình ---
# URLs của các Backend API (FastAPI) - bạn sẽ cần các endpoint này
PREVIEW_SEGMENT_URL = "http://127.0.0.1:8000/api/v1/analysis/preview-segment"
GET_ROUTE_URL = "http://127.0.0.1:8000/api/v1/routing/get-route"

# --- Khởi tạo Session State ---
# Dùng để lưu trữ danh sách các vùng/đường cấm giữa các lần re-run
if 'blocking_geometries' not in st.session_state:
    st.session_state['blocking_geometries'] = []

# --- Giao diện Streamlit ---
st.set_page_config(layout="wide")
st.title("🗺️ Công cụ tìm đường và quản lý giao thông")

# --- Chia layout chính ---
col1, col2 = st.columns([3, 2]) # 3 phần cho bản đồ, 2 phần cho bảng điều khiển

with col1:
    st.header("Bản đồ tương tác")
    # 1. Tạo một đối tượng bản đồ trung tâm ở Hà Nội
    m = folium.Map(location=[21.028511, 105.804817], zoom_start=13)

    # 2. Thêm plugin Draw vào bản đồ
    Draw(export=True).add_to(m)

    # Vẽ lại các vùng/đường cấm đã được lưu trong session state
    if st.session_state['blocking_geometries']:
        for geom in st.session_state['blocking_geometries']:
            folium.GeoJson(geom, style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0.3}).add_to(m)

    # 3. Hiển thị bản đồ trong Streamlit
    output = st_folium(m, width=800, height=600)

with col2:
    st.header("Bảng điều khiển")
    tab1, tab2 = st.tabs(["Vẽ vùng cấm/ngập", "Chọn đường theo địa chỉ"])

    # Tab 1: Vẽ vùng cấm thủ công
    with tab1:
        st.info("Sử dụng các công cụ bên trái bản đồ để vẽ một đa giác.")
        if output.get("all_drawings") and len(output["all_drawings"]) > 0:
            # Lấy hình mới nhất được vẽ
            last_drawn = output["all_drawings"][-1]
            st.write("Hình vừa vẽ:")
            st.json(last_drawn['geometry'])
            if st.button("Thêm vùng cấm này"):
                st.session_state['blocking_geometries'].append(last_drawn['geometry'])
                st.success("Đã thêm vùng cấm. Bản đồ sẽ được cập nhật.")
                st.rerun()

    # Tab 2: Chọn đường theo địa chỉ
    with tab2:
        st.subheader("🚧 Cấm/ngập một đoạn đường")
        road_name_ban = st.text_input("Tên đường", key="ban_road_name")
        from_address = st.text_input("Từ địa chỉ", key="ban_from_addr")
        to_address = st.text_input("Đến địa chỉ", key="ban_to_addr")

        if st.button("Xem trước & Lấy GeoJSON"):
            if all([road_name_ban, from_address, to_address]):
                payload = {
                    "street_name": road_name_ban,
                    "start_address": f"{from_address}, {road_name_ban}",
                    "end_address": f"{to_address}, {road_name_ban}"
                }
                try:
                    st.info("Đang gọi API để lấy geometry đoạn đường...")
                    # response = requests.post(PREVIEW_SEGMENT_URL, json=payload)
                    # response.raise_for_status()
                    # segment_geojson = response.json()

                    # --- PHẦN GIẢ LẬP KHI CHƯA CÓ BACKEND ---
                    st.warning("Backend chưa chạy. Đây là dữ liệu giả lập.")
                    segment_geojson = {
                        "type": "LineString",
                        "coordinates": [[105.80, 21.01], [105.81, 21.02]]
                    }
                    # --- KẾT THÚC PHẦN GIẢ LẬP ---

                    st.write("GeoJSON của đoạn đường:")
                    st.json(segment_geojson)
                    if st.button("Thêm đoạn đường cấm này"):
                        st.session_state['blocking_geometries'].append(segment_geojson)
                        st.success("Đã thêm. Bản đồ sẽ được cập nhật.")
                        st.rerun()

                except Exception as e:
                    st.error(f"Lỗi khi lấy dữ liệu: {e}")
            else:
                st.warning("Vui lòng nhập đủ thông tin.")

        st.divider()
        st.subheader("↔️ Thiết lập đường một chiều")
        st.write("(Tính năng đang phát triển)")
        oneway_road = st.text_input("Tên đường", key="oneway_road_name")
        oneway_from = st.text_input("Một chiều từ địa chỉ", key="oneway_from_addr")
        oneway_to = st.text_input("Đến địa chỉ", key="oneway_to_addr")

# --- Sidebar để hiển thị trạng thái ---
st.sidebar.header("Các vùng/đường cấm đã chọn")
if st.session_state['blocking_geometries']:
    st.sidebar.success(f"Đang áp dụng {len(st.session_state['blocking_geometries'])} điều kiện.")
    st.sidebar.json(st.session_state['blocking_geometries'])
    if st.sidebar.button("Xóa tất cả"):
        st.session_state['blocking_geometries'] = []
        st.rerun()
else:
    st.sidebar.info("Chưa có lựa chọn nào.")

# --- Phần tìm đường chính ---
st.divider()
st.header("Tìm đường với các điều kiện đã áp dụng")
start_point = st.text_input("Tọa độ điểm bắt đầu (lon, lat):", "105.85, 21.02")
end_point = st.text_input("Tọa độ điểm kết thúc (lon, lat):", "105.80, 21.00")

if st.button("Tìm đường"):
    try:
        start_lon, start_lat = map(float, start_point.split(','))
        end_lon, end_lat = map(float, end_point.split(','))

        # Chuẩn bị payload để gửi đến FastAPI
        payload = {
            "start_point": {"lon": start_lon, "lat": start_lat},
            "end_point": {"lon": end_lon, "lat": end_lat},
            "blocking_geometries": st.session_state['blocking_geometries'] # Gửi toàn bộ danh sách
        }

        st.info("Đang gửi yêu cầu tìm đường đến backend...")
        # response = requests.post(GET_ROUTE_URL, json=payload)
        # response.raise_for_status()
        # route_geojson = response.json()

        st.success("Backend đã nhận và đang xử lý!")
        st.write("Dữ liệu gửi đi:")
        st.json(payload)
        # Ở đây bạn sẽ nhận route_geojson về và vẽ tiếp lên bản đồ
        # Ví dụ: folium.GeoJson(route_geojson).add_to(m) và cập nhật lại bản đồ

    except Exception as e:
        st.error(f"Đã xảy ra lỗi: {e}")