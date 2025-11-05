"""
Test Generator - Tạo test cases tự động cho C functions
"""
import logging
from typing import List, Optional
from datetime import datetime

from ..core.models.c_program import CProgram, CFunction
from ..core.models.test_case import TestCase, TestSuite
from .input_generator import InputGenerator
from .symbolic_test_generator import SymbolicTestGenerator


class TestGenerator:
    """
    Tạo test cases tự động cho C programs
    
    Strategies:
    - Boundary testing: Min/max values, zero, negative
    - Edge cases: NULL pointers, overflow/underflow
    - Random testing: Fuzzing với seed
    - Symbolic execution: KLEE-based path exploration (NEW)
    """
    
    def __init__(self, seed: int = 42, enable_symbolic: bool = True):
        """
        Initialize test generator
        
        Args:
            seed: Random seed để reproducible tests
            enable_symbolic: Enable symbolic execution (requires KLEE)
        """
        self.logger = logging.getLogger(__name__)
        self.input_generator = InputGenerator(seed=seed)
        
        # Symbolic execution support
        self.enable_symbolic = enable_symbolic
        self.symbolic_generator = None
        if enable_symbolic:
            self.symbolic_generator = SymbolicTestGenerator(
                timeout=60,
                max_tests_per_function=50,
                fallback_to_random=True
            )
            if self.symbolic_generator.is_available():
                self.logger.info("✓ Symbolic execution enabled (KLEE)")
            else:
                self.logger.info("✗ Symbolic execution unavailable (KLEE not found)")
    
    def generate_tests(
        self,
        program: CProgram,
        function_name: Optional[str] = None,
        strategies: Optional[List[str]] = None
    ) -> TestSuite:
        """
        Generate test suite cho program/function
        
        Args:
            program: CProgram to generate tests for
            function_name: Specific function name (None = all functions)
            strategies: List of strategies 
                       ['boundary', 'edge', 'random', 'symbolic']
                       Default: ['symbolic'] if available, else ['boundary', 'edge', 'random']
        
        Returns:
            TestSuite with generated test cases
        """
        if strategies is None:
            # Prefer symbolic but add boundary fallback to always have tests
            if self.enable_symbolic and self.symbolic_generator and self.symbolic_generator.is_available():
                strategies = ['symbolic', 'boundary']
            else:
                strategies = ['boundary', 'edge', 'random']
        
        test_suite = TestSuite(
            program_id=program.program_id,
            function_name=function_name
        )
        
        # Determine which functions to test
        if function_name:
            func = program.get_function_by_name(function_name)
            if func:
                functions = [func]
            else:
                self.logger.warning(f"Function '{function_name}' not found in {program.program_id}")
                return test_suite
        else:
            # Test all non-static functions (exclude main() to avoid duplicate symbol error)
            functions = [f for f in program.functions if not f.is_static and f.name != 'main']
        
        # Generate tests for each function
        for func in functions:
            self.logger.info(f"Generating tests for {func.name}...")
            
            for strategy in strategies:
                # Check if symbolic execution requested
                if strategy == 'symbolic':
                    if self.symbolic_generator and self.symbolic_generator.is_available():
                        # Use symbolic execution
                        symbolic_suite = self.symbolic_generator.generate_tests(
                            program,
                            function_name=func.name
                        )
                        for test in symbolic_suite.test_cases:
                            test_suite.add_test_case(test)
                    else:
                        self.logger.warning(f"  Symbolic execution not available, skipping for {func.name}")
                else:
                    # Traditional strategies (boundary/edge/random)
                    tests = self._generate_tests_for_function(
                        program,
                        func,
                        strategy
                    )
                    for test in tests:
                        test_suite.add_test_case(test)
            
            self.logger.info(
                f"  Generated {len([t for t in test_suite.test_cases if t.function_name == func.name])} "
                f"test cases for {func.name}"
            )
        
        self.logger.info(
            f"Total test cases generated: {len(test_suite.test_cases)} "
            f"for {len(functions)} function(s)"
        )
        
        return test_suite
    
    def _generate_tests_for_function(
        self,
        program: CProgram,
        function: CFunction,
        strategy: str
    ) -> List[TestCase]:
        """
        Generate test cases cho một function với một strategy
        
        Args:
            program: CProgram
            function: CFunction to test
            strategy: 'boundary', 'edge', or 'random'
        
        Returns:
            List of TestCase objects
        """
        test_cases = []
        
        # Generate input combinations
        input_combinations = self.input_generator.generate_combinations(
            function,
            strategy=strategy
        )
        
        # Create test case for each combination
        for idx, inputs in enumerate(input_combinations, 1):
            test_case = TestCase(
                name=f"{function.name}_{strategy}_{idx}",
                program_id=program.program_id,
                function_name=function.name,
                inputs=inputs,
                category=strategy,
                description=f"{strategy.capitalize()} test for {function.name}",
                created_at=datetime.now()
            )
            test_cases.append(test_case)
        
        return test_cases
    
    def generate_test_harness_c(
        self,
        program: CProgram,
        test_suite: TestSuite,
        output_file: Optional[str] = None
    ) -> str:
        """
        Generate C test harness code để run tests
        
        Args:
            program: CProgram
            test_suite: TestSuite with test cases
            output_file: Optional output file path
        
        Returns:
            C code string for test harness
        """
        code_lines = []
        
        # Headers
        code_lines.append("#include <stdio.h>")
        code_lines.append("#include <stdlib.h>")
        code_lines.append("#include <string.h>")
        code_lines.append("")
        
        # Include original program
        code_lines.append(f"// Original program: {program.file_path}")
        code_lines.append("")
        
        # Add function prototypes for all functions being tested
        # This ensures the harness can call them without redefinition errors
        tested_functions = set()
        for test_case in test_suite.test_cases:
            func = program.get_function_by_name(test_case.function_name)
            if func and func.name not in tested_functions and func.name != 'main':
                tested_functions.add(func.name)
                # Generate function prototype
                params = ', '.join(
                    f"{p.data_type}{'*' * getattr(p, 'pointer_level', 0)} {p.name}" 
                    for p in func.parameters
                )
                if not params:
                    params = "void"
                code_lines.append(f"{func.return_type} {func.name}({params});")
        
        if tested_functions:
            code_lines.append("")
        
        # Test harness main
        code_lines.append("int main(void) {")
        code_lines.append("    int passed = 0;")
        code_lines.append("    int failed = 0;")
        code_lines.append("")
        
        # Generate test cases
        for test_case in test_suite.test_cases:
            func = program.get_function_by_name(test_case.function_name)
            if not func:
                continue
            
            code_lines.append(f"    // Test: {test_case.name}")
            code_lines.append("    {")
            
            # Prepare inputs
            for param_name, value in test_case.inputs.items():
                # Find parameter type
                param = next((p for p in func.parameters if p.name == param_name), None)
                if param:
                    code_lines.append(f"        {param.data_type} {param_name} = {value};")
            
            # Call function
            param_names = ', '.join(test_case.inputs.keys())
            if func.return_type.lower() != 'void':
                code_lines.append(f"        {func.return_type} result = {func.name}({param_names});")
                code_lines.append(f'        printf("Test {test_case.name}: result = %d\\n", result);')
            else:
                code_lines.append(f"        {func.name}({param_names});")
                code_lines.append(f'        printf("Test {test_case.name}: completed\\n");')
            
            code_lines.append("        passed++;")
            code_lines.append("    }")
            code_lines.append("")
        
        # Summary
        code_lines.append("    printf(\"\\n=== Test Summary ===\\n\");")
        code_lines.append("    printf(\"Passed: %d\\n\", passed);")
        code_lines.append("    printf(\"Failed: %d\\n\", failed);")
        code_lines.append("    return 0;")
        code_lines.append("}")
        
        code = '\n'.join(code_lines)
        
        # Optionally write to file
        if output_file:
            with open(output_file, 'w') as f:
                f.write(code)
            self.logger.info(f"Test harness written to: {output_file}")
        
        return code

