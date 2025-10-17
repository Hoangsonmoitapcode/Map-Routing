import networkx as nx
from typing import List, Dict, Any
from shapely.geometry import shape
import osmnx as ox
from .weather_service import predict_flood


def apply_dynamic_weights(
    G_base: nx.MultiDiGraph,
    blocking_geometries: List[Dict[str, Any]] = None,
    flood_model=None
) -> tuple:
    G_modified = G_base.copy()
    metadata = {"blocked_edges_count": 0, "is_flooded_predicted": False}

    if blocking_geometries:
        blocked_count = _apply_blocking_in_memory(G_modified, blocking_geometries)
        metadata["blocked_edges_count"] = blocked_count

    if flood_model:
        is_flooded = predict_flood(flood_model) == 1
        metadata["is_flooded_predicted"] = is_flooded
        weight_attribute = 'weight'

        for u, v, data in G_modified.edges(data=True):
            if is_flooded:
                data[weight_attribute] = data.get('length', 100) * 10
            else:
                data[weight_attribute] = data.get('length', 100)

    return G_modified, metadata


def _apply_blocking_in_memory(G: nx.MultiDiGraph, blocking_geometries: List[Dict]) -> int:
    total_affected = 0
    if not blocking_geometries:
        return 0

    edges_gdf = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
    if edges_gdf.empty:
        return 0

    for geom in blocking_geometries:
        geom_type = geom.get("type")
        blocking_shape = shape(geom)
        intersecting_edges_idx = edges_gdf.intersects(blocking_shape)
        intersecting_edges = edges_gdf[intersecting_edges_idx]

        for u, v, key in intersecting_edges.index:
            if G.has_edge(u, v, key):
                if geom_type in ["Polygon", "LineString"]:
                    G.remove_edge(u, v, key)
                    total_affected += 1

    return total_affected
