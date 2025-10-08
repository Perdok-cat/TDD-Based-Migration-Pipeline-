"""
Test case models cho TDD-based migration
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import uuid


class TestStatus(Enum):
    """Trạng thái của test"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestCase:
    """Đại diện cho một test case"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    program_id: str = ""
    function_name: str = ""
    
    # Test data
    inputs: Dict[str, Any] = field(default_factory=dict)
    expected_outputs: Optional[Dict[str, Any]] = None
    actual_outputs: Optional[Dict[str, Any]] = None
    
    # Metadata
    description: str = ""
    category: str = "functional"  # functional, boundary, edge_case, random
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "program_id": self.program_id,
            "function_name": self.function_name,
            "inputs": self.inputs,
            "expected_outputs": self.expected_outputs,
            "actual_outputs": self.actual_outputs,
            "description": self.description,
            "category": self.category
        }


@dataclass
class TestResult:
    """Kết quả chạy test"""
    test_case_id: str
    status: TestStatus = TestStatus.PENDING
    success: bool = False
    error_message: Optional[str] = None
    
    # Outputs
    outputs: Dict[str, Any] = field(default_factory=dict)
    
    # Execution info
    execution_time: timedelta = field(default_factory=lambda: timedelta(0))
    standard_output: str = ""
    standard_error: str = ""
    exit_code: Optional[int] = None
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def mark_success(self, outputs: Dict[str, Any]) -> None:
        """Đánh dấu test passed"""
        self.status = TestStatus.PASSED
        self.success = True
        self.outputs = outputs
        self.completed_at = datetime.now()
    
    def mark_failure(self, error: str, outputs: Optional[Dict[str, Any]] = None) -> None:
        """Đánh dấu test failed"""
        self.status = TestStatus.FAILED
        self.success = False
        self.error_message = error
        if outputs:
            self.outputs = outputs
        self.completed_at = datetime.now()
    
    def mark_error(self, error: str) -> None:
        """Đánh dấu test error (compilation error, runtime error, etc.)"""
        self.status = TestStatus.ERROR
        self.success = False
        self.error_message = error
        self.completed_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_case_id": self.test_case_id,
            "status": self.status.value,
            "success": self.success,
            "error_message": self.error_message,
            "outputs": self.outputs,
            "execution_time_ms": self.execution_time.total_seconds() * 1000,
            "standard_output": self.standard_output,
            "standard_error": self.standard_error,
            "exit_code": self.exit_code
        }


@dataclass
class OutputDifference:
    """Sự khác biệt giữa outputs"""
    variable_name: str
    c_value: Any
    csharp_value: Any
    description: str = ""
    tolerance: Optional[float] = None
    is_critical: bool = True
    
    def __str__(self) -> str:
        return (
            f"{self.variable_name}: C={self.c_value} vs C#={self.csharp_value}"
            f"{' (within tolerance)' if not self.is_critical else ''}"
        )


@dataclass
class ValidationResult:
    """Kết quả validation giữa C và C# outputs"""
    test_case_id: str
    is_match: bool = False
    differences: List[OutputDifference] = field(default_factory=list)
    
    # Test results
    c_result: Optional[TestResult] = None
    csharp_result: Optional[TestResult] = None
    
    # Statistics
    total_outputs: int = 0
    matching_outputs: int = 0
    different_outputs: int = 0
    
    # Timestamps
    validated_at: datetime = field(default_factory=datetime.now)
    
    def calculate_match_percentage(self) -> float:
        """Tính % outputs matching"""
        if self.total_outputs == 0:
            return 0.0
        return (self.matching_outputs / self.total_outputs) * 100
    
    def has_critical_differences(self) -> bool:
        """Kiểm tra có differences nghiêm trọng không"""
        return any(diff.is_critical for diff in self.differences)
    
    def get_summary(self) -> str:
        """Tạo summary text"""
        if self.is_match:
            return f"✓ All outputs match ({self.total_outputs} values)"
        else:
            critical = sum(1 for d in self.differences if d.is_critical)
            return (
                f"✗ {len(self.differences)} differences found "
                f"({critical} critical) out of {self.total_outputs} outputs"
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_case_id": self.test_case_id,
            "is_match": self.is_match,
            "match_percentage": self.calculate_match_percentage(),
            "differences": [
                {
                    "variable_name": diff.variable_name,
                    "c_value": str(diff.c_value),
                    "csharp_value": str(diff.csharp_value),
                    "description": diff.description,
                    "is_critical": diff.is_critical
                }
                for diff in self.differences
            ],
            "c_result": self.c_result.to_dict() if self.c_result else None,
            "csharp_result": self.csharp_result.to_dict() if self.csharp_result else None,
            "summary": self.get_summary()
        }


@dataclass
class TestSuite:
    """Tập hợp các test cases cho một program/function"""
    program_id: str
    function_name: Optional[str] = None
    test_cases: List[TestCase] = field(default_factory=list)
    
    # Results
    test_results: Dict[str, TestResult] = field(default_factory=dict)
    validation_results: Dict[str, ValidationResult] = field(default_factory=dict)
    
    def add_test_case(self, test_case: TestCase) -> None:
        """Thêm test case"""
        self.test_cases.append(test_case)
    
    def get_test_by_id(self, test_id: str) -> Optional[TestCase]:
        """Lấy test case theo ID"""
        for tc in self.test_cases:
            if tc.id == test_id:
                return tc
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Thống kê test suite"""
        total = len(self.test_cases)
        passed = sum(1 for r in self.validation_results.values() if r.is_match)
        failed = sum(1 for r in self.validation_results.values() if not r.is_match)
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "completed": len(self.validation_results),
            "pending": total - len(self.validation_results)
        }

