# Flow Chạy Hiện Tại - C to C# Migration System

## Tổng Quan
Hệ thống convert toàn bộ C project (nhiều files) thành một C# project với TDD-based approach.

---

## Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENTRY POINT: main.py                         │
│                  python main.py migrate -i <dir>                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│          1. LOAD CONFIGURATION                                   │
│  - Load config.yaml (Gemini API key, converter settings)         │
│  - Merge CLI options với YAML config                            │
│  - Initialize MigrationOrchestrator                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│          2. PARSE C PROGRAMS                                    │
│  MigrationOrchestrator.migrate_all()                             │
│                                                                  │
│  → _parse_c_programs(input_dir)                                 │
│    ├─ CParser.find_c_files() - Tìm tất cả .c/.h files          │
│    ├─ CParser.parse_file() - Parse từng file                    │
│    ├─ Extract: includes, functions, structs, enums, defines     │
│    └─ Tạo CProgram objects cho mỗi file                         │
│                                                                  │
│  Output: List[CProgram] - Tất cả C files đã được parse         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│          3. ANALYZE DEPENDENCIES                                │
│  → _analyze_dependencies()                                      │
│    ├─ DependenciesAnalysis.analyze_dependencies()               │
│    ├─ Build dependency graph từ includes và function calls     │
│    ├─ Detect circular dependencies                              │
│    └─ Determine conversion order (nếu cần)                      │
│                                                                  │
│  Output: DependencyGraph - Thông tin dependencies giữa files    │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│          4. CONVERT ENTIRE PROJECT                             │
│  → _convert_project_with_retry(programs, output_dir)            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 4.1 GENERATE TEST CASES                                   │  │
│  │    → _generate_tests(program) cho từng file               │  │
│  │      ├─ TestGenerator.generate_tests()                    │  │
│  │      ├─ Generate test cases cho mỗi function              │  │
│  │      └─ Combine tất cả test cases vào TestSuite          │  │
│  │                                                             │  │
│  │    Output: Combined TestSuite với tất cả test cases       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 4.2 RUN C TESTS (BASELINE)                                │  │
│  │    → _run_c_tests(program, test_suite) cho từng file      │  │
│  │      ├─ TestGenerator.generate_test_harness_c()          │  │
│  │      ├─ CTestRunner.run_tests()                           │  │
│  │      │  ├─ Compile C code với GCC                         │  │
│  │      │  ├─ Execute binary                                 │  │
│  │      │  └─ Parse output → TestResult objects              │  │
│  │      └─ Combine results từ tất cả files                   │  │
│  │                                                             │  │
│  │    Output: Dict[test_id → TestResult] - Baseline outputs   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 4.3 CONVERT TO C#                                         │  │
│  │    → project_converter.convert_project(programs)          │  │
│  │                                                             │  │
│  │    ProjectConverter.convert_project():                    │  │
│  │    ├─ Collect all components từ tất cả programs:         │  │
│  │    │  ├─ all_functions: Dict[func_name → CFunction]       │  │
│  │    │  ├─ all_structs: Dict[struct_name → CStruct]         │  │
│  │    │  ├─ all_enums: Dict[enum_name → CEnum]               │  │
│  │    │  ├─ all_defines: Dict[define_name → CDefine]         │  │
│  │    │  └─ all_variables: List[CVariable]                    │  │
│  │    │                                                         │  │
│  │    ├─ Convert từng program bằng HybridConverter:           │  │
│  │    │  └─ converter.convert(program) → C# code              │  │
│  │    │                                                         │  │
│  │    └─ Merge converted code:                                │  │
│  │      └─ _merge_converted_code()                            │  │
│  │        ├─ Extract functions từ converted chunks            │  │
│  │        ├─ Create single ConvertedCode class               │  │
│  │        ├─ Add all structs, enums, defines                  │  │
│  │        └─ Add all functions với static modifier            │  │
│  │                                                             │  │
│  │    Output: Complete C# code string                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 4.4 RUN C# TESTS                                          │  │
│  │    → _run_csharp_tests(combined_program, test_suite, code)│  │
│  │      ├─ CSharpTestRunner.generate_test_harness_csharp()   │  │
│  │      │  └─ Generate Program.cs với Main()                  │  │
│  │      │    └─ Call ConvertedCode.{func_name}() cho mỗi test│  │
│  │      │                                                      │  │
│  │      ├─ CSharpTestRunner.run_tests()                       │  │
│  │      │  ├─ Write ConvertedCode.cs và Program.cs           │  │
│  │      │  ├─ Compile với dotnet build                        │  │
│  │      │  ├─ Execute với dotnet run                          │  │
│  │      │  └─ Parse output → TestResult objects               │  │
│  │      │                                                      │  │
│  │      └─ Return Dict[test_id → TestResult]                  │  │
│  │                                                             │  │
│  │    Output: Dict[test_id → TestResult] - C# test outputs   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 4.5 VALIDATE OUTPUTS                                     │  │
│  │    → _validate_outputs(test_suite, c_results, csharp_results)││
│  │      └─ OutputValidator.validate()                        │  │
│  │        ├─ Compare C output vs C# output cho mỗi test     │  │
│  │        └─ Return ValidationResult objects                 │  │
│  │                                                             │  │
│  │    Output: List[ValidationResult] - Validation results     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 4.6 CHECK RESULTS                                         │  │
│  │    ├─ Nếu tất cả tests passed → SUCCESS                   │  │
│  │    ├─ Nếu có tests failed và còn retries → Retry          │  │
│  │    └─ Nếu hết retries → FAILED                             │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│          5. GENERATE REPORT                                     │
│  → _generate_reports(output_dir)                                │
│    └─ Create migration report (HTML/JSON/Markdown)               │
│                                                                  │
│  Output: MigrationReport với statistics                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXIT                                         │
│  - Display summary                                              │
│  - Return exit code (0 = success, 1 = failed)                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Chi Tiết Các Components

### 1. Entry Point (`main.py`)
- **Command**: `python main.py migrate -i <input_dir> -o <output_dir>`
- **Tasks**:
  - Load configuration từ `config/config.yaml`
  - Parse CLI arguments
  - Initialize `MigrationOrchestrator`
  - Run migration pipeline
  - Display results

### 2. Migration Orchestrator (`migration_orchestrator.py`)
- **Main Method**: `migrate_all(input_dir, output_dir)`
- **Workflow**:
  1. Parse tất cả C files → `List[CProgram]`
  2. Analyze dependencies → `DependencyGraph`
  3. Convert entire project → `_convert_project_with_retry()`
  4. Generate report

### 3. Project Converter (`project_converter.py`)
- **Main Method**: `convert_project(programs, project_name)`
- **Process**:
  1. **Collect**: Gộp tất cả components từ các C programs
  2. **Convert**: Convert từng program bằng `HybridConverter`
  3. **Merge**: Trích xuất và merge functions vào một `ConvertedCode` class
  4. **Output**: Complete C# code string

### 4. Test Generator (`test_generator.py`)
- **Purpose**: Generate test cases cho các functions
- **Strategies**:
  - Boundary testing
  - Edge cases
  - Random testing
  - Symbolic execution (KLEE)

### 5. Test Runners
- **CTestRunner**: Compile và run C tests, capture outputs
- **CSharpTestRunner**: Generate test harness, compile C#, run tests

### 6. Output Validator (`output_validator.py`)
- **Purpose**: So sánh outputs từ C và C# tests
- **Output**: `ValidationResult` objects với pass/fail status

---

## File Structure Sau Conversion

```
generated_csharp/
├── ConvertedCode.cs        # Tất cả converted code (từ tất cả C files)
│   ├── using directives
│   ├── Constants (từ #define)
│   ├── Enums
│   ├── Structs
│   └── Functions (tất cả functions từ project)
│
├── Program.cs              # Test harness với Main()
│   └── Calls ConvertedCode.{func_name}() cho mỗi test
│
└── generated_csharp.csproj  # .NET project file
```

---

## Key Differences So Với Version Cũ

### ❌ Version Cũ (File-by-file)
- Convert từng C file riêng lẻ
- Mỗi file → một ConversionResult riêng
- Không merge functions
- Test từng file độc lập

### ✅ Version Mới (Project-level)
- Convert toàn bộ project cùng lúc
- Tất cả files → một ConversionResult
- Merge tất cả functions vào `ConvertedCode` class
- Test toàn bộ project như một unit

---

## Retry Logic

Mỗi conversion attempt có thể retry tối đa `max_retries` lần (mặc định: 3):
- Nếu validation failed → retry với cùng parameters
- Nếu compilation failed → retry
- Nếu exception → retry

---

## Output Files

### Generated C# Files
- `generated_csharp/ConvertedCode.cs`: Tất cả converted code
- `generated_csharp/Program.cs`: Test harness
- `generated_csharp/generated_csharp.csproj`: Project file

### Reports (nếu enabled)
- `output/reports/migration_report.html`
- `output/reports/migration_report.json`
- `output/reports/migration_report.md`

---

## Error Handling

1. **Parse Errors**: Skip file, log warning, continue với files khác
2. **Compilation Errors**: Log error, retry (nếu còn retries)
3. **Test Failures**: Compare với baseline, retry conversion
4. **Validation Failures**: Mark test as failed, continue với tests khác

---

## Performance Considerations

- **Parallel Processing**: Có thể enable (chưa implement đầy đủ)
- **Caching**: Gemini converter có caching mechanism
- **Rate Limiting**: Gemini API có rate limiting configurable

---

## Example Run

```bash
$ python main.py migrate -i examples/test_project -o output/converted

[Step 1] Parsing C programs...
✓ Found 3 C programs

[Step 2] Analyzing dependencies...
✓ No circular dependencies found

[Step 3] Converting entire project...
  → Generating test cases for 3 files...
    Generated 15 total test cases
  → Running C tests (baseline)...
    C tests completed
  → Converting entire project to C#...
    Project conversion completed
  → Running C# tests...
    C# tests completed
  → Validating outputs (C vs C#)...
    Validation: 15/15 tests passed (100.0%)
  ✓ All tests passed!

[Step 5] Generating migration report...
✓ Migration Complete!
```

