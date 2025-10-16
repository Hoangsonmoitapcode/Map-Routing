import pytest
import networkx as nx
from unittest.mock import Mock, patch, MagicMock
from shapely.geometry import Point as ShapelyPoint, Polygon

from src.services.pathfinding_service import (
    find_standard_route,
    find_smart_route,
    _prepare_dynamic_subgraph
)
from src.app.schemas.route_input_format import RouteRequest, Point  # ✅ Đổi từ Coordinate thành Point


# ======================================================================
# FIXTURES - Tạo dữ liệu test
# ======================================================================

@pytest.fixture
def sample_graph():
    """Tạo một đồ thị mẫu đơn giản để test"""
    G = nx.MultiDiGraph()

    # Thêm nodes với tọa độ
    nodes = [
        (1, {"y": 21.0, "x": 105.0}),
        (2, {"y": 21.01, "x": 105.01}),
        (3, {"y": 21.02, "x": 105.02}),
        (4, {"y": 21.03, "x": 105.03}),
    ]
    G.add_nodes_from(nodes)

    # Thêm edges với các thuộc tính
    edges = [
        (1, 2, {"length": 1000, "travel_time": 60, "weight": 1.0}),
        (2, 3, {"length": 1500, "travel_time": 90, "weight": 1.5}),
        (3, 4, {"length": 1200, "travel_time": 72, "weight": 1.2}),
        (1, 3, {"length": 2000, "travel_time": 120, "weight": 2.0}),  # Đường tắt
    ]
    G.add_edges_from(edges)

    return G


@pytest.fixture
def sample_route_request():
    """Tạo một route request mẫu"""
    return RouteRequest(
        start_point=Point(lat=21.0, lon=105.0),  # ✅ Sửa thành Point
        end_point=Point(lat=21.03, lon=105.03),  # ✅ Sửa thành Point
        blocking_geometries=[]  # ✅ Đổi None thành [] vì default là []
    )


@pytest.fixture
def sample_route_request_with_blocking():
    """Tạo route request có vùng cấm"""
    blocking_polygon = {
        "type": "Polygon",
        "coordinates": [[[105.005, 21.005], [105.015, 21.005],
                         [105.015, 21.015], [105.005, 21.015],
                         [105.005, 21.005]]]
    }

    return RouteRequest(
        start_point=Point(lat=21.0, lon=105.0),  # ✅ Sửa thành Point
        end_point=Point(lat=21.03, lon=105.03),  # ✅ Sửa thành Point
        blocking_geometries=[blocking_polygon]
    )


# ======================================================================
# TEST: find_smart_route
# ======================================================================

def test_find_smart_route_success(sample_graph):
    """Test tìm đường thông minh thành công"""
    result = find_smart_route(sample_graph, start_node_id=1, end_node_id=4)

    assert "path" in result
    assert isinstance(result["path"], list)
    assert result["path"][0] == 1
    assert result["path"][-1] == 4


def test_find_smart_route_no_path(sample_graph):
    """Test khi không tìm thấy đường đi"""
    # Thêm node bị cô lập
    sample_graph.add_node(999, y=21.99, x=105.99)

    result = find_smart_route(sample_graph, start_node_id=1, end_node_id=999)

    assert "error" in result
    assert "No path found" in result["error"]


def test_find_smart_route_invalid_nodes(sample_graph):
    """Test với node không tồn tại"""
    with pytest.raises(nx.NodeNotFound):
        find_smart_route(sample_graph, start_node_id=1, end_node_id=9999)


# ======================================================================
# TEST: _prepare_dynamic_subgraph
# ======================================================================

@patch('src.services.pathfinding_service.weight_service.apply_dynamic_weights')
def test_prepare_dynamic_subgraph_success(mock_apply_weights, sample_graph, sample_route_request):
    """Test chuẩn bị subgraph thành công"""
    # Mock weight_service trả về graph đã modify
    mock_apply_weights.return_value = (sample_graph, None)

    result = _prepare_dynamic_subgraph(sample_route_request, sample_graph)

    assert result is not None
    assert isinstance(result, nx.MultiDiGraph)
    mock_apply_weights.assert_called_once()


@patch('src.services.pathfinding_service.weight_service.apply_dynamic_weights')
def test_prepare_dynamic_subgraph_with_blocking(
        mock_apply_weights,
        sample_graph,
        sample_route_request_with_blocking
):
    """Test chuẩn bị subgraph với vùng cấm"""
    mock_apply_weights.return_value = (sample_graph, None)

    result = _prepare_dynamic_subgraph(sample_route_request_with_blocking, sample_graph)

    assert result is not None
    # Verify blocking_geometries được truyền vào
    call_args = mock_apply_weights.call_args
    assert call_args[0][1] is not None  # blocking_geometries
    assert call_args[0][2] is None  # flood_model


def test_prepare_dynamic_subgraph_empty_graph(sample_route_request):
    """Test với đồ thị rỗng"""
    empty_graph = nx.MultiDiGraph()

    result = _prepare_dynamic_subgraph(sample_route_request, empty_graph)

    assert result is None


def test_prepare_dynamic_subgraph_none_graph(sample_route_request):
    """Test với đồ thị None"""
    result = _prepare_dynamic_subgraph(sample_route_request, None)

    assert result is None


# ======================================================================
# TEST: find_standard_route (Integration test)
# ======================================================================

@patch('src.services.pathfinding_service.map_data_service.find_nearest_node')
@patch('src.services.pathfinding_service.weight_service.apply_dynamic_weights')
@patch('src.services.pathfinding_service.ox.utils_graph.get_route_edge_attributes')
@patch('src.services.pathfinding_service.ox.graph_to_gdfs')
def test_find_standard_route_success(
        mock_graph_to_gdfs,
        mock_get_route_edges,
        mock_apply_weights,
        mock_find_nearest,
        sample_graph,
        sample_route_request
):
    """Test tìm đường tiêu chuẩn thành công"""
    # Setup mocks
    mock_apply_weights.return_value = (sample_graph, None)
    mock_find_nearest.side_effect = [1, 4]  # start_node, end_node

    # Mock edge attributes
    mock_get_route_edges.return_value = [
        {"length": 1000, "travel_time": 60},
        {"length": 1200, "travel_time": 72}
    ]

    # Mock GeoDataFrame
    mock_gdf = MagicMock()
    mock_gdf.unary_union.__geo_interface__ = {
        "type": "LineString",
        "coordinates": [[105.0, 21.0], [105.03, 21.03]]
    }
    mock_graph_to_gdfs.return_value = mock_gdf

    # Execute
    result = find_standard_route(sample_route_request, sample_graph)

    # Assertions
    assert "message" in result
    assert result["message"] == "Standard route found successfully!"
    assert "distance" in result
    assert "duration" in result
    assert "route" in result
    assert result["distance"] == 2200  # 1000 + 1200
    assert result["duration"] == 2.2  # (60 + 72) / 60 minutes


@patch('src.services.pathfinding_service.map_data_service.find_nearest_node')
@patch('src.services.pathfinding_service.weight_service.apply_dynamic_weights')
def test_find_standard_route_no_path(
        mock_apply_weights,
        mock_find_nearest,
        sample_graph,
        sample_route_request
):
    """Test khi không tìm thấy đường đi"""
    # Tạo graph không có đường đi
    G_isolated = nx.MultiDiGraph()
    G_isolated.add_nodes_from([(1, {"y": 21.0, "x": 105.0}),
                               (999, {"y": 21.99, "x": 105.99})])

    mock_apply_weights.return_value = (G_isolated, None)
    mock_find_nearest.side_effect = [1, 999]

    result = find_standard_route(sample_route_request, G_isolated)

    assert "error" in result
    assert "Không tìm thấy đường đi" in result["error"]


@patch('src.services.pathfinding_service.weight_service.apply_dynamic_weights')
def test_find_standard_route_graph_preparation_failed(
        mock_apply_weights,
        sample_route_request
):
    """Test khi không thể chuẩn bị đồ thị"""
    empty_graph = nx.MultiDiGraph()

    result = find_standard_route(sample_route_request, empty_graph)

    assert "error" in result
    assert "Không thể chuẩn bị đồ thị" in result["error"]


@patch('src.services.pathfinding_service.map_data_service.find_nearest_node')
@patch('src.services.pathfinding_service.weight_service.apply_dynamic_weights')
def test_find_standard_route_astar_exception(
        mock_apply_weights,
        mock_find_nearest,
        sample_graph,
        sample_route_request
):
    """Test khi A* gặp exception không mong muốn"""
    mock_apply_weights.return_value = (sample_graph, None)
    mock_find_nearest.side_effect = [1, 4]

    # Mock nx.astar_path để raise exception
    with patch('src.services.pathfinding_service.nx.astar_path') as mock_astar:
        mock_astar.side_effect = Exception("Unexpected error")

        result = find_standard_route(sample_route_request, sample_graph)

        assert "error" in result
        assert "Lỗi khi chạy A*" in result["error"]


# ======================================================================
# TEST: Edge cases
# ======================================================================

def test_find_standard_route_same_start_end(sample_graph):
    """Test khi điểm đầu và điểm cuối giống nhau"""
    request = RouteRequest(
        start_point=Point(lat=21.0, lon=105.0),  # ✅ Sửa thành Point
        end_point=Point(lat=21.0, lon=105.0),  # ✅ Sửa thành Point
        blocking_geometries=[]
    )

    with patch('src.services.pathfinding_service.map_data_service.find_nearest_node') as mock_find:
        with patch('src.services.pathfinding_service.weight_service.apply_dynamic_weights') as mock_weights:
            mock_weights.return_value = (sample_graph, None)
            mock_find.return_value = 1  # Cùng node

            with patch('src.services.pathfinding_service.nx.astar_path') as mock_astar:
                mock_astar.return_value = [1]  # Path chỉ có 1 node

                with patch('src.services.pathfinding_service.ox.utils_graph.get_route_edge_attributes') as mock_edges:
                    mock_edges.return_value = []  # Không có edge

                    with patch('src.services.pathfinding_service.ox.graph_to_gdfs') as mock_gdf:
                        mock_gdf_obj = MagicMock()
                        mock_gdf_obj.unary_union.__geo_interface__ = {
                            "type": "Point",
                            "coordinates": [105.0, 21.0]
                        }
                        mock_gdf.return_value = mock_gdf_obj

                        result = find_standard_route(request, sample_graph)

                        assert "distance" in result
                        assert result["distance"] == 0


# ======================================================================
# TEST: Performance & Stress
# ======================================================================

def test_find_standard_route_large_graph():
    """Test với đồ thị lớn (stress test)"""
    # Tạo đồ thị lớn hơn
    G = nx.grid_2d_graph(10, 10)
    G = nx.MultiDiGraph(G)

    # Thêm coordinates cho các nodes
    for node in G.nodes():
        G.nodes[node]['x'] = 105.0 + node[0] * 0.001
        G.nodes[node]['y'] = 21.0 + node[1] * 0.001

    # Thêm attributes cho edges
    for u, v in G.edges():
        G[u][v][0]['length'] = 100
        G[u][v][0]['travel_time'] = 10
        G[u][v][0]['weight'] = 1.0

    request = RouteRequest(
        start_point=Point(lat=21.0, lon=105.0),  # ✅ Sửa thành Point
        end_point=Point(lat=21.009, lon=105.009),  # ✅ Sửa thành Point
        blocking_geometries=[]
    )

    with patch('src.services.pathfinding_service.map_data_service.find_nearest_node') as mock_find:
        with patch('src.services.pathfinding_service.weight_service.apply_dynamic_weights') as mock_weights:
            mock_weights.return_value = (G, None)
            mock_find.side_effect = [(0, 0), (9, 9)]

            with patch('src.services.pathfinding_service.ox.utils_graph.get_route_edge_attributes') as mock_edges:
                mock_edges.return_value = [{"length": 100, "travel_time": 10}] * 18

                with patch('src.services.pathfinding_service.ox.graph_to_gdfs') as mock_gdf:
                    mock_gdf_obj = MagicMock()
                    mock_gdf_obj.unary_union.__geo_interface__ = {
                        "type": "LineString",
                        "coordinates": [[105.0, 21.0], [105.009, 21.009]]
                    }
                    mock_gdf.return_value = mock_gdf_obj

                    result = find_standard_route(request, G)

                    assert "message" in result
                    assert result["distance"] == 1800  # 18 edges * 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])