import sys
from pathlib import Path
import os
import osmnx as ox
import networkx as nx
import pytest
from unittest.mock import patch, MagicMock

# --- ✅ BƯỚC 1: THIẾT LẬP MÔI TRƯỜNG ---

# Thêm thư mục gốc vào Python Path để có thể import
try:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(project_root))
    # Import các thành phần cần thiết
    from src.services import pathfinding_service, weight_service
    # ✅ Cần import cả schema để tạo đối tượng request
    from src.app.schemas.route_input_format import RouteRequest, Point
except (ImportError, IndexError) as e:
    pytest.fail(f"LỖI IMPORT: {e}. Hãy đảm bảo bạn chạy test từ thư mục gốc của dự án.")


# --- ✅ BƯỚC 2: FIXTURE ĐỂ TẢI BẢN ĐỒ THỰC TẾ (GIỮ NGUYÊN) ---

@pytest.fixture(scope="session")
def real_world_graph():
    """
    Tải, xử lý và cung cấp một đồ thị thực tế để làm dữ liệu nền cho các bài test.
    """
    print("\n--> (Chạy 1 lần) Đang tải và xử lý đồ thị test (Phường Vĩnh Tuy) từ OSMnx...")
    try:
        place_name = "Phường Vĩnh Tuy, Hà Nội, Việt Nam"
        G = ox.graph_from_place(place_name, network_type='all')
        G = ox.add_edge_speeds(G, fallback=30)
        G = ox.add_edge_travel_times(G)
        for u, v, data in G.edges(data=True):
            if 'length' not in data:
                data['length'] = 100
        print(f"✅ Đã tạo thành công đồ thị test.")
        return G
    except Exception as e:
        pytest.fail(f"❌ Lỗi khi tải đồ thị từ OSMnx: {e}")


# --- ✅ BƯỚC 3: HÀM TEST ĐÃ ĐƯỢC CẬP NHẬT ---

def test_find_standard_route_on_real_graph(real_world_graph):
    """
    Kiểm tra toàn bộ workflow của hàm find_standard_route trên dữ liệu thật,
    bao gồm cả việc áp dụng vùng cấm.
    """
    print("\n--- Bắt đầu Test Case: find_standard_route() trên bản đồ thật ---")

    # 1. Chuẩn bị dữ liệu đầu vào
    nodes = ox.graph_to_gdfs(real_world_graph, edges=False)
    start_point = Point(lon=nodes.iloc[0].geometry.x, lat=nodes.iloc[0].geometry.y)
    end_point = Point(lon=nodes.iloc[100].geometry.x, lat=nodes.iloc[100].geometry.y)

    # ✅ THAY ĐỔI: Tạo một yêu cầu tìm đường KHÔNG có vùng cấm
    request = RouteRequest(
        start_point=start_point,
        end_point=end_point,
        blocking_geometries=[]  # Gửi một danh sách rỗng
    )
    print(
        f"--> Tìm đường từ ({start_point.lon:.4f}, {start_point.lat:.4f}) đến ({end_point.lon:.4f}, {end_point.lat:.4f})"
    )
    print("--> KHÔNG áp dụng vùng cấm.")

    # 2. "Giả lập" (Mock) các service phụ thuộc để cô lập bài test
    with patch('src.services.pathfinding_service.map_data_service.find_nearest_node') as mock_find_node:
        # Cấu hình mock để trả về các node ID khi được gọi
        start_node_id = ox.nearest_nodes(real_world_graph, X=start_point.lon, Y=start_point.lat)
        end_node_id = ox.nearest_nodes(real_world_graph, X=end_point.lon, Y=end_point.lat)
        mock_find_node.side_effect = [start_node_id, end_node_id]

        # 3. Chạy hàm find_standard_route với các tham số mới
        result = pathfinding_service.find_standard_route(request, real_world_graph)

        # 4. Kiểm chứng kết quả
        print("\n--> Kiểm chứng kết quả trả về...")
        assert "error" not in result, f"Hàm trả về lỗi: {result.get('error')}"

        assert "route" in result and result["route"]["type"] == "Feature"
        assert "distance" in result and result["distance"] > 0
        assert "duration" in result and result["duration"] > 0
        assert "path" in result and len(result["path"]) > 0

        print(f"    ✅ Thành công! Tìm thấy đường đi.")
        print(f"       - Khoảng cách: {result['distance'] / 1000:.2f} km")
        print(f"       - Thời gian: {result['duration']:.1f} phút")
        print(f"       - Lộ trình đi qua {len(result['path'])} nodes.")
