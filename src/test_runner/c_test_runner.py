"""
C Test Runner - Compile và run C tests để lấy baseline outputs
"""
import subprocess
import logging
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from ..core.models.c_program import CProgram
from ..core.models.test_case import TestSuite, TestResult, TestStatus


class CTestRunner:
    """
    Compile và run C tests
    
    Process:
    1. Generate test harness file
    2. Compile with GCC
    3. Execute binary
    4. Parse output
    5. Return TestResult objects
    """
    
    def __init__(self, gcc_path: str = "gcc", timeout: int = 30):
        """
        Initialize C test runner
        
        Args:
            gcc_path: Path to GCC compiler (default: 'gcc')
            timeout: Timeout cho mỗi test run (seconds)
        """
        self.gcc_path = gcc_path
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Verify GCC is available
        self._verify_compiler()
    
    def _verify_compiler(self) -> bool:
        """Verify GCC compiler is available"""
        try:
            result = subprocess.run(
                [self.gcc_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.logger.info(f"GCC compiler found: {self.gcc_path}")
                return True
            else:
                self.logger.error(f"GCC compiler not working: {self.gcc_path}")
                return False
        except Exception as e:
            self.logger.error(f"GCC compiler not found: {e}")
            return False
    
    def compile(
        self,
        source_files: List[str],
        output_binary: Optional[str] = None,
        compiler_flags: Optional[List[str]] = None
    ) -> bool:
        """
        Compile C source files
        
        Args:
            source_files: List of C source file paths
            output_binary: Output binary path (default: temp file)
            compiler_flags: Additional compiler flags
        
        Returns:
            True if compilation succeeded, False otherwise
        """
        if compiler_flags is None:
            compiler_flags = ["-std=c99", "-Wall", "-lm"]  # -lm for math library
        
        if output_binary is None:
            # Create temp file for binary
            fd, output_binary = tempfile.mkstemp(suffix=".out")
            os.close(fd)
        
        # Build compile command
        compile_cmd = [self.gcc_path] + source_files + ["-o", output_binary] + compiler_flags
        
        self.logger.info(f"Compiling: {' '.join(compile_cmd)}")
        
        try:
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.logger.info(f"✓ Compilation successful: {output_binary}")
                return True
            else:
                self.logger.error(f"✗ Compilation failed:")
                self.logger.error(f"  stderr: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("✗ Compilation timeout")
            return False
        except Exception as e:
            self.logger.error(f"✗ Compilation error: {e}")
            return False
    
    def run_tests(
        self,
        program: CProgram,
        test_suite: TestSuite,
        test_harness_code: str
    ) -> Dict[str, TestResult]:
        """
        Run C tests và capture outputs
        
        Args:
            program: CProgram being tested
            test_suite: TestSuite with test cases
            test_harness_code: Generated C test harness code
        
        Returns:
            Dict mapping test_case_id -> TestResult
        """
        results: Dict[str, TestResult] = {}
        
        # Create temporary directory for test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Write test harness
            harness_file = temp_path / "test_harness.c"
            harness_file.write_text(test_harness_code)
            
            # Copy/write original source (remove main() to avoid duplicate definition)
            source_file = temp_path / "original.c"
            # Remove main() function from source code
            cleaned_source = self._remove_main_function(program.source_code)
            source_file.write_text(cleaned_source)
            
            # Compile
            binary_file = temp_path / "test.out"
            compile_success = self.compile(
                source_files=[str(harness_file), str(source_file)],
                output_binary=str(binary_file)
            )
            
            if not compile_success:
                # Mark all tests as error
                for test_case in test_suite.test_cases:
                    result = TestResult(test_case_id=test_case.id)
                    result.mark_error("Compilation failed")
                    results[test_case.id] = result
                return results
            
            # Run binary
            self.logger.info("Running C tests...")
            
            try:
                start_time = datetime.now()
                
                run_result = subprocess.run(
                    [str(binary_file)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                
                end_time = datetime.now()
                execution_time = end_time - start_time
                
                # Parse output
                results = self._parse_test_output(
                    test_suite,
                    run_result.stdout,
                    run_result.stderr,
                    run_result.returncode,
                    execution_time
                )
                
                self.logger.info(f"✓ C tests completed in {execution_time.total_seconds():.2f}s")
                
            except subprocess.TimeoutExpired:
                self.logger.error(f"✗ Test execution timeout ({self.timeout}s)")
                # Mark all as error
                for test_case in test_suite.test_cases:
                    result = TestResult(test_case_id=test_case.id)
                    result.mark_error(f"Execution timeout ({self.timeout}s)")
                    results[test_case.id] = result
            
            except Exception as e:
                self.logger.error(f"✗ Test execution error: {e}")
                for test_case in test_suite.test_cases:
                    result = TestResult(test_case_id=test_case.id)
                    result.mark_error(f"Execution error: {str(e)}")
                    results[test_case.id] = result
        
        return results
    
    def _parse_test_output(
        self,
        test_suite: TestSuite,
        stdout: str,
        stderr: str,
        exit_code: int,
        execution_time: timedelta
    ) -> Dict[str, TestResult]:
        """
        Parse test output để extract results
        
        Args:
            test_suite: TestSuite
            stdout: Standard output
            stderr: Standard error
            exit_code: Exit code
            execution_time: Total execution time
        
        Returns:
            Dict mapping test_case_id -> TestResult
        """
        results: Dict[str, TestResult] = {}
        
        # Parse stdout line by line
        # Expected format: "Test <test_name>: result = <value>"
        #                  "Test <test_name>: completed"
        
        for test_case in test_suite.test_cases:
            result = TestResult(test_case_id=test_case.id)
            result.started_at = datetime.now()
            result.standard_output = stdout
            result.standard_error = stderr
            result.exit_code = exit_code
            result.execution_time = execution_time
            
            # Try to find test result in output
            test_pattern = f"Test {test_case.name}:"
            
            outputs = {}
            for line in stdout.split('\n'):
                if test_pattern in line:
                    # Extract result
                    if "result =" in line:
                        # Parse result value
                        parts = line.split("result =")
                        if len(parts) > 1:
                            try:
                                value_str = parts[1].strip()
                                # Try to parse as number
                                if '.' in value_str:
                                    outputs['return_value'] = float(value_str)
                                else:
                                    outputs['return_value'] = int(value_str)
                            except ValueError:
                                outputs['return_value'] = value_str
                    elif "completed" in line:
                        outputs['completed'] = True
            
            if outputs or exit_code == 0:
                result.mark_success(outputs)
            else:
                result.mark_failure("No output found or non-zero exit code", outputs)
            
            results[test_case.id] = result
        
        return results
    
    def _remove_main_function(self, source_code: str) -> str:
        """
        Remove main() function from source code to avoid duplicate symbol error.
        
        This assumes main() has standard format and removes it completely.
        """
        import re
        
        # More robust pattern that handles braces properly
        lines = source_code.split('\n')
        filtered_lines = []
        in_main = False
        brace_count = 0
        
        for i, line in enumerate(lines):
            # Check if this line starts main() function
            if re.match(r'\s*(int|void)\s+main\s*\(', line):
                in_main = True
                brace_count = line.count('{') - line.count('}')
                continue  # Skip this line
            
            if in_main:
                # Count braces
                brace_count += line.count('{') - line.count('}')
                
                # If we closed all braces (brace_count <= 0), we're done with main
                if brace_count <= 0:
                    in_main = False
                continue  # Skip lines inside main
            
            if not in_main:
                filtered_lines.append(line)
        
        result = '\n'.join(filtered_lines)
        
        # Remove multiple blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result

