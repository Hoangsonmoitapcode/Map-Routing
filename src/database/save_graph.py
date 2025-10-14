import osmnx as ox
from sqlalchemy import create_engine, text
import networkx as nx
import os

#sau sap nhap co 4 phuong
places_names =[
    "Phường Vĩnh Tuy, Hà Nội, Việt Nam",
    "Phường Mai Động, Hà Nội, Việt Nam",
    "Phường Vĩnh Hưng, Hà Nội, Việt Nam",
    "Phường Thanh Lương, Hà Nội, Việt Nam"
]

#gop do thi
graphs=[]
for place in places_names:
    print(f"dang tai {place}")
    G=ox.graph_from_place(place, network_type='drive')
    graphs.append(G)

G = graphs[0]
for graph in graphs[1:]:
    G = nx.compose(G, graph)

G = ox.project_graph(G)  # Chuyển sang hệ tọa độ chiếu (projected CRS)
G = ox.consolidate_intersections(G, tolerance=15)

print("da tai ban do")

# them speed va travel time lam trong so edge
G = ox.add_edge_speeds(G, fallback=30)
G = ox.add_edge_travel_times(G)

print("da them speed va travel time")

# 1. Chuyển đổi đồ thị thành GeoDataFrames
nodes, edges = ox.graph_to_gdfs(G)

print("Da chuyen doi thanh dataframe.")

# tao khoa thanh cot trong dtb (osmid, u, v, key)
nodes.reset_index(inplace=True)
edges.reset_index(inplace=True)
print("Reset index, 'osmid' and others are now columns.")

# 2. Tạo kết nối tới database PostGIS
# !!! THAY THẾ CÁC THÔNG SỐ CỦA BẠN VÀO ĐÂY !!!
db_user = os.getenv('POSTGRES_USER', 'postgres')
db_password = os.getenv('POSTGRES_PASSWORD', '123456')
db_host = os.getenv('POSTGRES_HOST', 'localhost')
db_port = os.getenv('POSTGRES_PORT', '5432')
db_name = os.getenv('POSTGRES_DB', 'map_route_dtb')

engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
print("da ket noi toi dtb.")

# Enable PostGIS extension
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    conn.commit()

# 3. Lưu các bảng nodes và edges vào PostGIS
# 'if_exists='replace'' sẽ xóa bảng cũ nếu đã tồn tại
edges.to_postgis('edges', engine, if_exists='replace')
nodes.to_postgis('nodes', engine, if_exists='replace')

print("da luu vao postgis")