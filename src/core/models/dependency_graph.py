"""
Dependency graph để quản lý dependencies giữa các C programs
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional
from collections import defaultdict


@dataclass
class DependencyNode:
    """Node trong dependency graph"""
    program_id: str
    dependencies: List[str] = field(default_factory=list)
    is_converted: bool = False
    conversion_order: Optional[int] = None
    
    def has_dependency(self, program_id: str) -> bool:
        """Kiểm tra có dependency với program_id không"""
        return program_id in self.dependencies


class DependencyGraph:
    """
    Biểu đồ dependencies giữa các C programs
    Hỗ trợ phát hiện circular dependencies và xác định thứ tự conversion
    """
    
    def __init__(self):
        self._nodes: Dict[str, DependencyNode] = {}
        self._reverse_dependencies: Dict[str, Set[str]] = defaultdict(set)
    
    @property
    def nodes(self) -> Dict[str, DependencyNode]:
        """Read-only access to nodes"""
        return self._nodes.copy()
    
    def add_node(self, program_id: str, dependencies: List[str]) -> None:
        """
        Thêm một node vào graph
        
        Args:
            program_id: ID của program
            dependencies: Danh sách các program IDs mà program này phụ thuộc vào
        """
        if program_id not in self._nodes:
            self._nodes[program_id] = DependencyNode(
                program_id=program_id,
                dependencies=dependencies
            )
        else:
            self._nodes[program_id].dependencies = dependencies
        
        # Update reverse dependencies
        for dep in dependencies:
            self._reverse_dependencies[dep].add(program_id)
            
            # Ensure dependent node exists
            if dep not in self._nodes:
                self._nodes[dep] = DependencyNode(program_id=dep)
    
    def mark_as_converted(self, program_id: str) -> None:
        """Đánh dấu một program đã được converted"""
        if program_id in self._nodes:
            self._nodes[program_id].is_converted = True
    
    def get_ready_to_convert(self) -> List[str]:
        """
        Lấy danh sách programs có thể convert ngay
        (tất cả dependencies đã được converted hoặc không có dependencies)
        
        Returns:
            List of program IDs ready to convert
        """
        ready = []
        
        for program_id, node in self._nodes.items():
            if node.is_converted:
                continue
            
            # Check if all dependencies are converted
            all_deps_converted = all(
                self._nodes.get(dep, DependencyNode(dep, [], True)).is_converted
                for dep in node.dependencies
            )
            
            if all_deps_converted:
                ready.append(program_id)
        
        return ready
    
    def get_dependent_programs(self, program_id: str) -> Set[str]:
        """
        Lấy danh sách programs phụ thuộc vào program này
        
        Args:
            program_id: ID của program
            
        Returns:
            Set of program IDs that depend on this program
        """
        return self._reverse_dependencies.get(program_id, set()).copy()
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Phát hiện circular dependencies sử dụng DFS
        
        Returns:
            List of cycles, mỗi cycle là một list of program IDs
        """
        cycles = []
        visited = set()
        recursion_stack = set()
        
        def dfs(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            recursion_stack.add(node_id)
            path.append(node_id)
            
            if node_id in self._nodes:
                for dep in self._nodes[node_id].dependencies:
                    if dep not in visited:
                        dfs(dep, path.copy())
                    elif dep in recursion_stack:
                        # Found a cycle
                        cycle_start = path.index(dep)
                        cycle = path[cycle_start:] + [dep]
                        cycles.append(cycle)
            
            path.pop()
            recursion_stack.remove(node_id)
        
        for node_id in self._nodes.keys():
            if node_id not in visited:
                dfs(node_id, [])
        
        return cycles
    
    def get_conversion_order(self) -> List[str]:
        """
        Xác định thứ tự conversion tối ưu sử dụng topological sort
        
        Returns:
            List of program IDs in conversion order
        
        Raises:
            ValueError: If circular dependencies exist
        """
        # Check for cycles first
        cycles = self.detect_circular_dependencies()
        if cycles:
            cycle_strs = [" -> ".join(cycle) for cycle in cycles]
            raise ValueError(
                f"Cannot determine conversion order due to circular dependencies:\n"
                + "\n".join(cycle_strs)
            )
        
        # Topological sort using Kahn's algorithm
        in_degree = {node_id: 0 for node_id in self._nodes}
        
        for node in self._nodes.values():
            for dep in node.dependencies:
                if dep in in_degree:
                    in_degree[node.program_id] += 1
        
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            # Sort for deterministic order
            queue.sort()
            node_id = queue.pop(0)
            order.append(node_id)
            
            # Reduce in-degree for dependent nodes
            for dependent in self._reverse_dependencies.get(node_id, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Set conversion order
        for idx, node_id in enumerate(order):
            self._nodes[node_id].conversion_order = idx
        
        return order
    
    def get_statistics(self) -> Dict[str, any]:
        """Lấy thống kê về dependency graph"""
        total_nodes = len(self._nodes)
        converted_nodes = sum(1 for node in self._nodes.values() if node.is_converted)
        total_edges = sum(len(node.dependencies) for node in self._nodes.values())
        
        cycles = self.detect_circular_dependencies()
        
        return {
            "total_programs": total_nodes,
            "converted_programs": converted_nodes,
            "pending_programs": total_nodes - converted_nodes,
            "total_dependencies": total_edges,
            "circular_dependencies": len(cycles),
            "cycles": cycles,
            "conversion_progress": (converted_nodes / total_nodes * 100) if total_nodes > 0 else 0
        }
    
    def visualize(self) -> str:
        """
        Tạo chuỗi text representation của graph (đơn giản)
        
        Returns:
            String representation of the graph
        """
        lines = ["Dependency Graph:", "=" * 50]
        
        for node_id, node in sorted(self._nodes.items()):
            status = "✓" if node.is_converted else "○"
            deps_str = ", ".join(node.dependencies) if node.dependencies else "none"
            lines.append(f"{status} {node_id}")
            lines.append(f"  Dependencies: {deps_str}")
            
            dependents = self._reverse_dependencies.get(node_id, set())
            if dependents:
                lines.append(f"  Used by: {', '.join(sorted(dependents))}")
        
        return "\n".join(lines)

