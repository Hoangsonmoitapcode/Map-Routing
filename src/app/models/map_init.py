import osmnx as ox
import networkx as nx
from pathlib import Path
import time
import os


def create_graph_file():
    # 1. Định nghĩa đường dẫn file đích
    file_path = Path("graph/vinhtuy.graphml")

    # DEBUG: In ra đường dẫn tuyệt đối
    print(f"📁 Thư mục làm việc hiện tại: {os.getcwd()}")
    print(f"📁 Đường dẫn tuyệt đối của file sẽ tạo: {file_path.absolute()}")
    print("-" * 60)

    # 2. Kiểm tra xem file đã tồn tại chưa
    if file_path.exists():
        file_size = file_path.stat().st_size / (1024 * 1024)
        print(f"✅ File đã tồn tại!")
        print(f"   Vị trí: {file_path.absolute()}")
        print(f"   Kích thước: {file_size:.2f} MB")
        return

    # 3. Nếu file chưa tồn tại, bắt đầu quá trình tạo file
    print(f"⚠️ File không tồn tại. Bắt đầu quá trình tải và tạo file...")
    start_time = time.time()

    # Đảm bảo thư mục cha tồn tại trước khi lưu
    file_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"✅ Đã tạo/kiểm tra thư mục: {file_path.parent.absolute()}")

    # Danh sách các khu vực cần tải
    places_names = [
        "Phường Vĩnh Tuy, Hà Nội, Việt Nam",
        "Phường Mai Động, Hà Nội, Việt Nam",
        "Phường Vĩnh Hưng, Hà Nội, Việt Nam",
        "Phường Thanh Lương, Hà Nội, Việt Nam"
    ]

    graphs = []
    for i, place in enumerate(places_names):
        print(f"[{i + 1}/{len(places_names)}] Đang tải dữ liệu cho: {place.split(',')[0]}...")
        try:
            G_place = ox.graph_from_place(place, network_type='all')
            graphs.append(G_place)
            print(f"   ✅ Thành công! Số nodes: {len(G_place.nodes)}, edges: {len(G_place.edges)}")
        except Exception as e:
            print(f"   ❌ Lỗi khi tải {place}: {e}")

    if not graphs:
        print("❌ Lỗi: Không tải được dữ liệu cho bất kỳ khu vực nào. Dừng chương trình.")
        return

    print("\n🔄 Đang gộp các đồ thị...")
    G = graphs[0]
    for graph in graphs[1:]:
        G = nx.compose(G, graph)
    print(f"   Tổng số nodes: {len(G.nodes)}, edges: {len(G.edges)}")

    print("🔄 Đang xử lý và hợp nhất các giao lộ...")
    G = ox.project_graph(G)
    G = ox.consolidate_intersections(G, tolerance=15)
    print(f"   Sau xử lý: {len(G.nodes)} nodes, {len(G.edges)} edges")

    # LƯU FILE VỚI ERROR HANDLING
    try:
        print(f"\n💾 Đang lưu đồ thị vào file: {file_path.absolute()}")
        ox.save_graphml(G, file_path)

        # Kiểm tra ngay sau khi lưu
        if file_path.exists():
            file_size = file_path.stat().st_size / (1024 * 1024)
            print(f"✅ File đã được lưu thành công!")
            print(f"   📍 Vị trí: {file_path.absolute()}")
            print(f"   📊 Kích thước: {file_size:.2f} MB")
        else:
            print(f"⚠️ Lệnh lưu đã chạy nhưng không tìm thấy file tại: {file_path.absolute()}")
    except Exception as e:
        print(f"❌ Lỗi khi lưu file: {e}")
        return

    end_time = time.time()
    print("-" * 60)
    print(f"⏱️ Thời gian thực hiện: {end_time - start_time:.2f} giây.")


if __name__ == "__main__":
    create_graph_file()