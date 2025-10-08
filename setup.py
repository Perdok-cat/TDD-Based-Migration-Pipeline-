"""
Setup script for C to C# Migration Pipeline
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="c-to-csharp-migration",
    version="1.0.0",
    description="TDD-based migration pipeline for C to C# conversion",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Migration System Team",
    author_email="",
    url="https://github.com/yourusername/c-to-csharp-migration",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.10",
    entry_points={
        "console_scripts": [
            "c2cs=main:cli",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Compilers",
    ],
    keywords="c csharp conversion migration tdd testing",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/c-to-csharp-migration/issues",
        "Source": "https://github.com/yourusername/c-to-csharp-migration",
        "Documentation": "https://c-to-csharp-migration.readthedocs.io",
    },
)

