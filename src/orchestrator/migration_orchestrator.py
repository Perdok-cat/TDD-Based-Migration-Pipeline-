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

# Import services (will be implemented)
# from ..parser.c_parser import CParser
# from ..dependency_analyzer.dependency_service import DependencyAnalyzerService
# from ..test_generator.test_generator import TestGenerator
# from ..test_runner.c_test_runner import CTestRunner
# from ..test_runner.csharp_test_runner import CSharpTestRunner
# from ..converter.c_to_csharp_converter import CToC#Converter
# from ..validator.output_validator import OutputValidator
# from ..report_generator.report_service import ReportService


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
        
        # Initialize services (commented out until implemented)
        # self.parser = CParser()
        # self.dependency_analyzer = DependencyAnalyzerService()
        # self.test_generator = TestGenerator()
        # self.c_test_runner = CTestRunner()
        # self.csharp_test_runner = CSharpTestRunner()
        # self.converter = CToC#Converter()
        # self.validator = OutputValidator()
        # self.report_service = ReportService()
        
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
            
            # Step 3: Get conversion order
            self.logger.info("\n[Step 3] Determining conversion order...")
            try:
                conversion_order = self.dependency_graph.get_conversion_order()
                self.logger.info(f"✓ Conversion order: {' → '.join(conversion_order)}")
            except ValueError as e:
                self.logger.error(f"✗ Cannot determine conversion order: {e}")
                return self.migration_report
            
            # Step 4: Main conversion loop
            self.logger.info("\n[Step 4] Starting conversion loop...")
            self.logger.info("-"*70)
            
            for idx, program_id in enumerate(conversion_order, 1):
                self.logger.info(f"\n[{idx}/{len(conversion_order)}] Processing: {program_id}")
                
                # Get program
                program = self._get_program_by_id(program_id)
                if not program:
                    self.logger.error(f"✗ Program not found: {program_id}")
                    continue
                
                # Convert single program with retry
                result = self._convert_program_with_retry(
                    program,
                    output_dir or self.config["output_dir"]
                )
                
                # Add to report
                self.migration_report.add_result(result)
                
                # Update dependency graph
                if result.status == ConversionStatus.SUCCESS:
                    self.dependency_graph.mark_as_converted(program_id)
                    program.is_converted = True
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
        output_dir: str
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
                
                # Sub-step 3: Convert to C#
                self.logger.info(f"  → Converting C to C#...")
                csharp_code = self._convert_to_csharp(program)
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
        # TODO: Implement with CParser
        self.logger.warning("CParser not yet implemented, using mock data")
        return []
    
    def _analyze_dependencies(self) -> DependencyGraph:
        """Analyze dependencies between programs"""
        # TODO: Implement with DependencyAnalyzerService
        self.logger.warning("DependencyAnalyzer not yet implemented, using empty graph")
        return DependencyGraph()
    
    def _generate_tests(self, program: CProgram) -> TestSuite:
        """Generate test cases for program"""
        # TODO: Implement with TestGenerator
        self.logger.warning("TestGenerator not yet implemented")
        return TestSuite(program_id=program.program_id)
    
    def _run_c_tests(self, program: CProgram, test_suite: TestSuite) -> Dict:
        """Run C tests and get baseline outputs"""
        # TODO: Implement with CTestRunner
        self.logger.warning("CTestRunner not yet implemented")
        return {}
    
    def _convert_to_csharp(self, program: CProgram) -> str:
        """Convert C program to C#"""
        # TODO: Implement with CToC#Converter
        self.logger.warning("CToC#Converter not yet implemented")
        return "// TODO: Generated C# code"
    
    def _run_csharp_tests(
        self,
        program: CProgram,
        test_suite: TestSuite,
        csharp_code: str
    ) -> Dict:
        """Run C# tests"""
        # TODO: Implement with CSharpTestRunner
        self.logger.warning("CSharpTestRunner not yet implemented")
        return {}
    
    def _validate_outputs(
        self,
        test_suite: TestSuite,
        c_results: Dict,
        csharp_results: Dict
    ) -> List[ValidationResult]:
        """Validate C vs C# outputs"""
        # TODO: Implement with OutputValidator
        self.logger.warning("OutputValidator not yet implemented")
        return []
    
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

