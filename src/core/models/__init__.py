"""Core models"""
from .c_program import CProgram, CFunction, CVariable, CStruct, CEnum
from .dependency_graph import DependencyGraph, DependencyNode
from .test_case import TestCase, TestResult, TestSuite, ValidationResult
from .conversion_result import ConversionResult, MigrationReport, ConversionStatus

__all__ = [
    'CProgram',
    'CFunction',
    'CVariable',
    'CStruct',
    'CEnum',
    'DependencyGraph',
    'DependencyNode',
    'TestCase',
    'TestResult',
    'TestSuite',
    'ValidationResult',
    'ConversionResult',
    'MigrationReport',
    'ConversionStatus',
]

