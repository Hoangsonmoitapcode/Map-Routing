from sqlalchemy import create_engine
import geopandas as gpd
import osmnx as ox
from src.app.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

def load_graph_from_db():
    """Load map data from database"""
    print("Loading map data from PostGIS...")
    nodes_gdf = gpd.read_postgis("SELECT * FROM nodes", engine, index_col='osmid', geom_col='geometry')
    edges_gdf = gpd.read_postgis("SELECT * FROM edges", engine, index_col=['u', 'v', 'key'], geom_col='geometry')
    G_base = ox.graph_from_gdfs(nodes_gdf, edges_gdf)
    print("Map data loaded.")
    return G_base