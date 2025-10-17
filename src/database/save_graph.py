# src/database/save_graph.py

import osmnx as ox
from sqlalchemy import create_engine, text
import networkx as nx
import os
from shapely.geometry import LineString

print("=" * 70)
print("NHẬP DỮ LIỆU BẢN ĐỒ VÀO CƠ SỞ DỮ LIỆU")
print("=" * 70)

# Danh sách khu vực cần tải dữ liệu
places_names = [
    "Phường Vĩnh Tuy, Hà Nội, Việt Nam",
    "Phường Mai Động, Hà Nội, Việt Nam",
    "Phường Vĩnh Hưng, Hà Nội, Việt Nam",
    "Phường Thanh Lương, Hà Nội, Việt Nam"
]

# Tải từng khu vực và gộp thành một đồ thị chung
graphs = []
for place in places_names:
    print(f"Đang tải: {place}")
    G = ox.graph_from_place(place, network_type='all')
    graphs.append(G)
    print(f"   {len(G.nodes)} nút, {len(G.edges)} cạnh")

# Hợp nhất các đồ thị khu vực lại
G = graphs[0]
for graph in graphs[1:]:
    G = nx.compose(G, graph)
print(f"\nSau khi gộp: {len(G.nodes)} nút, {len(G.edges)} cạnh")

# Chuẩn hóa và hợp nhất các nút giao gần nhau
G = ox.project_graph(G)
G = ox.consolidate_intersections(G, tolerance=15)
print(f"Sau khi hợp nhất giao lộ: {len(G.nodes)} nút, {len(G.edges)} cạnh")

# Thêm tốc độ và thời gian di chuyển
print("\nĐang thêm thông tin tốc độ và thời gian di chuyển...")
G = ox.add_edge_speeds(G, fallback=30)
G = ox.add_edge_travel_times(G)

# Đảm bảo mọi cạnh đều có geometry
print("\nKiểm tra và bổ sung geometry cho các cạnh...")
for u, v, k, data in G.edges(keys=True, data=True):
    if 'geometry' not in data or data['geometry'] is None:
        u_node = G.nodes[u]
        v_node = G.nodes[v]
        data['geometry'] = LineString([
            (u_node['x'], u_node['y']),
            (v_node['x'], v_node['y'])
        ])
print("   Tất cả cạnh đã có geometry")

# Chuyển đồ thị sang GeoDataFrame
print("\nChuyển đồ thị sang GeoDataFrame...")
nodes, edges = ox.graph_to_gdfs(G)
nodes.reset_index(inplace=True)
edges.reset_index(inplace=True)
print(f"   Số lượng nút: {len(nodes)}")
print(f"   Số lượng cạnh: {len(edges)}")
print(f"   Cạnh có geometry: {(~edges['geometry'].isna()).sum()}")

# Thiết lập thông tin kết nối PostGIS
db_user = os.getenv('POSTGRES_USER', 'postgres')
db_password = os.getenv('POSTGRES_PASSWORD', '123456')
db_host = os.getenv('POSTGRES_HOST', 'localhost')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_name = os.getenv('POSTGRES_DB', 'map_route_dtb')

engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
print("\nKết nối thành công tới cơ sở dữ liệu PostGIS")

# Bật extension PostGIS nếu chưa có
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    conn.commit()

# Ghi dữ liệu vào PostGIS
print("\nĐang ghi dữ liệu vào PostGIS...")
edges.to_postgis('edges', engine, if_exists='replace')
nodes.to_postgis('nodes', engine, if_exists='replace')

print("\n" + "=" * 70)
print("HOÀN TẤT: Dữ liệu bản đồ đã được lưu vào cơ sở dữ liệu.")
print("=" * 70)
