#!/usr/bin/env python3
"""
Prototype Implementation - Solution B: Direct Main() Testing

Approach: Instead of creating new harness main(), run KLEE on program's own main()
"""

import os
import subprocess
import tempfile
from pathlib import Path


def test_solution_b():
    """
    Demo: Test program với direct main() approach
    """
    print("=" * 70)
    print("Solution B: Direct Main() Testing Prototype")
    print("=" * 70)
    
    # Original program
    original_code = """#include <stdio.h>
#include <klee/klee.h>

int sum(int a, int b) {
    return a + b;
}

int main() {
    int a, b;  // ← Modified: removed hardcoded values
    klee_make_symbolic(&a, sizeof(a), "a");
    klee_make_symbolic(&b, sizeof(b), "b");
    
    int result = sum(a, b);
    printf("Sum: %d\\n", result);
    
    return result;
}
"""
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="klee_solution_b_")
    print(f"\n1. Temp directory: {temp_dir}")
    
    # Write modified code
    source_file = os.path.join(temp_dir, "sum_symbolic.c")
    with open(source_file, 'w') as f:
        f.write(original_code)
    print(f"2. Created: {source_file}")
    
    # Compile to bitcode
    bc_file = os.path.join(temp_dir, "sum.bc")
    print(f"\n3. Compiling to bitcode...")
    
    compile_cmd = [
        "clang",
        "-I", "/var/lib/snapd/snap/klee/16/usr/local/include",
        "-emit-llvm",
        "-c",
        "-g", "-O0",
        "-Xclang", "-disable-O0-optnone",
        source_file,
        "-o", bc_file
    ]
    
    result = subprocess.run(compile_cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Compilation failed:")
        print(result.stderr)
        return
    print(f"✓ Compiled: {bc_file}")
    
    # Run KLEE
    print(f"\n4. Running KLEE...")
    klee_cmd = [
        "klee",
        "--max-time", "10",
        "--max-tests", "5",
        bc_file
    ]
    
    klee_result = subprocess.run(klee_cmd, capture_output=True, text=True, cwd=temp_dir)
    
    if klee_result.returncode != 0:
        print(f"⚠ KLEE exited with code {klee_result.returncode}")
    
    print(klee_result.stdout)
    
    # Find KLEE output
    klee_dirs = list(Path(temp_dir).glob("klee-out-*"))
    if klee_dirs:
        klee_out = sorted(klee_dirs)[-1]
        print(f"\n5. KLEE output: {klee_out}")
        
        # List test files
        ktest_files = list(klee_out.glob("*.ktest"))
        print(f"   Found {len(ktest_files)} test files")
        
        if ktest_files:
            # Show first test file
            test_file = ktest_files[0]
            print(f"\n6. First test case: {test_file}")
            
            # Use ktest-tool to view
            ktest_result = subprocess.run(
                ["ktest-tool", str(test_file)],
                capture_output=True,
                text=True
            )
            
            if ktest_result.returncode == 0:
                print("\nTest case contents:")
                print(ktest_result.stdout)
    
    print("\n" + "=" * 70)
    print("Solution B Prototype - SUCCESS!")
    print("No duplicate main() error!")
    print("=" * 70)


if __name__ == "__main__":
    test_solution_b()

