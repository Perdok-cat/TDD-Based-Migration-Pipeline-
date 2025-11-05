"""
Input Generator - Generate test inputs cho các function
Bao gồm: boundary values, edge cases, random values
"""
import random
import sys
from typing import List, Any, Dict
from ..core.models.c_program import CFunction, CVariable, CDataType


class InputGenerator:
    """Generator cho test inputs"""
    
    def __init__(self, seed: int = 42):
        """
        Initialize input generator
        
        Args:
            seed: Random seed để reproducible
        """
        self.seed = seed
        random.seed(seed)
    
    def generate_boundary_values(self, param: CVariable) -> List[Any]:
        """
        Generate boundary values cho một parameter
        
        Args:
            param: CVariable parameter
            
        Returns:
            List of boundary values
        """
        values = []
        data_type = param.data_type.lower()
        
        # Integer types
        if 'int' in data_type:
            if 'unsigned' in data_type:
                values = [0, 1, 100, 1000, 2**32 - 1]  # unsigned int range
            else:
                values = [-2**31, -1000, -1, 0, 1, 1000, 2**31 - 1]
        
        # Short types
        elif 'short' in data_type:
            if 'unsigned' in data_type:
                values = [0, 1, 100, 2**16 - 1]
            else:
                values = [-2**15, -100, -1, 0, 1, 100, 2**15 - 1]
        
        # Long types
        elif 'long' in data_type:
            if 'unsigned' in data_type:
                values = [0, 1, 1000, 2**64 - 1]
            else:
                values = [-2**63, -1000, -1, 0, 1, 1000, 2**63 - 1]
        
        # Char types
        elif 'char' in data_type:
            if 'unsigned' in data_type:
                values = [0, 1, 65, 90, 97, 122, 255]  # A, Z, a, z, max
            else:
                values = [-128, 0, 32, 65, 90, 97, 122, 127]  # space, letters
        
        # Float types
        elif data_type == 'float':
            values = [-1e38, -1000.5, -1.0, -0.1, 0.0, 0.1, 1.0, 1000.5, 1e38]
        
        # Double types
        elif data_type == 'double':
            values = [-1e308, -1000.5, -1.0, -0.1, 0.0, 0.1, 1.0, 1000.5, 1e308]
        
        # Pointer - special handling
        elif param.is_pointer:
            values = [None]  # NULL pointer
        
        else:
            # Default values
            values = [0, 1, 100]
        
        return values
    
    def generate_edge_cases(self, param: CVariable) -> List[Any]:
        """
        Generate edge cases cho một parameter
        
        Args:
            param: CVariable parameter
            
        Returns:
            List of edge case values
        """
        values = []
        data_type = param.data_type.lower()
        
        # Integer overflow/underflow
        if 'int' in data_type:
            if 'unsigned' in data_type:
                values = [0, 2**32 - 1, 2**32]  # max + 1 to test overflow
            else:
                values = [-2**31 - 1, -2**31, 2**31 - 1, 2**31]
        
        # Zero and negative for unsigned
        elif 'unsigned' in data_type:
            values = [0, -1]  # negative for unsigned
        
        # Float special values
        elif data_type in ['float', 'double']:
            values = [0.0, -0.0, float('inf'), float('-inf')]
            # Note: NaN is tricky in tests
        
        # Null for pointers
        elif param.is_pointer:
            values = [None]
        
        return values
    
    def generate_random_values(self, param: CVariable, count: int = 5) -> List[Any]:
        """
        Generate random values cho một parameter
        
        Args:
            param: CVariable parameter
            count: Number of random values
            
        Returns:
            List of random values
        """
        values = []
        data_type = param.data_type.lower()
        
        for _ in range(count):
            # Integer types
            if 'int' in data_type:
                if 'unsigned' in data_type:
                    val = random.randint(0, min(2**32 - 1, sys.maxsize))
                else:
                    val = random.randint(-sys.maxsize - 1, sys.maxsize)
                values.append(val)
            
            # Short types
            elif 'short' in data_type:
                if 'unsigned' in data_type:
                    val = random.randint(0, 2**16 - 1)
                else:
                    val = random.randint(-2**15, 2**15 - 1)
                values.append(val)
            
            # Char types
            elif 'char' in data_type:
                if 'unsigned' in data_type:
                    val = random.randint(0, 255)
                else:
                    val = random.randint(-128, 127)
                values.append(val)
            
            # Float types
            elif data_type == 'float':
                val = random.uniform(-1000.0, 1000.0)
                values.append(val)
            
            # Double types
            elif data_type == 'double':
                val = random.uniform(-10000.0, 10000.0)
                values.append(val)
            
            # Default
            else:
                values.append(random.randint(0, 100))
        
        return values
    
    def generate_combinations(
        self,
        function: CFunction,
        strategy: str = 'boundary'
    ) -> List[Dict[str, Any]]:
        """
        Generate combinations of inputs cho tất cả parameters của function
        
        Args:
            function: CFunction to generate inputs for
            strategy: 'boundary', 'edge', 'random', or 'all'
            
        Returns:
            List of input combinations (each is a dict {param_name: value})
        """
        if not function.parameters:
            # No parameters, return single empty test case
            return [{}]
        
        combinations = []
        
        # Generate values for each parameter
        param_values: Dict[str, List[Any]] = {}
        
        for param in function.parameters:
            values = []
            
            if strategy == 'boundary':
                values = self.generate_boundary_values(param)
            elif strategy == 'edge':
                values = self.generate_edge_cases(param)
            elif strategy == 'random':
                values = self.generate_random_values(param, count=5)
            elif strategy == 'all':
                values = (
                    self.generate_boundary_values(param) +
                    self.generate_edge_cases(param) +
                    self.generate_random_values(param, count=3)
                )
            
            param_values[param.name] = values
        
        # Simple strategy: Test each parameter's values one by one
        # (Full cartesian product would be too many tests)
        
        # Strategy 1: One parameter at a time
        for param_name, values in param_values.items():
            for value in values:
                # Create input dict with default values for other params
                input_dict = {}
                for p in function.parameters:
                    if p.name == param_name:
                        input_dict[p.name] = value
                    else:
                        # Use a default value
                        input_dict[p.name] = self._get_default_value(p)
                
                combinations.append(input_dict)
        
        # Strategy 2: All minimum values, all maximum values
        if strategy in ['boundary', 'all']:
            # All min
            min_inputs = {}
            max_inputs = {}
            for param in function.parameters:
                vals = param_values[param.name]
                if vals:
                    min_inputs[param.name] = vals[0]
                    max_inputs[param.name] = vals[-1]
            
            combinations.append(min_inputs)
            combinations.append(max_inputs)
        
        return combinations
    
    def _get_default_value(self, param: CVariable) -> Any:
        """Get default value for a parameter type"""
        data_type = param.data_type.lower()
        
        if param.is_pointer:
            return None
        elif 'float' in data_type or 'double' in data_type:
            return 0.0
        else:
            return 0

