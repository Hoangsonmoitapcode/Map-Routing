# src/services/pathfinding_service.py
import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge

from . import map_data_service, weight_service
from src.app.schemas.route_input_format import RouteRequest


def find_smart_route(G_modified: nx.MultiDiGraph, start_node_id: int, end_node_id: int) -> dict:
    try:
        path = nx.astar_path(G_modified, source=start_node_id, target=end_node_id, weight='weight')
        return {"path": path}
    except nx.NetworkXNoPath:
        return {"error": f"no path found between {start_node_id} and {end_node_id}"}


def _prepare_dynamic_subgraph(request: RouteRequest, G_base: nx.MultiDiGraph) -> nx.MultiDiGraph | None:
    if not G_base or not G_base.nodes:
        return None

    # Extract flood and ban areas from blocking_geometries based on type
    flood_areas = []
    ban_areas = []
    
    if hasattr(request, 'flood_areas') and request.flood_areas:
        flood_areas = request.flood_areas
    if hasattr(request, 'ban_areas') and request.ban_areas:
        ban_areas = request.ban_areas
    
    # Legacy support: treat blocking_geometries as ban areas
    if request.blocking_geometries:
        ban_areas.extend(request.blocking_geometries)

    G_dynamic, _ = weight_service.apply_dynamic_weights(
        G_base,
        request.blocking_geometries,
        None,
        flood_areas,
        ban_areas
    )
    return G_dynamic


def find_standard_route(request: RouteRequest, G_base: nx.MultiDiGraph) -> dict:
    G_dynamic = _prepare_dynamic_subgraph(request, G_base)
    if G_dynamic is None:
        return {"error": "không thể chuẩn bị đồ thị cho việc tìm đường."}

    start_point = request.start_point
    end_point = request.end_point

    try:
        start_node_id = map_data_service.find_nearest_node(G_dynamic, start_point.lat, start_point.lon)
        end_node_id = map_data_service.find_nearest_node(G_dynamic, end_point.lat, end_point.lon)
    except ValueError as e:
        return {"error": str(e)}

    if start_node_id == end_node_id:
        return {"error": "hai điểm quá gần nhau, vui lòng chọn điểm xa hơn"}

    try:
        path_nodes = nx.astar_path(G_dynamic, source=start_node_id, target=end_node_id, weight='weight')
    except nx.NetworkXNoPath:
        return {"error": "không tìm thấy đường đi giữa hai điểm đã chọn."}
    except Exception as e:
        return {"error": f"lỗi khi chạy a*: {e}"}

    path_edges = ox.utils_graph.get_route_edge_attributes(G_dynamic, path_nodes)
    total_distance = sum(edge.get('length', 0) for edge in path_edges)
    # Use weight for duration calculation (weight represents travel time in seconds)
    total_duration_sec = sum(edge.get('weight', edge.get('travel_time', 0)) for edge in path_edges)

    geometries = []
    for i in range(len(path_nodes) - 1):
        u, v = path_nodes[i], path_nodes[i + 1]
        edge_data = G_dynamic.get_edge_data(u, v)
        if edge_data:
            first_key = list(edge_data.keys())[0]
            data = edge_data[first_key]
            if 'geometry' in data and data['geometry'] is not None:
                geometries.append(data['geometry'])
            else:
                u_node = G_dynamic.nodes[u]
                v_node = G_dynamic.nodes[v]
                geom = LineString([(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])])
                geometries.append(geom)

    if not geometries:
        return {"error": "không thể tạo geometry cho đường đi"}

    try:
        merged = linemerge(geometries)
        path_geometry = merged if not merged.is_empty else MultiLineString(geometries)
    except Exception:
        path_geometry = MultiLineString(geometries)

    return {
        "message": "standard route found successfully",
        "distance": total_distance,
        "duration": total_duration_sec / 60,
        "route": {
            "type": "Feature",
            "properties": {},
            "geometry": path_geometry.__geo_interface__
        },
        "path": path_nodes
    }
