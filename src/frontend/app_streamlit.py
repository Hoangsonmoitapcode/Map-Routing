import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import requests
import osmnx as ox
import networkx as nx
from pathlib import Path

# --- Cấu hình ---
GEOCODING_URL = "http://127.0.0.1:8000/api/v1/geocoding/loc-to-coords"
FIND_ROUTE_URL = "http://127.0.0.1:8000/api/v1/routing/find-standard-route"

# File lưu graph
GRAPH_FILE = Path("src/models/graph/vinhtuy.graphml")

# --- Khởi tạo Session State ---
if 'blocking_geometries' not in st.session_state:
    st.session_state['blocking_geometries'] = []

if 'flood_areas' not in st.session_state:
    st.session_state['flood_areas'] = []

if 'ban_areas' not in st.session_state:
    st.session_state['ban_areas'] = []

if 'oneway_areas' not in st.session_state:
    st.session_state['oneway_areas'] = []

if 'custom_graph' not in st.session_state:
    st.session_state['custom_graph'] = None

if 'current_route' not in st.session_state:
    st.session_state['current_route'] = None


def load_or_create_graph():
    """Load graph từ file hoặc tạo mới nếu chưa có"""
    if GRAPH_FILE.exists():
        st.info(f"Đang load graph từ file {GRAPH_FILE}...")
        G = ox.load_graphml(GRAPH_FILE)
        st.success("Đã load graph từ cache!")
        return G
    else:
        st.warning("Chưa có file cache. Đang tải từ OSM ...")
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
        st.success(f"Đã lưu graph vào {GRAPH_FILE}. Lần sau sẽ load nhanh hơn!")

        return G

# --- Giao diện Streamlit ---
st.set_page_config(layout="wide")
st.title("Công cụ tìm đường và quản lý giao thông")

# --- Chia layout chính ---
col1, col2 = st.columns([3, 2])  # 3 phần cho bản đồ, 2 phần cho bảng điều khiển

with col1:
    st.header("Bản đồ tương tác")

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

    # Tính bounds từ EDGES
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
        min_zoom=14,
        max_zoom=18,
        max_bounds=bounds,
        max_bounds_viscosity=1.0
    )
    m.fit_bounds(bounds)

    # Thêm plugin Draw vào bản đồ
    Draw(export=True).add_to(m)

    # Vẽ lại các vùng ngập (màu xanh dương)
    if st.session_state['flood_areas']:
        for geom in st.session_state['flood_areas']:
            folium.GeoJson(geom, style_function=lambda x: {'color': 'blue', 'weight': 3, 'fillOpacity': 0.3}).add_to(m)
    
    # Vẽ lại các vùng cấm (màu đỏ)
    if st.session_state['ban_areas']:
        for geom in st.session_state['ban_areas']:
            folium.GeoJson(geom, style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0.3}).add_to(m)
    
    # Vẽ lại các vùng cấm legacy (màu đỏ)
    if st.session_state['blocking_geometries']:
        for geom in st.session_state['blocking_geometries']:
            folium.GeoJson(geom, style_function=lambda x: {'color': 'red', 'weight': 3, 'fillOpacity': 0.3}).add_to(m)
    
    # Vẽ lại các đường một chiều (màu tím)
    if st.session_state['oneway_areas']:
        for geom in st.session_state['oneway_areas']:
            folium.GeoJson(geom, style_function=lambda x: {'color': 'purple', 'weight': 3, 'opacity': 0.8}).add_to(m)
    
    # Vẽ preview segment (màu cam)
    if 'preview_segment' in st.session_state and st.session_state['preview_segment']:
        preview_color = 'orange'  # Orange for preview
        folium.GeoJson(
            st.session_state['preview_segment'], 
            style_function=lambda x: {'color': preview_color, 'weight': 4, 'opacity': 0.8}
        ).add_to(m)

    # Vẽ route hiện tại nếu có
    if st.session_state['current_route']:
        route_data = st.session_state['current_route']
        
        # Vẽ đường đi
        route_layer = folium.GeoJson(
            route_data['route'],
            style_function=lambda x: {
                'color': 'green',
                'weight': 6,
                'opacity': 0.9
            }
        )
        route_layer.add_to(m)
        
        # Thêm marker điểm đầu/cuối với thông tin chi tiết
        coords = route_data['route']['geometry']['coordinates']
        
        # Marker điểm bắt đầu
        folium.Marker(
            [coords[0][1], coords[0][0]],
            popup=f"""
            <div style="font-family: Arial; font-size: 14px;">
                <h4 style="color: #1f77b4; margin: 0;"> Điểm bắt đầu</h4>
                <p style="margin: 5px 0;"><strong>Khoảng cách:</strong> {route_data['distance']/1000:.2f} km</p>
                <p style="margin: 5px 0;"><strong>Thời gian:</strong> {route_data['duration']:.0f} phút</p>
            </div>
            """,
            tooltip="Điểm bắt đầu",
            icon=folium.Icon(color='blue', icon='play', prefix='fa')
        ).add_to(m)
        
        # Marker điểm đến
        folium.Marker(
            [coords[-1][1], coords[-1][0]],
            popup=f"""
            <div style="font-family: Arial; font-size: 14px;">
                <h4 style="color: #d62728; margin: 0;">🏁 Điểm đến</h4>
                <p style="margin: 5px 0;"><strong>Khoảng cách:</strong> {route_data['distance']/1000:.2f} km</p>
                <p style="margin: 5px 0;"><strong>Thời gian:</strong> {route_data['duration']:.0f} phút</p>
            </div>
            """,
            tooltip="Điểm đến",
            icon=folium.Icon(color='red', icon='stop', prefix='fa')
        ).add_to(m)

    # Hiển thị bản đồ trong Streamlit
    output = st_folium(m, width=800, height=600)

with col2:
    st.header("Bảng điều khiển")
    tab1, tab2, tab3 = st.tabs(["Vẽ vùng ngập", "Vẽ vùng cấm", "Chọn đường theo địa chỉ"])

    # Tab 1: Vẽ vùng ngập (tăng gấp đôi trọng số)
    with tab1:
        st.info("Vẽ vùng ngập")
        if output.get("all_drawings") and len(output["all_drawings"]) > 0:
            # Lấy hình mới nhất được vẽ
            last_drawn = output["all_drawings"][-1]
            st.write("Hình vừa vẽ:")
            st.json(last_drawn['geometry'])
            if st.button("Thêm vùng ngập này", key="add_flood"):
                st.session_state['flood_areas'].append(last_drawn['geometry'])
                st.success("Đã thêm vùng ngập. Bản đồ sẽ được cập nhật.")
                st.rerun()

    # Tab 2: Vẽ vùng cấm (chặn hoàn toàn)
    with tab2:
        st.info("Vẽ vùng cấm")
        if output.get("all_drawings") and len(output["all_drawings"]) > 0:
            # Lấy hình mới nhất được vẽ
            last_drawn = output["all_drawings"][-1]
            st.write("Hình vừa vẽ:")
            st.json(last_drawn['geometry'])
            if st.button("Thêm vùng cấm này", key="add_ban"):
                st.session_state['ban_areas'].append(last_drawn['geometry'])
                st.success("Đã thêm vùng cấm. Bản đồ sẽ được cập nhật.")
                st.rerun()

    # Tab 3: Chọn đường theo địa chỉ
    with tab3:
        st.subheader("Cấm/ngập một đoạn đường")
        
        # Radio button để chọn loại
        area_type = st.radio("Chọn loại vùng:", ["Vùng ngập (tăng trọng số)", "Vùng cấm (chặn hoàn toàn)", "Đường một chiều"], key="area_type")
        
        road_name_ban = st.text_input("Tên đường, phố", key="ban_road_name")
        from_address = st.text_input("Từ địa chỉ", key="ban_from_addr")
        to_address = st.text_input("Đến địa chỉ", key="ban_to_addr")

        if st.button("Xem trước & Lấy GeoJSON"):
            if all([road_name_ban, from_address, to_address]):
                try:
                    st.info("Đang lấy tọa độ từ địa chỉ...")
                    
                    # Gọi API geocoding cho điểm bắt đầu
                    start_payload = {"address": f"{from_address}, {road_name_ban}"}
                    start_loc_res = requests.post(GEOCODING_URL, json=start_payload)
                    start_loc_res.raise_for_status()
                    
                    # Gọi API geocoding cho điểm kết thúc
                    end_payload = {"address": f"{to_address}, {road_name_ban}"}
                    end_loc_res = requests.post(GEOCODING_URL, json=end_payload)
                    end_loc_res.raise_for_status()
                    
                    start_coords = start_loc_res.json()
                    end_coords = end_loc_res.json()
                    
                    st.success("Đã lấy tọa độ thành công!")
                    st.write(f"Điểm bắt đầu: {start_coords}")
                    st.write(f"Điểm kết thúc: {end_coords}")
                    
                    # Tạo GeoJSON LineString từ 2 điểm
                    segment_geojson = {
                        "type": "LineString",
                        "coordinates": [
                            [start_coords["longitude"], start_coords["latitude"]],
                            [end_coords["longitude"], end_coords["latitude"]]
                        ]
                    }

                    st.write("GeoJSON của đoạn đường:")
                    st.json(segment_geojson)
                    
                    # Store preview segment in session state
                    st.session_state['preview_segment'] = segment_geojson
                    st.session_state['preview_type'] = area_type
                    st.rerun()

                except requests.exceptions.HTTPError as e:
                    st.error(f"Lỗi HTTP: {e}")
                    if hasattr(e.response, 'text'):
                        st.error(f"Chi tiết: {e.response.text}")
                except Exception as e:
                    st.error(f"Lỗi khi lấy dữ liệu: {e}")
            else:
                st.warning("Vui lòng nhập đủ thông tin.")

        # Add confirmation buttons that persist
        if 'preview_segment' in st.session_state and st.session_state['preview_segment']:
            st.write("---")
            st.write("**Xác nhận thêm đoạn đường:**")
            if st.session_state.get('preview_type') == "Vùng ngập (tăng trọng số)":
                if st.button("Thêm đoạn đường này", key="confirm_flood"):
                    st.session_state['flood_areas'].append(st.session_state['preview_segment'])
                    st.success("Đã thêm vùng ngập. Bản đồ sẽ được cập nhật.")
                    # Clear preview
                    del st.session_state['preview_segment']
                    del st.session_state['preview_type']
                    st.rerun()
            elif st.session_state.get('preview_type') == "Vùng cấm (chặn hoàn toàn)":
                if st.button("Thêm đoạn đường này", key="confirm_ban"):
                    st.session_state['ban_areas'].append(st.session_state['preview_segment'])
                    st.success("Đã thêm vùng cấm. Bản đồ sẽ được cập nhật.")
                    # Clear preview
                    del st.session_state['preview_segment']
                    del st.session_state['preview_type']
                    st.rerun()
            else:  # One-way road
                if st.button("Thêm đoạn đường này", key="confirm_oneway"):
                    st.session_state['oneway_areas'].append(st.session_state['preview_segment'])
                    st.success("Đã thêm đường một chiều. Bản đồ sẽ được cập nhật.")
                    # Clear preview
                    del st.session_state['preview_segment']
                    del st.session_state['preview_type']
                    st.rerun()

        st.divider()

# --- Sidebar để hiển thị trạng thái ---
st.sidebar.header("Thông tin tuyến đường")
if st.session_state['current_route']:
    route_data = st.session_state['current_route']
    st.sidebar.success("Đã tìm thấy tuyến đường!")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Khoảng cách", f"{route_data['distance'] / 1000:.2f} km")
    with col2:
        st.metric("Thời gian", f"{route_data['duration']:.0f} phút")
    
    if st.sidebar.button("Xóa tuyến đường", type="secondary"):
        st.session_state['current_route'] = None
        st.rerun()
else:
    st.sidebar.info("Chưa có tuyến đường nào được tìm.")

st.sidebar.divider()
st.sidebar.header("Các vùng đã chọn")

# Vùng ngập
if st.session_state['flood_areas']:
    st.sidebar.success(f" {len(st.session_state['flood_areas'])} vùng ngập")
    for i, area in enumerate(st.session_state['flood_areas']):
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.sidebar.write(f" Vùng ngập #{i+1}")
        with col2:
            if st.sidebar.button("❌", key=f"del_flood_{i}"):
                st.session_state['flood_areas'].pop(i)
                st.rerun()
    if st.sidebar.button("Xóa tất cả vùng ngập"):
        st.session_state['flood_areas'] = []
        st.rerun()
else:
    st.sidebar.info("Chưa có vùng ngập nào.")

# Vùng cấm
if st.session_state['ban_areas']:
    st.sidebar.success(f" {len(st.session_state['ban_areas'])} vùng cấm")
    for i, area in enumerate(st.session_state['ban_areas']):
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.sidebar.write(f" Vùng cấm #{i+1}")
        with col2:
            if st.sidebar.button("❌", key=f"del_ban_{i}"):
                st.session_state['ban_areas'].pop(i)
                st.rerun()
    if st.sidebar.button("Xóa tất cả vùng cấm"):
        st.session_state['ban_areas'] = []
        st.rerun()
else:
    st.sidebar.info(" Chưa có vùng cấm nào.")

# Đường một chiều
if st.session_state['oneway_areas']:
    st.sidebar.success(f" {len(st.session_state['oneway_areas'])} đường một chiều")
    for i, area in enumerate(st.session_state['oneway_areas']):
        col1, col2 = st.sidebar.columns([3, 1])
        with col1:
            st.sidebar.write(f" Đường một chiều #{i+1}")
        with col2:
            if st.sidebar.button("❌", key=f"del_oneway_{i}"):
                st.session_state['oneway_areas'].pop(i)
                st.rerun()
    if st.sidebar.button("Xóa tất cả đường một chiều"):
        st.session_state['oneway_areas'] = []
        st.rerun()
else:
    st.sidebar.info("Chưa có đường một chiều nào.")

# Legacy blocking geometries
if st.session_state['blocking_geometries']:
    st.sidebar.warning(f" {len(st.session_state['blocking_geometries'])} vùng cấm cũ")
    if st.sidebar.button("Xóa tất cả vùng cấm cũ"):
        st.session_state['blocking_geometries'] = []
        st.rerun()

# Phần tìm đường ở cuối trang
st.divider()
if st.session_state['current_route']:
    st.header("Tìm đường mới")
    st.info("Để tìm tuyến đường mới, nhập địa chỉ bên dưới và nhấn 'Tìm đường'")
else:
    st.header("Tìm đường")
    st.info("Nhập địa chỉ điểm bắt đầu và điểm đến để tìm tuyến đường tối ưu")

col1, col2 = st.columns(2)

with col1:
    start_address = st.text_input(
        "Điểm bắt đầu",
        placeholder="VD: 119 Lê Thanh Nghị, Hà Nội",
        help="Nhập địa chỉ điểm xuất phát"
    )

with col2:
    end_address = st.text_input(
        "Điểm đến",
        placeholder="VD: Cầu Vĩnh Tuy, Hà Nội",
        help="Nhập địa chỉ điểm đích"
    )

if st.button("Tìm đường", type="primary"):
    if not start_address or not end_address:
        st.error("Vui lòng nhập đủ địa chỉ!")
        st.stop()

    with st.spinner("Đang tìm đường tối ưu..."):
        try:
            # GỌI API
            payload = {
                "start_address": start_address,
                "end_address": end_address,
                "blocking_geometries": st.session_state['blocking_geometries'],
                "flood_areas": st.session_state['flood_areas'],
                "ban_areas": st.session_state['ban_areas']
            }

            response = requests.post(
                FIND_ROUTE_URL,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # Check if there's an error in the response
            if "error" in result:
                st.error(f"Không tìm thấy đường đi: {result['error']}")
                st.session_state['current_route'] = None
            else:
                # LƯU ROUTE VÀO SESSION STATE
                st.session_state['current_route'] = result
                
                # HIỂN THỊ KẾT QUẢ
                st.success("Tìm thấy đường đi!")
                st.rerun()  # Cập nhật bản đồ để hiển thị route

        except Exception as e:
            st.error(f"Lỗi: {e}")