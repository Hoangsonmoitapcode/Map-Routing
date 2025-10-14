import networkx as nx
from .weather_service import predict_flood


def find_smart_route(G_base, flood_model, start_node_id: int, end_node_id: int):
    """Find smart api with flood prediction"""
    is_flooded_prediction = predict_flood(flood_model)

    G_dynamic = G_base.copy()

    if is_flooded_prediction == 1:
        print("AI predicts flooding. Increasing travel costs...")
        for u, v, data in G_dynamic.edges(data=True):
            data['weight'] = data['length'] * 10
    else:
        print("Weather is clear. Using standard travel costs.")
        for u, v, data in G_dynamic.edges(data=True):
            data['weight'] = data['length']

    try:
        path = nx.astar_path(G_dynamic, source=start_node_id, target=end_node_id, weight='weight')
        return {
            "message": "Smart api found!",
            "is_flooded_predicted": bool(is_flooded_prediction),
            "path": path
        }
    except nx.NetworkXNoPath:
        return {"error": f"No path found between {start_node_id} and {end_node_id}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}


def find_standard_route(G_base, start_node_id: int, end_node_id: int):
    """Find the standard shortest path using pre-calculated travel_time."""

    # Không cần dự báo thời tiết, không cần copy đồ thị
    # Sử dụng trực tiếp trọng số 'travel_time' bạn đã tính toán khi nạp dữ liệu
    print("Finding standard route using 'travel_time' weight.")

    try:
        # Chạy A* với trọng số là 'travel_time'
        path = nx.astar_path(G_base, source=start_node_id, target=end_node_id, weight='travel_time')
        return {
            "message": "Standard route found!",
            "path": path
        }
    except nx.NetworkXNoPath:
        return {"error": f"No path found between {start_node_id} and {end_node_id}"}
    except Exception as e:
        return {"error": f"An error occurred: {e}"}
