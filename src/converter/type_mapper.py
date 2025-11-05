"""
Type Mapper - Map C types to C# types
"""
from typing import Dict, Tuple


class TypeMapper:
    """
    Map C types to C# types
    
    Handles:
    - Primitives: int → int, char → byte
    - Pointers: int* → ref int or IntPtr
    - Arrays: int[] → int[]
    - Structs: struct → class/struct
    """
    
    # Basic type mappings
    TYPE_MAP: Dict[str, str] = {
        # Integer types
        'int': 'int',
        'short': 'short',
        'long': 'long',
        'long long': 'long',
        'char': 'byte',
        
        # Unsigned types
        'unsigned int': 'uint',
        'unsigned short': 'ushort',
        'unsigned long': 'ulong',
        'unsigned long long': 'ulong',
        'unsigned char': 'byte',
        
        # Floating point
        'float': 'float',
        'double': 'double',
        'long double': 'double',
        
        # Other
        'void': 'void',
        'bool': 'bool',
        '_Bool': 'bool',
        
        # Size types
        'size_t': 'ulong',
        'ssize_t': 'long',
    }
    
    @staticmethod
    def map_type(c_type: str, is_pointer: bool = False, pointer_level: int = 0) -> str:
        """
        Map C type to C# type
        
        Args:
            c_type: C type string
            is_pointer: Whether it's a pointer type
            pointer_level: Level of pointer indirection
        
        Returns:
            C# type string
        """
        # Clean up type string
        c_type = c_type.strip()
        
        # Remove const, static, etc.
        c_type = c_type.replace('const ', '')
        c_type = c_type.replace('static ', '')
        c_type = c_type.replace('extern ', '')
        c_type = c_type.strip()
        
        # Get base type
        csharp_type = TypeMapper.TYPE_MAP.get(c_type, c_type)
        
        # Handle pointers
        if is_pointer:
            if pointer_level == 1:
                # Single pointer - use ref or IntPtr depending on context
                # For now, use ref
                csharp_type = f"ref {csharp_type}"
            else:
                # Multiple levels of indirection - use IntPtr
                csharp_type = "IntPtr"
        
        return csharp_type
    
    @staticmethod
    def map_function_signature(
        return_type: str,
        is_return_pointer: bool = False
    ) -> str:
        """
        Map function return type
        
        Args:
            return_type: C return type
            is_return_pointer: Whether return type is pointer
        
        Returns:
            C# return type
        """
        return TypeMapper.map_type(return_type, is_return_pointer)
    
    @staticmethod
    def needs_unsafe_context(c_type: str, is_pointer: bool = False) -> bool:
        """
        Check if type requires unsafe context in C#
        
        Args:
            c_type: C type
            is_pointer: Whether it's a pointer
        
        Returns:
            True if unsafe context is needed
        """
        # Pointers need unsafe context (except when using IntPtr)
        if is_pointer:
            return True
        
        # Some types might need unsafe
        unsafe_types = ['void*', 'char*', 'int*']
        return any(ut in c_type for ut in unsafe_types)

