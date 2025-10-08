# Đoạn code này nhằm mục đích test

# main.py
import argparse
from src.core.Cparser import CParser
from src.core.dependencies_analysis import DependenciesAnalysis

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=["."], help="File/thư mục cần phân tích")
    ap.add_argument("--mode", "-m", choices=["summary", "detailed", "full"], default="summary")
    ap.add_argument("--graph", "-g", action="store_true", help="Phân tích dependency graph")
    ap.add_argument("--export", "-e", action="store_true", help="Xuất DOT khi dùng --graph")
    args = ap.parse_args()

    cparser = CParser()
    project_data, file_data_for_graph = cparser.analyze_paths(args.paths, output_mode=args.mode)

    print("\n=== PROJECT SUMMARY ===")
    print(f"Total files: {len(project_data['files'])}")
    print(f"Total defined functions: {len(project_data['all_functions'])}")

    if args.graph:
        dep = DependenciesAnalysis()
        dep.analyze_dependencies(file_data_for_graph, export_graph=args.export)
