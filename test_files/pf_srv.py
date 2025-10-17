# tests/test_pathfinding_complete.py
import sys
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
import networkx as nx
import osmnx as ox

# ======================================================================
# SETUP ENVIRONMENT
# ======================================================================

try:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.append(str(project_root))

    from src.services import pathfinding_service, geocoding_service
    from src.app.schemas.route_input_format import RouteRequest, Point
except (ImportError, IndexError) as e:
    pytest.fail(f"LỖI IMPORT: {e}")


# ======================================================================
# MOCK DATABASE - Chạy trước khi import main.py
# ======================================================================

@pytest.fixture(scope="session", autouse=True)
def mock_database_for_api_tests():
    """Mock database loading để API tests không cần PostgreSQL thật"""
    with patch('src.database.load_database.load_graph_from_db') as mock_load_graph, \
            patch('src.app.models.models_loader.load_flood_model') as mock_load_model:
        # Tạo mock graph với geometry cho edges
        G_mock = nx.MultiDiGraph()
        G_mock.add_nodes_from([
            (1, {"y": 21.0, "x": 105.0}),
            (2, {"y": 21.01, "x": 105.01}),
        ])

        # ✅ QUAN TRỌNG: Thêm geometry cho edge để tránh lỗi khi format response
        from shapely.geometry import LineString
        G_mock.add_edge(
            1, 2,
            length=1000,
            travel_time=60,
            geometry=LineString([(105.0, 21.0), (105.01, 21.01)])
        )

        mock_load_graph.return_value = G_mock
        mock_load_model.return_value = None

        yield


# ======================================================================
# FIXTURES
# ======================================================================

@pytest.fixture(scope="session")
def real_world_graph():
    """Tải đồ thị thực tế từ OSMnx cho SERVICE tests"""
    print("\n🗺️  Đang tải đồ thị test (Phường Vĩnh Tuy, Hà Nội)...")
    try:
        place_name = "Phường Vĩnh Tuy, Hà Nội, Việt Nam"
        G = ox.graph_from_place(place_name, network_type='all')
        G = ox.add_edge_speeds(G, fallback=30)
        G = ox.add_edge_travel_times(G)

        for u, v, k, data in G.edges(keys=True, data=True):
            if 'length' not in data:
                data['length'] = 100
            # ✅ Đảm bảo có geometry
            if 'geometry' not in data:
                u_node = G.nodes[u]
                v_node = G.nodes[v]
                from shapely.geometry import LineString
                data['geometry'] = LineString([
                    (u_node['x'], u_node['y']),
                    (v_node['x'], v_node['y'])
                ])

        print(f"✅ Đã tải đồ thị: {len(G.nodes)} nodes, {len(G.edges)} edges")
        return G
    except Exception as e:
        pytest.fail(f"❌ Lỗi khi tải đồ thị: {e}")


@pytest.fixture
def sample_route_request(real_world_graph):
    """Tạo request mẫu từ đồ thị thực tế"""
    nodes = ox.graph_to_gdfs(real_world_graph, edges=False)

    start_point = Point(
        lon=nodes.iloc[0].geometry.x,
        lat=nodes.iloc[0].geometry.y
    )
    end_point = Point(
        lon=nodes.iloc[50].geometry.x,  # ✅ Giảm khoảng cách để test nhanh hơn
        lat=nodes.iloc[50].geometry.y
    )

    return RouteRequest(
        start_point=start_point,
        end_point=end_point,
        blocking_geometries=[]
    )


@pytest.fixture
def mock_api_client():
    """Tạo mock FastAPI test client"""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as client:
        yield client


# ======================================================================
# TEST 1: SERVICE LAYER - pathfinding_service.find_standard_route()
# ======================================================================

def test_service_find_standard_route(real_world_graph, sample_route_request):
    """Test service với real data"""
    print("\n" + "=" * 70)
    print("TEST 1: SERVICE LAYER - find_standard_route()")
    print("=" * 70)

    request = sample_route_request
    print(f"\n📍 Start: ({request.start_point.lon:.6f}, {request.start_point.lat:.6f})")
    print(f"📍 End: ({request.end_point.lon:.6f}, {request.end_point.lat:.6f})")

    with patch('src.services.pathfinding_service.map_data_service.find_nearest_node') as mock_find_node:
        start_node_id = ox.nearest_nodes(real_world_graph, X=request.start_point.lon, Y=request.start_point.lat)
        end_node_id = ox.nearest_nodes(real_world_graph, X=request.end_point.lon, Y=request.end_point.lat)
        mock_find_node.side_effect = [start_node_id, end_node_id]

        # Gọi service
        result = pathfinding_service.find_standard_route(request, real_world_graph)

        # Assertions
        assert "error" not in result, f"Service lỗi: {result.get('error')}"
        assert "route" in result
        assert "distance" in result and result["distance"] > 0
        assert "duration" in result and result["duration"] > 0
        assert "path" in result and len(result["path"]) > 0

        # Output
        print(f"\n✅ SERVICE TEST PASSED!")
        print(f"   📏 Distance: {result['distance']:.2f} m ({result['distance'] / 1000:.2f} km)")
        print(f"   ⏱️  Duration: {result['duration']:.2f} min")
        print(f"   🛣️  Nodes: {len(result['path'])}")
        print(f"   📍 Path: {result['path'][0]} → ... → {result['path'][-1]}")


# ======================================================================
# TEST 2: API LAYER - Mock Integration
# ======================================================================

def test_api_mock_integration(mock_api_client):
    """Test API với mock services"""
    print("\n" + "=" * 70)
    print("TEST 2: API LAYER - Mock Integration")
    print("=" * 70)

    with patch('src.services.geocoding_service.get_coords_from_address') as mock_geocode, \
            patch('src.services.pathfinding_service.find_standard_route') as mock_pathfinding:
        mock_geocode.side_effect = [
            {"latitude": 21.0, "longitude": 105.0},
            {"latitude": 21.01, "longitude": 105.01}
        ]

        mock_pathfinding.return_value = {
            "message": "Standard route found successfully!",
            "distance": 1500.5,
            "duration": 3.5,
            "route": {"type": "Feature",
                      "geometry": {"type": "LineString", "coordinates": [[105.0, 21.0], [105.01, 21.01]]}},
            "path": [1, 2, 3]
        }

        response = mock_api_client.post(
            "/api/v1/routing/find-standard-route",
            json={"start_address": "A", "end_address": "B", "blocking_geometries": []}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["distance"] == 1500.5

        print(f"\n✅ API MOCK TEST PASSED!")
        print(f"   📏 Distance: {data['distance']} m")


# ======================================================================
# TEST 3: FULL INTEGRATION - API → Service → Real Data
# ======================================================================

def test_full_integration(mock_api_client, real_world_graph):
    """✅ TEST QUAN TRỌNG: API gọi service thực với real data"""
    print("\n" + "=" * 70)
    print("TEST 3: FULL INTEGRATION - API → Service → Real Data")
    print("=" * 70)

    nodes = ox.graph_to_gdfs(real_world_graph, edges=False)
    start_node = nodes.iloc[0]
    end_node = nodes.iloc[50]

    with patch('src.services.geocoding_service.get_coords_from_address') as mock_geocode, \
            patch('src.app.api.path_finding._G_base', real_world_graph):
        mock_geocode.side_effect = [
            {"latitude": start_node.geometry.y, "longitude": start_node.geometry.x},
            {"latitude": end_node.geometry.y, "longitude": end_node.geometry.x}
        ]

        response = mock_api_client.post(
            "/api/v1/routing/find-standard-route",
            json={"start_address": "Test Start", "end_address": "Test End", "blocking_geometries": []}
        )

        assert response.status_code == 200, f"Failed: {response.json()}"
        data = response.json()

        assert "distance" in data and data["distance"] > 0
        assert "duration" in data and data["duration"] > 0
        assert "path" in data and len(data["path"]) > 0
        assert "route" in data

        print(f"\n✅ FULL INTEGRATION PASSED!")
        print(f"   📍 API → Service → A* → GeoJSON")
        print(f"   📏 Distance: {data['distance']:.2f} m ({data['distance'] / 1000:.2f} km)")
        print(f"   ⏱️  Duration: {data['duration']:.2f} min")
        print(f"   🛣️  Path: {len(data['path'])} nodes")


# ======================================================================
# TEST 4: ERROR HANDLING
# ======================================================================

def test_error_handling(mock_api_client):
    """Test xử lý lỗi"""
    print("\n" + "=" * 70)
    print("TEST 4: ERROR HANDLING")
    print("=" * 70)

    # Test 1: Graph not loaded
    with patch('src.app.api.path_finding._G_base', None):
        response = mock_api_client.post(
            "/api/v1/routing/find-standard-route",
            json={"start_address": "A", "end_address": "B"}
        )
        assert response.status_code == 500
        assert "Graph chưa được load" in response.json()["detail"]
        print("   ✅ Test 1: Graph not loaded - PASSED")

    # Test 2: Geocoding failed
    with patch('src.services.geocoding_service.get_coords_from_address', return_value=None), \
            patch('src.app.api.path_finding._G_base', MagicMock()):
        response = mock_api_client.post(
            "/api/v1/routing/find-standard-route",
            json={"start_address": "Invalid", "end_address": "Invalid"}
        )
        assert response.status_code == 400
        print("   ✅ Test 2: Geocoding failed - PASSED")

    # Test 3: No path found
    with patch('src.services.geocoding_service.get_coords_from_address') as mock_geocode, \
            patch('src.services.pathfinding_service.find_standard_route') as mock_pathfinding, \
            patch('src.app.api.path_finding._G_base', MagicMock()):
        mock_geocode.side_effect = [
            {"latitude": 21.0, "longitude": 105.0},
            {"latitude": 21.01, "longitude": 105.01}
        ]
        mock_pathfinding.return_value = {"error": "Không tìm thấy đường đi"}

        response = mock_api_client.post(
            "/api/v1/routing/find-standard-route",
            json={"start_address": "Start", "end_address": "End"}
        )
        assert response.status_code == 404
        print("   ✅ Test 3: No path found - PASSED")

    print("\n✅ ALL ERROR TESTS PASSED!")


# ======================================================================
# TEST 5: COMPATIBILITY CHECK
# ======================================================================

def test_service_api_compatibility(real_world_graph, sample_route_request, mock_api_client):
    """Test data contract giữa Service và API"""
    print("\n" + "=" * 70)
    print("TEST 5: SERVICE ↔ API COMPATIBILITY")
    print("=" * 70)

    # Part 1: Service output format
    print("\n📤 PART 1: Service output format")
    with patch('src.services.pathfinding_service.map_data_service.find_nearest_node') as mock_find_node:
        start_node = ox.nearest_nodes(real_world_graph, X=sample_route_request.start_point.lon,
                                      Y=sample_route_request.start_point.lat)
        end_node = ox.nearest_nodes(real_world_graph, X=sample_route_request.end_point.lon,
                                    Y=sample_route_request.end_point.lat)
        mock_find_node.side_effect = [start_node, end_node]

        result = pathfinding_service.find_standard_route(sample_route_request, real_world_graph)

        required_fields = ["message", "distance", "duration", "route", "path"]
        for field in required_fields:
            assert field in result, f"Missing field: {field}"

        print(f"   ✅ Service output complete: {list(result.keys())}")

    # Part 2: API input handling
    print("\n📥 PART 2: API input handling")
    with patch('src.services.geocoding_service.get_coords_from_address') as mock_geocode, \
            patch('src.services.pathfinding_service.find_standard_route') as mock_pathfinding:
        mock_geocode.side_effect = [
            {"latitude": 21.0, "longitude": 105.0},
            {"latitude": 21.01, "longitude": 105.01}
        ]

        def check_request(request: RouteRequest, G):
            assert hasattr(request, 'start_point') and hasattr(request, 'end_point')
            assert hasattr(request.start_point, 'lat') and hasattr(request.start_point, 'lon')
            print(f"   ✅ API creates correct RouteRequest")
            return {"message": "OK", "distance": 100, "duration": 1, "route": {}, "path": [1, 2]}

        mock_pathfinding.side_effect = check_request

        response = mock_api_client.post(
            "/api/v1/routing/find-standard-route",
            json={"start_address": "A", "end_address": "B", "blocking_geometries": []}
        )
        assert response.status_code == 200

    print("\n✅ COMPATIBILITY TEST PASSED!")


# ======================================================================
# TEST 6: DEBUG - Graph Coverage (Conditional)
# ======================================================================

@pytest.mark.skip(reason="Debug only - run manually when needed")
def test_debug_graph_coverage(real_world_graph):
    """Debug: Kiểm tra vùng phủ sóng của graph"""
    print("\n" + "=" * 70)
    print("TEST 6: DEBUG - Graph Coverage")
    print("=" * 70)

    nodes_gdf = ox.graph_to_gdfs(real_world_graph, edges=False)
    bounds = nodes_gdf.total_bounds

    print(f"\n📍 Graph Coverage:")
    print(f"   Lon: {bounds[0]:.6f} → {bounds[2]:.6f}")
    print(f"   Lat: {bounds[1]:.6f} → {bounds[3]:.6f}")

    test_coords = {
        "Lạc Trung": (21.003093, 105.8601711),
        "Trần Khát Chân": (21.006459, 105.863755),
    }

    print(f"\n📋 Address coverage:")
    for name, (lat, lon) in test_coords.items():
        in_bounds = (bounds[0] <= lon <= bounds[2] and bounds[1] <= lat <= bounds[3])
        print(f"   {name:20} {'✅ INSIDE' if in_bounds else '❌ OUTSIDE'}")


# ======================================================================
# RUN ALL TESTS
# ======================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])