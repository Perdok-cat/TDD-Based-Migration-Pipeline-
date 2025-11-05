"""
KLEE Wrapper - Integration với KLEE symbolic execution engine
"""
import os
import subprocess
import tempfile
import logging
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from ..core.models.c_program import CFunction, CVariable


@dataclass
class KleeTestCase:
    """Một test case từ KLEE"""
    test_id: int
    inputs: Dict[str, Any]  # parameter_name -> value
    path_info: str = ""
    
    
class KleeWrapper:
    """
    Wrapper cho KLEE symbolic execution engine
    
    KLEE workflow:
    1. Generate test harness với klee_make_symbolic()
    2. Compile to LLVM bitcode với clang
    3. Run KLEE symbolic execution
    4. Parse .ktest files to extract test inputs
    """
    
    def __init__(self, timeout: int = 60, max_tests: int = 100, clang_path: str = "clang", klee_path: str = "klee", ktest_tool_path: str = "ktest-tool", extra_clang_args: Optional[List[str]] = None, extra_klee_args: Optional[List[str]] = None):
        """
        Initialize KLEE wrapper
        
        Args:
            timeout: Timeout cho KLEE execution (seconds)
            max_tests: Max số test cases KLEE generate
        """
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self.max_tests = max_tests
        self.temp_dir = None
        # Tooling
        self.clang_path = os.environ.get("CLANG_PATH", clang_path)
        self.klee_path = os.environ.get("KLEE_PATH", klee_path)
        self.ktest_tool_path = os.environ.get("KTEST_TOOL_PATH", ktest_tool_path)
        self.extra_clang_args = extra_clang_args or []
        self.extra_klee_args = extra_klee_args or []
        # Detect KLEE include directories (for klee/klee.h), allow override via env
        self.klee_include_dirs = self._detect_klee_include_dirs()
    
    def check_klee_available(self) -> bool:
        """Check xem KLEE có available không"""
        try:
            result = subprocess.run(
                [self.klee_path, "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                self.logger.info("✓ KLEE is available")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
            self.logger.warning("✗ KLEE not found")
        return False
    
    def generate_test_cases(
        self,
        function: CFunction,
        source_code: str,
        includes: List[str] = None,
        include_dirs: Optional[List[str]] = None
    ) -> List[KleeTestCase]:
        """
        Generate test cases cho function bằng KLEE
        
        Args:
            function: CFunction to test
            source_code: Original C source code
            includes: Additional includes needed
            
        Returns:
            List of KleeTestCase objects
        """
        if not self.check_klee_available():
            self.logger.warning("KLEE not available, returning empty test list")
            return []
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(prefix="klee_")
        self.logger.info(f"KLEE temp dir: {self.temp_dir}")
        
        try:
            # Step 1: Generate KLEE harness
            harness_code = self._generate_klee_harness(function, source_code, includes)
            harness_file = os.path.join(self.temp_dir, "harness.c")
            with open(harness_file, 'w') as f:
                f.write(harness_code)
            # Write original source to temp so we can link implementation
            # REMOVE main() to avoid duplicate symbol error
            orig_code_clean = self._remove_main_function(source_code)
            orig_file = os.path.join(self.temp_dir, "orig.c")
            with open(orig_file, 'w') as f:
                f.write(orig_code_clean)
            
            # Step 2: Compile to LLVM bitcode
            bc_file = self._compile_to_bitcode(harness_file, orig_file, include_dirs or [])
            if not bc_file:
                return []
            
            # Step 3: Run KLEE
            klee_out_dir = self._run_klee(bc_file)
            if not klee_out_dir:
                return []
            
            # Step 4: Parse KLEE output (.ktest files)
            test_cases = self._parse_klee_outputs(klee_out_dir, function)
            
            self.logger.info(f"✓ KLEE generated {len(test_cases)} test cases")
            return test_cases
            
        except Exception as e:
            self.logger.error(f"KLEE execution failed: {e}")
            return []
        
        finally:
            # Cleanup temp files (optional - keep for debugging)
            # import shutil
            # shutil.rmtree(self.temp_dir, ignore_errors=True)
            pass
    
    def _generate_klee_harness(
        self,
        function: CFunction,
        source_code: str,
        includes: List[str] = None
    ) -> str:
        """Generate KLEE test harness"""
        lines = []
        
        # Include KLEE headers
        lines.append("#include <klee/klee.h>")
        lines.append("#include <assert.h>")
        lines.append("#include <stdio.h>")
        lines.append("#include <stdlib.h>")
        lines.append("")
        
        # Additional includes
        if includes:
            for inc in includes:
                lines.append(f'#include "{inc}"')
            lines.append("")
        
        # Original source code (if function definition not in headers)
        # For now, assume function is declared/defined elsewhere
        # In production, might need to include actual implementation
        
        # Function declaration (if not in includes)
        param_decls = ', '.join(
            f"{p.data_type}{'*' * p.pointer_level} {p.name}"
            for p in function.parameters
        )
        lines.append(f"// Function under test")
        lines.append(f"{function.return_type} {function.name}({param_decls});")
        lines.append("")
        
        # Main function with symbolic execution
        lines.append("int main(void) {")
        
        # Declare variables; for pointers, allocate small buffers to avoid invalid deref
        for param in function.parameters:
            param_type = param.data_type + ('*' * param.pointer_level)
            if getattr(param, 'pointer_level', 0) > 0 or getattr(param, 'is_pointer', False):
                base_type = param.data_type
                buf_name = f"{param.name}_buf"
                lines.append(f"    {base_type} {buf_name}[8];")
                lines.append(f"    {param_type} {param.name} = ({param_type}){buf_name};")
            else:
                lines.append(f"    {param_type} {param.name};")
        
        lines.append("")
        
        # Make variables symbolic (for pointers, make buffer symbolic)
        for param in function.parameters:
            if getattr(param, 'pointer_level', 0) > 0 or getattr(param, 'is_pointer', False):
                lines.append(
                    f'    klee_make_symbolic({param.name}, sizeof(*{param.name}) * 8, "{param.name}");'
                )
            else:
                lines.append(
                    f'    klee_make_symbolic(&{param.name}, sizeof({param.name}), "{param.name}");'
                )
        
        lines.append("")
        
        # Add constraints (optional - can add domain constraints here)
        # Example: klee_assume(b != 0); for division
        
        # Call function under test
        if function.return_type.lower() != 'void':
            lines.append(f"    {function.return_type} result = {function.name}(")
        else:
            lines.append(f"    {function.name}(")
        
        param_names = ', '.join(p.name for p in function.parameters)
        lines.append(f"        {param_names}")
        lines.append("    );")
        
        lines.append("")
        lines.append("    return 0;")
        lines.append("}")
        
        return '\n'.join(lines)
    
    def _compile_to_bitcode(self, harness_file: str, orig_file: str, include_dirs: List[str]) -> Optional[str]:
        """Compile harness and original C code to a single LLVM bitcode"""
        bc_file = os.path.join(os.path.dirname(harness_file), "combined.bc")
        
        try:
            # First compile each file separately to bitcode
            harness_bc = os.path.join(os.path.dirname(harness_file), "harness.bc")
            orig_bc = os.path.join(os.path.dirname(harness_file), "orig.bc")
            
            # Compile harness file
            harness_cmd = [
                self.clang_path,
                "-emit-llvm",
                "-c",  # Compile only, don't link
                "-g",
                "-O0",
                "-Xclang", "-disable-O0-optnone",
            ]
            # Add detected KLEE include dirs
            for inc in self.klee_include_dirs:
                harness_cmd.extend(["-I", inc])
            # Include dirs from caller
            for inc in include_dirs:
                harness_cmd.extend(["-I", inc])
            # Extra user-provided args
            harness_cmd.extend(self.extra_clang_args)
            # Input source and output
            harness_cmd.extend([harness_file, "-o", harness_bc])
            
            # Compile original file
            orig_cmd = [
                self.clang_path,
                "-emit-llvm",
                "-c",  # Compile only, don't link
                "-g",
                "-O0",
                "-Xclang", "-disable-O0-optnone",
            ]
            # Add detected KLEE include dirs (in case orig.c needs klee headers)
            for inc in self.klee_include_dirs:
                orig_cmd.extend(["-I", inc])

    


            # Include dirs from caller
            for inc in include_dirs:
                orig_cmd.extend(["-I", inc])
            # Extra user-provided args
            orig_cmd.extend(self.extra_clang_args)
            # Input source and output
            orig_cmd.extend([orig_file, "-o", orig_bc])
            
            # Compile harness
            result1 = subprocess.run(
                harness_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result1.returncode != 0:
                self.logger.error(f"Harness compilation failed: {result1.stderr}")
                return None
            
            # Compile original file
            result2 = subprocess.run(
                orig_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result2.returncode != 0:
                self.logger.error(f"Original file compilation failed: {result2.stderr}")
                return None
            
            # Now link the bitcode files together
            link_cmd = [
                "llvm-link",
                harness_bc,
                orig_bc,
                "-o", bc_file
            ]
            
            # Link the bitcode files
            link_result = subprocess.run(
                link_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if link_result.returncode == 0:
                self.logger.info(f"✓ Compiled to bitcode: {bc_file}")
                # Clean up intermediate files
                try:
                    os.remove(harness_bc)
                    os.remove(orig_bc)
                except OSError:
                    pass  # Ignore cleanup errors
                return bc_file
            else:
                self.logger.error(f"Bitcode linking failed: {link_result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("Compilation timeout")
            return None
        except FileNotFoundError as e:
            if "clang" in str(e):
                self.logger.error("clang not found. Install: sudo apt-get install clang")
            elif "llvm-link" in str(e):
                self.logger.error("llvm-link not found. Install: sudo apt-get install llvm")
            else:
                self.logger.error(f"Tool not found: {e}")
            return None

    def _detect_klee_include_dirs(self) -> List[str]:
        """Detect possible include directories that contain klee/klee.h."""
        # Highest priority: explicit env var
        env_dir = os.environ.get("KLEE_INCLUDE_DIR")
        candidates: List[str] = []
        if env_dir:
            candidates.append(env_dir)
        # Common install locations inside Docker image or native install
        candidates.extend([
            "/usr/local/include",
            "/usr/include",
            "/opt/homebrew/include",  # macOS Homebrew (if ever used)
        ])
        # Deduplicate and only keep existing paths
        seen = set()
        result: List[str] = []
        for path in candidates:
            if path and path not in seen and os.path.isdir(path):
                # Quick check for header
                if os.path.exists(os.path.join(path, "klee", "klee.h")):
                    result.append(path)
                else:
                    # Still add base include; user may provide includes explicitly
                    result.append(path)
                seen.add(path)
        return result
    
    def _run_klee(self, bc_file: str) -> Optional[str]:
        """Run KLEE on bitcode"""
        try:
            # Use relative path with cwd set to temp_dir to avoid Snap confinement issues
            bc_filename = os.path.basename(bc_file)
            
            cmd = [
                self.klee_path,
                "--optimize",
                "--max-time", str(self.timeout),
                "--max-tests", str(self.max_tests),
                "--libc=uclibc",
                "--posix-runtime",
            ]
            # Extra KLEE args if any
            cmd.extend(self.extra_klee_args)
            cmd.append(bc_filename)
            
            self.logger.info(f"Running KLEE: {' '.join(cmd)}")
            self.logger.info(f"Working directory: {self.temp_dir}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout + 10,
                cwd=self.temp_dir
            )
            
            # Log KLEE output for debugging
            if result.stdout:
                self.logger.debug(f"KLEE stdout:\n{result.stdout}")
            if result.stderr:
                self.logger.debug(f"KLEE stderr:\n{result.stderr}")
            
            # Log return code
            self.logger.info(f"KLEE exit code: {result.returncode}")
            
            # KLEE output dir is usually klee-out-0, klee-out-1, etc.
            klee_dirs = list(Path(self.temp_dir).glob("klee-out-*"))
            if klee_dirs:
                klee_out_dir = str(sorted(klee_dirs)[-1])  # Latest
                # Check if directory has any .ktest files
                ktest_files = list(Path(klee_out_dir).glob("*.ktest"))
                self.logger.info(f"✓ KLEE completed: {klee_out_dir} ({len(ktest_files)} test cases)")
                return klee_out_dir
            else:
                self.logger.error("✗ KLEE output directory not found")
                self.logger.error(f"  KLEE may have failed to execute properly")
                self.logger.error(f"  stdout: {result.stdout[:500] if result.stdout else '(empty)'}")
                self.logger.error(f"  stderr: {result.stderr[:500] if result.stderr else '(empty)'}")
                # List all files in temp_dir for debugging
                try:
                    temp_files = list(Path(self.temp_dir).iterdir())
                    self.logger.error(f"  Files in temp dir: {[f.name for f in temp_files]}")
                except Exception as e:
                    self.logger.error(f"  Could not list temp dir: {e}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.warning(f"KLEE timeout after {self.timeout}s")
            # Still try to parse partial results
            klee_dirs = list(Path(self.temp_dir).glob("klee-out-*"))
            if klee_dirs:
                return str(sorted(klee_dirs)[-1])
            return None
        except Exception as e:
            self.logger.error(f"KLEE execution error: {e}")
            return None
    
    def _parse_klee_outputs(
        self,
        klee_out_dir: str,
        function: CFunction
    ) -> List[KleeTestCase]:
        """Parse KLEE .ktest files"""
        test_cases = []
        
        # Find all .ktest files
        ktest_files = list(Path(klee_out_dir).glob("*.ktest"))
        
        for idx, ktest_file in enumerate(ktest_files, 1):
            try:
                inputs = self._parse_ktest_file(str(ktest_file), function)
                if inputs:
                    test_case = KleeTestCase(
                        test_id=idx,
                        inputs=inputs,
                        path_info=f"KLEE path {idx}"
                    )
                    test_cases.append(test_case)
            except Exception as e:
                self.logger.warning(f"Failed to parse {ktest_file}: {e}")
        
        return test_cases
    
    def _parse_ktest_file(
        self,
        ktest_file: str,
        function: CFunction
    ) -> Optional[Dict[str, Any]]:
        """
        Parse KLEE .ktest file to extract input values
        
        Note: This uses ktest-tool from KLEE
        """
        try:
            # Use ktest-tool to dump ktest file
            result = subprocess.run(
                [self.ktest_tool_path, ktest_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                return None
            
            # Parse ktest-tool output
            inputs = {}
            lines = result.stdout.split('\n')
            
            current_obj = None
            for line in lines:
                line = line.strip()
                
                # Object name (variable name)
                if line.startswith("object"):
                    parts = line.split("'")
                    if len(parts) >= 2:
                        current_obj = parts[1]
                
                # Object data (hex bytes)
                if line.startswith("hex") and current_obj:
                    hex_part = line.split(':')[1].strip()
                    hex_bytes = hex_part.replace('0x', '').replace(' ', '')
                    
                    # Convert hex to value based on parameter type
                    param = next((p for p in function.parameters if p.name == current_obj), None)
                    if param:
                        value = self._hex_to_value(hex_bytes, param.data_type)
                        inputs[current_obj] = value
                    
                    current_obj = None
            
            return inputs if inputs else None
            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.logger.warning(f"ktest-tool error: {e}")
            return None
    
    def _hex_to_value(self, hex_str: str, data_type: str) -> Any:
        """Convert hex string to typed value"""
        try:
            # Convert hex string to bytes
            byte_data = bytes.fromhex(hex_str)
            
            # Unpack based on type
            data_type_lower = data_type.lower()
            
            if 'int' in data_type_lower:
                if 'unsigned' in data_type_lower:
                    return struct.unpack('I', byte_data[:4])[0] if len(byte_data) >= 4 else 0
                else:
                    return struct.unpack('i', byte_data[:4])[0] if len(byte_data) >= 4 else 0
            
            elif 'long' in data_type_lower:
                if 'unsigned' in data_type_lower:
                    return struct.unpack('Q', byte_data[:8])[0] if len(byte_data) >= 8 else 0
                else:
                    return struct.unpack('q', byte_data[:8])[0] if len(byte_data) >= 8 else 0
            
            elif 'short' in data_type_lower:
                if 'unsigned' in data_type_lower:
                    return struct.unpack('H', byte_data[:2])[0] if len(byte_data) >= 2 else 0
                else:
                    return struct.unpack('h', byte_data[:2])[0] if len(byte_data) >= 2 else 0
            
            elif 'char' in data_type_lower:
                if 'unsigned' in data_type_lower:
                    return struct.unpack('B', byte_data[:1])[0] if len(byte_data) >= 1 else 0
                else:
                    return struct.unpack('b', byte_data[:1])[0] if len(byte_data) >= 1 else 0
            
            elif 'float' in data_type_lower:
                return struct.unpack('f', byte_data[:4])[0] if len(byte_data) >= 4 else 0.0
            
            elif 'double' in data_type_lower:
                return struct.unpack('d', byte_data[:8])[0] if len(byte_data) >= 8 else 0.0
            
            else:
                # Default: return as integer
                return int(hex_str, 16) if hex_str else 0
                
        except Exception as e:
            self.logger.warning(f"Failed to convert hex {hex_str} to {data_type}: {e}")
            return 0
    
    def _get_type_size(self, data_type: str) -> int:
        """Get size of C type in bytes"""
        data_type_lower = data_type.lower()
        
        if 'char' in data_type_lower:
            return 1
        elif 'short' in data_type_lower:
            return 2
        elif 'int' in data_type_lower:
            return 4
        elif 'long' in data_type_lower:
            return 8
        elif 'float' in data_type_lower:
            return 4
        elif 'double' in data_type_lower:
            return 8
        else:
            return 4  # Default
    
    def _remove_main_function(self, source_code: str) -> str:
        """
        Remove main() function from source code to avoid duplicate symbol error.
        
        Simple approach: Remove the main() function definition.
        This assumes main() is at the end and has standard format.
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
                    continue
            
            if not in_main:
                filtered_lines.append(line)
        
        result = '\n'.join(filtered_lines)
        
        # Remove multiple blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        return result

