"""
Project-level C to C# Converter
Converts entire C projects (multiple files) to a single C# project
"""
import logging
from typing import List, Dict, Set, Optional
from pathlib import Path

from ..core.models.c_program import CProgram, CFunction, CStruct, CEnum, CDefine, CVariable
from .hybrid_converter import HybridCToCSharpConverter
from .type_mapper import TypeMapper


class ProjectConverter:
    """
    Convert entire C project (multiple files) to C# project
    
    Features:
    - Combines all C files into a single C# project
    - Maintains proper namespace/class structure
    - Handles dependencies between files
    - Preserves function visibility and organization
    """
    
    def __init__(self, converter: Optional[HybridCToCSharpConverter] = None):
        """
        Initialize project converter
        
        Args:
            converter: HybridCToCSharpConverter instance (will create if None)
        """
        self.logger = logging.getLogger(__name__)
        self.converter = converter or HybridCToCSharpConverter()
        self.type_mapper = TypeMapper()
    
    def convert_project(
        self,
        programs: List[CProgram],
        project_name: Optional[str] = None
    ) -> str:
        """
        Convert entire C project to C# code
        
        Args:
            programs: List of CProgram objects representing all C files
            project_name: Optional project name (defaults to first program name)
            
        Returns:
            Complete C# code string with all converted code
        """
        if not programs:
            self.logger.error("No programs provided for conversion")
            return ""
        
        project_name = project_name or programs[0].program_id
        self.logger.info(f"Converting project '{project_name}' with {len(programs)} C files...")
        
        # Step 1: Collect all project components
        all_functions: Dict[str, CFunction] = {}  # func_name -> CFunction
        all_structs: Dict[str, CStruct] = {}
        all_enums: Dict[str, CEnum] = {}
        all_defines: Dict[str, CDefine] = {}
        all_variables: List[CVariable] = []
        
        # Track which file each component comes from
        function_sources: Dict[str, str] = {}  # func_name -> program_id
        
        for program in programs:
            self.logger.debug(f"Processing {program.program_id}: {len(program.functions)} functions")
            
            # Collect functions (check for duplicates)
            for func in program.functions:
                if func.name in all_functions:
                    self.logger.warning(
                        f"Function '{func.name}' already exists (from {function_sources[func.name]}), "
                        f"skipping duplicate from {program.program_id}"
                    )
                else:
                    all_functions[func.name] = func
                    function_sources[func.name] = program.program_id
            
            # Collect structs
            for struct in program.structs:
                if struct.name not in all_structs:
                    all_structs[struct.name] = struct
                else:
                    self.logger.warning(f"Struct '{struct.name}' already exists, skipping duplicate")
            
            # Collect enums
            for enum in program.enums:
                if enum.name not in all_enums:
                    all_enums[enum.name] = enum
                else:
                    self.logger.warning(f"Enum '{enum.name}' already exists, skipping duplicate")
            
            # Collect defines
            for define in program.defines:
                if define.name not in all_defines:
                    all_defines[define.name] = define
                else:
                    self.logger.warning(f"Define '{define.name}' already exists, skipping duplicate")
            
            # Collect global variables
            all_variables.extend(program.variables)
        
        self.logger.info(
            f"Collected: {len(all_functions)} functions, {len(all_structs)} structs, "
            f"{len(all_enums)} enums, {len(all_defines)} defines"
        )
        
        # Step 2: Convert each program individually to get code
        # Then merge into single structure
        converted_chunks: List[str] = []
        
        # Convert each program using the hybrid converter
        for program in programs:
            try:
                self.logger.debug(f"Converting {program.program_id}...")
                csharp_code = self.converter.convert(program)
                converted_chunks.append(csharp_code)
            except Exception as e:
                self.logger.error(f"Failed to convert {program.program_id}: {e}")
                continue
        
        # Step 3: Merge all converted code into single ConvertedCode class
        merged_code = self._merge_converted_code(
            all_functions,
            all_structs,
            all_enums,
            all_defines,
            all_variables,
            converted_chunks
        )
        
        self.logger.info(f"✓ Project conversion completed: {len(merged_code.splitlines())} lines")
        
        return merged_code
    
    def _merge_converted_code(
        self,
        functions: Dict[str, CFunction],
        structs: Dict[str, CStruct],
        enums: Dict[str, CEnum],
        defines: Dict[str, CDefine],
        variables: List[CVariable],
        converted_chunks: List[str]
    ) -> str:
        """
        Merge all converted code chunks into single ConvertedCode class
        
        Args:
            functions: All functions from project
            structs: All structs from project
            enums: All enums from project
            defines: All defines from project
            variables: All global variables
            converted_chunks: List of converted C# code strings
            
        Returns:
            Merged C# code string
        """
        code_lines = []
        
        # Using directives
        code_lines.extend([
            "using System;",
            "using System.Runtime.InteropServices;",
            ""
        ])
        
        # Convert defines (as constants)
        if defines:
            code_lines.append("public class ConvertedCode")
            code_lines.append("{")
            code_lines.append("    // Constants (from #define)")
            for define in defines.values():
                const_code = self._convert_define(define)
                if const_code:
                    code_lines.append("    " + const_code)
            code_lines.append("")
        else:
            code_lines.append("public class ConvertedCode")
            code_lines.append("{")
        
        # Convert enums
        if enums:
            for enum in enums.values():
                enum_code = self._convert_enum(enum)
                for line in enum_code.split('\n'):
                    code_lines.append("    " + line if line else "")
                code_lines.append("")
        
        # Convert structs
        if structs:
            for struct in structs.values():
                struct_code = self._convert_struct(struct)
                for line in struct_code.split('\n'):
                    code_lines.append("    " + line if line else "")
                code_lines.append("")
        
        # Convert global variables
        if variables:
            code_lines.append("    // Global variables")
            for var in variables:
                var_code = self._convert_variable(var, is_global=True)
                code_lines.append("    " + var_code)
            code_lines.append("")
        
        # Extract and merge functions from converted chunks
        # Parse each chunk to extract function definitions
        all_function_code: Dict[str, str] = {}  # func_name -> function code
        
        for chunk in converted_chunks:
            extracted_funcs = self._extract_functions_from_code(chunk)
            for func_name, func_code in extracted_funcs.items():
                if func_name not in all_function_code:
                    all_function_code[func_name] = func_code
                else:
                    self.logger.warning(f"Function '{func_name}' found in multiple chunks, using first")
        
        # Add functions to code
        for func_name in functions.keys():
            if func_name in all_function_code:
                func_code = all_function_code[func_name]
                # Ensure function has 'static' modifier
                func_code = self._ensure_static_modifier(func_code)
                for line in func_code.split('\n'):
                    code_lines.append("    " + line if line else "")
                code_lines.append("")
            else:
                # Generate stub if function not found in converted code
                self.logger.warning(f"Function '{func_name}' not found in converted code, generating stub")
                func = functions[func_name]
                stub_code = self._generate_function_stub(func)
                for line in stub_code.split('\n'):
                    code_lines.append("    " + line if line else "")
                code_lines.append("")
        
        # Close class
        code_lines.append("}")
        
        return '\n'.join(code_lines)
    
    def _extract_functions_from_code(self, csharp_code: str) -> Dict[str, str]:
        """
        Extract function definitions from C# code string
        Handles both normalized code (with ConvertedCode class) and raw function code
        
        Args:
            csharp_code: C# code string
            
        Returns:
            Dict mapping function_name -> function_code
        """
        import re
        functions: Dict[str, str] = {}
        lines = csharp_code.split('\n')
        
        current_func: List[str] = []
        brace_count = 0
        in_function = False
        func_name = None
        in_class = False
        class_brace_level = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Skip using directives
            if stripped.startswith('using '):
                continue
            
            # Track class declarations (but we want to extract functions inside)
            if 'class' in stripped and (stripped.startswith('public class') or stripped.startswith('private class') or stripped.startswith('class')):
                in_class = True
                class_brace_level = 0
                if '{' in stripped:
                    class_brace_level = 1
                continue
            
            # Track class brace level (only when not in a function)
            if in_class and not in_function:
                class_brace_level += line.count('{') - line.count('}')
                if class_brace_level <= 0:
                    in_class = False
                    continue
            
            # Only look for functions when inside a class
            if not in_class and not in_function:
                continue
            
            # Detect function start - look for access modifier + return type + function name + params
            # Pattern: [public|private] [static] returnType funcName(params)
            if not in_function and in_class:
                # More robust function detection - function must be inside class
                func_pattern = r'(?:public|private|protected|internal)\s+(?:static\s+)?(\w+)\s+(\w+)\s*\('
                match = re.search(func_pattern, stripped)
                if match:
                    return_type = match.group(1)
                    potential_func_name = match.group(2)
                    
                    # Exclude keywords that might match
                    if potential_func_name not in ['class', 'enum', 'struct', 'interface', 'namespace', 'const']:
                        in_function = True
                        func_name = potential_func_name
                        current_func = [line]
                        brace_count = stripped.count('{') - stripped.count('}')
                        continue
            
            if in_function:
                current_func.append(line)
                brace_count += line.count('{') - line.count('}')
                
                if brace_count <= 0:
                    # Function complete
                    if func_name:
                        func_code = '\n'.join(current_func)
                        # Remove class-level indentation if present (typically 4 spaces)
                        func_code = re.sub(r'^    ', '', func_code, flags=re.MULTILINE)
                        functions[func_name] = func_code
                    in_function = False
                    current_func = []
                    func_name = None
        
        return functions
    
    def _ensure_static_modifier(self, func_code: str) -> str:
        """Ensure function has 'static' modifier"""
        lines = func_code.split('\n')
        if lines:
            first_line = lines[0].strip()
            if 'static' not in first_line and ('public' in first_line or 'private' in first_line):
                lines[0] = lines[0].replace('public ', 'public static ', 1)
                lines[0] = lines[0].replace('private ', 'private static ', 1)
        return '\n'.join(lines)
    
    def _generate_function_stub(self, func: CFunction) -> str:
        """Generate C# function stub"""
        return_type = self.type_mapper.map_type(func.return_type)
        params = ', '.join(
            f"{self.type_mapper.map_type(p.data_type, p.is_pointer, p.pointer_level)} {p.name}"
            for p in func.parameters
        )
        
        return f"public static {return_type} {func.name}({params})\n{{\n    throw new NotImplementedException();\n}}"
    
    def _convert_define(self, define: CDefine) -> Optional[str]:
        """Convert #define to C# const"""
        if define.is_function_macro:
            return f"// TODO: Macro {define.name} - requires manual conversion"
        
        value = define.value.strip()
        if value.replace('.', '').replace('-', '').isdigit():
            if '.' in value:
                return f"public const double {define.name} = {value};"
            else:
                return f"public const int {define.name} = {value};"
        
        if value.startswith('"') and value.endswith('"'):
            return f"public const string {define.name} = {value};"
        
        return f"// #define {define.name} {value}"
    
    def _convert_enum(self, enum: CEnum) -> str:
        """Convert C enum to C# enum"""
        lines = [f"public enum {enum.name}", "{"]
        for name, value in enum.values.items():
            lines.append(f"    {name} = {value},")
        lines.append("}")
        return '\n'.join(lines)
    
    def _convert_struct(self, struct: CStruct) -> str:
        """Convert C struct to C# struct"""
        lines = [
            "[StructLayout(LayoutKind.Sequential)]",
            f"public struct {struct.name}",
            "{"
        ]
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
        """Convert C variable to C#"""
        csharp_type = self.type_mapper.map_type(
            var.data_type,
            var.is_pointer,
            var.pointer_level
        )
        
        modifiers = []
        if is_global:
            modifiers.append("public")
            if var.is_static:
                modifiers.append("static")
        if var.is_const:
            modifiers.append("const")
        
        modifier_str = ' '.join(modifiers) if modifiers else ''
        init_str = f" = {var.initial_value}" if var.initial_value is not None else ""
        
        return f"{modifier_str} {csharp_type} {var.name}{init_str};".strip()

