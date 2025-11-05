"""
Output Validator - So sánh outputs giữa C và C#
"""
import logging
import math
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..core.models.test_case import (
    TestSuite,
    TestResult,
    ValidationResult,
    OutputDifference
)


class OutputValidator:
    """
    Validate outputs giữa C và C# tests
    
    Features:
    - Exact comparison cho integers, strings
    - Tolerance comparison cho floating-point
    - Detailed diff reporting
    """
    
    def __init__(
        self,
        float_tolerance: float = 1e-6,
        double_tolerance: float = 1e-12
    ):
        """
        Initialize output validator
        
        Args:
            float_tolerance: Tolerance cho float comparison
            double_tolerance: Tolerance cho double comparison
        """
        self.logger = logging.getLogger(__name__)
        self.float_tolerance = float_tolerance
        self.double_tolerance = double_tolerance
    
    def validate(
        self,
        test_suite: TestSuite,
        c_results: Dict[str, TestResult],
        csharp_results: Dict[str, TestResult]
    ) -> List[ValidationResult]:
        """
        Validate C vs C# test results
        
        Args:
            test_suite: TestSuite being validated
            c_results: Dict of C test results (test_case_id -> TestResult)
            csharp_results: Dict of C# test results (test_case_id -> TestResult)
        
        Returns:
            List of ValidationResult objects
        """
        self.logger.info("Validating C vs C# outputs...")
        
        validation_results: List[ValidationResult] = []
        
        for test_case in test_suite.test_cases:
            test_id = test_case.id
            
            # Get results for this test case
            c_result = c_results.get(test_id)
            csharp_result = csharp_results.get(test_id)
            
            # Create validation result
            validation = ValidationResult(
                test_case_id=test_id,
                c_result=c_result,
                csharp_result=csharp_result,
                validated_at=datetime.now()
            )
            
            # Check if both tests ran successfully
            if not c_result or not csharp_result:
                validation.is_match = False
                validation.differences.append(
                    OutputDifference(
                        variable_name="test_execution",
                        c_value="missing" if not c_result else "present",
                        csharp_value="missing" if not csharp_result else "present",
                        description="Test did not execute on both platforms",
                        is_critical=True
                    )
                )
                validation_results.append(validation)
                continue
            
            # Compare outputs
            c_outputs = c_result.outputs
            csharp_outputs = csharp_result.outputs
            
            # Get all output keys
            all_keys = set(c_outputs.keys()) | set(csharp_outputs.keys())
            validation.total_outputs = len(all_keys)
            
            # Compare each output
            for key in all_keys:
                c_value = c_outputs.get(key)
                csharp_value = csharp_outputs.get(key)
                
                # Check if key exists in both
                if key not in c_outputs:
                    validation.differences.append(
                        OutputDifference(
                            variable_name=key,
                            c_value="<missing>",
                            csharp_value=csharp_value,
                            description="Output missing in C",
                            is_critical=True
                        )
                    )
                    validation.different_outputs += 1
                    continue
                
                if key not in csharp_outputs:
                    validation.differences.append(
                        OutputDifference(
                            variable_name=key,
                            c_value=c_value,
                            csharp_value="<missing>",
                            description="Output missing in C#",
                            is_critical=True
                        )
                    )
                    validation.different_outputs += 1
                    continue
                
                # Compare values
                is_match, difference = self._compare_values(key, c_value, csharp_value)
                
                if is_match:
                    validation.matching_outputs += 1
                else:
                    validation.different_outputs += 1
                    if difference:
                        validation.differences.append(difference)
            
            # Set overall match status
            validation.is_match = (
                validation.different_outputs == 0 and
                validation.total_outputs > 0
            )
            
            validation_results.append(validation)
        
        # Log summary
        total = len(validation_results)
        passed = sum(1 for v in validation_results if v.is_match)
        failed = total - passed
        
        self.logger.info(
            f"Validation completed: {passed}/{total} tests passed "
            f"({passed/total*100:.1f}%)" if total > 0 else "No tests to validate"
        )
        
        return validation_results
    
    def _compare_values(
        self,
        key: str,
        c_value: Any,
        csharp_value: Any
    ) -> tuple[bool, Optional[OutputDifference]]:
        """
        Compare two values with appropriate comparison method
        
        Args:
            key: Variable/output name
            c_value: C value
            csharp_value: C# value
        
        Returns:
            Tuple of (is_match, OutputDifference or None)
        """
        # Type check
        if type(c_value) != type(csharp_value):
            # Try to convert if possible
            try:
                if isinstance(c_value, (int, float)) and isinstance(csharp_value, (int, float)):
                    # Both numeric, can compare
                    pass
                else:
                    # Type mismatch
                    return False, OutputDifference(
                        variable_name=key,
                        c_value=c_value,
                        csharp_value=csharp_value,
                        description=f"Type mismatch: {type(c_value).__name__} vs {type(csharp_value).__name__}",
                        is_critical=True
                    )
            except:
                return False, OutputDifference(
                    variable_name=key,
                    c_value=c_value,
                    csharp_value=csharp_value,
                    description="Type mismatch",
                    is_critical=True
                )
        
        # Float comparison
        if isinstance(c_value, float) or isinstance(csharp_value, float):
            return self._compare_floats(key, c_value, csharp_value)
        
        # Exact comparison for other types
        if c_value == csharp_value:
            return True, None
        else:
            return False, OutputDifference(
                variable_name=key,
                c_value=c_value,
                csharp_value=csharp_value,
                description="Values do not match",
                is_critical=True
            )
    
    def _compare_floats(
        self,
        key: str,
        c_value: float,
        csharp_value: float
    ) -> tuple[bool, Optional[OutputDifference]]:
        """
        Compare floating-point values with tolerance
        
        Args:
            key: Variable name
            c_value: C float value
            csharp_value: C# float value
        
        Returns:
            Tuple of (is_match, OutputDifference or None)
        """
        # Convert to float
        try:
            c_val = float(c_value)
            cs_val = float(csharp_value)
        except (ValueError, TypeError):
            return False, OutputDifference(
                variable_name=key,
                c_value=c_value,
                csharp_value=csharp_value,
                description="Cannot convert to float",
                is_critical=True
            )
        
        # Check for special values
        if math.isnan(c_val) and math.isnan(cs_val):
            return True, None
        
        if math.isinf(c_val) and math.isinf(cs_val):
            if (c_val > 0) == (cs_val > 0):  # Same sign of infinity
                return True, None
        
        # Compare with tolerance
        diff = abs(c_val - cs_val)
        
        # Use relative tolerance for large numbers
        max_val = max(abs(c_val), abs(cs_val))
        if max_val > 1.0:
            tolerance = max_val * self.float_tolerance
        else:
            tolerance = self.float_tolerance
        
        if diff <= tolerance:
            # Within tolerance
            if diff > 0:
                # Small difference, not critical
                return True, OutputDifference(
                    variable_name=key,
                    c_value=c_val,
                    csharp_value=cs_val,
                    description=f"Float difference within tolerance: {diff:.2e}",
                    tolerance=tolerance,
                    is_critical=False
                )
            else:
                # Exact match
                return True, None
        else:
            # Outside tolerance
            return False, OutputDifference(
                variable_name=key,
                c_value=c_val,
                csharp_value=cs_val,
                description=f"Float difference exceeds tolerance: {diff:.2e} > {tolerance:.2e}",
                tolerance=tolerance,
                is_critical=True
            )
    
    def generate_diff_report(
        self,
        validation_results: List[ValidationResult]
    ) -> str:
        """
        Generate detailed diff report
        
        Args:
            validation_results: List of ValidationResult objects
        
        Returns:
            Human-readable diff report string
        """
        lines = []
        
        lines.append("="*70)
        lines.append("VALIDATION REPORT")
        lines.append("="*70)
        
        total = len(validation_results)
        passed = sum(1 for v in validation_results if v.is_match)
        failed = total - passed
        
        lines.append(f"\nSummary:")
        lines.append(f"  Total tests: {total}")
        lines.append(f"  Passed: {passed} ({passed/total*100:.1f}%)")
        lines.append(f"  Failed: {failed} ({failed/total*100:.1f}%)")
        lines.append("")
        
        # Details for failed tests
        if failed > 0:
            lines.append("Failed Tests:")
            lines.append("-"*70)
            
            for validation in validation_results:
                if not validation.is_match:
                    lines.append(f"\n❌ Test: {validation.test_case_id}")
                    lines.append(f"   {validation.get_summary()}")
                    
                    if validation.differences:
                        lines.append("   Differences:")
                        for diff in validation.differences:
                            lines.append(f"     • {diff}")
        
        lines.append("")
        lines.append("="*70)
        
        return '\n'.join(lines)

