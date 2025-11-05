"""
C to C# Converter - Convert C code to C#
"""
import logging
import re
from typing import List, Optional, Dict, Any

from ..core.models.c_program import CProgram, CFunction, CVariable, CStruct, CEnum, CDefine
from .type_mapper import TypeMapper


class CToCSharpConverter:
    """
    Convert C program to C#
    
    Process:
    1. Parse C code (already done by CParser)
    2. Transform AST components
    3. Generate C# code
    
    Conversion rules:
    - Functions: Add public static modifiers
    - Structs: Convert to C# struct or class
    - Variables: Map types
    - Control flow: Mostly same syntax
    - Memory: malloc/free → new/GC
    """
    
    def __init__(self):
        """Initialize converter"""
        self.logger = logging.getLogger(__name__)
        self.type_mapper = TypeMapper()
    
    def convert(self, program: CProgram) -> str:
        """
        Convert C program to C#
        
        Args:
            program: CProgram to convert
        
        Returns:
            C# code string
        """
        self.logger.info(f"Converting {program.program_id} to C#...")
        
        code_lines = []
        
        # Using directives
        code_lines.extend(self._generate_usings())
        code_lines.append("")
        
        # Namespace (optional, use Program class directly for simplicity)
        code_lines.append("public class Program")
        code_lines.append("{")
        
        # Convert defines (as constants)
        if program.defines:
            code_lines.append("    // Constants (from #define)")
            for define in program.defines:
                const_code = self._convert_define(define)
                if const_code:
                    code_lines.append("    " + const_code)
            code_lines.append("")
        
        # Convert enums
        if program.enums:
            for enum in program.enums:
                enum_code = self._convert_enum(enum)
                for line in enum_code.split('\n'):
                    code_lines.append("    " + line if line else "")
                code_lines.append("")
        
        # Convert structs
        if program.structs:
            for struct in program.structs:
                struct_code = self._convert_struct(struct)
                for line in struct_code.split('\n'):
                    code_lines.append("    " + line if line else "")
                code_lines.append("")
        
        # Convert global variables
        if program.variables:
            code_lines.append("    // Global variables")
            for var in program.variables:
                var_code = self._convert_variable(var, is_global=True)
                code_lines.append("    " + var_code)
            code_lines.append("")
        
        # Convert functions
        for func in program.functions:
            func_code = self._convert_function(func)
            for line in func_code.split('\n'):
                code_lines.append("    " + line if line else "")
            code_lines.append("")
        
        code_lines.append("}")
        
        csharp_code = '\n'.join(code_lines)
        
        self.logger.info(f"✓ Conversion completed: {len(code_lines)} lines generated")
        
        return csharp_code
    
    def _generate_usings(self) -> List[str]:
        """Generate using directives"""
        return [
            "using System;",
            "using System.Runtime.InteropServices;",
        ]
    
    def _convert_define(self, define: CDefine) -> Optional[str]:
        """
        Convert #define to C# const
        
        Args:
            define: CDefine object
        
        Returns:
            C# const declaration or None if not convertible
        """
        if define.is_function_macro:
            # Function macros are complex, skip for now
            return f"// TODO: Macro {define.name} - requires manual conversion"
        
        # Try to infer type from value
        value = define.value.strip()
        
        # Check if it's a number
        if value.replace('.', '').replace('-', '').isdigit():
            if '.' in value:
                return f"public const double {define.name} = {value};"
            else:
                return f"public const int {define.name} = {value};"
        
        # Check if it's a string
        if value.startswith('"') and value.endswith('"'):
            return f"public const string {define.name} = {value};"
        
        # Default: keep as comment
        return f"// #define {define.name} {value}"
    
    def _convert_enum(self, enum: CEnum) -> str:
        """
        Convert C enum to C# enum
        
        Args:
            enum: CEnum object
        
        Returns:
            C# enum code
        """
        lines = []
        lines.append(f"public enum {enum.name}")
        lines.append("{")
        
        for name, value in enum.values.items():
            lines.append(f"    {name} = {value},")
        
        lines.append("}")
        
        return '\n'.join(lines)
    
    def _convert_struct(self, struct: CStruct) -> str:
        """
        Convert C struct to C# struct
        
        Args:
            struct: CStruct object
        
        Returns:
            C# struct code
        """
        lines = []
        
        # Use [StructLayout] for C interop compatibility
        lines.append("[StructLayout(LayoutKind.Sequential)]")
        lines.append(f"public struct {struct.name}")
        lines.append("{")
        
        for member in struct.members:
            csharp_type = self.type_mapper.map_type(
                member.data_type,
                member.is_pointer,
                member.pointer_level
            )
            lines.append(f"    public {csharp_type} {member.name};")
        
        lines.append("}")
        
        return '\n'.join(lines)
    
    def _convert_variable(self, var: CVariable, is_global: bool = False) -> str:
        """
        Convert C variable to C#
        
        Args:
            var: CVariable object
            is_global: Whether it's a global variable
        
        Returns:
            C# variable declaration
        """
        csharp_type = self.type_mapper.map_type(
            var.data_type,
            var.is_pointer,
            var.pointer_level
        )
        
        # Add modifiers
        modifiers = []
        if is_global:
            modifiers.append("public")
            if var.is_static:
                modifiers.append("static")
        
        if var.is_const:
            modifiers.append("const")
        
        modifier_str = ' '.join(modifiers) if modifiers else ''
        
        # Initial value
        init_str = ""
        if var.initial_value is not None:
            init_str = f" = {var.initial_value}"
        
        return f"{modifier_str} {csharp_type} {var.name}{init_str};".strip()
    
    def _convert_function(self, func: CFunction) -> str:
        """
        Convert C function to C#
        
        Args:
            func: CFunction object
        
        Returns:
            C# function code
        """
        lines = []
        
        # Return type
        return_type = self.type_mapper.map_type(func.return_type)
        
        # Parameters
        params = []
        for param in func.parameters:
            param_type = self.type_mapper.map_type(
                param.data_type,
                param.is_pointer,
                param.pointer_level
            )
            params.append(f"{param_type} {param.name}")
        
        param_str = ', '.join(params)
        
        # Function signature
        modifiers = "public static"
        if func.is_inline:
            modifiers += " inline"  # C# doesn't have inline, but ok
        
        lines.append(f"{modifiers} {return_type} {func.name}({param_str})")
        lines.append("{")
        
        # Function body - convert C code to C#
        # For now, do simple text replacements
        body_lines = self._convert_function_body(func.body)
        for line in body_lines:
            lines.append("    " + line if line.strip() else "")
        
        lines.append("}")
        
        return '\n'.join(lines)
    
    def _convert_function_body(self, c_body: str) -> List[str]:
        """
        Convert C function body to C#
        
        This is a simplified conversion doing text replacements.
        A full implementation would parse the AST and transform it.
        
        Args:
            c_body: C function body code
        
        Returns:
            List of C# code lines
        """
        # Remove outer braces if present
        body = c_body.strip()
        if body.startswith('{'):
            body = body[1:]
        if body.endswith('}'):
            body = body[:-1]
        
        # Simple text replacements
        replacements = {
            'printf': 'Console.WriteLine',
            'scanf': 'Console.ReadLine',
            'malloc': 'new',  # Simplified
            'free': '// GC will handle',  # C# has GC
            'NULL': 'null',
            'nullptr': 'null',
        }
        
        for c_pattern, csharp_pattern in replacements.items():
            body = re.sub(r'\b' + c_pattern + r'\b', csharp_pattern, body)
        
        # Split into lines
        lines = body.split('\n')
        
        # Clean up lines
        cleaned_lines = []
        for line in lines:
            line = line.rstrip()
            if line:
                cleaned_lines.append(line)
        
        return cleaned_lines

