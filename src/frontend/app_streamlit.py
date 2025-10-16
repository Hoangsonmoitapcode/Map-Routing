import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import requests
import osmnx as ox
import networkx as nx
from pathlib import Path

# --- Cấu hình ---
PREVIEW_SEGMENT_URL = "http://127.0.0.1:8000/api/v1/analysis/preview-segment"
GET_ROUTE_URL = "http://127.0.0.1:8000/api/v1/routing/get-route"
SAVE_BLOCKING_URL = "http://127.0.0.1:8000/api/v1/analysis/save-blocking"
GEOCODING_URL = "http://127.0.0.1:8000/api/v1/geocoding/loc-to-coords"

# File lưu graph
GRAPH_FILE = Path("src/models/graph/vinhtuy.graphml")

# --- Khởi tạo Session State ---
if 'blocking_geometries' not in st.session_state:
    st.session_state['blocking_geometries'] = []

if 'custom_graph' not in st.session_state:
    st.session_state['custom_graph'] = None


def load_or_create_graph():
    """Load graph từ file hoặc tạo mới nếu chưa có"""
    if GRAPH_FILE.exists():
        st.info(f"📂 Đang load graph từ file {GRAPH_FILE}...")
        G = ox.load_graphml(GRAPH_FILE)
        st.success("✅ Đã load graph từ cache!")
        return G
    else:
        st.warning("⚠️ Chưa có file cache. Đang tải từ OSM (có thể mất vài phút)...")
        places_names = [
            "Phường Vĩnh Tuy, Hà Nội, Việt Nam",
            "Phường Mai Động, Hà Nội, Việt Nam",
            "Phường Vĩnh Hưng, Hà Nội, Việt Nam",
            "Phường Thanh Lương, Hà Nội, Việt Nam"
        ]

        graphs = []
        progress_bar = st.progress(0)
        for i, place in enumerate(places_names):
            st.write(f"Đang tải {place}...")
            G = ox.graph_from_place(place, network_type='all')
            graphs.append(G)
            progress_bar.progress((i + 1) / len(places_names))

        G = graphs[0]
        for graph in graphs[1:]:
            G = nx.compose(G, graph)

        st.write("Đang xử lý graph...")
        G = ox.project_graph(G)
        G = ox.consolidate_intersections(G, tolerance=15)

        # Lưu lại
        ox.save_graphml(G, GRAPH_FILE)
        st.success(f"💾 Đã lưu graph vào {GRAPH_FILE}. Lần sau sẽ load nhanh hơn!")

        return G

# --- Giao diện Streamlit ---
st.set_page_config(layout="wide")
st.title("Công cụ tìm đường và quản lý giao thông")

# --- Chia layout chính ---
col1, col2 = st.columns([3, 2])  # 3 phần cho bản đồ, 2 phần cho bảng điều khiển

with col1:
    st.header("Bản đồ tương tác")

    # ===== THAY ĐỔI LOGIC TẠO BẢN ĐỒ =====
    # Load custom graph nếu chưa có
    if st.session_state['custom_graph'] is None:
        with st.spinner("Đang tải bản đồ từ OSMnx..."):
            places_names = [
                "Phường Vĩnh Tuy, Hà Nội, Việt Nam",
                "Phường Mai Động, Hà Nội, Việt Nam",
                "Phường Vĩnh Hưng, Hà Nội, Việt Nam",
                "Phường Thanh Lương, Hà Nội, Việt Nam"
            ]

            graphs = []
            for place in places_names:
                G = ox.graph_from_place(place, network_type='all')
                graphs.append(G)

            G = graphs[0]
            for graph in graphs[1:]:
                G = nx.compose(G, graph)

            G = ox.project_graph(G)
            G = ox.consolidate_intersections(G, tolerance=15)

            st.session_state['custom_graph'] = G

    # Tạo bản đồ từ custom graph
    G = st.session_state['custom_graph']
    G_latlon = ox.project_graph(G, to_crs='EPSG:4326')

    # Lấy tọa độ từ graph
    nodes = ox.graph_to_gdfs(G_latlon, edges=False)
    edges = ox.graph_to_gdfs(G_latlon, nodes=False)

    # Tính bounds từ EDGES (chứ không phải nodes) để chặt chẽ hơn
    min_lat = edges.geometry.bounds['miny'].min()
    max_lat = edges.geometry.bounds['maxy'].max()
    min_lon = edges.geometry.bounds['minx'].min()
    max_lon = edges.geometry.bounds['maxx'].max()

    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2

    # Padding rất nhỏ để giới hạn chặt
    padding = 0.001  # ~100m
    bounds = [
        [min_lat - padding, min_lon - padding],
        [max_lat + padding, max_lon + padding]
    ]

    # Tạo bản đồ với giới hạn chặt chẽ
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        min_zoom=14,  # Không cho zoom out nhiều
        max_zoom=18,
        max_bounds=bounds,
        max_bounds_viscosity=1.0
    )
    m.fit_bounds(bounds)

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
        st.subheader("Cấm/ngập một đoạn đường")
        road_name_ban = st.text_input("Tên đường, phố", key="ban_road_name", example="Đường Kim Ngưu/ Phố Lê Thanh Nghị")
        from_address = st.text_input("Từ địa chỉ", key="ban_from_addr", example= "74/ Số 74")
        to_address = st.text_input("Đến địa chỉ", key="ban_to_addr")

        if st.button("Xem trước & Lấy GeoJSON"):
            if all([road_name_ban, from_address, to_address]):
                payload = {
                    "street_name": road_name_ban,
                    "start_address": f"{from_address}, {road_name_ban}",        #vi du 74 Phố Kim Ngưu
                    "end_address": f"{to_address}, {road_name_ban}"
                }
                try:
                    st.info("Đang gọi API để lấy geometry đoạn đường...")
                    response = requests.post(PREVIEW_SEGMENT_URL, json=payload)
                    response.raise_for_status()
                    segment_geojson = response.json()

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
        st.subheader("Thiết lập đường một chiều")
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

# Phần tìm đường ở cuối trang
st.divider()
st.header("🚗 Tìm đường thông minh")

col1, col2 = st.columns(2)

with col1:
    start_address = st.text_input(
        "🔵 Điểm bắt đầu",
        placeholder="VD: 119 Lê Thanh Nghị, Hà Nội"
    )

with col2:
    end_address = st.text_input(
        "🔴 Điểm đến",
        placeholder="VD: Cầu Vĩnh Tuy, Hà Nội"
    )

if st.button("🔍 Tìm đường", type="primary"):
    if not start_address or not end_address:
        st.error("Vui lòng nhập đủ địa chỉ!")
        st.stop()

    with st.spinner("Đang tìm đường tối ưu..."):
        try:
            # GỌI API
            payload = {
                "start_address": start_address,
                "end_address": end_address,
                "blocking_geometries": st.session_state['blocking_geometries']
            }

            response = requests.post(
                "http://127.0.0.1:8000/api/v1/routing/find-route",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # HIỂN THỊ KẾT QUẢ
            st.success("✅ Tìm thấy đường đi!")

            col_metric1, col_metric2 = st.columns(2)
            with col_metric1:
                st.metric("Khoảng cách", f"{result['distance'] / 1000:.2f} km")
            with col_metric2:
                st.metric("Thời gian", f"{result['duration']:.0f} phút")

            # VẼ ĐƯỜNG LÊN BẢN ĐỒ
            route_layer = folium.GeoJson(
                result['route'],
                style_function=lambda x: {
                    'color': 'green',
                    'weight': 5,
                    'opacity': 0.8
                }
            )
            route_layer.add_to(m)

            # Thêm marker điểm đầu/cuối
            coords = result['route']['geometry']['coordinates']
            folium.Marker(
                [coords[0][1], coords[0][0]],
                popup="Điểm bắt đầu",
                icon=folium.Icon(color='blue', icon='play')
            ).add_to(m)

            folium.Marker(
                [coords[-1][1], coords[-1][0]],
                popup="Điểm đến",
                icon=folium.Icon(color='red', icon='stop')
            ).add_to(m)

            st.rerun()  # Cập nhật bản đồ

        except Exception as e:
            st.error(f"❌ Lỗi: {e}")