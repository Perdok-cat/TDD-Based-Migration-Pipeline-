# Cparser.py
# pip install -U tree-sitter tree-sitter-c
from __future__ import annotations

import os
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set, Deque, Optional, Any

import tree_sitter_c as tsc
from tree_sitter import Language, Parser


class CParser:
    """
    Trình phân tích mã C dựa trên tree-sitter.
    Nhiệm vụ:
      - parse file .c/.h
      - trích xuất hàm, lời gọi, includes
      - quét thư mục dự án
      - tổng hợp project_data để dùng cho phân tích phụ thuộc
    """

    def __init__(self) -> None:
        self.language = Language(tsc.language())
        self.parser = Parser(self.language)

    # ----------------------- Utilities -----------------------

    @staticmethod
    def find_c_files(path: str | os.PathLike) -> List[Path]:
        """Tìm tất cả file .c/.h (đệ quy)."""
        p = Path(path)
        if p.is_file():
            return [p] if p.suffix in {".c", ".h"} else []
        if p.is_dir():
            files: List[Path] = []
            for pattern in ("**/*.c", "**/*.h"):
                files.extend(p.glob(pattern))
            return sorted(files)
        return []

    def parse_file(self, filepath: str | os.PathLike) -> Tuple[Any, bytes]:
        """Parse một file C, trả về (tree, raw_bytes)."""
        with open(filepath, "rb") as f:
            code = f.read()
        tree = self.parser.parse(code)
        return tree, code

    # -------------------- Tree walkers -----------------------

    @staticmethod
    def _node_text(node, code: bytes) -> str:
        return code[node.start_byte:node.end_byte].decode(errors="ignore")

    def to_sexpr(self, node, code: bytes) -> str:
        """Tạo S-expression tối giản."""
        if node.child_count == 0:
            text = self._node_text(node, code).replace("\n", "\\n")
            return f"({node.type} '{text}')"
        parts = [f"({node.type}"]
        for ch in node.children:
            parts.append(self.to_sexpr(ch, code))
        parts.append(")")
        return " ".join(parts)

    def walk_functions(self, node, code: bytes):
        """Yield (function_name, function_node)."""
        def find_identifier(n):
            if n.type == "identifier":
                return self._node_text(n, code)
            for child in n.children:
                r = find_identifier(child)
                if r:
                    return r
            return None

        if node.type == "function_definition":
            ident = None
            for ch in node.children:
                if ch.type in ("function_declarator", "pointer_declarator", "declarator"):
                    ident = find_identifier(ch)
                    if ident:
                        break
            if ident:
                yield ident, node

        for ch in node.children:
            yield from self.walk_functions(ch, code)

    def extract_calls_in_node(self, node, code: bytes) -> List[str]:
        """Trích xuất lời gọi hàm trong một cây con."""
        calls: List[str] = []

        def _walk(n):
            if n.type == "call_expression":
                fn = n.child_by_field_name("function")
                if fn:
                    calls.append(self._node_text(fn, code))
            for c in n.children:
                _walk(c)

        _walk(node)
        return calls

    def extract_includes_simple(self, root, code: bytes) -> Tuple[List[str], List[str]]:
        """
        Trích xuất #include theo 2 nhóm:
            - system_headers: <stdio.h>
            - user_headers: "my.h"
        """
        system_headers: List[str] = []
        user_headers: List[str] = []

        def _walk(n):
            if n.type == "preproc_include":
                for child in n.children:
                    if child.type == "system_lib_string":
                        text = self._node_text(child, code).strip()
                        header = text.strip("<>").strip()
                        system_headers.append(header)
                    elif child.type == "string_literal":
                        text = self._node_text(child, code).strip()
                        header = text.strip('"').strip()
                        user_headers.append(header)
            for c in n.children:
                _walk(c)

        _walk(root)
        return system_headers, user_headers

    # -------------------- Project analysis -------------------

    def analyze_paths(
        self,
        paths: List[str | os.PathLike],
        output_mode: str = "summary",
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Phân tích tập đường dẫn (file hoặc thư mục).
        Trả về:
            project_data:  thống kê hàm, calls, ...
            file_data_for_graph: { filepath: { user_includes, system_includes, functions, total_lines } }
        """
        all_files: List[Path] = []
        for p in paths:
            all_files.extend(self.find_c_files(p))
        all_files = sorted(set(all_files))

        project_data: Dict[str, Any] = {
            "files": {},
            "all_functions": defaultdict(list),  # func_name -> [files]
            "all_calls": defaultdict(int),       # func_name -> count
        }
        file_data_for_graph: Dict[str, Any] = {}

        for filepath in all_files:
            try:
                tree, code = self.parse_file(filepath)
                root = tree.root_node

                system_includes, user_includes = self.extract_includes_simple(root, code)

                file_info = {
                    "path": str(filepath),
                    "functions": {},  # name -> calls[]
                    "system_includes": system_includes,
                    "user_includes": user_includes,
                    "total_lines": len(code.split(b"\n")),
                }

                # functions + calls
                for func_name, func_node in self.walk_functions(root, code):
                    calls = self.extract_calls_in_node(func_node, code)
                    file_info["functions"][func_name] = calls
                    project_data["all_functions"][func_name].append(str(filepath))
                    for call in calls:
                        project_data["all_calls"][call] += 1

                project_data["files"][str(filepath)] = file_info
                file_data_for_graph[str(filepath)] = file_info

                if output_mode in ("detailed",):
                    print(f"[{filepath}] funcs={len(file_info['functions'])} includes={len(system_includes)+len(user_includes)}")

                if output_mode == "full":
                    sexpr = self.to_sexpr(root, code)
                    print(f"\n--- S-EXPR: {filepath} ---")
                    print(sexpr[:2000] + ("..." if len(sexpr) > 2000 else ""))

            except Exception as e:
                print(f"❌ Parse error at {filepath}: {e}", file=sys.stderr)

        return project_data, file_data_for_graph
