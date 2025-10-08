"""
Mô hình đại diện cho một C program và các thành phần của nó
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class CDataType(Enum):
    """C data types"""
    INT = "int"
    LONG = "long"
    SHORT = "short"
    CHAR = "char"
    FLOAT = "float"
    DOUBLE = "double"
    VOID = "void"
    POINTER = "pointer"
    STRUCT = "struct"
    UNION = "union"
    ENUM = "enum"
    ARRAY = "array"
    UNSIGNED_INT = "unsigned int"
    UNSIGNED_LONG = "unsigned long"
    UNSIGNED_SHORT = "unsigned short"
    UNSIGNED_CHAR = "unsigned char"


@dataclass
class CVariable:
    """Đại diện cho một biến trong C"""
    name: str
    data_type: str
    is_pointer: bool = False
    pointer_level: int = 0
    is_const: bool = False
    is_static: bool = False
    is_extern: bool = False
    initial_value: Optional[Any] = None
    array_size: Optional[int] = None
    struct_name: Optional[str] = None
    line_number: int = 0


@dataclass
class CFunction:
    """Đại diện cho một function trong C"""
    name: str
    return_type: str
    parameters: List[CVariable] = field(default_factory=list)
    body: str = ""
    is_static: bool = False
    is_inline: bool = False
    called_functions: List[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0
    complexity: int = 0  # Cyclomatic complexity


@dataclass
class CStruct:
    """Đại diện cho một struct trong C"""
    name: str
    members: List[CVariable] = field(default_factory=list)
    is_typedef: bool = False
    line_number: int = 0


@dataclass
class CEnum:
    """Đại diện cho một enum trong C"""
    name: str
    values: Dict[str, int] = field(default_factory=dict)
    line_number: int = 0


@dataclass
class CDefine:
    """Đại diện cho một #define directive"""
    name: str
    value: str
    is_function_macro: bool = False
    parameters: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class CInclude:
    """Đại diện cho một #include directive"""
    file_name: str
    is_system: bool  # <> vs ""
    line_number: int = 0


@dataclass
class CProgram:
    """Đại diện cho một C program/file"""
    program_id: str
    file_path: str
    source_code: str
    
    # Parsed components
    includes: List[CInclude] = field(default_factory=list)
    defines: List[CDefine] = field(default_factory=list)
    variables: List[CVariable] = field(default_factory=list)
    functions: List[CFunction] = field(default_factory=list)
    structs: List[CStruct] = field(default_factory=list)
    enums: List[CEnum] = field(default_factory=list)
    
    # Dependencies
    dependencies: List[str] = field(default_factory=list)  # Other C files/modules
    
    # Conversion status
    is_converted: bool = False
    converted_at: Optional[datetime] = None
    conversion_success: bool = False
    
    # Metadata
    lines_of_code: int = 0
    complexity_score: float = 0.0
    
    def get_function_by_name(self, name: str) -> Optional[CFunction]:
        """Lấy function theo tên"""
        for func in self.functions:
            if func.name == name:
                return func
        return None
    
    def get_struct_by_name(self, name: str) -> Optional[CStruct]:
        """Lấy struct theo tên"""
        for struct in self.structs:
            if struct.name == name:
                return struct
        return None
    
    def get_all_function_names(self) -> List[str]:
        """Lấy tất cả function names"""
        return [func.name for func in self.functions]
    
    def calculate_complexity(self) -> float:
        """Tính complexity score của program"""
        total_complexity = sum(func.complexity for func in self.functions)
        self.complexity_score = total_complexity / max(len(self.functions), 1)
        return self.complexity_score

