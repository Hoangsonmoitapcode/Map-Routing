import osmnx as ox
from sqlalchemy import create_engine, text

place_name = "Phường Vĩnh Tuy, Hà Nội, Việt Nam"

# Tải dữ liệu mạng lưới đường bộ từ OpenStreetMap
G = ox.graph_from_place(place_name, network_type='drive')

print("da tai ban do")

# 1. Chuyển đổi đồ thị thành GeoDataFrames

nodes, edges = ox.graph_to_gdfs(G)
print("Da chuyen doi thanh dataframe.")

# tao khoa thanh cot trong dtb (osmid, u, v, key)
nodes.reset_index(inplace=True)
edges.reset_index(inplace=True)
print("Reset index, 'osmid' and others are now columns.")

# 2. Tạo kết nối tới database PostGIS
# !!! THAY THẾ CÁC THÔNG SỐ CỦA BẠN VÀO ĐÂY !!!
db_user = 'postgres'
db_password = '123456'
db_host = 'localhost'
db_port = '5432'
db_name = 'map_route_dtb'

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