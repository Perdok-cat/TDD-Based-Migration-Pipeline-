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
        # Handle tree-sitter API differences gracefully
        self.parser = Parser()
        try:
            # tree-sitter >= 0.25.0 supports constructing Language from a capsule
            self.language = Language(tsc.language())
            self.parser.language = self.language
        except TypeError as e:
            # Older tree-sitter expects (library_path, name) and cannot use the capsule
            # Provide a clear, actionable error to upgrade dependencies
            raise RuntimeError(
                "Incompatible tree-sitter version detected. Please upgrade to tree-sitter>=0.25.0 and tree-sitter-c>=0.24.0 (pip install -U tree-sitter tree-sitter-c). Original error: "
                + str(e)
            )

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
    
    def extract_function_signature(self, func_node, code: bytes) -> Tuple[str, List[Tuple[str, str]]]:
        """
        Extract function signature: return type and parameters.
        
        Args:
            func_node: function_definition node
            code: source code bytes
            
        Returns:
            Tuple of (return_type, parameters) where parameters is list of (type, name) tuples
        """
        return_type = "void"
        parameters = []
        
        # Find the declarator and type specifier
        for child in func_node.children:
            # Extract return type from primitive_type or type_identifier
            if child.type in ("primitive_type", "type_identifier", "sized_type_specifier"):
                return_type = self._node_text(child, code).strip()
            
            # Extract parameters from function_declarator
            elif child.type == "function_declarator":
                # Find parameter_list
                param_list = child.child_by_field_name("parameters")
                if param_list:
                    parameters = self._extract_parameters(param_list, code)
        
        return return_type, parameters
    
    def _extract_parameters(self, param_list_node, code: bytes) -> List[Tuple[str, str]]:
        """Extract parameters from parameter_list node."""
        parameters = []
        
        for child in param_list_node.children:
            if child.type == "parameter_declaration":
                param_type = ""
                param_name = ""
                pointer_level = 0
                
                for param_child in child.children:
                    # Get type
                    if param_child.type in ("primitive_type", "type_identifier", "sized_type_specifier"):
                        param_type = self._node_text(param_child, code).strip()
                    
                    # Check for pointers
                    elif param_child.type == "pointer_declarator":
                        # Count pointer levels
                        temp_node = param_child
                        while temp_node.type == "pointer_declarator":
                            pointer_level += 1
                            # Find the actual identifier
                            for p_child in temp_node.children:
                                if p_child.type == "identifier":
                                    param_name = self._node_text(p_child, code).strip()
                                    temp_node = None
                                    break
                                elif p_child.type == "pointer_declarator":
                                    temp_node = p_child
                                    break
                            if temp_node is None:
                                break
                    
                    # Get identifier (non-pointer case)
                    elif param_child.type == "identifier":
                        param_name = self._node_text(param_child, code).strip()
                
                # Add pointer asterisks to type
                if pointer_level > 0:
                    param_type += "*" * pointer_level
                
                if param_type:
                    # If no name, use placeholder
                    if not param_name:
                        param_name = f"param{len(parameters)}"
                    parameters.append((param_type, param_name))
        
        return parameters

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
