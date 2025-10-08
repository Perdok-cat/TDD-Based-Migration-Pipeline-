"""
Conversion result models
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ConversionStatus(Enum):
    """Trạng thái conversion"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class ConversionIssueType(Enum):
    """Loại issue trong conversion"""
    SYNTAX_ERROR = "syntax_error"
    TYPE_MISMATCH = "type_mismatch"
    UNSUPPORTED_FEATURE = "unsupported_feature"
    COMPILATION_ERROR = "compilation_error"
    RUNTIME_ERROR = "runtime_error"
    TEST_FAILURE = "test_failure"
    WARNING = "warning"


@dataclass
class ConversionIssue:
    """Vấn đề phát sinh trong quá trình conversion"""
    type: ConversionIssueType
    severity: str  # "error", "warning", "info"
    message: str
    source_location: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        loc = f" at {self.source_location}:{self.line_number}" if self.source_location else ""
        return f"[{self.severity.upper()}] {self.type.value}{loc}: {self.message}"


@dataclass
class ConversionMetrics:
    """Metrics cho một conversion"""
    lines_of_code_c: int = 0
    lines_of_code_csharp: int = 0
    functions_converted: int = 0
    functions_total: int = 0
    structs_converted: int = 0
    structs_total: int = 0
    
    # Complexity
    cyclomatic_complexity_c: float = 0.0
    cyclomatic_complexity_csharp: float = 0.0
    
    # Test metrics
    tests_total: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    test_pass_rate: float = 0.0
    
    # Time
    parsing_time_seconds: float = 0.0
    conversion_time_seconds: float = 0.0
    testing_time_seconds: float = 0.0
    total_time_seconds: float = 0.0
    
    def calculate_test_pass_rate(self) -> None:
        """Tính test pass rate"""
        if self.tests_total > 0:
            self.test_pass_rate = (self.tests_passed / self.tests_total) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "loc_c": self.lines_of_code_c,
            "loc_csharp": self.lines_of_code_csharp,
            "functions": f"{self.functions_converted}/{self.functions_total}",
            "structs": f"{self.structs_converted}/{self.structs_total}",
            "complexity_c": round(self.cyclomatic_complexity_c, 2),
            "complexity_csharp": round(self.cyclomatic_complexity_csharp, 2),
            "tests": {
                "total": self.tests_total,
                "passed": self.tests_passed,
                "failed": self.tests_failed,
                "pass_rate": round(self.test_pass_rate, 2)
            },
            "time": {
                "parsing": round(self.parsing_time_seconds, 2),
                "conversion": round(self.conversion_time_seconds, 2),
                "testing": round(self.testing_time_seconds, 2),
                "total": round(self.total_time_seconds, 2)
            }
        }


@dataclass
class ConversionResult:
    """Kết quả conversion của một C program"""
    program_id: str
    status: ConversionStatus = ConversionStatus.PENDING
    
    # Source and target
    source_file: str = ""
    target_file: str = ""
    
    # Code
    c_code: str = ""
    csharp_code: str = ""
    
    # Issues
    issues: List[ConversionIssue] = field(default_factory=list)
    
    # Metrics
    metrics: ConversionMetrics = field(default_factory=ConversionMetrics)
    
    # Timestamps
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Retry info
    retry_count: int = 0
    max_retries: int = 3
    
    def add_issue(
        self,
        issue_type: ConversionIssueType,
        severity: str,
        message: str,
        location: Optional[str] = None,
        line: Optional[int] = None,
        suggestion: Optional[str] = None
    ) -> None:
        """Thêm một issue"""
        issue = ConversionIssue(
            type=issue_type,
            severity=severity,
            message=message,
            source_location=location,
            line_number=line,
            suggestion=suggestion
        )
        self.issues.append(issue)
    
    def has_errors(self) -> bool:
        """Kiểm tra có errors không"""
        return any(issue.severity == "error" for issue in self.issues)
    
    def has_warnings(self) -> bool:
        """Kiểm tra có warnings không"""
        return any(issue.severity == "warning" for issue in self.issues)
    
    def get_error_count(self) -> int:
        """Đếm số errors"""
        return sum(1 for issue in self.issues if issue.severity == "error")
    
    def get_warning_count(self) -> int:
        """Đếm số warnings"""
        return sum(1 for issue in self.issues if issue.severity == "warning")
    
    def can_retry(self) -> bool:
        """Kiểm tra có thể retry không"""
        return self.retry_count < self.max_retries
    
    def mark_success(self) -> None:
        """Đánh dấu conversion thành công"""
        self.status = ConversionStatus.SUCCESS
        self.completed_at = datetime.now()
    
    def mark_failed(self, error_message: str) -> None:
        """Đánh dấu conversion failed"""
        self.status = ConversionStatus.FAILED
        self.add_issue(
            ConversionIssueType.SYNTAX_ERROR,
            "error",
            error_message
        )
        self.completed_at = datetime.now()
    
    def get_summary(self) -> str:
        """Tạo summary text"""
        errors = self.get_error_count()
        warnings = self.get_warning_count()
        
        if self.status == ConversionStatus.SUCCESS:
            summary = f"✓ Conversion successful"
            if warnings > 0:
                summary += f" ({warnings} warnings)"
        else:
            summary = f"✗ Conversion failed: {errors} errors"
            if warnings > 0:
                summary += f", {warnings} warnings"
        
        if self.metrics.test_pass_rate > 0:
            summary += f" | Tests: {self.metrics.test_pass_rate:.1f}% passed"
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "program_id": self.program_id,
            "status": self.status.value,
            "source_file": self.source_file,
            "target_file": self.target_file,
            "issues": {
                "errors": self.get_error_count(),
                "warnings": self.get_warning_count(),
                "details": [str(issue) for issue in self.issues]
            },
            "metrics": self.metrics.to_dict(),
            "retry_count": self.retry_count,
            "summary": self.get_summary()
        }


@dataclass
class MigrationReport:
    """Báo cáo tổng hợp cho toàn bộ migration"""
    total_programs: int = 0
    converted_programs: int = 0
    failed_programs: int = 0
    skipped_programs: int = 0
    
    # Conversion results
    conversion_results: List[ConversionResult] = field(default_factory=list)
    
    # Overall metrics
    total_loc_c: int = 0
    total_loc_csharp: int = 0
    total_functions: int = 0
    total_tests: int = 0
    total_tests_passed: int = 0
    
    # Time
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_seconds: float = 0.0
    
    def add_result(self, result: ConversionResult) -> None:
        """Thêm conversion result"""
        self.conversion_results.append(result)
        self.total_loc_c += result.metrics.lines_of_code_c
        self.total_loc_csharp += result.metrics.lines_of_code_csharp
        self.total_functions += result.metrics.functions_total
        self.total_tests += result.metrics.tests_total
        self.total_tests_passed += result.metrics.tests_passed
        
        if result.status == ConversionStatus.SUCCESS:
            self.converted_programs += 1
        elif result.status == ConversionStatus.FAILED:
            self.failed_programs += 1
        elif result.status == ConversionStatus.SKIPPED:
            self.skipped_programs += 1
    
    def calculate_success_rate(self) -> float:
        """Tính success rate"""
        if self.total_programs == 0:
            return 0.0
        return (self.converted_programs / self.total_programs) * 100
    
    def calculate_test_pass_rate(self) -> float:
        """Tính test pass rate"""
        if self.total_tests == 0:
            return 0.0
        return (self.total_tests_passed / self.total_tests) * 100
    
    def get_summary(self) -> str:
        """Tạo summary text"""
        success_rate = self.calculate_success_rate()
        test_pass_rate = self.calculate_test_pass_rate()
        
        return f"""
Migration Summary
=================
Programs: {self.converted_programs}/{self.total_programs} converted ({success_rate:.1f}%)
Failed: {self.failed_programs}
Functions: {self.total_functions}
Lines of Code: {self.total_loc_c} (C) → {self.total_loc_csharp} (C#)
Tests: {self.total_tests_passed}/{self.total_tests} passed ({test_pass_rate:.1f}%)
Duration: {self.total_duration_seconds:.2f} seconds
        """.strip()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "summary": {
                "total_programs": self.total_programs,
                "converted": self.converted_programs,
                "failed": self.failed_programs,
                "skipped": self.skipped_programs,
                "success_rate": round(self.calculate_success_rate(), 2),
                "test_pass_rate": round(self.calculate_test_pass_rate(), 2)
            },
            "metrics": {
                "total_loc_c": self.total_loc_c,
                "total_loc_csharp": self.total_loc_csharp,
                "total_functions": self.total_functions,
                "total_tests": self.total_tests,
                "total_tests_passed": self.total_tests_passed
            },
            "duration_seconds": round(self.total_duration_seconds, 2),
            "results": [result.to_dict() for result in self.conversion_results]
        }

