#!/usr/bin/env python3
"""
Test runner script for MTG Collection Tool
Run this script to execute all unit tests
"""

import subprocess
import sys
import os

def run_tests():
    """Run all unit tests using pytest"""
    print("Running MTG Collection Tool Unit Tests...")
    print("=" * 50)
    
    # Ensure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'test_app.py',
            '-v',
            '--tb=short',
            '--durations=10'
        ], capture_output=False)
        
        if result.returncode == 0:
            print("\n" + "=" * 50)
            print("✅ All tests passed!")
        else:
            print("\n" + "=" * 50)
            print("❌ Some tests failed!")
            return False
            
    except FileNotFoundError:
        print("❌ Error: pytest not found. Please install test dependencies:")
        print("   pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False
    
    return True

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
