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

# CÁC HÀM NỘI BỘ ĐỂ CHUẨN BỊ ĐỒ THỊ

def _prepare_dynamic_subgraph(request: RouteRequest, G_base: nx.MultiDiGraph) -> nx.MultiDiGraph | None:
    """
    ✅ HÀM ĐÃ TỐI ƯU: Sử dụng toàn bộ đồ thị từ database thay vì subgraph.
    Chỉ áp dụng các điều kiện cấm/ngập.
    """
    # BƯỚC 1: SỬ DỤNG TOÀN BỘ ĐỒ THỊ
    print("1. Sử dụng toàn bộ đồ thị từ database...")
    if not G_base or not G_base.nodes:
        print("   -> Lỗi: Đồ thị cơ sở không tồn tại.")
        return None
    print(f"   -> Đang sử dụng đồ thị với {len(G_base.nodes)} nodes và {len(G_base.edges)} edges.")

    # BƯỚC 2: ÁP DỤNG CÁC ĐIỀU KIỆN CẤM/NGẬP
    print("2. Áp dụng các điều kiện động (vùng cấm, ngập)...")
    G_dynamic, _ = weight_service.apply_dynamic_weights(
        G_base,
        request.blocking_geometries,
        None  # Bỏ qua phần AI
    )
    return G_dynamic

# HÀM FIND_STANDARD_ROUTE

def find_standard_route(request: RouteRequest, G_base: nx.MultiDiGraph) -> dict:
    """
    Workflow tìm đường tiêu chuẩn hoàn chỉnh và được tối ưu hóa.
    Đây là hàm chính được gọi bởi API endpoint.
    """
    print("\n--- BẮT ĐẦU QUY TRÌNH TÌM ĐƯỜNG TIÊU CHUẨN ---")

    # ✅ THAY ĐỔI: Truyền G_base vào
    G_dynamic = _prepare_dynamic_subgraph(request, G_base)
    if G_dynamic is None:
        return {"error": "Không thể chuẩn bị đồ thị cho việc tìm đường."}

    start_point = request.start_point
    end_point = request.end_point

    # BƯỚC 3: TÌM NODE GẦN NHẤT TRÊN ĐỒ THỊ (LAST MILE)
    print("3. Tìm các node bắt đầu/kết thúc trên đồ thị...")
    start_node_id = map_data_service.find_nearest_node(G_dynamic, start_point.lat, start_point.lon)
    end_node_id = map_data_service.find_nearest_node(G_dynamic, end_point.lat, end_point.lon)
    print(f"   -> Đi từ node {start_node_id} đến {end_node_id}.")

    # BƯỚC 4: CHẠY THUẬT TOÁN A* TRÊN ĐỒ THỊ
    print("4. Chạy thuật toán A* để tìm đường tiêu chuẩn...")
    try:
        path_nodes = nx.astar_path(G_dynamic, source=start_node_id, target=end_node_id, weight='travel_time')
    except nx.NetworkXNoPath:
        return {"error": "Không tìm thấy đường đi giữa hai điểm đã chọn."}
    except Exception as e:
        return {"error": f"Lỗi khi chạy A*: {e}"}
    print("   -> Đã tìm thấy đường đi.")

    # BƯỚC 5: ĐỊNH DẠNG KẾT QUẢ TRẢ VỀ
    print("5. Định dạng kết quả cuối cùng...")
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

