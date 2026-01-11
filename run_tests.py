#!/usr/bin/env python3
"""
Test runner for SolaGuard MCP Server.
"""

import subprocess
import sys
from pathlib import Path


def run_tests(test_type="unit"):
    """Run tests with proper configuration."""
    print(f"🧪 Running SolaGuard {test_type.title()} Tests...")
    
    if test_type == "unit":
        test_path = "tests/"
        exclude_pattern = "--ignore=tests/integration --ignore=tests/manual"
    elif test_type == "integration":
        test_path = "tests/integration/"
        exclude_pattern = ""
    elif test_type == "all":
        test_path = "tests/"
        exclude_pattern = "--ignore=tests/manual"
    else:
        print(f"❌ Unknown test type: {test_type}")
        return 1
    
    # Run pytest with coverage
    cmd = [
        "uv", "run", "pytest",
        test_path,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    if exclude_pattern:
        cmd.append(exclude_pattern)
    
    # Add coverage for unit tests
    if test_type in ["unit", "all"]:
        cmd.extend([
            "--cov=src/solaguard",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent, check=False)
        
        if result.returncode == 0:
            print(f"\n✅ All {test_type} tests passed!")
            if test_type in ["unit", "all"]:
                print("📊 Coverage report generated in htmlcov/")
        else:
            print(f"\n❌ {test_type.title()} tests failed with exit code {result.returncode}")
            
        return result.returncode
        
    except FileNotFoundError:
        print("❌ pytest not found. Make sure you have installed dev dependencies:")
        print("   uv sync --dev")
        return 1
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return 1


def run_quick_test():
    """Run quick manual test."""
    print("🚀 Running quick test...")
    
    cmd = ["uv", "run", "python", "tests/manual/test_quick_check.py"]
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent, check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running quick test: {e}")
        return 1


def run_specific_test(test_file):
    """Run a specific test file."""
    print(f"🧪 Running {test_file}...")
    
    # Find the test file
    test_path = None
    for search_dir in ["tests/", "tests/integration/", "tests/manual/"]:
        potential_path = Path(__file__).parent / search_dir / test_file
        if potential_path.exists():
            test_path = str(potential_path)
            break
    
    if not test_path:
        print(f"❌ Test file not found: {test_file}")
        return 1
    
    cmd = [
        "uv", "run", "pytest",
        test_path,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent, check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return 1


def print_usage():
    """Print usage information."""
    print("Usage: python run_tests.py [command]")
    print()
    print("Commands:")
    print("  unit         Run unit tests only (default)")
    print("  integration  Run integration tests only")
    print("  all          Run all tests")
    print("  quick        Run quick manual test")
    print("  <filename>   Run specific test file")
    print()
    print("Examples:")
    print("  python run_tests.py")
    print("  python run_tests.py unit")
    print("  python run_tests.py integration")
    print("  python run_tests.py all")
    print("  python run_tests.py quick")
    print("  python run_tests.py test_reference_parser.py")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command in ["unit", "integration", "all"]:
            exit_code = run_tests(command)
        elif command == "quick":
            exit_code = run_quick_test()
        elif command in ["help", "-h", "--help"]:
            print_usage()
            exit_code = 0
        else:
            # Assume it's a test file
            test_file = command
            if not test_file.startswith("test_"):
                test_file = f"test_{test_file}"
            if not test_file.endswith(".py"):
                test_file = f"{test_file}.py"
            
            exit_code = run_specific_test(test_file)
    else:
        # Default to unit tests
        exit_code = run_tests("unit")
    
    sys.exit(exit_code)