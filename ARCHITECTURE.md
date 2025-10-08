# Kiến trúc Hệ thống Migration Pipeline

## 📐 Tổng quan Kiến trúc

Hệ thống được thiết kế theo kiến trúc **layered architecture** với các thành phần loosely coupled, cho phép dễ dàng test và mở rộng.

```
┌─────────────────────────────────────────────────────┐
│              CLI Layer (main.py)                    │
│  - Command-line interface                           │
│  - User interaction                                 │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│         Orchestrator Layer                          │
│  - MigrationOrchestrator                           │
│  - Workflow coordination                            │
│  - Retry logic                                      │
└─────────────────────┬───────────────────────────────┘
                      │
         ┌────────────┼────────────┐
         │            │            │
┌────────▼─────┐ ┌───▼──────┐ ┌──▼─────────┐
│   Parser     │ │Converter │ │  Validator │
│   Layer      │ │  Layer   │ │   Layer    │
└──────────────┘ └──────────┘ └────────────┘
         │            │            │
┌────────▼─────┐ ┌───▼──────┐ ┌──▼─────────┐
│ Dependency   │ │Test Gen  │ │Test Runner │
│  Analyzer    │ │  Layer   │ │   Layer    │
└──────────────┘ └──────────┘ └────────────┘
         │            │            │
         └────────────┼────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│          Core Models Layer                          │
│  - CProgram, DependencyGraph                        │
│  - TestCase, ConversionResult                       │
└─────────────────────────────────────────────────────┘
```

## 🔄 Workflow Chi tiết (Theo Sơ đồ)

### Phase 1: Initialization
```
Start
  ↓
Parse C Programs ──→ CParser
  ↓
Build Dependency Graph ──→ DependencyAnalyzer
  ↓
Check Circular Dependencies
  ↓
Get Conversion Order (Topological Sort)
```

### Phase 2: Main Loop (Per Component)
```
FOR each component in conversion_order:
  │
  ├─ Step 1: Check Dependencies
  │   └─ All dependencies converted? → YES: Continue, NO: Skip
  │
  ├─ Step 2: Generate Test Cases
  │   ├─ TestGenerator.generate_tests()
  │   ├─ Boundary tests
  │   ├─ Edge cases
  │   └─ Random tests
  │
  ├─ Step 3: Run C Tests (Baseline)
  │   ├─ Build C test harness
  │   ├─ CTestRunner.compile()
  │   ├─ CTestRunner.run_tests()
  │   └─ Capture baseline outputs
  │
  ├─ Step 4: Convert C to C#
  │   ├─ CToC#Converter.parse_c()
  │   ├─ Build AST
  │   ├─ Transform AST
  │   ├─ Generate C# code
  │   └─ Generate C# test harness
  │
  ├─ Step 5: Run C# Tests
  │   ├─ CSharpTestRunner.compile()
  │   ├─ CSharpTestRunner.run_tests()
  │   └─ Capture C# outputs
  │
  ├─ Step 6: Validate Outputs
  │   ├─ OutputValidator.compare(c_output, cs_output)
  │   ├─ Check tolerance for floats
  │   └─ Generate diff report
  │
  ├─ Step 7: Decision Point
  │   ├─ All tests pass? → YES: Mark as converted, Continue
  │   └─ Tests fail? → NO: Retry (max 3 times) or Mark as failed
  │
  └─ Update dependency graph
END FOR
```

### Phase 3: Finalization
```
Generate Migration Report
  ├─ HTML Report
  ├─ JSON Report
  └─ Markdown Summary
  ↓
Display Statistics
  ↓
End
```

## 📦 Các Thành phần Chính

### 1. Parser Layer
**Trách nhiệm**: Parse C source code thành AST

**Modules**:
- `c_parser.py`: Main parser using pycparser
- `ast_builder.py`: Build custom AST representation
- `symbol_extractor.py`: Extract functions, variables, structs

**Input**: C source files (.c, .h)
**Output**: `CProgram` objects with parsed components

### 2. Dependency Analyzer Layer
**Trách nhiệm**: Phân tích dependencies và xác định thứ tự conversion

**Modules**:
- `dependency_service.py`: Main service
- `graph_builder.py`: Build dependency graph
- `cycle_detector.py`: Detect circular dependencies

**Algorithms**:
- DFS for cycle detection
- Kahn's algorithm for topological sort

### 3. Test Generator Layer
**Trách nhiệm**: Tạo test cases tự động

**Modules**:
- `test_generator.py`: Main generator
- `input_generator.py`: Generate test inputs
  - Boundary values
  - Edge cases
  - Random values
- `test_harness_builder.py`: Build test scaffolding

**Strategies**:
- **Boundary Testing**: Min/max values, zero, negative
- **Edge Cases**: NULL pointers, empty arrays
- **Random Testing**: Fuzzing with seed

### 4. Converter Layer
**Trách nhiệm**: Convert C code to C#

**Modules**:
- `c_to_csharp_converter.py`: Main converter
- `type_mapper.py`: Map C types to C# types
  - Primitives: int → int, char → byte
  - Pointers: int* → ref int or IntPtr
  - Arrays: int[] → int[]
  - Structs: struct → class/struct
- `syntax_transformer.py`: Transform C syntax to C#
  - Functions: void func() → public static void Func()
  - Control flow: for/while → same but C# style
  - Memory: malloc/free → new/GC
- `code_generator.py`: Generate C# code from AST

**Conversion Rules**:
```
C                          C#
--------------------------------------------
int x;                  → int x;
int *p;                 → ref int p; (or IntPtr)
struct Point { }        → public struct Point { }
void func()             → public static void Func()
malloc(size)            → new byte[size]
printf()                → Console.WriteLine()
NULL                    → null
#define MAX 100         → const int MAX = 100;
typedef struct { } T    → public struct T { }
```

### 5. Test Runner Layer
**Trách nhiệm**: Compile và run tests

**Modules**:
- `c_test_runner.py`: Run C tests
  - Compile with GCC
  - Execute binary
  - Capture stdout/stderr
- `csharp_test_runner.py`: Run C# tests
  - Compile with dotnet/csc
  - Execute assembly
  - Capture outputs
- `compiler_wrapper.py`: Wrapper cho compilers

**Process**:
1. Generate test harness file
2. Compile with inputs embedded
3. Execute
4. Parse output
5. Return TestResult

### 6. Validator Layer
**Trách nhiệm**: So sánh outputs giữa C và C#

**Modules**:
- `output_validator.py`: Main validator
- `diff_generator.py`: Generate detailed diffs
- `tolerance_checker.py`: Handle floating-point comparison

**Validation Logic**:
```python
def validate(c_output, cs_output):
    for key in c_output:
        c_val = c_output[key]
        cs_val = cs_output[key]
        
        if isinstance(c_val, float):
            # Floating point comparison with tolerance
            if abs(c_val - cs_val) > tolerance:
                report_difference()
        elif isinstance(c_val, str):
            # String comparison
            if c_val != cs_val:
                report_difference()
        else:
            # Exact comparison
            if c_val != cs_val:
                report_difference()
```

### 7. Report Generator Layer
**Trách nhiệm**: Tạo báo cáo conversion

**Modules**:
- `report_service.py`: Main service
- `html_reporter.py`: Generate HTML report
- `json_reporter.py`: Generate JSON report
- `markdown_reporter.py`: Generate Markdown

**Report Contents**:
- Summary statistics
- Per-component results
- Test pass/fail details
- Conversion issues
- Code metrics

### 8. Orchestrator Layer
**Trách nhiệm**: Điều phối toàn bộ workflow

**Modules**:
- `migration_orchestrator.py`: Main orchestrator
- `pipeline.py`: Pipeline execution
- `retry_handler.py`: Handle retry logic

**Features**:
- Component selection based on dependencies
- Retry logic (max 3 attempts)
- Error handling
- Progress tracking
- Logging

## 🔐 Core Models

### CProgram
Đại diện cho một C source file với tất cả components:
- Functions
- Variables
- Structs/Unions/Enums
- Includes/Defines
- Dependencies

### DependencyGraph
Graph structure quản lý dependencies:
- Nodes: Programs
- Edges: Dependencies
- Operations:
  - Add node
  - Mark as converted
  - Get ready to convert
  - Detect cycles
  - Topological sort

### TestCase & TestResult
Test case với inputs/outputs và kết quả execution

### ValidationResult
Kết quả so sánh giữa C và C# outputs

### ConversionResult
Kết quả conversion của một component với:
- Status (success/failed)
- Issues (errors/warnings)
- Metrics (LOC, complexity, test pass rate)
- Retry count

## 🚀 Extension Points

Hệ thống được thiết kế để dễ dàng extend:

1. **Custom Parsers**: Implement parser cho C dialects khác
2. **Custom Converters**: Thêm converters cho ngôn ngữ khác (C to Java, etc.)
3. **Custom Test Generators**: Thêm strategies khác (property-based testing)
4. **Custom Validators**: Thêm validation rules
5. **Plugins**: Plugin system cho custom transformations

## 🎯 Design Patterns

1. **Strategy Pattern**: Test generation strategies
2. **Factory Pattern**: Create parsers, converters
3. **Observer Pattern**: Progress notifications
4. **Template Method**: Conversion pipeline steps
5. **Dependency Injection**: All services injected

## 📊 Data Flow

```
C Source Files
      ↓
   [Parser]
      ↓
  CProgram Objects
      ↓
[Dependency Analyzer]
      ↓
Dependency Graph
      ↓
[Orchestrator Loop]
      ↓
  ┌─────────────┐
  │ Component   │
  └──────┬──────┘
         ↓
  [Test Generator]
         ↓
    Test Cases
         ↓
  [C Test Runner] ──→ Baseline Outputs
         ↓
    [Converter]
         ↓
     C# Code
         ↓
[C# Test Runner] ──→ C# Outputs
         ↓
    [Validator]
         ↓
 Validation Results
         ↓
[Report Generator]
         ↓
  HTML/JSON Reports
```

## 🔧 Configuration

Tất cả settings được config qua YAML:
- Compiler settings
- Test generation settings
- Conversion rules
- Validation tolerances
- Output formats

## 📈 Performance Considerations

1. **Caching**: Cache parsed ASTs
2. **Parallel Processing**: Convert independent components in parallel
3. **Incremental**: Only reprocess changed files
4. **Memory**: Stream large files, don't load all into memory

## 🧪 Testing Strategy

1. **Unit Tests**: Test mỗi module riêng lẻ
2. **Integration Tests**: Test workflow end-to-end
3. **Golden Tests**: Compare known good conversions
4. **Performance Tests**: Benchmark với large codebases

