"""
Migration Orchestrator - Điều phối toàn bộ workflow migration
Đây là thành phần chính thực hiện workflow theo sơ đồ
"""
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
import time

from ..core.models.c_program import CProgram
from ..core.models.dependency_graph import DependencyGraph
from ..core.models.test_case import TestCase, TestSuite, ValidationResult
from ..core.models.conversion_result import (
    ConversionResult,
    MigrationReport,
    ConversionStatus
)

# Import services
from ..test_generator.test_generator import TestGenerator
from ..test_runner.c_test_runner import CTestRunner
from ..test_runner.csharp_test_runner import CSharpTestRunner
from ..converter.hybrid_converter import create_converter
from ..validator.output_validator import OutputValidator
from ..core.Cparser import CParser
from ..core.models.c_program import CInclude, CFunction, CVariable
from ..core.dependencies_analysis import DependenciesAnalysis
# from ..report_generator.report_service import ReportService  # TODO: Implement later


class MigrationOrchestrator:
    """
    Orchestrator chính cho migration pipeline
    Thực hiện workflow theo sơ đồ:
    1. Parse C programs
    2. Build dependency graph
    3. Loop: Select component → Test → Convert → Validate
    4. Generate report
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize orchestrator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.test_generator = TestGenerator()
        self.c_test_runner = CTestRunner()
        self.csharp_test_runner = CSharpTestRunner()
        self.converter = create_converter(self.config.get("converter", {}))
        self.validator = OutputValidator()
        # self.report_service = ReportService()  # TODO: Implement later
        
        # State
        self.programs: List[CProgram] = []
        self.dependency_graph: Optional[DependencyGraph] = None
        self.migration_report: MigrationReport = MigrationReport()
    
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            "max_retries": 3,
            "parallel_execution": False,
            "generate_html_report": True,
            "generate_json_report": True,
            "output_dir": "output",
            "verbose": True
        }
    
    def migrate_all(
        self,
        input_dir: str,
        output_dir: Optional[str] = None
    ) -> MigrationReport:
        """
        Thực hiện migration cho tất cả C programs trong thư mục
        
        Args:
            input_dir: Thư mục chứa C source files
            output_dir: Thư mục output (optional)
            
        Returns:
            MigrationReport với kết quả
        """
        start_time = time.time()
        self.migration_report.started_at = datetime.now()
        
        self.logger.info("="*70)
        self.logger.info("Starting C to C# Migration Pipeline")
        self.logger.info("="*70)
        
        try:
            # Step 1: Parse C programs
            self.logger.info("\n[Step 1] Parsing C programs...")
            self.programs = self._parse_c_programs(input_dir)
            self._parsed_programs = self.programs  # Store for dependency analysis
            self.migration_report.total_programs = len(self.programs)
            self.logger.info(f"✓ Found {len(self.programs)} C programs")
            
            # Step 2: Build dependency graph
            self.logger.info("\n[Step 2] Analyzing dependencies...")
            self.dependency_graph = self._analyze_dependencies()
            cycles = self.dependency_graph.detect_circular_dependencies()
            if cycles:
                self.logger.warning(f"⚠ Found {len(cycles)} circular dependencies")
                for cycle in cycles:
                    self.logger.warning(f"  Cycle: {' → '.join(cycle)}")
            else:
                self.logger.info("✓ No circular dependencies found")
            
            # Step 3: Determine conversion order
            self.logger.info("\n[Step 3] Determining conversion order...")
            try:
                conversion_order = self.dependency_graph.get_conversion_order()
                self.logger.info(f"✓ Conversion order: {' → '.join(conversion_order)}")
            except ValueError as e:
                self.logger.error(f"✗ Cannot determine conversion order: {e}")
                return self.migration_report
            
            # Step 4: Convert files one by one in dependency order
            self.logger.info("\n[Step 4] Converting files in dependency order...")
            self.logger.info("-"*70)
            
            # Accumulate converted code from all files
            all_converted_code_parts: List[str] = []
            
            for idx, program_id in enumerate(conversion_order, 1):
                self.logger.info(f"\n[{idx}/{len(conversion_order)}] Converting: {program_id}")
                
                # Get program
                program = self._get_program_by_id(program_id)
                if not program:
                    self.logger.error(f"✗ Program not found: {program_id}")
                    continue
                
                # Convert single file with retry (using Gemini API)
                result = self._convert_program_with_retry(
                    program,
                    output_dir or self.config["output_dir"],
                    previously_converted_code=all_converted_code_parts  # Pass context of already converted files
                )
                
                # Add to report
                self.migration_report.add_result(result)
                
                # Update dependency graph and accumulate converted code
                if result.status == ConversionStatus.SUCCESS:
                    self.dependency_graph.mark_as_converted(program_id)
                    program.is_converted = True
                    # Accumulate converted code for next files
                    if result.csharp_code:
                        all_converted_code_parts.append(result.csharp_code)
                    self.logger.info(f"✓ {program_id}: {result.get_summary()}")
                else:
                    self.logger.error(f"✗ {program_id}: {result.get_summary()}")
            
            # Step 5: Generate report
            self.logger.info("\n[Step 5] Generating migration report...")
            self._generate_reports(output_dir or self.config["output_dir"])
            
        except Exception as e:
            self.logger.exception(f"Fatal error in migration pipeline: {e}")
        
        finally:
            # Finalize report
            self.migration_report.completed_at = datetime.now()
            self.migration_report.total_duration_seconds = time.time() - start_time
            
            self.logger.info("\n" + "="*70)
            self.logger.info("Migration Pipeline Completed")
            self.logger.info("="*70)
            self.logger.info(self.migration_report.get_summary())
        
        return self.migration_report
    
    def _convert_program_with_retry(
        self,
        program: CProgram,
        output_dir: str,
        previously_converted_code: Optional[List[str]] = None
    ) -> ConversionResult:
        """
        Convert một program với retry logic
        Thực hiện workflow: Test Generation → C Test → Conversion → C# Test → Validation
        
        Args:
            program: CProgram to convert
            output_dir: Output directory
            
        Returns:
            ConversionResult
        """
        result = ConversionResult(
            program_id=program.program_id,
            source_file=program.file_path,
            max_retries=self.config["max_retries"]
        )
        result.started_at = datetime.now()
        result.status = ConversionStatus.IN_PROGRESS
        
        max_retries = self.config["max_retries"]
        
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                self.logger.info(f"  Retry attempt {attempt}/{max_retries}")
            
            try:
                # Sub-step 1: Generate test cases
                self.logger.info(f"  → Generating test cases...")
                test_suite = self._generate_tests(program)
                result.metrics.tests_total = len(test_suite.test_cases)
                self.logger.info(f"    Generated {len(test_suite.test_cases)} test cases")
                
                # Sub-step 2: Run C tests (baseline)
                self.logger.info(f"  → Running C tests (baseline)...")
                c_test_results = self._run_c_tests(program, test_suite)
                self.logger.info(f"    C tests completed")
                
                # Sub-step 3: Convert to C# using Gemini API
                self.logger.info(f"  → Converting C to C# using Gemini API...")
                csharp_code = self._convert_to_csharp(program, previously_converted_code)
                result.csharp_code = csharp_code
                self.logger.info(f"    Conversion completed")
                
                # Sub-step 4: Run C# tests
                self.logger.info(f"  → Running C# tests...")
                csharp_test_results = self._run_csharp_tests(program, test_suite, csharp_code)
                self.logger.info(f"    C# tests completed")
                
                # Sub-step 5: Validate outputs
                self.logger.info(f"  → Validating outputs (C vs C#)...")
                validation_results = self._validate_outputs(
                    test_suite,
                    c_test_results,
                    csharp_test_results
                )
                
                # Count passed/failed tests
                passed = sum(1 for v in validation_results if v.is_match)
                failed = len(validation_results) - passed
                result.metrics.tests_passed = passed
                result.metrics.tests_failed = failed
                result.metrics.calculate_test_pass_rate()
                
                self.logger.info(
                    f"    Validation: {passed}/{len(validation_results)} tests passed "
                    f"({result.metrics.test_pass_rate:.1f}%)"
                )
                
                # Check if all tests passed
                if all(v.is_match for v in validation_results):
                    result.mark_success()
                    self.logger.info(f"  ✓ All tests passed!")
                    break
                else:
                    if attempt < max_retries:
                        self.logger.warning(f"  ✗ {failed} tests failed, retrying...")
                        result.retry_count = attempt
                    else:
                        result.mark_failed(f"{failed} tests failed after {max_retries} attempts")
                        self.logger.error(f"  ✗ Max retries reached, conversion failed")
                
            except Exception as e:
                error_msg = f"Error during conversion: {str(e)}"
                self.logger.error(f"  ✗ {error_msg}")
                if attempt >= max_retries:
                    result.mark_failed(error_msg)
                result.retry_count = attempt
        
        result.completed_at = datetime.now()
        return result
    
    # Placeholder methods (to be implemented with actual services)
    
    def _parse_c_programs(self, input_dir: str) -> List[CProgram]:
        """Parse all C programs in directory"""
        self.logger.info(f"Parsing C programs from: {input_dir}")
        
        try:
            parser = CParser()
            
            # Find all C files
            c_files = parser.find_c_files(input_dir)
            if not c_files:
                self.logger.warning(f"No C files found in {input_dir}")
                return []
            
            self.logger.info(f"Found {len(c_files)} C files to parse")
            
            programs = []
            for file_path in c_files:
                try:
                    # Parse the file
                    tree, code_bytes = parser.parse_file(file_path)
                    
                    # Check if parsing was successful
                    if tree is None:
                        self.logger.error(f"Failed to parse {file_path}: tree is None")
                        continue
                    
                    if tree.root_node is None:
                        self.logger.error(f"Failed to parse {file_path}: root_node is None")
                        continue
                    
                    # Check for parse errors
                    if tree.root_node.has_error:
                        self.logger.warning(f"Parse tree has errors for {file_path}, but continuing...")
                    
                    source_code = code_bytes.decode('utf-8', errors='ignore')
                    
                    # Extract basic information
                    root = tree.root_node
                    system_includes, user_includes = parser.extract_includes_simple(root, code_bytes)
                    
                    # Create CInclude objects
                    includes = []
                    for header in system_includes:
                        includes.append(CInclude(
                            file_name=header,
                            is_system=True,
                            line_number=0  # TODO: Extract actual line numbers
                        ))
                    for header in user_includes:
                        includes.append(CInclude(
                            file_name=header,
                            is_system=False,
                            line_number=0  # TODO: Extract actual line numbers
                        ))
                    
                    # Extract functions
                    functions = []
                    for func_name, func_node in parser.walk_functions(root, code_bytes):
                        # Extract function calls
                        calls = parser.extract_calls_in_node(func_node, code_bytes)
                        
                        # Get function text
                        func_text = parser._node_text(func_node, code_bytes)
                        
                        # Extract function signature (return type and parameters)
                        return_type, param_list = parser.extract_function_signature(func_node, code_bytes)
                        
                        # Convert parameter tuples to CVariable objects
                        from ..core.models.c_program import CVariable
                        parameters = []
                        for param_type, param_name in param_list:
                            # Count pointer levels
                            pointer_level = param_type.count('*')
                            base_type = param_type.replace('*', '').strip()
                            
                            parameters.append(CVariable(
                                name=param_name,
                                data_type=base_type,
                                pointer_level=pointer_level,
                                is_pointer=(pointer_level > 0)
                            ))
                        
                        # Create CFunction object
                        c_function = CFunction(
                            name=func_name,
                            return_type=return_type,
                            parameters=parameters,
                            body=func_text,
                            called_functions=calls,
                            line_start=func_node.start_point[0] + 1,
                            line_end=func_node.end_point[0] + 1,
                            complexity=0  # TODO: Calculate complexity
                        )
                        functions.append(c_function)
                    
                    # Create CProgram object
                    program_id = file_path.stem  # Use filename without extension as ID
                    program = CProgram(
                        program_id=program_id,
                        file_path=str(file_path),
                        source_code=source_code,
                        includes=includes,
                        functions=functions,
                        lines_of_code=len(source_code.split('\n')),
                        complexity_score=0.0
                    )
                    
                    # Calculate complexity
                    program.calculate_complexity()
                    
                    programs.append(program)
                    self.logger.debug(f"Parsed {file_path}: {len(functions)} functions, {len(includes)} includes")
                    
                except Exception as e:
                    self.logger.error(f"Failed to parse {file_path}: {e}")
                    import traceback
                    self.logger.debug(f"Traceback: {traceback.format_exc()}")
                    continue
            
            self.logger.info(f"Successfully parsed {len(programs)} C programs")
            return programs
            
        except Exception as e:
            self.logger.error(f"Error parsing C programs: {e}")
            return []
    
    def _analyze_dependencies(self) -> DependencyGraph:
        """Analyze dependencies between programs"""
        self.logger.info("Analyzing dependencies between C programs")
        
        try:
            if not hasattr(self, '_parsed_programs') or not self._parsed_programs:
                self.logger.warning("No parsed programs available for dependency analysis")
                return DependencyGraph()
            
            # Create file data for dependency analysis
            file_data_for_graph = {}
            for program in self._parsed_programs:
                file_path = program.file_path
                file_name = Path(file_path).name
                
                # Extract user includes (non-system headers)
                user_includes = []
                for include in program.includes:
                    if not include.is_system:
                        user_includes.append(include.file_name)
                
                file_data_for_graph[file_path] = {
                    'user_includes': user_includes,
                    'system_includes': [inc.file_name for inc in program.includes if inc.is_system],
                    'functions': program.get_all_function_names(),
                    'total_lines': program.lines_of_code
                }
            
            # Use DependenciesAnalysis to build dependency graph
            deps_analyzer = DependenciesAnalysis()
            graph, order, cycles = deps_analyzer.analyze_dependencies(
                file_data_for_graph, 
                export_graph=False
            )
            
            # Convert to DependencyGraph format
            dependency_graph = DependencyGraph()
            
            # Add nodes to dependency graph
            for file_path, program in zip(file_data_for_graph.keys(), self._parsed_programs):
                file_name = Path(file_path).name
                program_id = program.program_id
                
                # Get dependencies for this file
                dependencies = []
                if file_name in graph:
                    for dep_file in graph[file_name]:
                        # Find the corresponding program ID
                        dep_program_id = None
                        for p in self._parsed_programs:
                            if Path(p.file_path).name == dep_file:
                                dep_program_id = p.program_id
                                break
                        
                        if dep_program_id and dep_program_id != program_id:
                            dependencies.append(dep_program_id)
                
                dependency_graph.add_node(program_id, dependencies)
            
            # Log analysis results
            stats = dependency_graph.get_statistics()
            self.logger.info(f"Dependency analysis complete:")
            self.logger.info(f"  - Total programs: {stats['total_programs']}")
            self.logger.info(f"  - Total dependencies: {stats['total_dependencies']}")
            self.logger.info(f"  - Circular dependencies: {stats['circular_dependencies']}")
            
            if cycles:
                self.logger.warning(f"Found {len(cycles)} circular dependencies:")
                for i, cycle in enumerate(cycles, 1):
                    cycle_str = " -> ".join(cycle)
                    self.logger.warning(f"  Cycle {i}: {cycle_str}")
            else:
                self.logger.info("No circular dependencies found")
            
            # Try to get conversion order
            try:
                conversion_order = dependency_graph.get_conversion_order()
                self.logger.info(f"Recommended conversion order: {conversion_order}")
            except ValueError as e:
                self.logger.warning(f"Cannot determine conversion order: {e}")
            
            return dependency_graph
            
        except Exception as e:
            self.logger.error(f"Error analyzing dependencies: {e}")
            return DependencyGraph()
    
    def _generate_tests(self, program: CProgram) -> TestSuite:
        """Generate test cases for program"""
        return self.test_generator.generate_tests(program)
    
    def _run_c_tests(self, program: CProgram, test_suite: TestSuite) -> Dict:
        """Run C tests and get baseline outputs"""
        # Generate test harness
        test_harness_code = self.test_generator.generate_test_harness_c(program, test_suite)
        
        # Run tests
        return self.c_test_runner.run_tests(program, test_suite, test_harness_code)
    
    def _convert_to_csharp(self, program: CProgram, previously_converted_code: Optional[List[str]] = None) -> str:
        """
        Convert C program to C# using Gemini API
        
        Args:
            program: CProgram to convert
            previously_converted_code: List of C# code from previously converted files (for context)
            
        Returns:
            C# code string
        """
        # Use HybridConverter which will use Gemini API if available
        # Previously converted code can be used as context if needed
        return self.converter.convert(program)
    
    def _run_csharp_tests(
        self,
        program: CProgram,
        test_suite: TestSuite,
        csharp_code: str
    ) -> Dict:
        """Run C# tests"""
        # Generate C# test harness
        test_harness_code = self.csharp_test_runner.generate_test_harness_csharp(program, test_suite)
        
        # Run tests
        return self.csharp_test_runner.run_tests(program, test_suite, csharp_code, test_harness_code)
    
    def _validate_outputs(
        self,
        test_suite: TestSuite,
        c_results: Dict,
        csharp_results: Dict
    ) -> List[ValidationResult]:
        """Validate C vs C# outputs"""
        return self.validator.validate(test_suite, c_results, csharp_results)
    
    def _generate_reports(self, output_dir: str) -> None:
        """Generate migration reports"""
        # TODO: Implement with ReportService
        self.logger.warning("ReportService not yet implemented")
        pass
    
    def _get_program_by_id(self, program_id: str) -> Optional[CProgram]:
        """Get program by ID"""
        for program in self.programs:
            if program.program_id == program_id:
                return program
        return None

