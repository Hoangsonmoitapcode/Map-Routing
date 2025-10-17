import osmnx as ox
import networkx as nx
from pathlib import Path
import time
import os


def create_graph_file():
    """Tải và lưu đồ thị giao thông 4 phường ở Hà Nội thành file .graphml"""
    file_path = Path("graph/vinhtuy.graphml")

    print(f"📁 Working dir: {os.getcwd()}")
    print(f"📁 Output file: {file_path.absolute()}")
    print("-" * 50)

    # Nếu file đã tồn tại thì bỏ qua
    if file_path.exists():
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"✅ File đã tồn tại ({size_mb:.2f} MB)")
        return

    print("⚙️  File chưa tồn tại — bắt đầu tạo mới...")
    start_time = time.time()
    file_path.parent.mkdir(parents=True, exist_ok=True)

    places = [
        "Phường Vĩnh Tuy, Hà Nội, Việt Nam",
        "Phường Mai Động, Hà Nội, Việt Nam",
        "Phường Vĩnh Hưng, Hà Nội, Việt Nam",
        "Phường Thanh Lương, Hà Nội, Việt Nam"
    ]

    graphs = []
    for i, place in enumerate(places, start=1):
        print(f"[{i}/{len(places)}] Đang tải: {place.split(',')[0]}...")
        try:
            G_part = ox.graph_from_place(place, network_type="all")
            graphs.append(G_part)
            print(f"   ✅ {len(G_part.nodes)} nodes, {len(G_part.edges)} edges")
        except Exception as e:
            print(f"   ❌ Lỗi: {e}")

    if not graphs:
        print("❌ Không tải được dữ liệu khu vực nào.")
        return

    print("\n🔄 Gộp và xử lý đồ thị...")
    G = nx.compose_all(graphs)
    G = ox.project_graph(G)
    G = ox.consolidate_intersections(G, tolerance=15)
    print(f"   ➤ Kết quả: {len(G.nodes)} nodes, {len(G.edges)} edges")

    try:
        print(f"\n💾 Đang lưu: {file_path.absolute()}")
        ox.save_graphml(G, file_path)
        size_mb = file_path.stat().st_size / (1024 * 1024)
        print(f"✅ Lưu thành công ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file: {e}")
        return

    print("-" * 50)
    print(f"⏱️ Thời gian: {time.time() - start_time:.2f} giây")


if __name__ == "__main__":
    create_graph_file()
