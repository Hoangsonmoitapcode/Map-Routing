from sqlalchemy import create_engine
import geopandas as gpd
import osmnx as ox
from src.app.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

#CRS: hệ quy chiếu, bao gồm geographic CRS: định vị điểm trên bề mặt cong của trái đất, đang sử dụng WGS 84 (ESPG 4326): xác định vị trí dự trên lat/lon
#project CRS: hệ quy chiếu lên bản đồ phẳng để tính khoảng cách 

def load_graph_from_db():
    """Tải dữ liệu bản đồ từ PostGIS và tạo đồ thị OSMnx"""
    print("Đang tải dữ liệu bản đồ từ PostGIS...")

    # Đọc dữ liệu nodes và edges từ PostGIS
    nodes_gdf = gpd.read_postgis(
        "SELECT * FROM nodes",
        engine,
        index_col='osmid',
        geom_col='geometry'
    )

    edges_gdf = gpd.read_postgis(
        "SELECT * FROM edges",
        engine,
        index_col=['u', 'v', 'key'],
        geom_col='geometry'
    )

    # Kiểm tra dữ liệu có hợp lệ không
    if nodes_gdf.empty or edges_gdf.empty:
        print("Lỗi: bảng nodes hoặc edges trống trong cơ sở dữ liệu.")
        return None

    # Đặt/chuẩn hóa hệ tọa độ về WGS84 (EPSG:4326)
    def _looks_projected(gdf) -> bool:
        try:
            xs = gdf.geometry.x
            ys = gdf.geometry.y
            return (xs.abs().max() > 180) or (ys.abs().max() > 90)
        except Exception:
            return False

    # Ưu tiên dùng CRS từ DB; nếu thiếu và giá trị toạ độ lớn, coi như đó đang là data của project CRS=  UTM 48N (EPSG:32648) cho Hà Nội
    if nodes_gdf.crs is None and _looks_projected(nodes_gdf):
        nodes_gdf.set_crs(epsg=32648, inplace=True)
    if edges_gdf.crs is None and _looks_projected(edges_gdf):
        edges_gdf.set_crs(epsg=32648, inplace=True)

    # Chuyển về WGS84 để hiển thị theo tọa độ của cầu
    if nodes_gdf.crs is None:
        nodes_gdf.set_crs(epsg=4326, inplace=True)
    elif nodes_gdf.crs.to_epsg() != 4326:
        nodes_gdf = nodes_gdf.to_crs(epsg=4326) #chuyen tu project crs sang geo crs de co toa do dung

    if edges_gdf.crs is None:
        edges_gdf.set_crs(epsg=4326, inplace=True)
    elif edges_gdf.crs.to_epsg() != 4326:
        edges_gdf = edges_gdf.to_crs(epsg=4326)

    # Fallback: nếu sau các bước trên mà toạ độ vẫn không ở dải WGS84, cưỡng bức gán 32648 rồi chuyển sang 4326
    try:
        if (nodes_gdf.geometry.y.abs().max() > 90) or (nodes_gdf.geometry.x.abs().max() > 180):
            nodes_gdf.set_crs(epsg=32648, inplace=True, allow_override=True)
            nodes_gdf = nodes_gdf.to_crs(epsg=4326)
        if (edges_gdf.geometry.y.abs().max() > 90) or (edges_gdf.geometry.x.abs().max() > 180):
            edges_gdf.set_crs(epsg=32648, inplace=True, allow_override=True)
            edges_gdf = edges_gdf.to_crs(epsg=4326)
    except Exception:
        pass

    # Kiểm tra geometry bị thiếu
    missing_geom = edges_gdf['geometry'].isna().sum()
    print(f"   Số lượng nodes: {len(nodes_gdf)}")
    print(f"   Số lượng edges: {len(edges_gdf)}")
    print(f"   Số cạnh có geometry: {len(edges_gdf) - missing_geom}")

    if missing_geom > 0:
        print(f"   Cảnh báo: có {missing_geom} cạnh thiếu geometry.")

    # Đồng bộ cột x/y với geometry sau khi chuyển CRS về WGS84
    try:
        nodes_gdf['x'] = nodes_gdf.geometry.x
        nodes_gdf['y'] = nodes_gdf.geometry.y
    except Exception:
        pass

    # Tạo đồ thị OSMnx từ GeoDataFrame
    G_base = ox.graph_from_gdfs(nodes_gdf, edges_gdf)

    # Kiểm tra ngẫu nhiên một cạnh
    sample_edge = list(G_base.edges(keys=True, data=True))[0]
    u, v, k, data = sample_edge
    if 'geometry' in data and data['geometry'] is not None:
        print(f"   Cạnh mẫu có geometry gồm {len(data['geometry'].coords)} điểm.")
    else:
        print("   Cạnh mẫu không có geometry.")

    print("Dữ liệu bản đồ đã được tải thành công.")
    return G_base
