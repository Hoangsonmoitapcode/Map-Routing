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
# Các hàm tiện ích phục vụ xử lý bản đồ và định tuyến
# ======================================================================

def get_subgraph_from_bbox(bbox: tuple) -> nx.MultiDiGraph:
    """
    Tải một phần đồ thị (nodes, edges) từ PostGIS dựa trên bounding box.
    bbox: (min_lon, min_lat, max_lon, max_lat)
    """
    bbox_polygon = box(*bbox)
    bbox_wkt = bbox_polygon.wkt

    nodes_sql = """
        SELECT * FROM nodes 
        WHERE ST_Intersects(geometry, ST_GeomFromText(%(bbox_wkt)s, 4326));
    """
    edges_sql = """
        SELECT * FROM edges 
        WHERE ST_Intersects(geometry, ST_GeomFromText(%(bbox_wkt)s, 4326));
    """

    with engine.connect() as conn:
        nodes_gdf = gpd.read_postgis(
            nodes_sql, conn, params={"bbox_wkt": bbox_wkt},
            index_col='osmid', geom_col='geometry'
        )
        edges_gdf = gpd.read_postgis(
            edges_sql, conn, params={"bbox_wkt": bbox_wkt},
            index_col=['u', 'v', 'key'], geom_col='geometry'
        )

    if nodes_gdf.empty or edges_gdf.empty:
        return ox.MultiDiGraph()

    nodes_gdf.set_crs("EPSG:4326", inplace=True)
    edges_gdf.set_crs("EPSG:4326", inplace=True)

    return ox.graph_from_gdfs(nodes_gdf, edges_gdf)


def _graph_bounds(G: nx.MultiDiGraph) -> tuple:
    """
    Trả về (min_lat, min_lon, max_lat, max_lon) dựa trên thuộc tính node 'y' (lat) và 'x' (lon).
    """
    ys = [data.get('y') for _, data in G.nodes(data=True) if data.get('y') is not None]
    xs = [data.get('x') for _, data in G.nodes(data=True) if data.get('x') is not None]
    if not xs or not ys:
        return 0.0, 0.0, 0.0, 0.0
    return min(ys), min(xs), max(ys), max(xs)


def find_nearest_node(G: nx.MultiDiGraph, lat: float, lon: float) -> int:
    """
    Tìm osmid của node gần nhất với một cặp tọa độ (lat, lon) trong đồ thị G.
    """
    from geopy.distance import geodesic

    # 1) kiểm tra điểm đầu vào có nằm trong phạm vi đồ thị với padding nhỏ hay không
    min_lat, min_lon, max_lat, max_lon = _graph_bounds(G)
    padding_deg = 0.03  # ~2-3km quanh biên, tránh chặn sớm trước bước snap
    if not (
        (min_lat - padding_deg) <= lat <= (max_lat + padding_deg)
        and (min_lon - padding_deg) <= lon <= (max_lon + padding_deg)
    ):
        # Không chặn sớm; vẫn thử snap rồi kiểm tra khoảng cách thực tế
        pass

    # 2) tìm node gần nhất
    nearest_node_id = ox.nearest_nodes(G, X=lon, Y=lat)
    node_data = G.nodes[nearest_node_id]
    node_lat = node_data['y']
    node_lon = node_data['x']
    # Nếu toạ độ node không hợp lệ (do CRS/x,y bị đảo), thử hoán đổi
    if abs(node_lat) > 90 or abs(node_lon) > 180:
        node_lat, node_lon = node_lon, node_lat

    distance_km = geodesic((lat, lon), (node_lat, node_lon)).kilometers

    if distance_km > 4.0:
        raise ValueError(
            f"Địa chỉ nằm ngoài phạm vi cho phép (cách {distance_km:.1f} km). "
            f"Vui lòng chọn địa chỉ trong khu vực được hỗ trợ."
        )

    print(f"-> Node {nearest_node_id} cách điểm input {distance_km * 1000:.0f} m")
    return nearest_node_id


# ======================================================================
# Các hàm xử lý vùng cấm và truy vấn vùng bị ảnh hưởng
# ======================================================================

def _get_affected_edges_sql_clause(input_geojson: dict) -> tuple | None:
    """
    Xây dựng câu lệnh SQL và tham số lọc các cạnh (edges) bị ảnh hưởng
    bởi vùng hình học (geojson).
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
            "ST_DWithin(geometry::geography, "
            "ST_GeomFromText(:geom_wkt, 4326)::geography, :buffer)"
        )
        params["buffer"] = BUFFER_METERS_AROUND_POINT
    else:
        return None

    return sql_where_clause, params


def get_affected_edges_by_geometry(input_geojson: dict) -> dict | None:
    """
    Trả về GeoJSON của các edges bị ảnh hưởng (dùng để hiển thị preview).
    """
    clause_tuple = _get_affected_edges_sql_clause(input_geojson)
    if not clause_tuple:
        return None

    sql_where_clause, params = clause_tuple
    sql = text(f"""
        SELECT ST_AsGeoJSON(ST_Collect(geometry)) AS collected_geom
        FROM edges
        WHERE {sql_where_clause};
    """)

    with engine.connect() as conn:
        result = conn.execute(sql, params).scalar_one_or_none()

    return json.loads(result) if result else None


def get_affected_edge_ids(input_geojson: dict) -> list:
    """
    Trả về danh sách [(u, v, key), ...] của các edges bị ảnh hưởng.
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
        rows = conn.execute(sql, params).fetchall()

    return [(row.u, row.v, row.key) for row in rows]
