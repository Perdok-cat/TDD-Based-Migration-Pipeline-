# Quick Start Guide

## 🚀 Bắt đầu nhanh trong 5 phút

### Bước 1: Cài đặt

```bash
# Clone repository
git clone <your-repo>
cd python_migration_system

# Tạo virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
venv\Scripts\activate     # Windows

# Cài đặt dependencies
pip install -r requirements.txt

# Kiểm tra cài đặt
python main.py info
```

### Bước 2: Chuẩn bị C source files

Tạo thư mục chứa C files của bạn:

```bash
mkdir -p examples/c_samples
```

Ví dụ file `calculator.c`:

```c
// examples/c_samples/calculator.c
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int subtract(int a, int b) {
    return a - b;
}

int multiply(int a, int b) {
    return a * b;
}

float divide(int a, int b) {
    if (b == 0) {
        return 0.0;
    }
    return (float)a / b;
}

int main() {
    printf("Calculator\n");
    printf("5 + 3 = %d\n", add(5, 3));
    printf("5 - 3 = %d\n", subtract(5, 3));
    printf("5 * 3 = %d\n", multiply(5, 3));
    printf("5 / 2 = %.2f\n", divide(5, 2));
    return 0;
}
```

### Bước 3: Chạy migration

```bash
# Phân tích dependencies trước
python main.py analyze -i examples/c_samples --visualize

# Chạy migration
python main.py migrate -i examples/c_samples -o output/converted

# Xem report
python main.py report -i output/test_results -o output/reports
```

### Bước 4: Kiểm tra kết quả

```bash
# Xem converted C# code
cat output/converted/calculator.cs

# Xem HTML report
open output/reports/migration_report.html  # Mac
xdg-open output/reports/migration_report.html  # Linux
start output/reports/migration_report.html  # Windows
```

## 📝 Ví dụ sử dụng

### Example 1: Simple function

**Input (C)**:
```c
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
```

**Output (C#)**:
```csharp
public static int Factorial(int n) {
    if (n <= 1) return 1;
    return n * Factorial(n - 1);
}
```

### Example 2: Struct

**Input (C)**:
```c
struct Point {
    int x;
    int y;
};

struct Point createPoint(int x, int y) {
    struct Point p;
    p.x = x;
    p.y = y;
    return p;
}
```

**Output (C#)**:
```csharp
public struct Point {
    public int X;
    public int Y;
}

public static Point CreatePoint(int x, int y) {
    Point p = new Point();
    p.X = x;
    p.Y = y;
    return p;
}
```

### Example 3: Arrays

**Input (C)**:
```c
int sum_array(int arr[], int size) {
    int sum = 0;
    for (int i = 0; i < size; i++) {
        sum += arr[i];
    }
    return sum;
}
```

**Output (C#)**:
```csharp
public static int SumArray(int[] arr, int size) {
    int sum = 0;
    for (int i = 0; i < size; i++) {
        sum += arr[i];
    }
    return sum;
}
```

## 🎯 Workflow theo sơ đồ

```
1. Parsing C programs
   └─ Tìm tất cả .c files
   └─ Parse mỗi file thành AST
   └─ Extract functions, structs, variables

2. Dependency Analysis
   └─ Phân tích #include, function calls
   └─ Build dependency graph
   └─ Detect circular dependencies
   └─ Determine conversion order

3. For each component (theo thứ tự):
   
   3.1. Check if ready (all deps converted)
        └─ YES: Continue
        └─ NO: Skip (will process later)
   
   3.2. Generate test cases
        └─ Boundary tests (min, max, zero)
        └─ Edge cases (NULL, empty)
        └─ Random tests
   
   3.3. Run C tests (baseline)
        └─ Compile C test harness
        └─ Execute with test inputs
        └─ Capture outputs
   
   3.4. Convert to C#
        └─ Transform AST
        └─ Map types
        └─ Generate C# code
   
   3.5. Run C# tests
        └─ Compile C# test harness
        └─ Execute with same inputs
        └─ Capture outputs
   
   3.6. Validate
        └─ Compare C outputs vs C# outputs
        └─ Check tolerance for floats
        └─ Generate diff if mismatch
   
   3.7. Decision
        └─ All pass? → Mark as converted, continue
        └─ Some fail? → Retry (max 3 times)
        └─ Still fail? → Mark as failed, log issues

4. Generate Report
   └─ HTML report với visualizations
   └─ JSON report cho automation
   └─ Markdown summary
```

## ⚙️ Configuration

Customize behavior via `config/config.yaml`:

```yaml
migration:
  max_retries: 3
  parallel_execution: false

test_generation:
  auto_generate: true
  tests_per_function: 5

validation:
  floating_point_tolerance: 1.0e-6

output:
  generate_html_report: true
  verbose_logging: true
```

## 🔧 Advanced Usage

### Custom test cases

Tạo file `test_specs.yaml`:

```yaml
calculator:
  add:
    - inputs: {a: 5, b: 3}
      expected: 8
    - inputs: {a: -5, b: 3}
      expected: -2
  divide:
    - inputs: {a: 10, b: 2}
      expected: 5.0
    - inputs: {a: 5, b: 0}
      expected: 0.0  # Handle division by zero
```

Chạy với custom tests:

```bash
python main.py migrate -i examples/c_samples --test-spec test_specs.yaml
```

### Parallel processing

```bash
python main.py migrate -i examples/c_samples --parallel --workers 4
```

### Debug mode

```bash
python main.py migrate -i examples/c_samples --debug
```

## 📊 Hiểu kết quả

### Success case
```
✓ calculator.c: Conversion successful
  - 4 functions converted
  - 10 tests passed (100%)
  - 0 errors, 0 warnings
```

### Partial success
```
✓ calculator.c: Conversion successful (1 warning)
  - 4 functions converted
  - 9/10 tests passed (90%)
  - 0 errors, 1 warning
  
  Warnings:
  - divide(): Potential division by zero not handled in C#
```

### Failure case
```
✗ calculator.c: Conversion failed
  - 3/4 functions converted
  - 7/10 tests passed (70%)
  - 2 errors, 1 warning
  
  Errors:
  - multiply(): Output mismatch (C: 15, C#: 16)
  - divide(): Compilation error in C# code
```

## 🐛 Troubleshooting

### Issue: "C compiler not found"
```bash
# Install GCC
sudo apt-get install gcc  # Ubuntu/Debian
brew install gcc          # Mac
```

### Issue: "C# compiler not found"
```bash
# Install .NET SDK
# Download from: https://dotnet.microsoft.com/download
```

### Issue: "Parser error"
```bash
# Check C file syntax
gcc -fsyntax-only your_file.c
```

### Issue: "Test timeout"
```bash
# Increase timeout in config
migration:
  timeout_seconds: 600  # 10 minutes
```

## 📚 Tài nguyên

- [Architecture Documentation](ARCHITECTURE.md)
- [Full README](README.md)
- [API Documentation](docs/api.md) (TODO)
- [Examples](examples/)

## 💡 Tips

1. **Bắt đầu với files đơn giản**: Test với small C files trước
2. **Review config**: Customize settings cho project của bạn
3. **Check dependencies**: Đảm bảo không có circular dependencies
4. **Test incremental**: Convert từng component một
5. **Review reports**: Luôn xem reports để hiểu issues

## 🎓 Next Steps

Sau khi làm quen với basic workflow:

1. Tìm hiểu về [Architecture](ARCHITECTURE.md)
2. Implement các services còn thiếu (Parser, Converter, etc.)
3. Customize type mappings cho domain của bạn
4. Thêm custom validation rules
5. Tối ưu performance với parallel processing

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📮 Support

- Issues: [GitHub Issues](https://github.com/yourusername/repo/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/repo/discussions)

