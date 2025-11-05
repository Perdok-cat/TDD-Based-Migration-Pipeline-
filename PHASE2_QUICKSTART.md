# Phase 2 Quick Start Guide 🚀

## Tổng Quan

Phase 2 thực hiện workflow chính của migration system:
**Test → Convert → Validate**

## Cài Đặt Dependencies

### 1. Python Dependencies
```bash
# Đã có từ Phase 1
pip install -r requirements.txt
```

### 2. External Compilers

#### GCC (cho C tests)
```bash
# Linux/Ubuntu
sudo apt-get install gcc

# macOS
brew install gcc

# Verify
gcc --version
```

#### .NET SDK (cho C# tests - Recommended)
```bash
# Linux
wget https://dot.net/v1/dotnet-install.sh
chmod +x dotnet-install.sh
./dotnet-install.sh

# Verify
dotnet --version
```

#### Alternative: Mono (cho C# tests)
```bash
# Linux/Ubuntu
sudo apt-get install mono-complete

# Verify
csc /version
```

## Quick Test

Chạy test script để verify Phase 2 hoạt động:

```bash
cd python_migration_system
python test_phase2.py
```

Expected output:
```
======================================================================
TESTING PHASE 2 COMPONENTS
======================================================================

[1] Creating test program...
✓ Program created: test_add

[2] Testing Test Generator...
✓ Test suite generated
  Total test cases: XX

[3] Testing Test Harness Generation...
✓ C test harness generated

[4] Testing C to C# Converter...
✓ C# code generated

[5] Testing C# Test Harness Generation...
✓ C# test harness generated

[6] Testing Output Validator...
✓ Validation completed

✓ ALL PHASE 2 COMPONENTS TESTED SUCCESSFULLY
```

## Usage Examples

### Example 1: Standalone Test Generation

```python
from src.test_generator.test_generator import TestGenerator
from src.core.models.c_program import CProgram, CFunction, CVariable

# Create a simple C function model
add_func = CFunction(
    name="add",
    return_type="int",
    parameters=[
        CVariable(name="a", data_type="int"),
        CVariable(name="b", data_type="int")
    ]
)

# Create program
program = CProgram(
    program_id="my_program",
    file_path="program.c",
    source_code="...",
    functions=[add_func]
)

# Generate tests
generator = TestGenerator(seed=42)
test_suite = generator.generate_tests(
    program,
    strategies=['boundary', 'edge', 'random']
)

print(f"Generated {len(test_suite.test_cases)} test cases")
for tc in test_suite.test_cases:
    print(f"  - {tc.name}: {tc.inputs}")
```

### Example 2: Convert C to C#

```python
from src.converter.c_to_csharp_converter import CToCSharpConverter

# Create converter
converter = CToCSharpConverter()

# Convert program
csharp_code = converter.convert(program)

# Save to file
with open('output/Program.cs', 'w') as f:
    f.write(csharp_code)

print("C# code generated!")
```

### Example 3: Full Workflow with Orchestrator

```python
from src.orchestrator.migration_orchestrator import MigrationOrchestrator

# Create orchestrator
orchestrator = MigrationOrchestrator(config={
    'max_retries': 3,
    'output_dir': 'output',
    'verbose': True
})

# Run migration for a directory
report = orchestrator.migrate_all(
    input_dir='path/to/c/project',
    output_dir='output'
)

# Print summary
print(report.get_summary())
```

## Phase 2 Components

| Component | Description | Status |
|-----------|-------------|--------|
| **TestGenerator** | Generate test cases tự động | ✅ |
| **InputGenerator** | Generate boundary/edge/random inputs | ✅ |
| **CTestRunner** | Compile và run C tests | ✅ |
| **CSharpTestRunner** | Compile và run C# tests | ✅ |
| **CToCSharpConverter** | Convert C code to C# | ✅ |
| **TypeMapper** | Map C types to C# types | ✅ |
| **OutputValidator** | Validate C vs C# outputs | ✅ |
| **MigrationOrchestrator** | Điều phối workflow | ✅ |

## Test Strategies

Phase 2 hỗ trợ 3 test strategies:

### 1. Boundary Testing
Test với min/max values:
- `int`: -2³¹, 0, 2³¹-1
- `float`: -1e38, 0.0, 1e38
- `char`: 0, 127, 255

### 2. Edge Case Testing
Test các trường hợp đặc biệt:
- Overflow/underflow
- NULL pointers
- Special float values (inf, -inf)

### 3. Random Testing
Fuzzing với reproducible seed:
- Random integers
- Random floats
- Random combinations

## Troubleshooting

### Issue: GCC not found
```
Error: GCC compiler not found
```
**Solution:** Install GCC:
```bash
sudo apt-get install gcc
```

### Issue: C# compiler not found
```
Error: C# compiler not found
```
**Solution:** Install .NET SDK or Mono:
```bash
# Option 1: .NET SDK
wget https://dot.net/v1/dotnet-install.sh
./dotnet-install.sh

# Option 2: Mono
sudo apt-get install mono-complete
```

### Issue: Compilation timeout
```
Error: Compilation timeout
```
**Solution:** Tăng timeout trong config:
```python
orchestrator = MigrationOrchestrator(config={
    'compilation_timeout': 60  # seconds
})
```

## Next Steps

1. ✅ Phase 1: Parse C code và analyze dependencies
2. ✅ **Phase 2: Test generation và conversion** (CURRENT)
3. ⏳ Phase 3: Report generation
4. ⏳ End-to-end integration testing
5. ⏳ Performance optimization

## Architecture

```
Phase 2 Workflow:
┌─────────────────────────────────────────────────┐
│  FOR each component in conversion_order:        │
│                                                  │
│  1. Generate Test Cases                         │
│     └─→ TestGenerator                           │
│         ├─ Boundary tests                       │
│         ├─ Edge cases                           │
│         └─ Random tests                         │
│                                                  │
│  2. Run C Tests (Baseline)                      │
│     └─→ CTestRunner                             │
│         ├─ Generate test harness                │
│         ├─ Compile with GCC                     │
│         ├─ Execute binary                       │
│         └─ Capture outputs                      │
│                                                  │
│  3. Convert C to C#                             │
│     └─→ CToCSharpConverter                      │
│         ├─ Map types                            │
│         ├─ Convert functions                    │
│         ├─ Convert structs                      │
│         └─ Generate C# code                     │
│                                                  │
│  4. Run C# Tests                                │
│     └─→ CSharpTestRunner                        │
│         ├─ Generate C# test harness             │
│         ├─ Compile with dotnet/csc              │
│         ├─ Execute assembly                     │
│         └─ Capture outputs                      │
│                                                  │
│  5. Validate Outputs                            │
│     └─→ OutputValidator                         │
│         ├─ Compare C vs C# outputs              │
│         ├─ Check tolerances                     │
│         ├─ Generate diff report                 │
│         └─ Mark pass/fail                       │
│                                                  │
│  6. Decision Point                              │
│     ├─ All tests pass? → Mark success           │
│     └─ Tests fail? → Retry (max 3x)             │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Documentation

Xem thêm tài liệu chi tiết:
- [PHASE2_IMPLEMENTATION.md](docs/PHASE2_IMPLEMENTATION.md) - Chi tiết implementation
- [ARCHITECTURE.md](ARCHITECTURE.md) - Tổng quan kiến trúc
- [INPUT_OUTPUT_SPEC.md](INPUT_OUTPUT_SPEC.md) - Spec cho input/output

## Support

Nếu gặp vấn đề, check:
1. Dependencies đã install đầy đủ chưa
2. Compilers (gcc, dotnet/csc) có trong PATH không
3. Test script chạy thành công không: `python test_phase2.py`

---

**Status:** ✅ Phase 2 Implementation Complete  
**Date:** 2025-10-08


