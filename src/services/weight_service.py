import networkx as nx
from typing import List, Dict, Any
from shapely.geometry import shape
import osmnx as ox
from .weather_service import predict_flood


def apply_dynamic_weights(
    G_base: nx.MultiDiGraph,
    blocking_geometries: List[Dict[str, Any]] = None,
    flood_model=None,
    flood_areas: List[Dict[str, Any]] = None,
    ban_areas: List[Dict[str, Any]] = None
) -> tuple:
    G_modified = G_base.copy()
    metadata = {
        "blocked_edges_count": 0, 
        "is_flooded_predicted": False,
        "flood_affected_edges": 0,
        "ban_affected_edges": 0
    }

    # Apply flood model prediction (global flood condition)
    if flood_model:
        is_flooded = predict_flood(flood_model) == 1
        metadata["is_flooded_predicted"] = is_flooded
        weight_attribute = 'weight'

        for u, v, data in G_modified.edges(data=True):
            if is_flooded:
                # Double the weight for flood conditions
                data[weight_attribute] = data.get('length', 100) * 2
            else:
                data[weight_attribute] = data.get('length', 100)

    # Apply flood areas (user-selected flood zones - double weight)
    if flood_areas:
        flood_count = _apply_flood_areas(G_modified, flood_areas)
        metadata["flood_affected_edges"] = flood_count

    # Apply ban areas (user-selected ban zones - infinite weight)
    if ban_areas:
        ban_count = _apply_ban_areas(G_modified, ban_areas)
        metadata["ban_affected_edges"] = ban_count

    # Legacy blocking geometries (treat as ban areas)
    if blocking_geometries:
        blocked_count = _apply_blocking_in_memory(G_modified, blocking_geometries)
        metadata["blocked_edges_count"] = blocked_count

    return G_modified, metadata


def _apply_blocking_in_memory(G: nx.MultiDiGraph, blocking_geometries: List[Dict]) -> int:
    total_affected = 0
    if not blocking_geometries:
        return 0

    edges_gdf = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
    if edges_gdf.empty:
        return 0

    for geom in blocking_geometries:
        try:
            # Xử lý cả hai format: GeoJSON Feature và Geometry object
            if "geometry" in geom:
                # Format: {"type": "Feature", "geometry": {...}, "properties": {...}}
                geom_data = geom["geometry"]
                geom_type = geom_data.get("type")
            else:
                # Format: {"type": "Polygon", "coordinates": [...]} (từ Draw plugin)
                geom_data = geom
                geom_type = geom.get("type")
            
            blocking_shape = shape(geom_data)
            intersecting_edges_idx = edges_gdf.intersects(blocking_shape)
            intersecting_edges = edges_gdf[intersecting_edges_idx]

            for u, v, key in intersecting_edges.index:
                if G.has_edge(u, v, key):
                    if geom_type in ["Polygon", "LineString"]:
                        G.remove_edge(u, v, key)
                        total_affected += 1
                        
        except Exception as e:
            print(f"Warning: Không thể xử lý geometry {geom}: {e}")
            continue

    return total_affected


def _apply_flood_areas(G: nx.MultiDiGraph, flood_areas: List[Dict]) -> int:
    """Apply flood areas by doubling edge weights (not blocking completely)"""
    total_affected = 0
    if not flood_areas:
        return 0

    edges_gdf = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
    if edges_gdf.empty:
        return 0

    for geom in flood_areas:
        try:
            # Handle both GeoJSON Feature and Geometry object formats
            if "geometry" in geom:
                geom_data = geom["geometry"]
            else:
                geom_data = geom
            
            flood_shape = shape(geom_data)
            intersecting_edges_idx = edges_gdf.intersects(flood_shape)
            intersecting_edges = edges_gdf[intersecting_edges_idx]

            for u, v, key in intersecting_edges.index:
                if G.has_edge(u, v, key):
                    # Double the weight instead of removing the edge
                    edge_data = G[u][v][key]
                    current_weight = edge_data.get('weight', edge_data.get('length', 100))
                    edge_data['weight'] = current_weight * 2
                    total_affected += 1
                        
        except Exception as e:
            print(f"Warning: Cannot process flood geometry {geom}: {e}")
            continue

    return total_affected


def _apply_ban_areas(G: nx.MultiDiGraph, ban_areas: List[Dict]) -> int:
    """Apply ban areas by removing edges completely"""
    total_affected = 0
    if not ban_areas:
        return 0

    edges_gdf = ox.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
    if edges_gdf.empty:
        return 0

    for geom in ban_areas:
        try:
            # Handle both GeoJSON Feature and Geometry object formats
            if "geometry" in geom:
                geom_data = geom["geometry"]
            else:
                geom_data = geom
            
            ban_shape = shape(geom_data)
            intersecting_edges_idx = edges_gdf.intersects(ban_shape)
            intersecting_edges = edges_gdf[intersecting_edges_idx]

            for u, v, key in intersecting_edges.index:
                if G.has_edge(u, v, key):
                    # Remove the edge completely
                    G.remove_edge(u, v, key)
                    total_affected += 1
                        
        except Exception as e:
            print(f"Warning: Cannot process ban geometry {geom}: {e}")
            continue

    return total_affected
