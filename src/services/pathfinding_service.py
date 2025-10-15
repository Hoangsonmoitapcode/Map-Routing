import networkx as nx
import osmnx as ox
import geopandas as gpd

# Import các service và schema cần thiết
from . import map_data_service, weight_service
from src.app.schemas.route_input_format import RouteRequest


# ======================================================================
# HÀM FIND_SMART_ROUTE (GIỮ NGUYÊN ĐỂ PHÁT TRIỂN SAU)
# ======================================================================

def find_smart_route(G_modified: nx.MultiDiGraph, start_node_id: int, end_node_id: int) -> dict:
    """
   Tìm đường THÔNG MINH trên graph đã được modify bởi weight_service, sử dụng trọng số 'weight'.
   """
    try:
        path = nx.astar_path(G_modified, source=start_node_id, target=end_node_id, weight='weight')
        return {"path": path}
    except nx.NetworkXNoPath:
        return {"error": f"No path found between {start_node_id} and {end_node_id}"}


# ======================================================================
# CÁC HÀM NỘI BỘ ("PRIVATE") ĐỂ CHUẨN BỊ ĐỒ THỊ
# ======================================================================

def _calculate_bbox_for_request(request: RouteRequest, buffer: float = 0.01):
    """
    Hàm nội bộ để tính toán bounding box bao quanh tất cả các điểm và hình học.
    """
    points = [request.start_point, request.end_point]
    min_lon = min(p.lon for p in points)
    min_lat = min(p.lat for p in points)
    max_lon = max(p.lon for p in points)
    max_lat = max(p.lat for p in points)

    if request.blocking_geometries:
        gdf = gpd.GeoDataFrame.from_features([
            {"type": "Feature", "geometry": geom, "properties": {}}
            for geom in request.blocking_geometries
        ])
        geom_bounds = gdf.total_bounds
        min_lon = min(min_lon, geom_bounds[0])
        min_lat = min(min_lat, geom_bounds[1])
        max_lon = max(max_lon, geom_bounds[2])
        max_lat = max(max_lat, geom_bounds[3])

    return (min_lon - buffer, min_lat - buffer, max_lon + buffer, max_lat + buffer)


def _prepare_dynamic_subgraph(request: RouteRequest) -> nx.MultiDiGraph | None:
    """
    ✅ HÀM MỚI: Chịu trách nhiệm cho toàn bộ logic tạo và tối ưu subgraph.
    Bao gồm: tính bbox, tải từ DB, và áp dụng các điều kiện cấm/ngập.
    """
    # BƯỚC 1: TÍNH TOÁN VÙNG QUAN TÂM (BOUNDING BOX)
    print("1. Tính toán Bounding Box cho yêu cầu...")
    bbox = _calculate_bbox_for_request(request)

    # BƯỚC 2: TẢI ĐỒ THỊ CON (SUBGRAPH) TỪ DATABASE
    print("2. Tải Subgraph từ database...")
    G_subgraph = map_data_service.get_subgraph_from_bbox(bbox)
    if not G_subgraph.nodes:
        print("   -> Lỗi: Không tìm thấy dữ liệu bản đồ trong khu vực yêu cầu.")
        return None
    print(f"   -> Đã tải Subgraph với {len(G_subgraph.nodes)} nodes và {len(G_subgraph.edges)} edges.")

    # BƯỚC 3: ÁP DỤNG CÁC ĐIỀU KIỆN CẤM/NGẬP
    print("3. Áp dụng các điều kiện động (vùng cấm, ngập)...")
    # Gọi weight_service nhưng không truyền flood_model
    G_dynamic, _ = weight_service.apply_dynamic_weights(
        G_subgraph,
        request.blocking_geometries,
        None  # Bỏ qua phần AI
    )
    return G_dynamic


# ======================================================================
# HÀM FIND_STANDARD_ROUTE (ĐÃ ĐƯỢC TỐI ƯU HÓA HOÀN CHỈNH)
# ======================================================================

def find_standard_route(request: RouteRequest) -> dict:
    """
    Workflow tìm đường tiêu chuẩn hoàn chỉnh và được tối ưu hóa.
    Đây là hàm chính được gọi bởi API endpoint.
    """
    print("\n--- BẮT ĐẦU QUY TRÌNH TÌM ĐƯỜNG TIÊU CHUẨN ---")

    # ✅ THAY ĐỔI: Gọi hàm helper để chuẩn bị đồ thị
    G_dynamic = _prepare_dynamic_subgraph(request)
    if G_dynamic is None:
        return {"error": "Không thể chuẩn bị đồ thị cho việc tìm đường."}

    start_point = request.start_point
    end_point = request.end_point

    # BƯỚC 4: TÌM NODE GẦN NHẤT TRÊN ĐỒ THỊ (LAST MILE)
    print("4. Tìm các node bắt đầu/kết thúc trên đồ thị...")
    start_node_id = map_data_service.find_nearest_node(G_dynamic, start_point.lat, start_point.lon)
    end_node_id = map_data_service.find_nearest_node(G_dynamic, end_point.lat, end_point.lon)
    print(f"   -> Đi từ node {start_node_id} đến {end_node_id}.")

    # BƯỚC 5: CHẠY THUẬT TOÁN A* TRÊN ĐỒ THỊ CON
    print("5. Chạy thuật toán A* để tìm đường tiêu chuẩn...")
    try:
        path_nodes = nx.astar_path(G_dynamic, source=start_node_id, target=end_node_id, weight='travel_time')
    except nx.NetworkXNoPath:
        return {"error": "Không tìm thấy đường đi giữa hai điểm đã chọn."}
    except Exception as e:
        return {"error": f"Lỗi khi chạy A*: {e}"}
    print("   -> Đã tìm thấy đường đi.")

    # BƯỚC 6: ĐỊNH DẠNG KẾT QUẢ TRẢ VỀ
    print("6. Định dạng kết quả cuối cùng...")
    path_edges = ox.utils_graph.get_route_edge_attributes(G_dynamic, path_nodes)
    total_distance = sum(edge.get('length', 0) for edge in path_edges)
    total_duration_sec = sum(edge.get('travel_time', 0) for edge in path_edges)
    path_gdf = ox.graph_to_gdfs(G_dynamic.subgraph(path_nodes), nodes=False)
    path_geometry = path_gdf.unary_union

    final_result = {
        "message": "Standard route found successfully!",
        "distance": total_distance,
        "duration": total_duration_sec / 60,  # Đổi sang phút
        "route": {
            "type": "Feature",
            "properties": {},
            "geometry": path_geometry.__geo_interface__
        }
    }

    print("--- KẾT THÚC QUY TRÌNH ---")
    return final_result

