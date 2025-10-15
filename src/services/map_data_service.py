# src/services/map_data_service.py
from sqlalchemy import text
import geopandas as gpd
import json
import osmnx as ox
import networkx as nx
from src.app.core.config import engine
from shapely.geometry import box

BUFFER_METERS_AROUND_POINT = 20.0


# ======================================================================
# ✅ THÊM MỚI: CÁC HÀM TIỆN ÍCH CHO VIỆC TÌM ĐƯỜNG
# ======================================================================

def get_subgraph_from_bbox(bbox: tuple) -> nx.MultiDiGraph:
    """
    Tải một phần đồ thị (nodes, edges) từ PostGIS dựa trên bounding box.
    Đây là hàm tối ưu hóa cốt lõi, chỉ lấy dữ liệu cần thiết.
    bbox: (min_lon, min_lat, max_lon, max_lat)
    """
    bbox_polygon = box(*bbox)
    bbox_wkt = bbox_polygon.wkt

    nodes_sql = "SELECT * FROM nodes WHERE ST_Intersects(geometry, ST_GeomFromText(%(bbox_wkt)s, 4326));"
    edges_sql = "SELECT * FROM edges WHERE ST_Intersects(geometry, ST_GeomFromText(%(bbox_wkt)s, 4326));"

    with engine.connect() as conn:
        # GeoPandas sẽ tự động xử lý các tham số một cách an toàn
        nodes_gdf = gpd.read_postgis(nodes_sql, conn, params={"bbox_wkt": bbox_wkt}, index_col='osmid',
                                     geom_col='geometry')
        edges_gdf = gpd.read_postgis(edges_sql, conn, params={"bbox_wkt": bbox_wkt}, index_col=['u', 'v', 'key'],
                                     geom_col='geometry')

    if nodes_gdf.empty or edges_gdf.empty:
        return ox.MultiDiGraph()

    # Đảm bảo hệ tọa độ được thiết lập đúng trước khi tạo graph
    nodes_gdf.set_crs("EPSG:4326", inplace=True)
    edges_gdf.set_crs("EPSG:4326", inplace=True)

    return ox.graph_from_gdfs(nodes_gdf, edges_gdf)


def find_nearest_node(G: nx.MultiDiGraph, lat: float, lon: float) -> int:
    """
    Tìm osmid của node gần nhất với một cặp tọa độ trên đồ thị G.
    """
    # OSMnx cung cấp hàm tiện lợi để thực hiện việc này
    return ox.nearest_nodes(G, X=lon, Y=lat)


# ======================================================================
# CÁC HÀM PHÂN TÍCH VÙNG CẤM (GIỮ NGUYÊN)
# ======================================================================

def _get_affected_edges_sql_clause(input_geojson: dict) -> tuple | None:
    """
    Hàm nội bộ để tái sử dụng logic xây dựng câu lệnh SQL và tham số.
    """
    geom_type = input_geojson.get("type")
    if not geom_type:
        return None

    try:
        gdf = gpd.GeoDataFrame.from_features([
            {"type": "Feature", "geometry": input_geojson, "properties": {}}
        ])
        geom_wkt = gdf.geometry.to_wkt().iloc[0]
    except Exception:
        return None

    params = {"geom_wkt": geom_wkt}

    if geom_type in ["Polygon", "LineString"]:
        sql_where_clause = "ST_Intersects(geometry, ST_GeomFromText(:geom_wkt, 4326))"
    elif geom_type == "Point":
        sql_where_clause = (
            "ST_DWithin("
            "    geometry::geography, "
            "    ST_GeomFromText(:geom_wkt, 4326)::geography, "
            "    :buffer"
            ")"
        )
        params["buffer"] = BUFFER_METERS_AROUND_POINT
    else:
        return None

    return sql_where_clause, params


def get_affected_edges_by_geometry(input_geojson: dict) -> dict | None:
    """Trả về GeoJSON của các edges bị ảnh hưởng (dùng cho preview)"""
    clause_tuple = _get_affected_edges_sql_clause(input_geojson)
    if not clause_tuple:
        return None

    sql_where_clause, params = clause_tuple
    sql = text(f"""
        SELECT ST_AsGeoJSON(ST_Collect(geometry)) as collected_geom
        FROM edges
        WHERE {sql_where_clause};
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, params).scalar_one_or_none()

    return json.loads(result) if result else None


def get_affected_edge_ids(input_geojson: dict) -> list:
    """
    Trả về list [(u, v, key), ...] của các edges bị ảnh hưởng.
    """
    clause_tuple = _get_affected_edges_sql_clause(input_geojson)
    if not clause_tuple:
        return []

    sql_where_clause, params = clause_tuple
    sql = text(f"""
        SELECT u, v, key
        FROM edges
        WHERE {sql_where_clause};
    """)

    with engine.connect() as conn:
        results = conn.execute(sql, params).fetchall()

    return [(row.u, row.v, row.key) for row in results]

