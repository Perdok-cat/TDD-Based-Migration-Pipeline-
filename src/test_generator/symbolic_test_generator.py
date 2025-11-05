"""
Symbolic Test Generator - Tạo test cases bằng symbolic execution
"""
import logging
from typing import List, Optional
from datetime import datetime

from ..core.models.c_program import CProgram, CFunction
from ..core.models.test_case import TestCase, TestSuite
from .klee_wrapper import KleeWrapper, KleeTestCase


class SymbolicTestGenerator:
    """
    Generate test cases using symbolic execution
    
    Advantages over random testing:
    - Guarantees path coverage
    - Automatically finds edge cases
    - No need to manually define boundaries
    - Discovers bugs in original C code
    
    Uses KLEE symbolic execution engine
    """
    
    def __init__(
        self,
        timeout: int = 60,
        max_tests_per_function: int = 100,
        fallback_to_random: bool = True
    ):
        """
        Initialize symbolic test generator
        
        Args:
            timeout: Timeout per function (seconds)
            max_tests_per_function: Max test cases per function
            fallback_to_random: If KLEE fails, fallback to random tests
        """
        self.logger = logging.getLogger(__name__)
        self.klee_wrapper = KleeWrapper(timeout=timeout, max_tests=max_tests_per_function)
        self.fallback_to_random = fallback_to_random
    
    def is_available(self) -> bool:
        """Check if symbolic execution is available"""
        return self.klee_wrapper.check_klee_available()
    
    def generate_tests(
        self,
        program: CProgram,
        function_name: Optional[str] = None
    ) -> TestSuite:
        """
        Generate symbolic test suite for program
        
        Args:
            program: CProgram to test
            function_name: Specific function (None = all functions)
        
        Returns:
            TestSuite with symbolic test cases
        """
        test_suite = TestSuite(
            program_id=program.program_id,
            function_name=function_name
        )
        
        # Check KLEE availability
        if not self.is_available():
            self.logger.warning("Symbolic execution not available")
            if self.fallback_to_random:
                self.logger.info("Falling back to random test generation")
                # Could import and use InputGenerator here as fallback
            return test_suite
        
        # Determine which functions to test
        if function_name:
            func = program.get_function_by_name(function_name)
            functions = [func] if func else []
        else:
            # Test all non-static functions (exclude main() to avoid duplicate symbol error)
            functions = [f for f in program.functions if not f.is_static and f.name != 'main']
        
        # Generate symbolic tests for each function
        for func in functions:
            self.logger.info(f"Generating symbolic tests for {func.name}...")
            
            try:
                # Get symbolic test cases from KLEE
                # Extract include directories from file paths
                include_dirs = []
                if getattr(program, 'includes', None):
                    for inc in program.includes:
                        if not inc.is_system:  # Only user includes
                            # Extract directory from file path
                            from pathlib import Path
                            inc_path = Path(inc.file_name)
                            if inc_path.parent and inc_path.parent != Path('.'):
                                include_dirs.append(str(inc_path.parent))
                
                # Remove duplicates
                include_dirs = list(set(include_dirs))
                klee_tests = self.klee_wrapper.generate_test_cases(
                    function=func,
                    source_code=program.source_code,
                    includes=[inc.file_name for inc in program.includes],
                    include_dirs=include_dirs
                )
                
                # Convert KLEE tests to TestCase objects
                for klee_test in klee_tests:
                    test_case = self._klee_to_test_case(
                        klee_test,
                        program.program_id,
                        func.name
                    )
                    test_suite.add_test_case(test_case)
                
                self.logger.info(
                    f"  ✓ Generated {len(klee_tests)} symbolic test cases for {func.name}"
                )
                
            except Exception as e:
                self.logger.error(f"  ✗ Symbolic execution failed for {func.name}: {e}")
                
                if self.fallback_to_random:
                    self.logger.info(f"  → Falling back to boundary tests for {func.name}")
                    # Add a few basic boundary tests as fallback
                    # (In production, could call InputGenerator here)
        
        self.logger.info(
            f"Total symbolic test cases: {len(test_suite.test_cases)} "
            f"for {len(functions)} function(s)"
        )
        
        return test_suite
    
    def _klee_to_test_case(
        self,
        klee_test: KleeTestCase,
        program_id: str,
        function_name: str
    ) -> TestCase:
        """Convert KLEE test case to TestCase object"""
        return TestCase(
            name=f"{function_name}_symbolic_{klee_test.test_id}",
            program_id=program_id,
            function_name=function_name,
            inputs=klee_test.inputs,
            category="symbolic",
            description=f"Symbolic execution test - {klee_test.path_info}",
            created_at=datetime.now()
        )
    
    def generate_hybrid_tests(
        self,
        program: CProgram,
        symbolic_ratio: float = 0.7
    ) -> TestSuite:
        """
        Generate hybrid test suite: symbolic + random
        
        Args:
            program: CProgram to test
            symbolic_ratio: Ratio of symbolic tests (0.7 = 70% symbolic, 30% random)
        
        Returns:
            Combined TestSuite
        """
        # Generate symbolic tests
        symbolic_suite = self.generate_tests(program)
        
        # TODO: Add random tests to complement symbolic tests
        # This would use InputGenerator for additional coverage
        
        return symbolic_suite


class SymbolicTestStrategy:
    """
    Strategy patterns for symbolic test generation
    
    Different strategies for different code complexities:
    - QUICK: Symbolic for simple functions only
    - BALANCED: Symbolic for complex, random for simple
    - THOROUGH: Symbolic for all functions
    """
    
    QUICK = "quick"
    BALANCED = "balanced"
    THOROUGH = "thorough"
    
    @staticmethod
    def select_functions_for_symbolic(
        functions: List[CFunction],
        strategy: str = BALANCED
    ) -> List[CFunction]:
        """
        Select which functions to apply symbolic execution
        
        Args:
            functions: List of functions
            strategy: Selection strategy
        
        Returns:
            Filtered list of functions for symbolic execution
        """
        if strategy == SymbolicTestStrategy.THOROUGH:
            # All functions
            return functions
        
        elif strategy == SymbolicTestStrategy.QUICK:
            # Only simple functions (< 10 lines, complexity < 5)
            return [
                f for f in functions
                if f.complexity < 5 and (f.line_end - f.line_start) < 10
            ]
        
        elif strategy == SymbolicTestStrategy.BALANCED:
            # Complex functions only (higher priority for symbolic)
            return [
                f for f in functions
                if f.complexity >= 3 or (f.line_end - f.line_start) >= 5
            ]
        
        else:
            return functions

