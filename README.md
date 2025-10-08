# C to C# Migration Pipeline - TDD-Based System (Python Implementation)

## 🎯 Tổng quan
Hệ thống migration tự động từ **C sang C#** sử dụng phương pháp Test-Driven Development (TDD) để đảm bảo tính chính xác của code sau khi chuyển đổi. Toàn bộ pipeline được xây dựng bằng **Python**.

## 🏗️ Kiến trúc hệ thống

### Workflow chính (theo sơ đồ):

```
┌─────────────────────────────────────────────────────────────┐
│  1. C Parser           → Parse C source files               │
│  2. Dependency Parser  → Build dependency graph             │
│  3. Component Selector → Select ready-to-convert components │
│  4. Test Generator     → Generate test inputs               │
│  5. C Test Runner      → Run C tests (baseline)             │
│  6. C→C# Converter     → Convert C to C#                    │
│  7. C# Test Runner     → Run C# tests                       │
│  8. Validator          → Compare outputs (C vs C#)          │
│  9. Report Generator   → Generate conversion report         │
│ 10. Loop               → Until all components converted     │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Cấu trúc thư mục

```
python_migration_system/
├── src/
│   ├── core/
│   │   ├── models/              # Data models
│   │   │   ├── c_program.py
│   │   │   ├── dependency_graph.py
│   │   │   ├── test_case.py
│   │   │   ├── conversion_result.py
│   │   │   └── validation_result.py
│   │   └── interfaces/          # Abstract interfaces
│   │       ├── parser_interface.py
│   │       ├── converter_interface.py
│   │       └── test_runner_interface.py
│   │
│   ├── parser/
│   │   ├── c_parser.py          # Parse C source code
│   │   ├── ast_builder.py       # Build Abstract Syntax Tree
│   │   └── symbol_extractor.py  # Extract functions, variables, etc.
│   │
│   ├── dependency_analyzer/
│   │   ├── dependency_service.py     # Analyze dependencies
│   │   ├── graph_builder.py          # Build dependency graph
│   │   └── cycle_detector.py         # Detect circular dependencies
│   │
│   ├── test_generator/
│   │   ├── test_generator.py         # Generate test cases
│   │   ├── input_generator.py        # Generate test inputs
│   │   └── test_harness_builder.py   # Build test harness
│   │
│   ├── converter/
│   │   ├── c_to_csharp_converter.py  # Main converter
│   │   ├── type_mapper.py            # Map C types to C# types
│   │   ├── syntax_transformer.py     # Transform syntax
│   │   └── code_generator.py         # Generate C# code
│   │
│   ├── test_runner/
│   │   ├── c_test_runner.py          # Compile & run C tests
│   │   ├── csharp_test_runner.py     # Compile & run C# tests
│   │   └── compiler_wrapper.py       # Wrapper for GCC & CSC
│   │
│   ├── validator/
│   │   ├── output_validator.py       # Compare outputs
│   │   ├── diff_generator.py         # Generate diffs
│   │   └── tolerance_checker.py      # Handle floating-point tolerance
│   │
│   ├── report_generator/
│   │   ├── report_service.py         # Generate reports
│   │   ├── html_reporter.py          # HTML report
│   │   ├── json_reporter.py          # JSON report
│   │   └── markdown_reporter.py      # Markdown report
│   │
│   ├── orchestrator/
│   │   ├── migration_orchestrator.py # Main workflow orchestrator
│   │   ├── pipeline.py               # Pipeline execution
│   │   └── retry_handler.py          # Handle retry logic
│   │
│   └── utils/
│       ├── logger.py                 # Logging utilities
│       ├── file_manager.py           # File operations
│       └── config.py                 # Configuration
│
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── e2e/                     # End-to-end tests
│
├── examples/
│   ├── c_samples/               # Sample C programs
│   └── expected_csharp/         # Expected C# outputs
│
├── output/
│   ├── converted/               # Converted C# code
│   ├── reports/                 # Conversion reports
│   ├── test_results/            # Test results
│   └── logs/                    # Log files
│
├── config/
│   ├── config.yaml              # Main configuration
│   ├── type_mapping.yaml        # C to C# type mappings
│   └── compiler_settings.yaml   # Compiler settings
│
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
├── pyproject.toml              # Poetry config (optional)
├── Dockerfile                   # Docker configuration
└── main.py                      # Entry point
```

## 🛠️ Công nghệ sử dụng

- **Language**: Python 3.10+
- **Parser**: pycparser (C parser for Python)
- **AST**: Python AST module + custom C AST
- **Testing**: pytest, pytest-cov
- **CLI**: Click or Typer
- **Config**: PyYAML, pydantic
- **Logging**: loguru or structlog
- **Reports**: Jinja2 (HTML), json, markdown
- **Code Generation**: string templates + AST manipulation
- **Async**: asyncio (for parallel test execution)
- **Type Checking**: mypy, pydantic

## 📦 Cài đặt

```bash
# Clone repository
git clone <repo_url>
cd python_migration_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## 🚀 Sử dụng

### Command Line

```bash
# Basic usage
python main.py migrate --input examples/c_samples --output output/converted

# With specific component
python main.py migrate --input src/calculator.c --component calculator

# Generate report only
python main.py report --input output/test_results

# Analyze dependencies only
python main.py analyze --input examples/c_samples
```

### Python API

```python
from src.orchestrator.migration_orchestrator import MigrationOrchestrator
from src.utils.config import Config

# Load configuration
config = Config.from_file("config/config.yaml")

# Create orchestrator
orchestrator = MigrationOrchestrator(config)

# Run migration
result = orchestrator.migrate_all(
    input_dir="examples/c_samples",
    output_dir="output/converted"
)

# Check results
if result.success:
    print(f"Successfully converted {result.converted_count} components")
else:
    print(f"Failed: {result.error_message}")
```

## 📝 Quy trình Migration (Chi tiết)

### 1. C Parser & Dependency Analysis
```python
# Parse C source files
parser = CParser()
programs = parser.parse_directory("examples/c_samples")

# Build dependency graph
dependency_service = DependencyAnalyzerService()
graph = dependency_service.analyze_dependencies(programs)

# Detect circular dependencies
cycles = graph.detect_circular_dependencies()
```

### 2. Component Selection
```python
# Get components ready to convert (all dependencies satisfied)
ready_components = graph.get_ready_to_convert()

# Select one component
component = ready_components[0]
```

### 3. Test Generation
```python
# Generate test inputs (automatically or from spec)
test_generator = TestGenerator()
test_cases = test_generator.generate_tests(component)

# Build C test harness
c_harness = test_generator.build_c_test_harness(component, test_cases)
```

### 4. C Test Execution (Baseline)
```python
# Compile C test scripts
c_runner = CTestRunner()
c_runner.compile(c_harness)

# Run with test inputs
baseline_results = c_runner.run_tests(test_cases)
```

### 5. C to C# Conversion
```python
# Convert C to C#
converter = CToC#Converter()
csharp_code = converter.convert(component)

# Generate C# test scripts
csharp_harness = converter.generate_test_harness(component, test_cases)
```

### 6. C# Test Execution
```python
# Compile C# test scripts
csharp_runner = CSharpTestRunner()
csharp_runner.compile(csharp_harness)

# Run with same test inputs
csharp_results = csharp_runner.run_tests(test_cases)
```

### 7. Validation
```python
# Compare outputs
validator = OutputValidator()
validation_result = validator.validate(baseline_results, csharp_results)

if not validation_result.is_match:
    # Retry or report differences
    print(f"Differences found: {validation_result.differences}")
```

### 8. Report Generation
```python
# Generate conversion report
reporter = ReportService()
reporter.generate_report(
    conversion_results,
    validation_results,
    output_path="output/reports/report.html"
)
```

## 🧪 Testing Strategy

### Unit Tests
```bash
pytest tests/unit -v
```

### Integration Tests
```bash
pytest tests/integration -v
```

### End-to-End Tests
```bash
pytest tests/e2e -v
```

### Coverage
```bash
pytest --cov=src --cov-report=html
```

## 📊 Configuration

### config.yaml
```yaml
migration:
  max_retries: 3
  parallel_execution: true
  workers: 4

compiler:
  c_compiler: gcc
  csharp_compiler: csc  # or dotnet
  optimization_level: O2

test_generation:
  auto_generate: true
  boundary_testing: true
  random_seed: 42

validation:
  floating_point_tolerance: 1e-6
  string_comparison: exact

output:
  generate_html_report: true
  generate_json_report: true
  verbose_logging: true
```

## 🎯 Best Practices

1. **Incremental Migration**: Convert từng component theo dependency order
2. **Automated Testing**: Tự động hóa 100% việc testing
3. **Version Control**: Track tất cả changes với git
4. **Documentation**: Document mọi quyết định và edge cases
5. **Rollback Strategy**: Có kế hoạch rollback nếu cần
6. **Code Review**: Review converted code trước khi merge
7. **Performance**: Optimize cho performance với async/parallel execution

## 🔧 Troubleshooting

### Common Issues

1. **Compilation Errors**
   - Check compiler paths in config
   - Verify C/C# compiler versions
   - Review compiler output in logs

2. **Test Failures**
   - Check test inputs/outputs
   - Review tolerance settings
   - Examine diff reports

3. **Dependency Issues**
   - Review dependency graph
   - Check for circular dependencies
   - Verify all dependencies are available

### Logs
```bash
# View logs
tail -f output/logs/migration.log

# Debug mode
python main.py migrate --debug --input examples/c_samples
```

## 📈 Metrics & Monitoring

The system tracks:
- Conversion success rate
- Test pass rate
- Execution time per component
- Code complexity metrics
- Lines of code converted
- Number of manual interventions needed

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Write tests
4. Implement feature
5. Run tests & linters
6. Submit pull request

## 📄 License

MIT License - See LICENSE file for details

# TDD-Based-Migration-Pipeline-
