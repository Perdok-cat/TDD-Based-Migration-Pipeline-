# Dependencies_analysis.py
from __future__ import annotations

import os
from collections import defaultdict, deque
from typing import Dict, Set, List, Tuple, Any, Optional


class DependenciesAnalysis:
    """
    Phân tích phụ thuộc file-level:
      - build_dependency_graph (từ user_includes)
      - topological_sort (Kahn)
      - find_cycles_dfs (liệt kê chu trình)
      - export_graph_dot (Graphviz)
      - scc/tarjan (tuỳ chọn) + đồ thị nén
    """

    # -------------------- Graph build --------------------

    @staticmethod
    def build_dependency_graph(file_data: Dict[str, Any]) -> Dict[str, Set[str]]:
        """
        file_data: { filepath: { 'user_includes': [...], ... } }
        return: graph Dict[filename -> Set[filename]]
        """
        graph: Dict[str, Set[str]] = defaultdict(set)

        # basename -> [fullpaths]cc/tarjan (tuỳ chọn) + đồ thị nén
        basename_map: Dict[str, List[str]] = defaultdict(list)
        for fp in file_data.keys():
            basename_map[os.path.basename(fp)].append(fp)

        for filepath, info in file_data.items():
            src = os.path.basename(filepath)

            for inc in info.get("user_includes", []):
                inc_base = os.path.basename(inc)
                if inc_base in basename_map:
                    # Ưu tiên cùng thư mục
                    parent = os.path.dirname(filepath)
                    candidates = basename_map[inc_base]
                    chosen = inc_base
                    for cand in candidates:
                        if os.path.dirname(cand) == parent:
                            chosen = os.path.basename(cand)
                            break
                    graph[src].add(chosen)
                else:
                    # include ngoài project hoặc chưa tìm thấy
                    graph[src].add(inc_base)

            if src not in graph:
                graph[src] = set()

        return graph

    # -------------------- Cycle / Topo --------------------

    @staticmethod
    def find_cycles_dfs(graph: Dict[str, Set[str]]) -> List[List[str]]:
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {u: WHITE for u in graph}
        cycles: List[List[str]] = []

        def dfs(u: str, stack: List[str]):
            color[u] = GRAY
            stack.append(u)
            for v in graph.get(u, set()):
                if v not in color:
                    color[v] = WHITE
                if color[v] == WHITE:
                    dfs(v, stack.copy())
                elif color[v] == GRAY:
                    # back edge => cycle
                    if v in stack:
                        i = stack.index(v)
                        cycles.append(stack[i:] + [v])
            color[u] = BLACK
            stack.pop()

        for u in list(graph.keys()):
            if color[u] == WHITE:
                dfs(u, [])
        return cycles

    @staticmethod
    def topological_sort(graph: Dict[str, Set[str]]) -> Tuple[Optional[List[str]], List[List[str]]]:
        # gather all nodes
        nodes = set(graph.keys())
        for deps in graph.values():
            nodes.update(deps)

        indeg = {u: 0 for u in nodes}
        for u in graph:
            for v in graph[u]:
                indeg[v] = indeg.get(v, 0) + 1

        q = deque([u for u in nodes if indeg.get(u, 0) == 0])
        order: List[str] = []

        while q:
            u = q.popleft()
            order.append(u)
            for v in graph.get(u, set()):
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)

        if len(order) != len(nodes):
            return None, DependenciesAnalysis.find_cycles_dfs(graph)
        return order, []

    # -------------------- DOT export --------------------

    @staticmethod
    def export_graph_dot(graph: Dict[str, Set[str]], output_file: str = "dependency_graph.dot") -> None:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("digraph Dependencies {\n")
            f.write("  rankdir=LR;\n")
            f.write('  node [shape=box, style="rounded,filled"];\n\n')

            nodes = set(graph.keys())
            for dests in graph.values():
                nodes.update(dests)

            for n in sorted(nodes):
                if n.endswith(".h"):
                    f.write(f'  "{n}" [fillcolor=lightblue];\n')
                elif n.endswith(".c"):
                    f.write(f'  "{n}" [fillcolor=lightgreen];\n')
                else:
                    f.write(f'  "{n}" [fillcolor=lightgray];\n')

            f.write("\n")
            for src, dests in sorted(graph.items()):
                for dst in sorted(dests):
                    f.write(f'  "{src}" -> "{dst}";\n')

            f.write("}\n")

        print(f"✅ DOT written: {output_file}")
        print(f"   👉 dot -Tpng {output_file} -o dependency_graph.png")

    # -------------------- SCC (optional) --------------------

    @staticmethod
    def tarjan_scc(graph: Dict[str, Set[str]]) -> List[List[str]]:
        index = 0
        indices: Dict[str, int] = {}
        low: Dict[str, int] = {}
        st: List[str] = []
        onstack: Set[str] = set()
        sccs: List[List[str]] = []

        def strongconnect(v: str):
            nonlocal index
            indices[v] = low[v] = index
            index += 1
            st.append(v); onstack.add(v)

            for w in graph.get(v, set()):
                if w not in indices:
                    strongconnect(w)
                    low[v] = min(low[v], low[w])
                elif w in onstack:
                    low[v] = min(low[v], indices[w])

            if low[v] == indices[v]:
                comp: List[str] = []
                while True:
                    w = st.pop()
                    onstack.remove(w)
                    comp.append(w)
                    if w == v:
                        break
                sccs.append(comp)

        for v in list(graph.keys()):
            if v not in indices:
                strongconnect(v)
        return sccs

    @staticmethod
    def condense_graph(graph: Dict[str, Set[str]], sccs: List[List[str]]) -> Tuple[Dict[str, int], Dict[int, Set[int]]]:
        comp_id: Dict[str, int] = {}
        for i, comp in enumerate(sccs):
            for node in comp:
                comp_id[node] = i

        condensed: Dict[int, Set[int]] = defaultdict(set)
        for u, dests in graph.items():
            for v in dests:
                if comp_id[u] != comp_id[v]:
                    condensed[comp_id[u]].add(comp_id[v])
        return comp_id, condensed

    @staticmethod
    def topo_on_condensed(condensed: Dict[int, Set[int]]) -> List[int]:
        indeg = defaultdict(int)
        for u, dests in condensed.items():
            for v in dests:
                indeg[v] += 1
            _ = indeg[u]  # ensure present
        q = [u for u, d in indeg.items() if d == 0]
        order: List[int] = []
        while q:
            u = q.pop()
            order.append(u)
            for v in list(condensed[u]):
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)
        return order

    # -------------------- One-shot pipeline --------------------

    def analyze_dependencies(
        self,
        file_data_for_graph: Dict[str, Any],
        export_graph: bool = False,
    ) -> Tuple[Dict[str, Set[str]], Optional[List[str]], List[List[str]]]:
        """
        Trả về:
          - graph
          - order (nếu không có vòng)
          - cycles (nếu có)
        """
        graph = self.build_dependency_graph(file_data_for_graph)

        # In ngắn gọn
        print("\n=== DEPENDENCY GRAPH (file-level) ===")
        for src, dests in sorted(graph.items()):
            deps = ", ".join(sorted(dests)) if dests else "(none)"
            print(f"  {src} -> {{{deps}}}")

        order, cycles = self.topological_sort(graph)
        if order is not None:
            print("\n✅ No cycles found.")
            print("📋 Suggested topological order:")
            for i, f in enumerate(order, 1):
                print(f"  {i}. {f}")
        else:
            print(f"\n⚠️ Detected {len(cycles)} cycle(s):")
            for i, cyc in enumerate(cycles, 1):
                print(f"  Cycle {i}: {' -> '.join(cyc)}")

            # Gợi ý thêm: phân rã theo SCC
            sccs = self.tarjan_scc(graph)
            print("\n🔎 SCCs (strongly connected components):")
            for i, comp in enumerate(sccs, 1):
                mark = " (CYCLE)" if len(comp) > 1 else ""
                print(f"  SCC {i}: {comp}{mark}")

            comp_id, condensed = self.condense_graph(graph, sccs)
            topo_scc = self.topo_on_condensed(condensed)
            print("\n📦 Topological order on condensed graph (SCCs):")
            print("  " + " -> ".join([f"SCC#{i}" for i in topo_scc]))

        if export_graph:
            self.export_graph_dot(graph)

        return graph, order, cycles
