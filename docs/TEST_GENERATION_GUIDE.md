# 🧪 Test Generation Guide

## 📋 Tổng quan

Test generation là bước **quan trọng nhất** trong TDD-based migration pipeline. Mục tiêu là tạo ra các test cases để:
1. ✅ Capture baseline behavior của C code
2. ✅ Validate rằng C# code hoạt động giống hệt C code
3. ✅ Phát hiện regressions và bugs

---

## 🎯 Chiến lược Test Generation

### 3 Loại Test Cases

```
┌─────────────────────────────────────────────────────────┐
│  1. BOUNDARY TESTS      (Min, Max, Zero values)        │
│  2. EDGE CASE TESTS     (NULL, Empty, Special values)  │
│  3. RANDOM TESTS        (Fuzzing with seed)            │
└─────────────────────────────────────────────────────────┘
```

---

## 1️⃣ Boundary Value Testing

### 📐 Nguyên tắc

Test với các giá trị **biên** (boundary values) của mỗi data type:
- **Minimum value** (INT_MIN, 0, etc.)
- **Maximum value** (INT_MAX, etc.)
- **Zero**
- **One before/after boundary**

### 🔢 Boundary Values theo Data Type

```python
BOUNDARY_VALUES = {
    'int': [
        0,                    # Zero
        1,                    # Positive edge
        -1,                   # Negative edge
        2147483647,          # INT_MAX
        -2147483648,         # INT_MIN
        2147483646,          # INT_MAX - 1
        -2147483647,         # INT_MIN + 1
    ],
    
    'unsigned int': [
        0,                    # Min
        1,                    # Min + 1
        4294967295,          # UINT_MAX
        4294967294,          # UINT_MAX - 1
    ],
    
    'short': [
        0,                    # Zero
        32767,               # SHRT_MAX
        -32768,              # SHRT_MIN
    ],
    
    'char': [
        0,                    # '\0' (null character)
        32,                   # Space
        65,                   # 'A'
        97,                   # 'a'
        127,                  # Max ASCII
        -128,                 # CHAR_MIN (signed)
    ],
    
    'float': [
        0.0,                  # Zero
        1.0,                  # One
        -1.0,                 # Negative one
        0.0001,               # Small positive
        -0.0001,              # Small negative
        3.4028235e+38,       # FLT_MAX
        1.17549435e-38,      # FLT_MIN
    ],
    
    'double': [
        0.0,
        1.0,
        -1.0,
        1.7976931348623157e+308,  # DBL_MAX
        2.2250738585072014e-308,  # DBL_MIN
    ],
    
    'pointer': [
        None,                 # NULL pointer
        # Valid addresses generated at runtime
    ],
    
    'array': [
        [],                   # Empty array
        [0],                  # Single element
        [0] * 100,           # Full array (max size)
    ]
}
```

### 📝 Ví dụ: Boundary Tests cho `int add(int a, int b)`

```python
def generate_boundary_tests_for_add(function):
    """
    Generate boundary value tests for add(int a, int b)
    """
    tests = []
    
    # Test case 1: Zero + Zero
    tests.append({
        'name': 'add_zero_zero',
        'inputs': {'a': 0, 'b': 0},
        'expected': 0,
        'category': 'boundary'
    })
    
    # Test case 2: Max + Zero
    tests.append({
        'name': 'add_max_zero',
        'inputs': {'a': 2147483647, 'b': 0},
        'expected': 2147483647,
        'category': 'boundary'
    })
    
    # Test case 3: Min + Zero
    tests.append({
        'name': 'add_min_zero',
        'inputs': {'a': -2147483648, 'b': 0},
        'expected': -2147483648,
        'category': 'boundary'
    })
    
    # Test case 4: Positive + Positive
    tests.append({
        'name': 'add_pos_pos',
        'inputs': {'a': 1, 'b': 1},
        'expected': 2,
        'category': 'boundary'
    })
    
    # Test case 5: Negative + Negative
    tests.append({
        'name': 'add_neg_neg',
        'inputs': {'a': -1, 'b': -1},
        'expected': -2,
        'category': 'boundary'
    })
    
    # Test case 6: Positive + Negative
    tests.append({
        'name': 'add_pos_neg',
        'inputs': {'a': 5, 'b': -3},
        'expected': 2,
        'category': 'boundary'
    })
    
    # Test case 7: Overflow detection (optional)
    tests.append({
        'name': 'add_overflow',
        'inputs': {'a': 2147483647, 'b': 1},
        'expected': -2147483648,  # Integer overflow wraps around
        'category': 'boundary',
        'note': 'Tests integer overflow behavior'
    })
    
    return tests
```

**Output**: 7 test cases covering boundary conditions

---

## 2️⃣ Edge Case Testing

### 🎯 Nguyên tắc

Test với các **trường hợp đặc biệt** mà có thể gây lỗi:
- **NULL pointers**
- **Empty arrays/strings**
- **Division by zero**
- **Buffer boundaries**
- **Special characters**

### 📋 Edge Cases theo Function Type

#### A. Functions với Pointers

```python
def generate_edge_cases_pointer_function(function):
    """
    int* findMax(int* arr, int size)
    """
    tests = []
    
    # Edge case 1: NULL pointer
    tests.append({
        'name': 'findMax_null_pointer',
        'inputs': {'arr': None, 'size': 0},
        'expected': None,
        'category': 'edge_case',
        'note': 'NULL pointer handling'
    })
    
    # Edge case 2: Empty array
    tests.append({
        'name': 'findMax_empty_array',
        'inputs': {'arr': [], 'size': 0},
        'expected': None,
        'category': 'edge_case'
    })
    
    # Edge case 3: Single element
    tests.append({
        'name': 'findMax_single_element',
        'inputs': {'arr': [42], 'size': 1},
        'expected': 42,
        'category': 'edge_case'
    })
    
    return tests
```

#### B. Functions với Division

```python
def generate_edge_cases_division(function):
    """
    float divide(int a, int b)
    """
    tests = []
    
    # Edge case 1: Division by zero
    tests.append({
        'name': 'divide_by_zero',
        'inputs': {'a': 5, 'b': 0},
        'expected': 0.0,  # Or error, depending on implementation
        'category': 'edge_case',
        'note': 'Division by zero should be handled'
    })
    
    # Edge case 2: Zero dividend
    tests.append({
        'name': 'divide_zero_dividend',
        'inputs': {'a': 0, 'b': 5},
        'expected': 0.0,
        'category': 'edge_case'
    })
    
    # Edge case 3: Negative division
    tests.append({
        'name': 'divide_negative',
        'inputs': {'a': -10, 'b': 2},
        'expected': -5.0,
        'category': 'edge_case'
    })
    
    return tests
```

#### C. Functions với Strings

```python
def generate_edge_cases_string_function(function):
    """
    int strlen_custom(char* str)
    """
    tests = []
    
    # Edge case 1: NULL string
    tests.append({
        'name': 'strlen_null',
        'inputs': {'str': None},
        'expected': 0,
        'category': 'edge_case'
    })
    
    # Edge case 2: Empty string
    tests.append({
        'name': 'strlen_empty',
        'inputs': {'str': ''},
        'expected': 0,
        'category': 'edge_case'
    })
    
    # Edge case 3: Single character
    tests.append({
        'name': 'strlen_single_char',
        'inputs': {'str': 'a'},
        'expected': 1,
        'category': 'edge_case'
    })
    
    # Edge case 4: Special characters
    tests.append({
        'name': 'strlen_special_chars',
        'inputs': {'str': '!@#$%'},
        'expected': 5,
        'category': 'edge_case'
    })
    
    return tests
```

#### D. Functions với Arrays

```python
def generate_edge_cases_array_function(function):
    """
    int sumArray(int arr[], int size)
    """
    tests = []
    
    # Edge case 1: Empty array
    tests.append({
        'name': 'sumArray_empty',
        'inputs': {'arr': [], 'size': 0},
        'expected': 0,
        'category': 'edge_case'
    })
    
    # Edge case 2: All zeros
    tests.append({
        'name': 'sumArray_all_zeros',
        'inputs': {'arr': [0, 0, 0, 0], 'size': 4},
        'expected': 0,
        'category': 'edge_case'
    })
    
    # Edge case 3: All negatives
    tests.append({
        'name': 'sumArray_all_negatives',
        'inputs': {'arr': [-1, -2, -3], 'size': 3},
        'expected': -6,
        'category': 'edge_case'
    })
    
    # Edge case 4: Mixed positive/negative
    tests.append({
        'name': 'sumArray_mixed',
        'inputs': {'arr': [5, -3, 2, -1], 'size': 4},
        'expected': 3,
        'category': 'edge_case'
    })
    
    return tests
```

---

## 3️⃣ Random Testing (Fuzzing)

### 🎲 Nguyên tắc

Generate random inputs để:
- Discover unexpected behaviors
- Test với wide range of values
- Increase test coverage

### 🔧 Implementation với Seed

```python
import random

def generate_random_tests(function, count=10, seed=42):
    """
    Generate random test cases with reproducible seed
    """
    random.seed(seed)  # For reproducibility
    tests = []
    
    for i in range(count):
        test = generate_random_test_for_function(function, i)
        tests.append(test)
    
    return tests

def generate_random_test_for_function(function, test_id):
    """
    Generate a single random test based on function signature
    """
    inputs = {}
    
    for param in function.parameters:
        # Generate random value based on parameter type
        if param.data_type == 'int':
            inputs[param.name] = random.randint(-1000, 1000)
        elif param.data_type == 'float':
            inputs[param.name] = random.uniform(-1000.0, 1000.0)
        elif param.data_type == 'char':
            inputs[param.name] = chr(random.randint(32, 126))  # Printable ASCII
        elif param.is_pointer and 'int' in param.data_type:
            # Generate random array
            size = random.randint(1, 20)
            inputs[param.name] = [random.randint(-100, 100) for _ in range(size)]
    
    return {
        'name': f'random_test_{test_id}',
        'inputs': inputs,
        'expected': None,  # Will be determined by running C code
        'category': 'random',
        'seed': 42,
        'test_id': test_id
    }
```

### 📊 Ví dụ Random Tests

```python
# For: int add(int a, int b)
random_tests = [
    {'name': 'random_test_0', 'inputs': {'a': 342, 'b': -156}, 'category': 'random'},
    {'name': 'random_test_1', 'inputs': {'a': -789, 'b': 234}, 'category': 'random'},
    {'name': 'random_test_2', 'inputs': {'a': 0, 'b': 999}, 'category': 'random'},
    {'name': 'random_test_3', 'inputs': {'a': -42, 'b': -87}, 'category': 'random'},
    {'name': 'random_test_4', 'inputs': {'a': 555, 'b': 444}, 'category': 'random'},
    # ... more random tests
]
```

---

## 🏗️ Test Generator Architecture

### Class Structure

```python
class TestGenerator:
    """Main test generator"""
    
    def __init__(self, config=None):
        self.config = config or {}
        self.boundary_generator = BoundaryTestGenerator()
        self.edge_case_generator = EdgeCaseTestGenerator()
        self.random_generator = RandomTestGenerator(seed=42)
    
    def generate_tests(self, program: CProgram) -> TestSuite:
        """Generate all tests for a program"""
        suite = TestSuite(program_id=program.program_id)
        
        for function in program.functions:
            # Skip main() and static functions if configured
            if function.name == 'main' or function.is_static:
                continue
            
            # Generate tests for this function
            tests = self.generate_tests_for_function(function)
            for test in tests:
                suite.add_test_case(test)
        
        return suite
    
    def generate_tests_for_function(self, function: CFunction) -> List[TestCase]:
        """Generate tests for a single function"""
        tests = []
        
        # 1. Boundary tests
        if self.config.get('boundary_testing', True):
            boundary_tests = self.boundary_generator.generate(function)
            tests.extend(boundary_tests)
        
        # 2. Edge case tests
        if self.config.get('edge_case_testing', True):
            edge_tests = self.edge_case_generator.generate(function)
            tests.extend(edge_tests)
        
        # 3. Random tests
        if self.config.get('random_testing', True):
            count = self.config.get('tests_per_function', 5)
            random_tests = self.random_generator.generate(function, count)
            tests.extend(random_tests)
        
        # Convert to TestCase objects
        test_cases = []
        for test_data in tests:
            test_case = TestCase(
                name=test_data['name'],
                program_id=function.name,
                function_name=function.name,
                inputs=test_data['inputs'],
                category=test_data.get('category', 'functional'),
                description=test_data.get('note', '')
            )
            test_cases.append(test_case)
        
        return test_cases
```

### Boundary Test Generator

```python
class BoundaryTestGenerator:
    """Generate boundary value tests"""
    
    BOUNDARY_VALUES = {
        'int': [0, 1, -1, 2147483647, -2147483648],
        'unsigned int': [0, 1, 4294967295],
        'short': [0, 32767, -32768],
        'char': [0, 32, 127, -128],
        'float': [0.0, 1.0, -1.0, 3.4028235e+38],
        'double': [0.0, 1.0, -1.0, 1.7976931348623157e+308],
    }
    
    def generate(self, function: CFunction) -> List[dict]:
        """Generate boundary tests for function"""
        tests = []
        
        # Get parameter combinations
        param_values = []
        for param in function.parameters:
            values = self._get_boundary_values_for_type(param.data_type)
            param_values.append((param.name, values))
        
        # Generate combinations (select subset to avoid explosion)
        tests.extend(self._generate_combinations(param_values, function.name))
        
        return tests
    
    def _get_boundary_values_for_type(self, data_type: str) -> List:
        """Get boundary values for a data type"""
        return self.BOUNDARY_VALUES.get(data_type, [0, 1, -1])
    
    def _generate_combinations(self, param_values, func_name) -> List[dict]:
        """Generate test combinations"""
        tests = []
        
        # Strategy 1: One-at-a-time (each param at boundary, others normal)
        for i, (param_name, values) in enumerate(param_values):
            for value in values:
                inputs = {}
                for j, (pname, pvalues) in enumerate(param_values):
                    if i == j:
                        inputs[pname] = value  # Boundary value
                    else:
                        inputs[pname] = pvalues[0]  # Default value
                
                tests.append({
                    'name': f'{func_name}_boundary_{param_name}_{value}',
                    'inputs': inputs,
                    'category': 'boundary'
                })
        
        # Strategy 2: All boundaries (cartesian product - limited)
        # Only if number of params is small to avoid explosion
        if len(param_values) <= 2:
            # Generate all combinations
            import itertools
            all_combos = itertools.product(*[vals for _, vals in param_values])
            for combo in list(all_combos)[:10]:  # Limit to 10
                inputs = {name: val for (name, _), val in zip(param_values, combo)}
                tests.append({
                    'name': f'{func_name}_boundary_combo_{len(tests)}',
                    'inputs': inputs,
                    'category': 'boundary'
                })
        
        return tests
```

### Edge Case Generator

```python
class EdgeCaseTestGenerator:
    """Generate edge case tests"""
    
    def generate(self, function: CFunction) -> List[dict]:
        """Generate edge case tests"""
        tests = []
        
        # Detect function characteristics
        has_pointers = any(p.is_pointer for p in function.parameters)
        has_division = 'div' in function.name.lower() or '/' in function.body
        has_arrays = any('[]' in p.data_type for p in function.parameters)
        
        # Generate appropriate edge cases
        if has_pointers:
            tests.extend(self._generate_pointer_edge_cases(function))
        
        if has_division:
            tests.extend(self._generate_division_edge_cases(function))
        
        if has_arrays:
            tests.extend(self._generate_array_edge_cases(function))
        
        # General edge cases
        tests.extend(self._generate_general_edge_cases(function))
        
        return tests
    
    def _generate_pointer_edge_cases(self, function: CFunction) -> List[dict]:
        """Edge cases for functions with pointers"""
        return [
            {
                'name': f'{function.name}_null_pointer',
                'inputs': {p.name: None if p.is_pointer else 0 
                          for p in function.parameters},
                'category': 'edge_case',
                'note': 'NULL pointer test'
            }
        ]
    
    def _generate_division_edge_cases(self, function: CFunction) -> List[dict]:
        """Edge cases for division functions"""
        tests = []
        
        # Find divisor parameter (usually second param or named 'b', 'divisor', etc.)
        for param in function.parameters:
            if param.name in ['b', 'divisor', 'denominator']:
                inputs = {p.name: 5 if p.name != param.name else 0 
                         for p in function.parameters}
                tests.append({
                    'name': f'{function.name}_division_by_zero',
                    'inputs': inputs,
                    'category': 'edge_case',
                    'note': 'Division by zero test'
                })
                break
        
        return tests
    
    def _generate_array_edge_cases(self, function: CFunction) -> List[dict]:
        """Edge cases for array functions"""
        return [
            {
                'name': f'{function.name}_empty_array',
                'inputs': {'arr': [], 'size': 0},
                'category': 'edge_case',
                'note': 'Empty array test'
            },
            {
                'name': f'{function.name}_single_element',
                'inputs': {'arr': [42], 'size': 1},
                'category': 'edge_case',
                'note': 'Single element array'
            }
        ]
    
    def _generate_general_edge_cases(self, function: CFunction) -> List[dict]:
        """General edge cases"""
        tests = []
        
        # All zeros
        all_zeros = {p.name: 0 for p in function.parameters}
        tests.append({
            'name': f'{function.name}_all_zeros',
            'inputs': all_zeros,
            'category': 'edge_case',
            'note': 'All parameters zero'
        })
        
        return tests
```

---

## 📋 Complete Example

### Input Function

```c
// C function
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}
```

### Generated Tests

```python
test_suite = [
    # Boundary tests
    {'name': 'factorial_boundary_0', 'inputs': {'n': 0}, 'category': 'boundary'},
    {'name': 'factorial_boundary_1', 'inputs': {'n': 1}, 'category': 'boundary'},
    {'name': 'factorial_boundary_neg', 'inputs': {'n': -1}, 'category': 'boundary'},
    {'name': 'factorial_boundary_10', 'inputs': {'n': 10}, 'category': 'boundary'},
    
    # Edge cases
    {'name': 'factorial_negative', 'inputs': {'n': -5}, 'category': 'edge_case'},
    {'name': 'factorial_large', 'inputs': {'n': 20}, 'category': 'edge_case'},
    
    # Random tests
    {'name': 'factorial_random_0', 'inputs': {'n': 7}, 'category': 'random'},
    {'name': 'factorial_random_1', 'inputs': {'n': 3}, 'category': 'random'},
    {'name': 'factorial_random_2', 'inputs': {'n': 15}, 'category': 'random'},
]
```

### Test Coverage

- ✅ **10 test cases** total
- ✅ **4 boundary tests** (0, 1, negative, positive)
- ✅ **2 edge case tests** (negative input, large input)
- ✅ **3 random tests** (varied inputs)
- ✅ Covers base case, recursive case, edge cases

---

## 🎯 Best Practices

### 1. Balance Test Count
```yaml
# Config
test_generation:
  boundary_testing: true
  edge_case_testing: true
  random_testing: true
  tests_per_function: 5      # Reasonable number
  max_total_tests: 50        # Limit per program
```

### 2. Prioritize Important Functions
```python
def should_generate_extensive_tests(function: CFunction) -> bool:
    """Decide if function needs extensive testing"""
    # More tests for:
    # - Complex functions (high cyclomatic complexity)
    # - Functions with pointers
    # - Mathematical functions
    # - Functions with many parameters
    
    if function.complexity > 10:
        return True
    if any(p.is_pointer for p in function.parameters):
        return True
    if len(function.parameters) > 3:
        return True
    
    return False
```

### 3. Use Test Specifications for Critical Functions
```yaml
# test_specs.yaml - Manual test cases for critical functions
calculator:
  divide:
    - inputs: {a: 10, b: 2}
      expected: 5.0
      note: "Normal division"
    
    - inputs: {a: 5, b: 0}
      expected: 0.0
      note: "Division by zero must be handled"
    
    - inputs: {a: 0, b: 5}
      expected: 0.0
      note: "Zero dividend"
```

---

## 📊 Test Statistics

Với config mặc định, cho một typical C program:

```
Program: calculator.c (6 functions)

Generated tests:
├── add()        : 12 tests (4 boundary, 3 edge, 5 random)
├── subtract()   : 12 tests (4 boundary, 3 edge, 5 random)
├── multiply()   : 12 tests (4 boundary, 3 edge, 5 random)
├── divide()     : 15 tests (4 boundary, 6 edge, 5 random) ← More edge cases
├── factorial()  : 10 tests (4 boundary, 1 edge, 5 random)
└── power()      : 12 tests (4 boundary, 3 edge, 5 random)

Total: 73 test cases
```

---

## 🚀 Next Steps

1. ✅ Understand test generation strategies
2. ⏳ Implement `TestGenerator` class
3. ⏳ Implement `BoundaryTestGenerator`
4. ⏳ Implement `EdgeCaseTestGenerator`
5. ⏳ Implement `RandomTestGenerator`
6. ⏳ Write unit tests for test generators
7. ⏳ Test với real C functions

---

**See also**:
- `IMPLEMENTATION_GUIDE.md` - Implementation details
- `ARCHITECTURE.md` - Overall architecture
- Test generation code in `src/test_generator/`

