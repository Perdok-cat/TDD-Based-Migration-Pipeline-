# Implementation Guide

## 🎯 Hướng dẫn triển khai chi tiết

Document này cung cấp hướng dẫn từng bước để implement các services còn thiếu trong hệ thống.

## 📋 Checklist triển khai

### Phase 1: Core Infrastructure (Đã hoàn thành ✓)
- [x] Core models (CProgram, DependencyGraph, TestCase, etc.)
- [x] Orchestrator skeleton
- [x] CLI interface
- [x] Configuration system
- [x] Project structure

### Phase 2: Parser & Analyzer (Cần triển khai)
- [ ] C Parser implementation
- [ ] AST Builder
- [ ] Symbol Extractor
- [ ] Dependency Analyzer
- [ ] Tests for parser

### Phase 3: Test Generation (Cần triển khai)
- [ ] Test Generator
- [ ] Input Generator (boundary, edge case, random)
- [ ] Test Harness Builder
- [ ] Tests for test generation

### Phase 4: Converter (Cần triển khai)
- [ ] Type Mapper
- [ ] Syntax Transformer
- [ ] Code Generator
- [ ] C to C# Converter
- [ ] Tests for converter

### Phase 5: Test Runners (Cần triển khai)
- [ ] Compiler Wrapper
- [ ] C Test Runner
- [ ] C# Test Runner
- [ ] Tests for runners

### Phase 6: Validator (Cần triển khai)
- [ ] Output Validator
- [ ] Diff Generator
- [ ] Tolerance Checker
- [ ] Tests for validator

### Phase 7: Report Generator (Cần triển khai)
- [ ] HTML Reporter
- [ ] JSON Reporter
- [ ] Markdown Reporter
- [ ] Report Service
- [ ] Tests for reports

### Phase 8: Integration & Polish
- [ ] End-to-end tests
- [ ] Performance optimization
- [ ] Documentation
- [ ] Examples

## 🔨 Chi tiết triển khai từng module

### 1. Parser Implementation

#### 1.1 C Parser (`src/parser/c_parser.py`)

```python
from pycparser import parse_file, c_ast
from ..core.models import CProgram, CFunction, CVariable

class CParser:
    def __init__(self, config=None):
        self.config = config or {}
    
    def parse_file(self, file_path: str) -> CProgram:
        """Parse a C file into CProgram"""
        # Use pycparser to parse
        ast = parse_file(file_path, use_cpp=True)
        
        # Extract components
        program = CProgram(
            program_id=self._extract_program_id(file_path),
            file_path=file_path,
            source_code=self._read_file(file_path)
        )
        
        # Visit AST and extract
        visitor = CProgramVisitor()
        visitor.visit(ast)
        
        program.functions = visitor.functions
        program.variables = visitor.variables
        program.structs = visitor.structs
        # ... etc
        
        return program
    
    def parse_directory(self, dir_path: str) -> List[CProgram]:
        """Parse all C files in directory"""
        programs = []
        for file_path in self._find_c_files(dir_path):
            try:
                program = self.parse_file(file_path)
                programs.append(program)
            except Exception as e:
                logger.error(f"Failed to parse {file_path}: {e}")
        return programs
```

**Dependencies**: `pycparser`

**Key tasks**:
1. Use pycparser để parse C code thành AST
2. Traverse AST để extract functions, variables, structs
3. Handle #include, #define directives
4. Extract function calls để build dependencies

**Testing**:
- Test với simple C files
- Test với complex C files (pointers, structs)
- Test error handling

---

### 2. Dependency Analyzer

#### 2.1 Dependency Service (`src/dependency_analyzer/dependency_service.py`)

```python
class DependencyAnalyzerService:
    def analyze_dependencies(
        self, 
        programs: List[CProgram]
    ) -> DependencyGraph:
        """Build dependency graph from programs"""
        graph = DependencyGraph()
        
        for program in programs:
            # Extract dependencies from includes and function calls
            deps = self._extract_dependencies(program)
            graph.add_node(program.program_id, deps)
        
        return graph
    
    def _extract_dependencies(
        self, 
        program: CProgram
    ) -> List[str]:
        """Extract dependencies from a program"""
        deps = set()
        
        # From #include directives
        for include in program.includes:
            if not include.is_system:
                deps.add(self._normalize_include(include.file_name))
        
        # From function calls to external functions
        all_local_functions = set(program.get_all_function_names())
        for function in program.functions:
            for called in function.called_functions:
                if called not in all_local_functions:
                    deps.add(called)
        
        return list(deps)
```

**Key tasks**:
1. Extract dependencies từ #include
2. Extract dependencies từ function calls
3. Build dependency graph
4. Detect circular dependencies
5. Calculate conversion order

---

### 3. Test Generator

#### 3.1 Test Generator (`src/test_generator/test_generator.py`)

```python
class TestGenerator:
    def generate_tests(
        self, 
        program: CProgram
    ) -> TestSuite:
        """Generate test cases for a program"""
        suite = TestSuite(program_id=program.program_id)
        
        for function in program.functions:
            # Generate tests for each function
            tests = self._generate_tests_for_function(function)
            for test in tests:
                suite.add_test_case(test)
        
        return suite
    
    def _generate_tests_for_function(
        self, 
        function: CFunction
    ) -> List[TestCase]:
        """Generate test cases for a function"""
        tests = []
        
        # Boundary tests
        tests.extend(self._generate_boundary_tests(function))
        
        # Edge cases
        tests.extend(self._generate_edge_case_tests(function))
        
        # Random tests
        if self.config.get('random_testing', True):
            tests.extend(self._generate_random_tests(function))
        
        return tests
    
    def _generate_boundary_tests(
        self, 
        function: CFunction
    ) -> List[TestCase]:
        """Generate boundary value tests"""
        # For each parameter, generate min/max/zero tests
        # Example: for int parameter, test with 0, INT_MIN, INT_MAX
        pass
```

**Key tasks**:
1. Analyze function signature để determine test inputs
2. Generate boundary value tests
3. Generate edge case tests (NULL, zero, empty)
4. Generate random tests với seed
5. Build test harness code

---

### 4. C to C# Converter

#### 4.1 Type Mapper (`src/converter/type_mapper.py`)

```python
class TypeMapper:
    """Map C types to C# types"""
    
    DEFAULT_MAPPINGS = {
        'int': 'int',
        'long': 'long',
        'short': 'short',
        'char': 'byte',
        'float': 'float',
        'double': 'double',
        'void': 'void',
        'unsigned int': 'uint',
        'unsigned long': 'ulong',
        'unsigned short': 'ushort',
        'unsigned char': 'byte',
    }
    
    def map_type(self, c_type: str, is_pointer: bool = False) -> str:
        """Map C type to C# type"""
        base_type = self.DEFAULT_MAPPINGS.get(c_type, c_type)
        
        if is_pointer:
            # Option 1: Use ref/out
            # Option 2: Use IntPtr
            # Option 3: Use unsafe pointer
            if self.config.get('use_unsafe_code', False):
                return f"{base_type}*"
            else:
                return f"ref {base_type}"
        
        return base_type
```

#### 4.2 C to C# Converter (`src/converter/c_to_csharp_converter.py`)

```python
class CToC#Converter:
    def convert(self, program: CProgram) -> str:
        """Convert C program to C# code"""
        
        # Build C# code structure
        csharp_code = []
        
        # Add using statements
        csharp_code.append("using System;")
        csharp_code.append("")
        
        # Add namespace
        csharp_code.append(f"namespace {self._get_namespace(program)}")
        csharp_code.append("{")
        
        # Add class
        class_name = self._get_class_name(program)
        csharp_code.append(f"    public class {class_name}")
        csharp_code.append("    {")
        
        # Convert structs
        for struct in program.structs:
            csharp_code.extend(self._convert_struct(struct))
        
        # Convert functions
        for function in program.functions:
            csharp_code.extend(self._convert_function(function))
        
        # Close class and namespace
        csharp_code.append("    }")
        csharp_code.append("}")
        
        return "\n".join(csharp_code)
    
    def _convert_function(self, function: CFunction) -> List[str]:
        """Convert C function to C# method"""
        lines = []
        
        # Convert return type
        return_type = self.type_mapper.map_type(function.return_type)
        
        # Convert parameters
        params = []
        for param in function.parameters:
            param_type = self.type_mapper.map_type(
                param.data_type, 
                param.is_pointer
            )
            params.append(f"{param_type} {param.name}")
        
        # Build method signature
        method_name = self._to_pascal_case(function.name)
        signature = (
            f"        public static {return_type} "
            f"{method_name}({', '.join(params)})"
        )
        lines.append(signature)
        lines.append("        {")
        
        # Convert body
        body = self._convert_function_body(function.body)
        lines.extend(f"            {line}" for line in body)
        
        lines.append("        }")
        lines.append("")
        
        return lines
```

**Key tasks**:
1. Map C types to C# types
2. Convert C syntax to C# syntax
3. Handle pointers (unsafe code hoặc ref/out)
4. Convert structs to classes/structs
5. Convert function calls
6. Handle memory management (malloc → new)

---

### 5. Test Runners

#### 5.1 C Test Runner (`src/test_runner/c_test_runner.py`)

```python
class CTestRunner:
    def compile(self, test_harness_code: str) -> Path:
        """Compile C test harness"""
        # Write code to temp file
        temp_file = self._write_temp_file(test_harness_code, ".c")
        output_file = temp_file.with_suffix(".exe")
        
        # Compile with GCC
        cmd = [
            self.config['c_compiler'],
            *self.config['c_compiler_flags'],
            str(temp_file),
            "-o", str(output_file)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.get('timeout_seconds', 30)
        )
        
        if result.returncode != 0:
            raise CompilationError(result.stderr)
        
        return output_file
    
    def run_tests(
        self, 
        test_suite: TestSuite
    ) -> Dict[str, TestResult]:
        """Run all tests and return results"""
        results = {}
        
        for test_case in test_suite.test_cases:
            result = self._run_single_test(test_case)
            results[test_case.id] = result
        
        return results
    
    def _run_single_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        result = TestResult(test_case_id=test_case.id)
        result.started_at = datetime.now()
        
        try:
            # Build test harness with this test case
            harness = self._build_test_harness(test_case)
            
            # Compile
            executable = self.compile(harness)
            
            # Run
            proc_result = subprocess.run(
                [str(executable)],
                capture_output=True,
                text=True,
                timeout=self.config.get('timeout_seconds', 30)
            )
            
            # Parse output
            outputs = self._parse_output(proc_result.stdout)
            result.mark_success(outputs)
            
        except Exception as e:
            result.mark_error(str(e))
        
        return result
```

**Key tasks**:
1. Build test harness từ test cases
2. Compile C code với GCC
3. Execute compiled binary
4. Capture và parse outputs
5. Handle timeouts và errors

---

### 6. Output Validator

#### 6.1 Output Validator (`src/validator/output_validator.py`)

```python
class OutputValidator:
    def validate(
        self,
        test_suite: TestSuite,
        c_results: Dict[str, TestResult],
        csharp_results: Dict[str, TestResult]
    ) -> List[ValidationResult]:
        """Validate C vs C# outputs"""
        validation_results = []
        
        for test_case in test_suite.test_cases:
            c_result = c_results.get(test_case.id)
            cs_result = csharp_results.get(test_case.id)
            
            validation = self._validate_single_test(
                test_case, 
                c_result, 
                cs_result
            )
            validation_results.append(validation)
        
        return validation_results
    
    def _validate_single_test(
        self,
        test_case: TestCase,
        c_result: TestResult,
        cs_result: TestResult
    ) -> ValidationResult:
        """Validate a single test"""
        validation = ValidationResult(test_case_id=test_case.id)
        validation.c_result = c_result
        validation.csharp_result = cs_result
        
        # Compare outputs
        c_outputs = c_result.outputs
        cs_outputs = cs_result.outputs
        
        validation.total_outputs = len(c_outputs)
        
        for key in c_outputs:
            c_val = c_outputs[key]
            cs_val = cs_outputs.get(key)
            
            if self._values_match(c_val, cs_val):
                validation.matching_outputs += 1
            else:
                diff = OutputDifference(
                    variable_name=key,
                    c_value=c_val,
                    csharp_value=cs_val,
                    is_critical=True
                )
                validation.differences.append(diff)
                validation.different_outputs += 1
        
        validation.is_match = (validation.different_outputs == 0)
        
        return validation
    
    def _values_match(self, c_val, cs_val) -> bool:
        """Check if two values match"""
        if isinstance(c_val, float) and isinstance(cs_val, float):
            tolerance = self.config.get('floating_point_tolerance', 1e-6)
            return abs(c_val - cs_val) < tolerance
        else:
            return c_val == cs_val
```

---

## 🧪 Testing Strategy

Mỗi module cần có comprehensive tests:

### Unit Tests
```python
# tests/unit/test_type_mapper.py
def test_map_basic_types():
    mapper = TypeMapper()
    assert mapper.map_type('int') == 'int'
    assert mapper.map_type('char') == 'byte'

def test_map_pointer_types():
    mapper = TypeMapper(config={'use_unsafe_code': False})
    assert mapper.map_type('int', is_pointer=True) == 'ref int'
```

### Integration Tests
```python
# tests/integration/test_conversion_pipeline.py
def test_full_conversion():
    # Given
    c_code = """
    int add(int a, int b) {
        return a + b;
    }
    """
    
    # When
    parser = CParser()
    converter = CToC#Converter()
    program = parser.parse_string(c_code)
    csharp_code = converter.convert(program)
    
    # Then
    assert 'public static int Add' in csharp_code
```

---

## 📚 Resources

### C Parsing
- pycparser documentation: https://github.com/eliben/pycparser
- C11 standard: https://www.iso-9899.info/wiki/The_Standard

### C# Code Generation
- Roslyn: https://github.com/dotnet/roslyn
- C# language spec: https://docs.microsoft.com/en-us/dotnet/csharp/

### Testing
- pytest: https://docs.pytest.org/
- unittest: https://docs.python.org/3/library/unittest.html

---

## 🎯 Priority Order

Đề xuất thứ tự implement:

1. **Parser** (cao nhất) - Cần để parse C code
2. **Dependency Analyzer** - Cần để xác định conversion order
3. **Converter** - Core functionality
4. **Test Generator** - Cần để generate tests
5. **Test Runners** - Cần để run tests
6. **Validator** - Cần để validate results
7. **Report Generator** - Cuối cùng

---

## 💡 Tips

1. **Start small**: Implement với simple C code trước
2. **Test early**: Viết tests ngay từ đầu
3. **Iterate**: Implement incrementally, test frequently
4. **Document**: Document assumptions và edge cases
5. **Review**: Code review với team

## 🔗 Next Steps

1. Pick một module để start (recommend: Parser)
2. Read tài liệu liên quan
3. Write skeleton code
4. Write tests
5. Implement functionality
6. Test thoroughly
7. Move to next module

Good luck! 🚀

