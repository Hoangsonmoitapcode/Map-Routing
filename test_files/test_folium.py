import streamlit as st
import folium
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx

st.set_page_config(page_title="Đường đi qua giao lộ thực", layout="wide")

st.title("🚗 Vẽ đường đi giữa các giao lộ thật ở Hà Nội")

# === 1. Dữ liệu thật: các giao lộ ===
points = [
    (21.0046, 105.8727),  # Vĩnh Tuy – Minh Khai
    (21.0030, 105.8700),  # Times City
    (21.0059, 105.8496),  # Bạch Mai – Đại La
]

# === 2. Tải mạng đường khu vực quanh các điểm này ===
G = ox.graph_from_point(points[0], dist=3000, network_type="drive")

# === 3. Tìm node gần nhất trong mạng đường cho mỗi điểm ===
node_ids = [ox.distance.nearest_nodes(G, lon, lat) for lat, lon in points]

# === 4. Tìm đường đi ngắn nhất lần lượt qua các điểm ===
route_nodes = []
for i in range(len(node_ids) - 1):
    path = nx.shortest_path(G, node_ids[i], node_ids[i + 1], weight="length")
    route_nodes.extend(path if i == 0 else path[1:])

# === 5. Lấy danh sách toạ độ đường đi ===
route_coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in route_nodes]

# === 6. Tạo bản đồ Folium ===
m = folium.Map(location=points[0], zoom_start=14)

# Vẽ tuyến đường thực tế
folium.PolyLine(
    route_coords,
    color="blue",
    weight=6,
    opacity=0.8,
    tooltip="Tuyến đường thực tế giữa các giao lộ"
).add_to(m)

# Đánh dấu điểm đầu/cuối
for idx, (lat, lon) in enumerate(points):
    folium.Marker(
        location=(lat, lon),
        popup=f"Điểm {idx+1}",
        icon=folium.Icon(color="red" if idx == 0 else "green" if idx == len(points)-1 else "orange")
    ).add_to(m)

# === 7. Hiển thị bản đồ ===
st_folium(m, width=900, height=600)
