# tests/test_path_finding_api.py
import pytest
from unittest.mock import patch, MagicMock
import networkx as nx


# ✅ Mock dependencies với đúng import path
@pytest.fixture(scope="session", autouse=True)
def mock_dependencies():
    """Mock tất cả dependencies để test nhanh"""
    with patch('src.database.load_database.load_graph_from_db') as mock_graph_loader, \
            patch('src.app.models.models_loader.load_flood_model') as mock_model_loader:
        # Tạo mock graph
        G = nx.MultiDiGraph()
        G.add_nodes_from([
            (1, {"y": 21.0, "x": 105.0}),
            (2, {"y": 21.01, "x": 105.01}),
        ])
        G.add_edge(1, 2, length=1000, travel_time=60)

        mock_graph_loader.return_value = G
        mock_model_loader.return_value = None

        yield


@pytest.fixture
def client():
    """Tạo test client"""
    from fastapi.testclient import TestClient
    from main import app  # ✅ main.py ở folder gốc

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_graph():
    """Tạo mock graph"""
    G = nx.MultiDiGraph()
    G.add_nodes_from([
        (1, {"y": 21.0, "x": 105.0}),
        (2, {"y": 21.01, "x": 105.01}),
    ])
    G.add_edge(1, 2, length=1000, travel_time=60)
    return G


@pytest.fixture(autouse=True)
def setup_globals(mock_graph):
    """Setup global variables trước mỗi test"""
    from src.app.api import path_finding
    path_finding._G_base = mock_graph
    path_finding._flood_model = None
    yield
    path_finding._G_base = None
    path_finding._flood_model = None


# ======================================================================
# TEST: find_route_endpoint (Smart route - chưa implement)
# ======================================================================

def test_find_route_endpoint_not_implemented(client):
    """Test endpoint smart route trả về 501"""
    response = client.post(
        "/api/v1/routing/find-route",
        json={
            "start_point": {"lat": 21.0, "lon": 105.0},
            "end_point": {"lat": 21.01, "lon": 105.01},
            "blocking_geometries": []
        }
    )

    assert response.status_code == 501
    assert "chưa được implement" in response.json()["detail"]


# ======================================================================
# TEST: find_standard_route_endpoint
# ======================================================================

@patch('src.services.pathfinding_service.find_standard_route')
@patch('src.services.geocoding_service.get_coords_from_address')
def test_find_standard_route_success(
        mock_geocode,
        mock_pathfinding,
        client
):
    """Test tìm đường thành công"""
    # Mock geocoding
    mock_geocode.side_effect = [
        {"latitude": 21.0, "longitude": 105.0},
        {"latitude": 21.01, "longitude": 105.01}
    ]

    # Mock pathfinding
    mock_pathfinding.return_value = {
        "message": "Standard route found successfully!",
        "distance": 1500,
        "duration": 2.5,
        "route": {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[105.0, 21.0], [105.01, 21.01]]
            }
        }
    }

    # Request
    response = client.post(
        "/api/v1/routing/find-standard-route",
        params={
            "start_address": "Hoan Kiem, Hanoi",
            "end_address": "Ba Dinh, Hanoi"
        }
    )

    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["distance"] == 1500
    assert data["duration"] == 2.5


@patch('src.services.geocoding_service.get_coords_from_address')
def test_find_standard_route_graph_not_loaded(mock_geocode, client):
    """Test khi graph chưa được load"""
    from src.app.api import path_finding

    # Backup và set None
    original_graph = path_finding._G_base
    path_finding._G_base = None

    try:
        response = client.post(
            "/api/v1/routing/find-standard-route",
            params={
                "start_address": "Hoan Kiem",
                "end_address": "Ba Dinh"
            }
        )

        assert response.status_code == 500
        assert "Graph chưa được load" in response.json()["detail"]
    finally:
        # Restore
        path_finding._G_base = original_graph


@patch('src.services.pathfinding_service.find_standard_route')
@patch('src.services.geocoding_service.get_coords_from_address')
def test_find_standard_route_no_path_found(
        mock_geocode,
        mock_pathfinding,
        client
):
    """Test khi không tìm thấy đường"""
    mock_geocode.side_effect = [
        {"latitude": 21.0, "longitude": 105.0},
        {"latitude": 21.99, "longitude": 105.99}
    ]

    # Mock pathfinding trả về lỗi
    mock_pathfinding.return_value = {
        "error": "Không tìm thấy đường đi giữa hai điểm đã chọn."
    }

    response = client.post(
        "/api/v1/routing/find-standard-route",
        params={
            "start_address": "Hoan Kiem",
            "end_address": "Far Away Place"
        }
    )

    assert response.status_code == 404
    assert "Không tìm thấy đường đi" in response.json()["detail"]


@patch('src.services.geocoding_service.get_coords_from_address')
def test_find_standard_route_geocoding_failed(mock_geocode, client):
    """Test khi geocoding thất bại"""
    # Mock geocoding trả về None
    mock_geocode.return_value = None

    response = client.post(
        "/api/v1/routing/find-standard-route",
        params={
            "start_address": "Invalid Address",
            "end_address": "Another Invalid"
        }
    )

    assert response.status_code == 500
    assert "Lỗi" in response.json()["detail"]


# ======================================================================
# TEST CASE BỔ SUNG: Test với blocking_geometries
# ======================================================================

@patch('src.services.pathfinding_service.find_standard_route')
@patch('src.services.geocoding_service.get_coords_from_address')
def test_find_standard_route_with_blocking_geometries(
        mock_geocode,
        mock_pathfinding,
        client
):
    """Test tìm đường với vùng cấm"""
    mock_geocode.side_effect = [
        {"latitude": 21.0, "longitude": 105.0},
        {"latitude": 21.01, "longitude": 105.01}
    ]

    mock_pathfinding.return_value = {
        "message": "Route found with blocked areas avoided",
        "distance": 2000,
        "duration": 3.5,
        "route": {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[105.0, 21.0], [105.005, 21.005], [105.01, 21.01]]
            }
        }
    }

    blocking_geom = {
        "type": "Polygon",
        "coordinates": [[[105.0, 21.0], [105.01, 21.0], [105.01, 21.01], [105.0, 21.01], [105.0, 21.0]]]
    }

    response = client.post(
        "/api/v1/routing/find-standard-route",
        params={
            "start_address": "Hoan Kiem",
            "end_address": "Ba Dinh"
        },
        json={"blocking_geometries": [blocking_geom]}
    )

    assert response.status_code == 200
    assert response.json()["distance"] == 2000